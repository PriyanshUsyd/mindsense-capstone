"""
Boundary/edge-case tests for the evidence contract, added 2026-08-29 as
part of the 50-test Week 4 verification pass. Complements
test_evidence_contract.py's original 8 fixtures (kept unchanged).
"""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

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
from tests.contracts.test_evidence_contract import _valid_packet_kwargs


# --- FeatureWindow.coverage_ratio boundaries ---------------------------------

def test_coverage_ratio_zero_is_valid():
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["coverage_ratio"] = 0.0
    fw = FeatureWindow(**kwargs)
    assert fw.coverage_ratio == 0.0


def test_coverage_ratio_one_is_valid():
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["coverage_ratio"] = 1.0
    fw = FeatureWindow(**kwargs)
    assert fw.coverage_ratio == 1.0


def test_coverage_ratio_negative_rejected():
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["coverage_ratio"] = -0.001
    with pytest.raises(ValidationError):
        FeatureWindow(**kwargs)


def test_coverage_ratio_above_one_rejected():
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["coverage_ratio"] = 1.001
    with pytest.raises(ValidationError):
        FeatureWindow(**kwargs)


# --- FeatureWindow.observed_days / expected_days -----------------------------

def test_observed_days_zero_is_valid():
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["observed_days"] = 0
    fw = FeatureWindow(**kwargs)
    assert fw.observed_days == 0


def test_observed_days_negative_rejected():
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["observed_days"] = -1
    with pytest.raises(ValidationError):
        FeatureWindow(**kwargs)


def test_expected_days_zero_rejected():
    """expected_days is a denominator concept (days the window was supposed
    to cover) — zero would make coverage_ratio meaningless."""
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["expected_days"] = 0
    with pytest.raises(ValidationError):
        FeatureWindow(**kwargs)


def test_observed_days_can_exceed_expected_days():
    """Not physically expected, but the contract doesn't forbid it outright
    (e.g. a late-arriving duplicate day) — documents current behaviour
    rather than asserting a rule that doesn't exist yet."""
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["observed_days"] = 999
    kwargs["expected_days"] = 14
    fw = FeatureWindow(**kwargs)
    assert fw.observed_days > fw.expected_days


# --- PersonalBaseline.n_baseline_observations --------------------------------

def test_n_baseline_observations_zero_is_valid_when_ineligible():
    kwargs = _valid_packet_kwargs()
    kwargs["baseline"] = PersonalBaseline(
        method="n/a",
        value=None,
        n_baseline_observations=0,
        eligibility_status=EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE,
        ineligible_reason="no prior windows at all",
    )
    kwargs["evidence"] = None
    kwargs["claim_policy"] = ClaimPolicy(
        approved_claim_ids=(ApprovedClaimId.NOT_ENOUGH_DATA,),
        prohibited_claim_ids=tuple(ProhibitedClaimId),
        permitted_response_modes=(ResponseMode.INSUFFICIENT_DATA,),
    )
    packet = EvidencePacket(**kwargs)
    assert packet.baseline.n_baseline_observations == 0


def test_n_baseline_observations_negative_rejected():
    with pytest.raises(ValidationError):
        PersonalBaseline(
            method="n/a",
            value=None,
            n_baseline_observations=-1,
            eligibility_status=EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE,
            ineligible_reason="x",
        )


# --- Claim policy edge cases --------------------------------------------------

def test_empty_approved_claim_ids_is_valid_shape():
    """An empty approved-claims tuple is structurally valid (e.g. a fully
    refused turn) — the contract doesn't force at least one claim."""
    policy = ClaimPolicy(
        approved_claim_ids=(),
        prohibited_claim_ids=tuple(ProhibitedClaimId),
        permitted_response_modes=(ResponseMode.REFUSAL,),
    )
    assert policy.approved_claim_ids == ()


def test_claim_policy_rejects_duplicate_type_in_wrong_enum():
    """A prohibited claim id string cannot be smuggled into approved_claim_ids
    — the two fields use distinct enums, so pydantic must reject a
    cross-enum value even though both enums are `str` subclasses."""
    with pytest.raises(ValidationError):
        ClaimPolicy(
            approved_claim_ids=("diagnosis",),  # a ProhibitedClaimId value, not Approved
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.NORMAL,),
        )


def test_all_four_prohibited_claims_always_representable():
    policy = ClaimPolicy(
        approved_claim_ids=(),
        prohibited_claim_ids=tuple(ProhibitedClaimId),
        permitted_response_modes=(ResponseMode.REFUSAL,),
    )
    assert set(policy.prohibited_claim_ids) == {
        ProhibitedClaimId.DIAGNOSIS,
        ProhibitedClaimId.CAUSAL_EXPLANATION,
        ProhibitedClaimId.TREATMENT_OR_CRISIS_ADVICE,
        ProhibitedClaimId.RISK_PREDICTION,
    }


# --- StatisticalEvidence CI ordering (documents current lack of a check) ----

def test_confidence_interval_low_greater_than_high_not_currently_rejected():
    """Documents a real gap: the contract does not currently enforce
    confidence_interval_low <= confidence_interval_high. Not fixed here
    (that's Moe's/Statistics's field to own), but the gap should be visible
    rather than silently assumed away."""
    evidence = StatisticalEvidence(
        within_person_deviation_estimate=1.0,
        confidence_interval_low=5.0,
        confidence_interval_high=1.0,
        direction=Direction.ABOVE_BASELINE,
        evidence_strength=EvidenceStrength.WEAK,
    )
    assert evidence.confidence_interval_low > evidence.confidence_interval_high


# --- Frozen / extra=forbid enforcement across every sub-model ----------------

@pytest.mark.parametrize(
    "model_cls,kwargs",
    [
        (PacketIdentity, _valid_packet_kwargs()["identity"].model_dump()),
        (FeatureWindow, _valid_packet_kwargs()["feature_window"].model_dump()),
        (PersonalBaseline, _valid_packet_kwargs()["baseline"].model_dump()),
        (StatisticalEvidence, _valid_packet_kwargs()["evidence"].model_dump()),
        (UncertaintyReasons, _valid_packet_kwargs()["uncertainty"].model_dump()),
        (ClaimPolicy, _valid_packet_kwargs()["claim_policy"].model_dump()),
    ],
)
def test_every_submodel_rejects_unknown_field(model_cls, kwargs):
    with pytest.raises(ValidationError):
        model_cls(**{**kwargs, "totally_unexpected_field": "nope"})


def test_evidence_packet_round_trips_through_json():
    packet = EvidencePacket(**_valid_packet_kwargs())
    restored = EvidencePacket.model_validate_json(packet.model_dump_json())
    assert restored == packet


def test_datetime_field_rejects_non_datetime_string():
    kwargs = _valid_packet_kwargs()["identity"].model_dump()
    kwargs["generated_at"] = "not-a-real-timestamp"
    with pytest.raises(ValidationError):
        PacketIdentity(**kwargs)


def test_platform_enum_rejects_unknown_value():
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["platform"] = "windows_phone"
    with pytest.raises(ValidationError):
        FeatureWindow(**kwargs)


def test_window_end_before_window_start_not_currently_rejected():
    """Documents another real gap, same rationale as the CI-ordering test
    above — flagged, not silently fixed by guessing at Data Pipeline's
    intended validation rule."""
    kwargs = _valid_packet_kwargs()["feature_window"].model_dump()
    kwargs["window_start"] = date(2026, 8, 20)
    kwargs["window_end"] = date(2026, 8, 1)
    fw = FeatureWindow(**kwargs)
    assert fw.window_end < fw.window_start
