"""
Valid/invalid fixtures for the evidence contract, per build-reference.md
Section 5's freeze requirement ("a valid fixture, an invalid fixture, and a
regenerated OpenAPI export"). Built to fill the Week 4 gap — still needs
review by Moe (Stats) and Richard (SLM) as the contract's two primary
consumers before contract-v1.0.0 is actually tagged.
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


def _valid_packet_kwargs():
    return dict(
        identity=PacketIdentity(
            contract_version="1.0.0",
            packet_id="pkt_test_0001",
            model_spec_id="mixedlm_v1",
            generated_at=datetime(2026, 8, 29, 12, 0, 0),
            participant_ref="opaque-ref-123",
        ),
        feature_window=FeatureWindow(
            feature_id="unlock_count",
            unit="count",
            window_start=date(2026, 8, 1),
            window_end=date(2026, 8, 14),
            value=42.0,
            observed_days=13,
            expected_days=14,
            coverage_ratio=13 / 14,
            platform=Platform.IOS,
            quality_flags=(),
        ),
        baseline=PersonalBaseline(
            method="trailing person-mean, 4 prior eligible windows",
            value=38.5,
            n_baseline_observations=4,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            ineligible_reason=None,
        ),
        evidence=StatisticalEvidence(
            within_person_deviation_estimate=3.5,
            confidence_interval_low=0.2,
            confidence_interval_high=6.8,
            direction=Direction.ABOVE_BASELINE,
            evidence_strength=EvidenceStrength.MODERATE,
        ),
        uncertainty=UncertaintyReasons(
            item_level=("small baseline sample (n=4)",),
            packet_level=(),
        ),
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


def test_valid_packet_constructs():
    packet = EvidencePacket(**_valid_packet_kwargs())
    assert packet.identity.contract_version == "1.0.0"
    assert packet.evidence.direction == Direction.ABOVE_BASELINE


def test_frozen_and_extra_forbidden():
    packet = EvidencePacket(**_valid_packet_kwargs())
    with pytest.raises(ValidationError):
        packet.identity.packet_id = "changed"  # frozen=True


def test_invalid_packet_rejects_unknown_field():
    kwargs = _valid_packet_kwargs()
    with pytest.raises(ValidationError):
        PacketIdentity(**{**kwargs["identity"].model_dump(), "unexpected_field": "nope"})


def test_invalid_coverage_ratio_out_of_range():
    kwargs = _valid_packet_kwargs()
    fw = kwargs["feature_window"].model_dump()
    fw["coverage_ratio"] = 1.5
    with pytest.raises(ValidationError):
        FeatureWindow(**fw)


def test_insufficient_data_packet_has_no_evidence():
    kwargs = _valid_packet_kwargs()
    kwargs["baseline"] = PersonalBaseline(
        method="trailing person-mean, 4 prior eligible windows",
        value=None,
        n_baseline_observations=1,
        eligibility_status=EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE,
        ineligible_reason="only 1 prior eligible window; minimum is 4 (see docs/statistics/cold-start-policy.md)",
    )
    kwargs["evidence"] = None
    kwargs["claim_policy"] = ClaimPolicy(
        approved_claim_ids=(ApprovedClaimId.NOT_ENOUGH_DATA,),
        prohibited_claim_ids=tuple(ProhibitedClaimId),
        permitted_response_modes=(ResponseMode.INSUFFICIENT_DATA,),
    )
    packet = EvidencePacket(**kwargs)
    assert packet.evidence is None
    assert packet.baseline.eligibility_status == EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE
