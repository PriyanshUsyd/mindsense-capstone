"""
End-to-end integration tests, added 2026-08-29: a FeatureWindow flows
through Moe's real eligibility logic, into the evidence contract, and is
checked against what the SLM safety gate expects to consume. This is the
genuine cross-role integration point the Week 4 pieces need to agree on —
not a re-test of any single module in isolation.

Pipeline under test:
  raw counters -> classify_state() [Statistics] -> to_eligibility_status()
  -> PersonalBaseline / EvidencePacket [shared contract] -> AssistantDraft
  [SLM] -> validate_draft() [SLM safety gate]
"""

from datetime import date, datetime, timezone

import pytest

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
from backend.slm.safety_gate import (
    CLAIM_NOT_APPROVED,
    MISSING_UNCERTAINTY_STATEMENT,
    RESPONSE_MODE_NOT_PERMITTED,
    UNKNOWN_EVIDENCE_ID,
    validate_draft,
)
from backend.statistics.eligibility import (
    STATE_C_MIN_CALENDAR_DAYS,
    STATE_C_MIN_EMAS,
    STATE_C_MIN_VALID_SENSOR_DAYS,
    ColdStartState,
    classify_state,
    to_eligibility_status,
)


def _base_identity() -> PacketIdentity:
    return PacketIdentity(
        contract_version="1.0.0",
        packet_id="pkt_e2e_0001",
        model_spec_id="mixedlm_v1",
        generated_at=datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc),
        participant_ref="opaque-ref-e2e",
    )


def _base_feature_window(coverage_ratio: float = 0.9) -> FeatureWindow:
    return FeatureWindow(
        feature_id="unlock_count",
        unit="count",
        window_start=date(2026, 8, 1),
        window_end=date(2026, 8, 28),
        value=42.0,
        observed_days=25,
        expected_days=28,
        coverage_ratio=coverage_ratio,
        platform=Platform.IOS,
    )


# --- Full pipeline: State A (no data) ----------------------------------------


def test_state_a_produces_ineligible_packet_with_no_evidence():
    state = classify_state(calendar_days=3, valid_sensor_days=1, ema_count=0)
    assert state == ColdStartState.A_INSUFFICIENT_DATA

    eligibility_status = to_eligibility_status(state)
    assert eligibility_status == EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW

    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(coverage_ratio=0.1),
        baseline=PersonalBaseline(
            method="n/a — State A",
            value=None,
            n_baseline_observations=0,
            eligibility_status=eligibility_status,
            ineligible_reason="below Moe's State B floor (7 calendar days / 5 valid sensor-days / 1 EMA)",
        ),
        evidence=None,
        uncertainty=UncertaintyReasons(packet_level=("no history yet",)),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(ApprovedClaimId.NOT_ENOUGH_DATA,),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.INSUFFICIENT_DATA,),
        ),
    )
    assert packet.evidence is None

    draft = _draft(
        packet,
        response_mode=ResponseMode.INSUFFICIENT_DATA,
        claim_ids_used=(ApprovedClaimId.NOT_ENOUGH_DATA,),
        includes_uncertainty_statement=False,
    )
    ok, reason = validate_draft(packet, draft)
    assert ok is True, reason


def _draft(
    packet,
    response_mode,
    claim_ids_used,
    includes_uncertainty_statement,
    evidence_ids_referenced=None,
):
    from backend.contracts.evidence import AssistantDraft

    return AssistantDraft(
        packet_id=packet.identity.packet_id,
        response_mode=response_mode,
        claim_ids_used=claim_ids_used,
        evidence_ids_referenced=(
            (packet.feature_window.feature_id,)
            if evidence_ids_referenced is None
            else evidence_ids_referenced
        ),
        text=(
            "There is not enough data or history for comparison."
            if response_mode == ResponseMode.INSUFFICIENT_DATA
            else "synthetic test response"
        ),
        includes_uncertainty_statement=includes_uncertainty_statement,
    )


# --- Full pipeline: State B (partial — descriptive only, no comparison) -----


def test_state_b_produces_partial_packet_with_value_but_no_statistical_evidence():
    state = classify_state(calendar_days=10, valid_sensor_days=6, ema_count=1)
    assert state == ColdStartState.B_PARTIAL_HISTORY

    eligibility_status = to_eligibility_status(state)
    assert eligibility_status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY

    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(coverage_ratio=0.6),
        baseline=PersonalBaseline(
            method="n/a — State B, too early for a baseline",
            value=None,
            n_baseline_observations=1,
            eligibility_status=eligibility_status,
        ),
        evidence=None,  # State B must NOT carry StatisticalEvidence
        uncertainty=UncertaintyReasons(item_level=("too early to compare",)),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(
                ApprovedClaimId.OBSERVATION_OF_DEVIATION,
                ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
                ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,
            ),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.UNCERTAINTY,),
        ),
    )
    assert packet.evidence is None
    assert (
        packet.baseline.eligibility_status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY
    )

    draft = _draft(
        packet,
        response_mode=ResponseMode.UNCERTAINTY,
        claim_ids_used=(
            ApprovedClaimId.OBSERVATION_OF_DEVIATION,
            ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
        ),
        includes_uncertainty_statement=True,
    )
    ok, reason = validate_draft(packet, draft)
    assert ok is True, reason


