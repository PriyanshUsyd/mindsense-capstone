from datetime import date

from backend.contracts.evidence import EligibilityStatus, EvidencePacket, ResponseMode
from backend.slm.request_policy import RequestCategory, RequestDisposition
from backend.slm.response_health import (
    RESPONSE_HEALTH_CHECK_VERSION,
    EvidenceContractViolation,
    check_response_health,
)
from backend.slm.service import SLMService
from benchmarks.slm_model_comparison import comparison_cases


class MustNotRun:
    def generate_draft(self, packet: EvidencePacket, question: str):
        raise AssertionError("unhealthy evidence reached the local model")


def test_valid_eligible_and_partial_packets_are_healthy(eligible_packet):
    partial_packet = comparison_cases()[1].packet

    eligible = check_response_health(eligible_packet)
    partial = check_response_health(partial_packet)

    assert eligible.check_version == RESPONSE_HEALTH_CHECK_VERSION == "0.1.0"
    assert eligible.healthy is True
    assert eligible.violations == ()
    assert eligible.rejection_reason is None
    assert partial.healthy is True


def test_health_check_reports_explicit_violations_in_stable_order(eligible_packet):
    packet = eligible_packet.model_copy(
        update={
            "identity": eligible_packet.identity.model_copy(
                update={"contract_version": "9.9.9"}
            ),
            "feature_window": eligible_packet.feature_window.model_copy(
                update={
                    "window_start": date(2026, 8, 20),
                    "window_end": date(2026, 8, 1),
                    "observed_days": 29,
                    "expected_days": 28,
                }
            ),
            "evidence": eligible_packet.evidence.model_copy(
                update={
                    "within_person_deviation_estimate": 4.0,
                    "confidence_interval_low": 5.0,
                    "confidence_interval_high": 1.0,
                }
            ),
        }
    )

    report = check_response_health(packet)

    assert report.healthy is False
    assert report.violations == (
        EvidenceContractViolation.UNSUPPORTED_CONTRACT_VERSION,
        EvidenceContractViolation.WINDOW_DATE_ORDER_INVALID,
        EvidenceContractViolation.OBSERVED_DAYS_EXCEED_EXPECTED,
        EvidenceContractViolation.CONFIDENCE_INTERVAL_ORDER_INVALID,
    )
    assert report.rejection_reason == (
        "evidence_contract_violation:unsupported_contract_version,"
        "window_date_order_invalid,observed_days_exceed_expected,"
        "confidence_interval_order_invalid"
    )


def test_eligible_packet_requires_baseline_and_statistical_evidence(eligible_packet):
    packet = eligible_packet.model_copy(
        update={
            "baseline": eligible_packet.baseline.model_copy(
                update={
                    "value": None,
                    "n_baseline_observations": 0,
                    "ineligible_reason": "contradicts eligible state",
                }
            ),
            "evidence": None,
        }
    )

    report = check_response_health(packet)

    assert report.violations == (
        EvidenceContractViolation.ELIGIBLE_BASELINE_MISSING,
        EvidenceContractViolation.ELIGIBLE_BASELINE_OBSERVATIONS_MISSING,
        EvidenceContractViolation.ELIGIBLE_INELIGIBLE_REASON_PRESENT,
        EvidenceContractViolation.ELIGIBLE_EVIDENCE_MISSING,
    )


def test_noneligible_packet_rejects_comparison_state_and_requires_reason(
    eligible_packet,
):
    packet = eligible_packet.model_copy(
        update={
            "baseline": eligible_packet.baseline.model_copy(
                update={
                    "eligibility_status": EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY,
                    "ineligible_reason": "  ",
                }
            )
        }
    )

    report = check_response_health(packet)

    assert report.violations == (
        EvidenceContractViolation.NON_ELIGIBLE_BASELINE_PRESENT,
        EvidenceContractViolation.NON_ELIGIBLE_EVIDENCE_PRESENT,
        EvidenceContractViolation.NON_ELIGIBLE_REASON_MISSING,
    )


def test_health_check_rejects_nonfinite_values_and_estimate_outside_ci(
    eligible_packet,
):
    nonfinite = eligible_packet.model_copy(
        update={
            "feature_window": eligible_packet.feature_window.model_copy(
                update={"value": float("inf")}
            ),
            "baseline": eligible_packet.baseline.model_copy(
                update={"value": float("nan")}
            ),
            "evidence": eligible_packet.evidence.model_copy(
                update={"within_person_deviation_estimate": float("inf")}
            ),
        }
    )
    outside = eligible_packet.model_copy(
        update={
            "evidence": eligible_packet.evidence.model_copy(
                update={
                    "within_person_deviation_estimate": 20.0,
                    "confidence_interval_low": 1.0,
                    "confidence_interval_high": 13.0,
                }
            )
        }
    )

    assert check_response_health(nonfinite).violations == (
        EvidenceContractViolation.FEATURE_VALUE_NOT_FINITE,
        EvidenceContractViolation.BASELINE_VALUE_NOT_FINITE,
        EvidenceContractViolation.EVIDENCE_VALUE_NOT_FINITE,
    )
    assert check_response_health(outside).violations == (
        EvidenceContractViolation.ESTIMATE_OUTSIDE_CONFIDENCE_INTERVAL,
    )


def test_claim_policy_safety_invariants_are_checked(eligible_packet):
    approved = eligible_packet.claim_policy.approved_claim_ids
    packet = eligible_packet.model_copy(
        update={
            "claim_policy": eligible_packet.claim_policy.model_copy(
                update={
                    "approved_claim_ids": (*approved, approved[0]),
                    "prohibited_claim_ids": (),
                    "permitted_response_modes": (),
                }
            )
        }
    )

    assert check_response_health(packet).violations == (
        EvidenceContractViolation.PROHIBITED_CLAIM_SET_INCOMPLETE,
        EvidenceContractViolation.APPROVED_CLAIM_IDS_DUPLICATED,
        EvidenceContractViolation.PERMITTED_RESPONSE_MODES_EMPTY,
    )


def test_unhealthy_packet_uses_generic_fallback_before_model(eligible_packet):
    packet = eligible_packet.model_copy(
        update={
            "feature_window": eligible_packet.feature_window.model_copy(
                update={"observed_days": 29, "expected_days": 28}
            )
        }
    )

    service = SLMService(MustNotRun())
    response = service.respond(packet, "What changed?")

    assert service.check_response_health(packet) == check_response_health(packet)
    assert response.response_mode == ResponseMode.GENERIC_FALLBACK
    assert response.request_disposition == RequestDisposition.ALLOW
    assert response.request_category == RequestCategory.IN_SCOPE
    assert response.used_fallback is True
    assert response.model_invoked is False
    assert response.model_tag is None
    assert response.rejection_reason == (
        "evidence_contract_violation:observed_days_exceed_expected"
    )


def test_crisis_routing_precedes_evidence_health_check(eligible_packet):
    packet = eligible_packet.model_copy(
        update={
            "feature_window": eligible_packet.feature_window.model_copy(
                update={"observed_days": 29, "expected_days": 28}
            )
        }
    )

    response = SLMService(MustNotRun()).respond(packet, "I want to kill myself.")

    assert response.response_mode == ResponseMode.CRISIS_AWARE_FALLBACK
    assert response.request_category == RequestCategory.CRISIS_SELF_HARM
    assert response.rejection_reason == "crisis_language_detected"
    assert response.model_invoked is False
