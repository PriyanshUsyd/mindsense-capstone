from datetime import date, datetime, timezone

import pytest

from backend.contracts.evidence import (
    ApprovedClaimId,
    AssistantDraft,
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


@pytest.fixture
def eligible_packet() -> EvidencePacket:
    return EvidencePacket(
        identity=PacketIdentity(
            contract_version="1.0.0",
            packet_id="pkt_slm_001",
            model_spec_id="mixedlm_v1",
            generated_at=datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc),
            participant_ref="opaque-session-ref",
        ),
        feature_window=FeatureWindow(
            feature_id="unlock_count",
            unit="count_per_day",
            window_start=date(2026, 8, 1),
            window_end=date(2026, 8, 28),
            value=42.0,
            observed_days=25,
            expected_days=28,
            coverage_ratio=25 / 28,
            platform=Platform.ANDROID,
        ),
        baseline=PersonalBaseline(
            method="trailing person-mean, 28-day window",
            value=35.0,
            n_baseline_observations=4,
            eligibility_status=EligibilityStatus.ELIGIBLE,
        ),
        evidence=StatisticalEvidence(
            within_person_deviation_estimate=7.0,
            confidence_interval_low=1.0,
            confidence_interval_high=13.0,
            direction=Direction.ABOVE_BASELINE,
            evidence_strength=EvidenceStrength.MODERATE,
        ),
        uncertainty=UncertaintyReasons(
            item_level=("moderate evidence strength",),
        ),
        claim_policy=ClaimPolicy(
            approved_claim_ids=(
                ApprovedClaimId.OBSERVATION_OF_DEVIATION,
                ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
                ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,
            ),
            prohibited_claim_ids=tuple(ProhibitedClaimId),
            permitted_response_modes=(ResponseMode.NORMAL,),
        ),
    )


@pytest.fixture
def valid_draft(eligible_packet: EvidencePacket) -> AssistantDraft:
    return AssistantDraft(
        packet_id=eligible_packet.identity.packet_id,
        response_mode=ResponseMode.NORMAL,
        claim_ids_used=(
            ApprovedClaimId.OBSERVATION_OF_DEVIATION,
            ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
        ),
        evidence_ids_referenced=(eligible_packet.feature_window.feature_id,),
        text=(
            "Your phone unlock count was 42 unlocks per day, compared with "
            "your own baseline of 35 unlocks per day. This estimate is "
            "uncertain and should be interpreted cautiously."
        ),
        includes_uncertainty_statement=True,
    )