def test_state_b_draft_missing_uncertainty_statement_is_rejected():
    """State B/uncertainty responses MUST carry an uncertainty statement —
    the safety gate must reject a draft that omits it, per
    skills/slm-ollama.md criterion 4."""
    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(coverage_ratio=0.6),
        baseline=PersonalBaseline(
            method="n/a",
            value=None,
            n_baseline_observations=1,
            eligibility_status=EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY,
        ),
        evidence=None,
        uncertainty=UncertaintyReasons(item_level=("too early",)),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(ApprovedClaimId.OBSERVATION_OF_DEVIATION,),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.UNCERTAINTY,),
        ),
    )
    draft = _draft(
        packet,
        response_mode=ResponseMode.UNCERTAINTY,
        claim_ids_used=(ApprovedClaimId.OBSERVATION_OF_DEVIATION,),
        includes_uncertainty_statement=False,
    )
    ok, reason = validate_draft(packet, draft)
    assert ok is False
    assert reason == MISSING_UNCERTAINTY_STATEMENT


# --- Full pipeline: State C (full — comparison allowed) ----------------------


def test_state_c_produces_eligible_packet_with_full_evidence():
    state = classify_state(
        calendar_days=STATE_C_MIN_CALENDAR_DAYS,
        valid_sensor_days=STATE_C_MIN_VALID_SENSOR_DAYS,
        ema_count=STATE_C_MIN_EMAS,
    )
    assert state == ColdStartState.C_FULL_HISTORY

    eligibility_status = to_eligibility_status(state)
    assert eligibility_status == EligibilityStatus.ELIGIBLE

    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(coverage_ratio=0.95),
        baseline=PersonalBaseline(
            method="trailing person-mean, 28-day window",
            value=38.5,
            n_baseline_observations=STATE_C_MIN_EMAS,
            eligibility_status=eligibility_status,
        ),
        evidence=StatisticalEvidence(
            within_person_deviation_estimate=3.5,
            confidence_interval_low=0.2,
            confidence_interval_high=6.8,
            direction=Direction.ABOVE_BASELINE,
            evidence_strength=EvidenceStrength.MODERATE,
        ),
        uncertainty=UncertaintyReasons(item_level=("moderate confidence",)),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(
                ApprovedClaimId.OBSERVATION_OF_DEVIATION,
                ApprovedClaimId.WITHIN_PERSON_ASSOCIATION,
                ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
                ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,
            ),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.NORMAL,),
        ),
    )
    assert packet.evidence is not None

    draft = _draft(
        packet,
        response_mode=ResponseMode.NORMAL,
        claim_ids_used=(
            ApprovedClaimId.OBSERVATION_OF_DEVIATION,
            ApprovedClaimId.WITHIN_PERSON_ASSOCIATION,
            ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
        ),
        includes_uncertainty_statement=True,
    )
    ok, reason = validate_draft(packet, draft)
    assert ok is True, reason


# --- Safety gate must actually catch violations, not just pass good input --


def test_gate_rejects_prohibited_claim_smuggled_via_wrong_response_mode():
    """A draft trying to use a claim id the packet's ClaimPolicy never
    approved must be rejected outright."""
    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(),
        baseline=PersonalBaseline(
            method="n/a",
            value=None,
            n_baseline_observations=0,
            eligibility_status=EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
        ),
        evidence=None,
        uncertainty=UncertaintyReasons(),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(ApprovedClaimId.NOT_ENOUGH_DATA,),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.INSUFFICIENT_DATA,),
        ),
    )
    draft = _draft(
        packet,
        response_mode=ResponseMode.INSUFFICIENT_DATA,
        claim_ids_used=(
            ApprovedClaimId.WITHIN_PERSON_ASSOCIATION,
        ),  # not approved by this packet
        includes_uncertainty_statement=False,
    )
    ok, reason = validate_draft(packet, draft)
    assert ok is False
    assert reason == CLAIM_NOT_APPROVED


