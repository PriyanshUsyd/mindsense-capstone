"""
Builds a REAL `EvidencePacket` for one participant, feature, and "as-of"
date — the integration glue that was missing between the tested statistics
modules (`backend.statistics.eligibility.classify_state`,
`backend.statistics.evidence`) and the request-handling path
(`backend/api/app.py`'s `/respond`).

CONTEXT (2026-09-16): `/respond` previously accepted a client-supplied
`EvidencePacket` as-is (schema validation only) and never called any of
this package's classification logic — `NormalResponse.tsx` sent the same
hardcoded `EXAMPLE_ELIGIBLE_GPS_PACKET` on every request, so `classify_state`
and `evidence.py` were exercised only by tests, never by a real request.
This module closes that gap. It is an INTEGRATION task, not a statistics-
methodology task: every classification decision below calls into Moe
Tanaka's existing, tested modules (`eligibility.py`, `evidence.py`,
`mixed_effects_model.py`) unchanged; this file only assembles their real
outputs into the frozen `EvidencePacket` contract. The one place this
module makes its own call (see `_claim_policy_for` for State C / no_claim)
is flagged explicitly below, not silently invented.

Cold-start gate inputs (spec §4.3, `eligibility.classify_state`):
`calendar_days` / `valid_sensor_days` / `ema_count` are each participant's
CUMULATIVE history up to `as_of` (days since their first sensing row;
total valid sensor-days and EMA responses ever recorded) — not a fixed
trailing window. This matches CLAUDE.md's "cold-start applies per
evaluation opportunity; State C does not persist": recomputing these counts
fresh at a different `as_of` for the same participant can yield a
different state, by design.

The descriptive `FeatureWindow` (what value is actually reported) and the
comparison `PersonalBaseline` use CLAUDE.md's locked windows instead:
comparison window `[-14, -1]` relative to `as_of`, baseline window
`[-42, -15]`.

Per-person `evidence_strength` (Section 7) goes through
`evidence.extract_person_slopes` + `evidence.reclassify_family213`
UNCHANGED, using the non-bootstrapped SE (`slope_se=None`). This means
`evidence_strength` resolves to `insufficient` (-> `no_claim`) for every
participant here, REGARDLESS of the real AR(1) fit's point estimate.

**UPDATED 2026-09-16, after rebasing onto Moe's PR #20/#21:** the SE gap
above is no longer an open methodology question — `backend.statistics
.bootstrap` (parametric + cluster, B=500 replicates each) plus
`evidence.intersect_bootstrap_evidence` is now the real, confirmed,
production-intended per-person classification (23/214 participants
`evidence_available` under intersection on the real dataset — see
`evidence.py`'s module docstring and `docs/statistics/preregistration.md`
section 4.1). This module deliberately does NOT call that path yet: B=500
per method costs ~30-40 minutes per feature (`tier1_runner.py`'s
docstring), which is an offline/batch computation, not something a
request-serving process can run lazily on first request the way this
module's existing `_evidence_table()` does for the cheap (non-bootstrap)
fit. Wiring the real intersection result into `/respond` needs a
precomputed/cached per-participant table (e.g. a batch job writing
`bootstrap`'s output somewhere `build_evidence_packet` can look it up),
which is a real follow-up, not done here — flagged rather than either
silently left stale or hastily bolted on as a slow first-request path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from backend.contracts.evidence import (
    ApprovedClaimId,
    ClaimPolicy,
    Direction,
    EligibilityStatus,
    EvidencePacket,
    EvidenceStrength,
    FeatureWindow,
    PacketIdentity,
    PersonalBaseline,
    Platform,
    ProhibitedClaimId,
    ResponseMode,
    StatisticalEvidence,
    UncertaintyReasons,
)
from backend.data_pipeline.ces_eligibility import make_pseudonymizer
from backend.statistics import evidence as evidence_module
from backend.statistics import r_bridge
from backend.statistics.eligibility import (
    ColdStartState,
    classify_state,
    to_eligibility_status,
)
from backend.statistics.feature_specs import (
    GPS_DISTANCE_SPEC,
    UNLOCK_FREQUENCY_SPEC,
    FeatureSpec,
)
from backend.statistics.mixed_effects_model import build_model_frame, fit_ar1_effect

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
LOCAL_DEMO_PARTICIPANT_ALIAS = "local-demo"

# CLAUDE.md "Finalised decisions": comparison window [-14, -1], baseline
# window [-42, -15] (the narrower of the two locked options; [-70, -15] is
# the wider alternative, not used here — see module docstring).
COMPARISON_WINDOW_DAYS = 14
BASELINE_WINDOW_DAYS = 28
BASELINE_GAP_DAYS = 15  # baseline window ends this many days before as_of

# Never invented: the same salt-per-process pseudonymisation rule
# ces_eligibility.py already uses (participant_ref must never be the raw
# CES uid — skills/privacy-security.md). Fixed once at import so repeated
# requests for the same participant within one process get the same
# pseudonym; never persisted or reused across process restarts.
_pseudonymize = make_pseudonymizer()

@dataclass(frozen=True)
class _FeatureMeta:
    spec: FeatureSpec
    unit: str
    value_scale: float
    load_cols: tuple[str, ...]


_FEATURES: dict[str, _FeatureMeta] = {
    # `unit` / `value_scale` deliberately match the exact strings
    # `backend/slm/output_grounding.py::_LABELS` recognises — that frozen
    # grammar fails closed (falls back, never generates text) on any other
    # spelling. DISCOVERED WIRING THIS UP: the statistics side's own
    # internal name for the second Tier-1 feature is `unlock_num_ep_0`
    # (`feature_specs.UNLOCK_FREQUENCY_SPEC.name`) and its raw unit is a
    # plain count — neither matches output_grounding.py's "unlock_count" /
    # "count_per_day" pairing, a naming drift between the two sides that
    # was invisible until a packet for that feature was actually run
    # through real text generation for the first time. This module's
    # public `feature_id` (the dict key) is deliberately the SLM-side
    # name; `spec` still points at the real statistics-side FeatureSpec.
    "gps_distance": _FeatureMeta(
        spec=GPS_DISTANCE_SPEC,
        unit="kilometres_per_day",
        value_scale=1.0 / 1000.0,  # cleaned values are in metres
        load_cols=("uid", "day", "quality_loc", "loc_dist_ep_0", "is_ios"),
    ),
    "unlock_count": _FeatureMeta(
        spec=UNLOCK_FREQUENCY_SPEC,
        unit="count_per_day",
        value_scale=1.0,
        load_cols=("uid", "day", "unlock_num_ep_0", "is_ios"),
    ),
}


class UnknownParticipant(ValueError):
    """Raised when `participant_id` has no rows in the real sensing dataset."""


class UnknownFeature(ValueError):
    """Raised for a `feature_id` this module does not know how to build."""


def _to_date(day_value: int) -> date:
    value = str(day_value)
    return date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def _load_cleaned_sensing(feature_id: str) -> pd.DataFrame:
    meta = _FEATURES[feature_id]
    df = pd.read_csv(DATASET_DIR / "Sensing" / "sensing.csv", usecols=list(meta.load_cols))
    df = df.sort_values(["uid", "day"]).reset_index(drop=True)
    return meta.spec.clean_fn(df)


_CLEANED_SENSING_CACHE: dict[str, pd.DataFrame] = {}
_EMA_CACHE: pd.DataFrame | None = None
_EVIDENCE_TABLE_CACHE: dict[str, pd.DataFrame | None] = {}


def _cleaned_sensing(feature_id: str) -> pd.DataFrame:
    if feature_id not in _FEATURES:
        raise UnknownFeature(f"unknown feature_id {feature_id!r}, expected one of {sorted(_FEATURES)}")
    if feature_id not in _CLEANED_SENSING_CACHE:
        _CLEANED_SENSING_CACHE[feature_id] = _load_cleaned_sensing(feature_id)
    return _CLEANED_SENSING_CACHE[feature_id]


def _ema() -> pd.DataFrame:
    global _EMA_CACHE
    if _EMA_CACHE is None:
        _EMA_CACHE = pd.read_csv(
            DATASET_DIR / "EMA" / "general_ema.csv", usecols=["uid", "day", "phq4_score"]
        ).dropna(subset=["phq4_score"])
    return _EMA_CACHE


def select_local_demo_participant(feature_id: str = "gps_distance") -> str:
    """Choose a deterministic local participant without publishing a raw UID.

    The browser sends :data:`LOCAL_DEMO_PARTICIPANT_ALIAS`; only the backend
    resolves that alias. Selection favours the participant with the most valid
    feature days and EMA observations so the local demonstration has a useful
    evidence window. The raw identifier remains process-local and is never
    returned by the API.
    """
    cleaned = _cleaned_sensing(feature_id)
    meta = _FEATURES[feature_id]
    sensor_counts = (
        cleaned.groupby("uid")[meta.spec.value_col]
        .count()
        .rename("valid_sensor_days")
    )
    ema_counts = _ema().groupby("uid")["phq4_score"].count().rename("ema_count")
    candidates = sensor_counts.to_frame().join(ema_counts, how="inner")
    candidates = candidates[
        (candidates["valid_sensor_days"] > 0) & (candidates["ema_count"] > 0)
    ].copy()
    if candidates.empty:
        raise UnknownParticipant(
            f"no local demo participant is available for feature_id {feature_id!r}"
        )

    candidates = candidates.reset_index()
    candidates["uid"] = candidates["uid"].astype(str)
    candidates = candidates.sort_values(
        ["valid_sensor_days", "ema_count", "uid"],
        ascending=[False, False, True],
    )
    return str(candidates.iloc[0]["uid"])


def _evidence_table(feature_id: str) -> pd.DataFrame | None:
    """Per-person `evidence.reclassify_family213` table for `feature_id`,
    computed once per process and cached — this is a cohort-wide model fit
    (spec §1.2-1.7), not something to redo per HTTP request.

    Returns `None` when the real R engine
    (`backend.statistics.r_bridge.r_bridge_available()`) is not usable in
    this process: `evidence.extract_person_slopes` requires real per-person
    BLUPs, which only the R engine produces (see `mixed_effects_model.py`'s
    `Ar1EffectResult.blups` docstring) — the Python GEE fallback is
    population-averaged and has none. Rather than run an expensive cohort
    GEE fit whose only possible outcome is "cannot classify" in that case,
    this is skipped outright and reported honestly via the packet's
    `uncertainty.item_level`.
    """
    if feature_id in _EVIDENCE_TABLE_CACHE:
        return _EVIDENCE_TABLE_CACHE[feature_id]

    if not r_bridge.r_bridge_available():
        _EVIDENCE_TABLE_CACHE[feature_id] = None
        return None

    meta = _FEATURES[feature_id]
    cleaned = _cleaned_sensing(feature_id)
    frame = build_model_frame(cleaned, _ema(), feature_spec=meta.spec)
    ar1 = fit_ar1_effect(frame)
    if ar1.blups is None:
        _EVIDENCE_TABLE_CACHE[feature_id] = None
        return None

    person_slopes = evidence_module.extract_person_slopes(ar1, frame)
    outcome_sd = float(frame["phq4_score"].std())
    predictor_sd = float(frame["x_within"].std())
    table = evidence_module.reclassify_family213(person_slopes, outcome_sd, predictor_sd)
    table = table.set_index("uid")
    _EVIDENCE_TABLE_CACHE[feature_id] = table
    return table


@dataclass
class _ClaimPolicyChoice:
    approved: tuple[ApprovedClaimId, ...]
    response_modes: tuple[ResponseMode, ...]


def _claim_policy_for(
    eligibility_status: EligibilityStatus, user_facing_evidence: str | None
) -> _ClaimPolicyChoice:
    """Maps a real classification outcome to a `ClaimPolicy`. Every branch
    mirrors the canonical mappings already agreed and tested in
    `tests/integration/test_end_to_end_evidence_flow.py`.

    `eligibility_status` is only ever `ELIGIBLE` here when `build_evidence_packet`
    also attached real `StatisticalEvidence` — `backend/slm/response_health.py`
    enforces that pairing as a hard invariant (see that discovery noted in
    `build_evidence_packet`'s State C branch), so "ELIGIBLE with no
    evidence" never reaches this function; the `else` below is a defensive
    fallback, not a reachable real case.
    """
    if eligibility_status in (
        EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
        EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE,
    ):
        return _ClaimPolicyChoice(
            approved=(ApprovedClaimId.NOT_ENOUGH_DATA,),
            response_modes=(ResponseMode.INSUFFICIENT_DATA,),
        )
    if eligibility_status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY:
        return _ClaimPolicyChoice(
            approved=(
                ApprovedClaimId.TREND_DESCRIPTION,
                ApprovedClaimId.NOT_ENOUGH_DATA,
                ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
                ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,
            ),
            response_modes=(ResponseMode.UNCERTAINTY,),
        )
    # ELIGIBLE (State C)
    if user_facing_evidence == "evidence_available":
        return _ClaimPolicyChoice(
            approved=(
                ApprovedClaimId.OBSERVATION_OF_DEVIATION,
                ApprovedClaimId.WITHIN_PERSON_ASSOCIATION,
                ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
                ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,
            ),
            response_modes=(ResponseMode.NORMAL,),
        )
    return _ClaimPolicyChoice(
        approved=(
            ApprovedClaimId.OBSERVATION_OF_DEVIATION,
            ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
            ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,
        ),
        response_modes=(ResponseMode.UNCERTAINTY,),
    )


def build_evidence_packet(
    participant_id: str,
    feature_id: str = "gps_distance",
    as_of: date | None = None,
) -> EvidencePacket:
    """Builds a REAL `EvidencePacket` for `participant_id` from the actual
    CES pipeline output — the function `/respond` calls instead of trusting
    a client-supplied packet.

    `as_of` defaults to the last calendar day this participant actually has
    a sensing row for (this is retrospective study data, not a live
    stream — there is no "now" otherwise). Raises `UnknownParticipant` if
    `participant_id` has no sensing rows at all.
    """
    cleaned = _cleaned_sensing(feature_id)
    meta = _FEATURES[feature_id]
    clean_col = meta.spec.value_col

    person = cleaned[cleaned["uid"] == participant_id]
    if person.empty:
        raise UnknownParticipant(f"no sensing rows for participant_id {participant_id!r}")

    person = person.copy()
    person["date"] = person["day"].apply(_to_date)
    person = person.sort_values("date")

    if as_of is None:
        as_of = person["date"].max()

    history = person[person["date"] <= as_of]
    first_day = history["date"].min()
    calendar_days = (as_of - first_day).days + 1
    valid_sensor_days = int(history[clean_col].notna().sum())

    ema_rows = _ema()
    person_ema = ema_rows[ema_rows["uid"] == participant_id].copy()
    person_ema["date"] = person_ema["day"].apply(_to_date)
    person_ema = person_ema[person_ema["date"] <= as_of]
    ema_count = len(person_ema)

    state = classify_state(calendar_days, valid_sensor_days, ema_count)
    eligibility_status = to_eligibility_status(state)

    platform = Platform.IOS if int(person["is_ios"].iloc[0]) == 1 else Platform.ANDROID

    comparison_end = as_of
    comparison_start = as_of - timedelta(days=COMPARISON_WINDOW_DAYS - 1)
    comparison_rows = history[
        (history["date"] >= comparison_start) & (history["date"] <= comparison_end)
    ]
    comparison_values = comparison_rows[clean_col].dropna()
    observed_days = len(comparison_values)
    value_scale = meta.value_scale
    feature_value = float(comparison_values.mean()) * value_scale if observed_days > 0 else 0.0

    feature_window = FeatureWindow(
        feature_id=feature_id,
        unit=meta.unit,
        window_start=comparison_start,
        window_end=comparison_end,
        value=feature_value,
        observed_days=observed_days,
        expected_days=COMPARISON_WINDOW_DAYS,
        coverage_ratio=observed_days / COMPARISON_WINDOW_DAYS,
        platform=platform,
        quality_flags=() if observed_days > 0 else ("no_valid_days_in_comparison_window",),
    )

    baseline_end = as_of - timedelta(days=BASELINE_GAP_DAYS)
    baseline_start = baseline_end - timedelta(days=BASELINE_WINDOW_DAYS - 1)

    user_facing_evidence: str | None = None
    statistical_evidence: StatisticalEvidence | None = None
    uncertainty_items: list[str] = []

    if state == ColdStartState.A_INSUFFICIENT_DATA:
        baseline = PersonalBaseline(
            method="n/a — State A",
            value=None,
            n_baseline_observations=0,
            eligibility_status=eligibility_status,
            ineligible_reason="below Moe's State B floor (7 calendar days / 5 valid sensor-days / 1 EMA)",
        )
        uncertainty_items.append("no history yet")

    elif state == ColdStartState.B_PARTIAL_HISTORY:
        baseline = PersonalBaseline(
            method="n/a — State B, too early for a baseline",
            value=None,
            n_baseline_observations=ema_count,
            eligibility_status=eligibility_status,
            ineligible_reason="below Moe's State C floor (28 calendar days / 20 valid sensor-days / 3 EMAs)",
        )
        uncertainty_items.append("too early to compare")

    else:  # State C (cold-start says comparison is data-sufficient)
        baseline_rows = history[
            (history["date"] >= baseline_start) & (history["date"] <= baseline_end)
        ]
        baseline_values = baseline_rows[clean_col].dropna()
        n_baseline = len(baseline_values)

        evidence_label: str | None = None
        if n_baseline > 0:
            table = _evidence_table(feature_id)
            if table is None:
                evidence_label = None
                uncertainty_items.append(
                    "per-person evidence-strength classification requires the real R "
                    "engine (backend.statistics.r_bridge), which is not usable in this "
                    "process — see backend/statistics/evidence.py's module docstring"
                )
            elif participant_id not in table.index:
                uncertainty_items.append(
                    "this participant's occasions did not pass the model's occasion-"
                    "validity gate, so no per-person slope was fit for this feature"
                )
            else:
                row = table.loc[participant_id]
                evidence_label = str(row["label_bh"])
                user_facing_evidence = evidence_module.to_user_facing_evidence(evidence_label)
                if user_facing_evidence == "evidence_available":
                    slope_i = float(row["slope_i"])
                    statistical_evidence = StatisticalEvidence(
                        within_person_deviation_estimate=slope_i,
                        # No per-person CI is available without the
                        # unreconciled bootstrap SE (evidence.py docstring)
                        # — reporting the point estimate as a zero-width
                        # interval would misrepresent precision we don't
                        # have, so this branch is unreachable in practice
                        # (see module docstring: label_bh is always
                        # "insufficient" without slope_se). Kept for
                        # structural completeness only.
                        confidence_interval_low=slope_i,
                        confidence_interval_high=slope_i,
                        direction=(
                            Direction.ABOVE_BASELINE
                            if slope_i > 0
                            else Direction.BELOW_BASELINE
                            if slope_i < 0
                            else Direction.NO_CLEAR_DIRECTION
                        ),
                        evidence_strength=EvidenceStrength(evidence_label),
                    )

        if statistical_evidence is not None:
            # Only combination `backend/slm/response_health.py` accepts for
            # ELIGIBLE: a real baseline value AND real StatisticalEvidence
            # both present. Confirmed by running this against real
            # participants (see PR description) — `response_health.py`
            # enforces this pairing as a hard invariant, stricter than the
            # Pydantic contract's own field-level comment suggests.
            baseline_value = float(baseline_values.mean()) * value_scale
            baseline = PersonalBaseline(
                method="trailing person-mean, 28-day window",
                value=baseline_value,
                n_baseline_observations=n_baseline,
                eligibility_status=eligibility_status,
            )
        else:
            # DISCOVERED WIRING REAL DATA THROUGH THIS FOR THE FIRST TIME:
            # `eligibility.ColdStartState.C_FULL_HISTORY` (data-sufficiency
            # for a *comparison*) and `response_health.py`'s ELIGIBLE
            # invariant (requires real StatisticalEvidence) are not the same
            # condition — per the real Week 5 numbers, most State C
            # occasions (~64%) have no significant per-person evidence.
            # `response_health.py` has no contract-legal way to say
            # "comparison-eligible, but no defensible relationship claim",
            # so this demotes to PARTIAL_DESCRIPTIVE_ONLY (no baseline
            # value shown, matching that status's other real usage for
            # State B) rather than sending ELIGIBLE with evidence=None,
            # which `response_health.py` rejects outright
            # (`eligible_evidence_missing`) — flagged here for Priyansh/
            # SLM review, not silently worked around.
            eligibility_status = EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY
            reason = (
                "no valid sensor-days in the 28-day baseline window"
                if n_baseline == 0
                else (
                    f"per-person evidence-strength label: {evidence_label}"
                    if evidence_label is not None
                    else "per-person evidence-strength classification unavailable in this process"
                )
            )
            baseline = PersonalBaseline(
                method="n/a — comparison-eligible by history, but no defensible evidence",
                value=None,
                n_baseline_observations=n_baseline,
                eligibility_status=eligibility_status,
                ineligible_reason=reason,
            )
            if n_baseline == 0:
                uncertainty_items.append("no baseline window data despite full history")
            user_facing_evidence = None

    identity = PacketIdentity(
        contract_version="1.0.0",
        packet_id=f"real_{feature_id}_{_pseudonymize(participant_id)}_{as_of.isoformat()}",
        model_spec_id="backend.statistics_v1",
        generated_at=datetime.now(timezone.utc),
        participant_ref=_pseudonymize(participant_id),
    )

    claim_choice = _claim_policy_for(eligibility_status, user_facing_evidence)
    claim_policy = ClaimPolicy(
        approved_claim_ids=claim_choice.approved,
        prohibited_claim_ids=tuple(ProhibitedClaimId),
        permitted_response_modes=claim_choice.response_modes,
    )

    return EvidencePacket(
        identity=identity,
        feature_window=feature_window,
        baseline=baseline,
        evidence=statistical_evidence,
        uncertainty=UncertaintyReasons(item_level=tuple(uncertainty_items)),
        claim_policy=claim_policy,
    )
