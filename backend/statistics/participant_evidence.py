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

Per-person evidence (preregistration section 4.1, wired in 2026-10-16):
`/respond` reads the precomputed B=500 bootstrap result from the
fingerprinted aggregated cache (`bootstrap_cache.load_aggregated_cache`,
the same reader `tier1_runner.py` uses) and uses its `label_intersection`
column: `evidence_available` only where the parametric and cluster
bootstrap SE estimates independently agree after BH-FDR control over the
cohort family (section 2.2). No rule is added here; the label is used as
computed. The bootstrap itself is never run from a request.

Engines: when R is usable in this process the R-built cache is read first;
the Python-built cache (`bootstrap.ENGINE_PYTHON`, same model, method, B and
seed) is read when R is not usable, or when no R-built cache exists. Its
fingerprint does not depend on R, so it works on machines without R.

Fail closed: a missing, stale, unreadable, malformed or not owner-only
cache, or a participant without a row all leave the packet at `no_claim`
(no comparison value). Nothing is guessed and nothing raises to
the caller. The non-bootstrapped per-request fit (`slope_se=None`, which
could only ever produce `insufficient`) is no longer run.

A State C participant is sent as `ELIGIBLE` (comparison with their own
baseline, plus the uncertainty sentence) only when their intersection label
is `evidence_available` AND the recent-vs-baseline deviation is defined this
occasion (section 5.1: at least 7 valid days in the recent window and a
non-zero baseline SD). Otherwise the packet is `PARTIAL_DESCRIPTIVE_ONLY`
with a `backend.contracts.comparison_reasons` value, so the output grammar
says the history is long enough but the comparison cannot be reported,
instead of "too early to compare". That sentence stays for State A/B only.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

from backend.contracts.comparison_reasons import (
    STATE_C_EVIDENCE_NOT_REPORTABLE,
    STATE_C_TOO_FEW_RECORDED_DAYS,
)
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
from backend.statistics import bootstrap, bootstrap_cache, r_bridge
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
from backend.statistics.mixed_effects_model import build_model_frame

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
logger = logging.getLogger(__name__)

# Where the B=500 aggregated cache lives (git-ignored, owner-only). A module
# attribute so tests can point it at a temporary directory.
BOOTSTRAP_CACHE_ROOT = bootstrap_cache.CACHE_ROOT
# Engine names the cached runs record (part of each cache's fingerprint).
BOOTSTRAP_ENGINE = bootstrap.ENGINE_R
BOOTSTRAP_ENGINE_PYTHON = bootstrap.ENGINE_PYTHON
# Preregistration section 5.1: the deviation is undefined with fewer than 7
# valid days in the recent window, or a zero baseline SD.
MIN_RECENT_DAYS_FOR_DEVIATION = 7
# Two-sided 95% normal quantile for the contract's CI fields (not shown to
# participants; the label above decides what may be said).
_Z_95 = 1.959963984540054
_STRENGTH_ORDER = {"moderate": 1, "strong": 2}
_REQUIRED_EVIDENCE_COLUMNS = frozenset(
    {
        "uid",
        "slope_i",
        "slope_se_parametric",
        "slope_se_cluster",
        "label_parametric",
        "label_cluster",
        "label_intersection",
    }
)
LOCAL_DEMO_PARTICIPANT_ALIAS = "local-demo"

# CLAUDE.md "Finalised decisions": comparison window [-14, -1], baseline
# window [-42, -15] (the narrower of the two locked options; [-70, -15] is
# the wider alternative, not used here — see module docstring).
COMPARISON_WINDOW_DAYS = 14
BASELINE_WINDOW_DAYS = 28
BASELINE_GAP_DAYS = 15  # baseline window ends this many days before as_of