def test_gate_rejects_response_mode_outside_permitted_set():
    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(),
        baseline=PersonalBaseline(
            method="n/a",
            value=None,
            n_baseline_observations=0,
            eligibility_status=EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
        ),
        evidence=None,
        uncertainty=UncertaintyReasons(),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(ApprovedClaimId.NOT_ENOUGH_DATA,),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.INSUFFICIENT_DATA,),
        ),
    )
    draft = _draft(
        packet,
        response_mode=ResponseMode.NORMAL,  # not in permitted_response_modes
        claim_ids_used=(ApprovedClaimId.NOT_ENOUGH_DATA,),
        includes_uncertainty_statement=False,
    )
    ok, reason = validate_draft(packet, draft)
    assert ok is False
    assert reason == RESPONSE_MODE_NOT_PERMITTED


def test_gate_rejects_evidence_id_not_in_packet():
    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(),
        baseline=PersonalBaseline(
            method="n/a",
            value=None,
            n_baseline_observations=0,
            eligibility_status=EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
        ),
        evidence=None,
        uncertainty=UncertaintyReasons(),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(ApprovedClaimId.NOT_ENOUGH_DATA,),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.INSUFFICIENT_DATA,),
        ),
    )
    draft = _draft(
        packet,
        response_mode=ResponseMode.INSUFFICIENT_DATA,
        claim_ids_used=(ApprovedClaimId.NOT_ENOUGH_DATA,),
        includes_uncertainty_statement=False,
        evidence_ids_referenced=("some_feature_that_does_not_exist",),
    )
    ok, reason = validate_draft(packet, draft)
    assert ok is False
    assert reason == UNKNOWN_EVIDENCE_ID


def test_gate_accepts_fallback_modes_without_requiring_uncertainty_statement():
    """generic_fallback / refusal / crisis_aware_fallback are exempt from
    the uncertainty-statement requirement — they don't explain anything for
    uncertainty to attach to (they're not a 'ready' explanation)."""
    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(),
        baseline=PersonalBaseline(
            method="n/a",
            value=None,
            n_baseline_observations=0,
            eligibility_status=EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
        ),
        evidence=None,
        uncertainty=UncertaintyReasons(),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.GENERIC_FALLBACK,),
        ),
    )
    draft = _draft(
        packet,
        response_mode=ResponseMode.GENERIC_FALLBACK,
        claim_ids_used=(ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,),
        includes_uncertainty_statement=False,
    )
    ok, reason = validate_draft(packet, draft)
    assert ok is True, reason


@pytest.mark.parametrize(
    "state,expected_status",
    [
        (
            ColdStartState.A_INSUFFICIENT_DATA,
            EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
        ),
        (ColdStartState.B_PARTIAL_HISTORY, EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY),
        (ColdStartState.C_FULL_HISTORY, EligibilityStatus.ELIGIBLE),
    ],
)
def test_to_eligibility_status_mapping_is_total_and_correct(state, expected_status):
    assert to_eligibility_status(state) == expected_status


# --- Direct unit coverage of the safety gate's individual rejection paths ---


def test_gate_rejects_on_packet_id_mismatch_directly():
    from backend.slm.safety_gate import PACKET_ID_MISMATCH

    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(),
        baseline=PersonalBaseline(
            method="n/a",
            value=None,
            n_baseline_observations=0,
            eligibility_status=EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
        ),
        evidence=None,
        uncertainty=UncertaintyReasons(),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(ApprovedClaimId.NOT_ENOUGH_DATA,),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.INSUFFICIENT_DATA,),
        ),
    )
    draft = _draft(
        packet,
        response_mode=ResponseMode.INSUFFICIENT_DATA,
        claim_ids_used=(ApprovedClaimId.NOT_ENOUGH_DATA,),
        includes_uncertainty_statement=False,
    )
    from backend.contracts.evidence import AssistantDraft as _AD

    mismatched_draft = _AD(
        **{**draft.model_dump(), "packet_id": "some_other_packet_id"}
    )
    ok, reason = validate_draft(packet, mismatched_draft)
    assert ok is False
    assert reason == PACKET_ID_MISMATCH


def test_gate_accepts_evidence_id_referencing_the_packet_id_itself():
    """packet_id is itself a valid evidence id a draft can reference,
    per safety_gate.py's documented valid_evidence_ids set."""
    packet = EvidencePacket(
        identity=_base_identity(),
        feature_window=_base_feature_window(),
        baseline=PersonalBaseline(
            method="n/a",
            value=None,
            n_baseline_observations=0,
            eligibility_status=EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
        ),
        evidence=None,
        uncertainty=UncertaintyReasons(),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(ApprovedClaimId.NOT_ENOUGH_DATA,),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.INSUFFICIENT_DATA,),
        ),
    )
    draft = _draft(
        packet,
        response_mode=ResponseMode.INSUFFICIENT_DATA,
        claim_ids_used=(ApprovedClaimId.NOT_ENOUGH_DATA,),
        includes_uncertainty_statement=False,
        evidence_ids_referenced=(packet.identity.packet_id,),
    )
    ok, reason = validate_draft(packet, draft)
    assert ok is True, reason