def _round_user_facing(value: float) -> float:
    """Round a user-facing feature/baseline value to the nearest whole unit
    (km/day for `gps_distance`, unlocks/day for `unlock_count`).

    Decided 2026-09-27 (Week 8), on the strength of each feature's per-
    participant day-to-day variability inside the same 14-day window this
    value is computed from — see "User-facing numeric precision" in
    `docs/statistics/preregistration.md` for the full analysis. In short:
    the median within-person coefficient of variation is ~1.28 for
    `loc_dist_ep_0` (day-to-day SD exceeds the mean) and ~0.30 for
    `unlock_num_ep_0`. Any decimal digit on either feature is precision the
    measurement does not have; showing one is not showing a more accurate
    number, it is showing a falsely precise one (the concrete case that
    triggered this: `120.71428571428571` unlocks/day, reported independently
    in `docs/ui/demo-machine-verification-2026-09-21.md` lines 66-70,
    `docs/evaluation/week8-fallback-e2e.md` line 110, and
    `docs/slm/week8-safety-context-integration.md` line 43 — this function
    is the answer to all three).

    A coarser step (e.g. rounding GPS to the nearest 5 km) was considered
    and rejected: it reads worse than a plain integer, and this system
    expresses uncertainty through the response template's hedging sentence,
    not through the granularity of the number itself.

    Uses `Decimal` with `ROUND_HALF_UP` rather than Python's built-in
    `round`, which is round-half-to-even ("banker's rounding") and would
    silently round e.g. `0.5 -> 0`, not the ordinary half-up rounding a
    participant-facing "nearest whole number" rule implies.

    Known limitation, recorded rather than special-cased: a participant
    whose 14-day GPS average is under 1 km/day is shown "0 km per day".
    They did move; whole-number rounding removes it from view. Keeping one
    decimal place only below that threshold was considered and rejected —
    a rule that changes shape below a cutoff is a second rule, not the same
    rule applied more carefully.

    Called from `build_evidence_packet` at the point `FeatureWindow.value`
    / `PersonalBaseline.value` are computed — not from
    `backend/slm/output_grounding.py` at render time. The `EvidencePacket`
    is the canonical value; `output_grounding.validate_output_grounding`
    checks rendered text against the packet's stored values with exact
    `Decimal` equality, so the value shown to a participant must already be
    what is stored on the packet, not rounded a second time on the way out.
    """
    return float(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


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
_EVIDENCE_TABLE_CACHE: dict[str, _EvidenceTable] = {}


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


@dataclass(frozen=True)
class _EvidenceTable:
    """The cached intersection table indexed by uid, or `None` with the
    reason it could not be used (recorded in `uncertainty.item_level`)."""

    table: pd.DataFrame | None
    unavailable_reason: str | None = None


def _evidence_table(feature_id: str) -> _EvidenceTable:
    """Per-person bootstrap intersection table for `feature_id`, loaded once
    per process from the aggregated B=500 cache (preregistration section
    4.1). Never fits or bootstraps anything per request and never raises:
    every failure becomes `table=None`, which callers treat as `no_claim`."""
    if feature_id not in _EVIDENCE_TABLE_CACHE:
        _EVIDENCE_TABLE_CACHE[feature_id] = _load_evidence_table(feature_id)
    return _EVIDENCE_TABLE_CACHE[feature_id]


def _cache_engines() -> tuple[str, ...]:
    """R-built cache first when R is usable (its fingerprint records the R and
    nlme versions, so it is only valid where R loads); the Python-built cache
    otherwise, or when no R-built cache exists."""
    if r_bridge.r_bridge_available():
        return (BOOTSTRAP_ENGINE, BOOTSTRAP_ENGINE_PYTHON)
    return (BOOTSTRAP_ENGINE_PYTHON,)


def _load_evidence_table(feature_id: str) -> _EvidenceTable:
    meta = _FEATURES[feature_id]
    try:
        frame = build_model_frame(_cleaned_sensing(feature_id), _ema(), feature_spec=meta.spec)
        cached = None
        for engine in _cache_engines():
            cached = bootstrap_cache.load_aggregated_cache(
                meta.spec, frame, engine=engine, cache_root=BOOTSTRAP_CACHE_ROOT
            )
            if cached is not None:
                break
    except Exception as exc:  # noqa: BLE001 - fail closed; stale, unreadable or permission errors alike
        # Exception type only: messages can carry local paths.
        logger.warning("event=bootstrap_cache_unusable feature=%s error=%s", feature_id, type(exc).__name__)
        return _EvidenceTable(None, "per-person evidence unavailable: bootstrap cache unusable")
    if cached is None:
        return _EvidenceTable(None, "per-person evidence unavailable: no bootstrap cache")
    table = cached.intersection
    if (
        not _REQUIRED_EVIDENCE_COLUMNS <= set(table.columns)
        or table["uid"].duplicated().any()
    ):
        logger.warning("event=bootstrap_cache_malformed feature=%s", feature_id)
        return _EvidenceTable(None, "per-person evidence unavailable: bootstrap cache malformed")
    return _EvidenceTable(table.set_index("uid"))


def _statistical_evidence(row: pd.Series) -> StatisticalEvidence | None:
    """`StatisticalEvidence` for an intersection row labelled
    `evidence_available`, or `None` if any field is unusable (fail closed).

    Strength is the weaker of the two methods' own BH labels (both are
    strong/moderate for an intersection-positive row). The contract's CI uses
    the larger of the two bootstrap SEs, the conservative choice; it is not
    shown to participants and does not affect the label."""
    if str(row["label_intersection"]) != "evidence_available":
        return None
    labels = (str(row["label_parametric"]), str(row["label_cluster"]))
    if not all(label in _STRENGTH_ORDER for label in labels):
        return None
    strength = min(labels, key=_STRENGTH_ORDER.__getitem__)
    try:
        slope_i = float(row["slope_i"])
        slope_se = max(float(row["slope_se_parametric"]), float(row["slope_se_cluster"]))
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(slope_i) and math.isfinite(slope_se) and slope_se > 0):
        return None
    return StatisticalEvidence(
        within_person_deviation_estimate=slope_i,
        confidence_interval_low=slope_i - _Z_95 * slope_se,
        confidence_interval_high=slope_i + _Z_95 * slope_se,
        direction=(
            Direction.ABOVE_BASELINE
            if slope_i > 0
            else Direction.BELOW_BASELINE
            if slope_i < 0
            else Direction.NO_CLEAR_DIRECTION
        ),
        evidence_strength=EvidenceStrength(strength),
    )


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
    feature_value = (
        _round_user_facing(float(comparison_values.mean()) * value_scale)
        if observed_days > 0
        else 0.0
    )

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
        baseline_sd = float(baseline_values.std(ddof=1)) if n_baseline > 1 else 0.0
        # Preregistration section 5.1: no deviation value this occasion with
        # fewer than 7 valid recent days or a zero (or undefined) baseline SD.
        deviation_defined = (
            observed_days >= MIN_RECENT_DAYS_FOR_DEVIATION
            and math.isfinite(baseline_sd)
            and baseline_sd > 0
        )
        if not deviation_defined:
            uncertainty_items.append(
                "too few recorded days in the recent or baseline window for a comparison"
            )

        evidence_table = _evidence_table(feature_id)
        if evidence_table.table is None:
            uncertainty_items.append(evidence_table.unavailable_reason or "per-person evidence unavailable")
        elif participant_id not in evidence_table.table.index:
            uncertainty_items.append(
                "this participant's occasions did not pass the model's occasion-"
                "validity gate, so no per-person slope was fit for this feature"
            )
        else:
            row = evidence_table.table.loc[participant_id]
            # Already the user-facing 2-valued label (evidence.intersect_bootstrap_evidence).
            user_facing_evidence = str(row["label_intersection"])
            if user_facing_evidence == "evidence_available":
                statistical_evidence = _statistical_evidence(row)
                if statistical_evidence is None:
                    user_facing_evidence = "no_claim"
                    uncertainty_items.append("per-person evidence row unusable; treated as no_claim")
            else:
                uncertainty_items.append("per-person evidence is no_claim under the bootstrap intersection")

        if statistical_evidence is not None and deviation_defined:
            # Only combination `backend/slm/response_health.py` accepts for
            # ELIGIBLE: a real baseline value AND real StatisticalEvidence.
            baseline_value = _round_user_facing(float(baseline_values.mean()) * value_scale)
            baseline = PersonalBaseline(
                method="trailing person-mean, 28-day window",
                value=baseline_value,
                n_baseline_observations=n_baseline,
                eligibility_status=eligibility_status,
            )
        else:
            # The contract allows a baseline value only on an ELIGIBLE packet
            # with StatisticalEvidence, so a State C comparison that cannot be
            # reported is sent as PARTIAL_DESCRIPTIVE_ONLY. The reason code
            # tells the output grammar to say the history is long enough,
            # not "too early to compare".
            eligibility_status = EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY
            statistical_evidence = None
            user_facing_evidence = None
            baseline = PersonalBaseline(
                method="n/a — comparison-eligible by history, but comparison not reportable",
                value=None,
                n_baseline_observations=n_baseline,
                eligibility_status=eligibility_status,
                ineligible_reason=(
                    STATE_C_EVIDENCE_NOT_REPORTABLE
                    if deviation_defined
                    else STATE_C_TOO_FEW_RECORDED_DAYS
                ),
            )

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
