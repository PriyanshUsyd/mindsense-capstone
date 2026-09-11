"""Deterministic semantic health checks for frozen EvidencePacket inputs.

The shared Pydantic contract intentionally remains frozen.  These checks sit
at the SLM boundary and reject structurally valid but internally inconsistent
packets before a local model can turn them into participant-facing text.
"""

from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel, ConfigDict

from backend.contracts.evidence import (
    EligibilityStatus,
    EvidencePacket,
    ProhibitedClaimId,
)

SUPPORTED_EVIDENCE_CONTRACT_VERSION = "1.0.0"
RESPONSE_HEALTH_CHECK_VERSION = "0.1.0"


class EvidenceContractViolation(str, Enum):
    """Stable, machine-readable violations returned in deterministic order."""

    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    WINDOW_DATE_ORDER_INVALID = "window_date_order_invalid"
    OBSERVED_DAYS_EXCEED_EXPECTED = "observed_days_exceed_expected"
    FEATURE_VALUE_NOT_FINITE = "feature_value_not_finite"
    BASELINE_VALUE_NOT_FINITE = "baseline_value_not_finite"
    ELIGIBLE_BASELINE_MISSING = "eligible_baseline_missing"
    ELIGIBLE_BASELINE_OBSERVATIONS_MISSING = "eligible_baseline_observations_missing"
    ELIGIBLE_INELIGIBLE_REASON_PRESENT = "eligible_ineligible_reason_present"
    ELIGIBLE_EVIDENCE_MISSING = "eligible_evidence_missing"
    NON_ELIGIBLE_BASELINE_PRESENT = "non_eligible_baseline_present"
    NON_ELIGIBLE_EVIDENCE_PRESENT = "non_eligible_evidence_present"
    NON_ELIGIBLE_REASON_MISSING = "non_eligible_reason_missing"
    EVIDENCE_VALUE_NOT_FINITE = "evidence_value_not_finite"
    CONFIDENCE_INTERVAL_ORDER_INVALID = "confidence_interval_order_invalid"
    ESTIMATE_OUTSIDE_CONFIDENCE_INTERVAL = "estimate_outside_confidence_interval"
    PROHIBITED_CLAIM_SET_INCOMPLETE = "prohibited_claim_set_incomplete"
    APPROVED_CLAIM_IDS_DUPLICATED = "approved_claim_ids_duplicated"
    PERMITTED_RESPONSE_MODES_EMPTY = "permitted_response_modes_empty"


class ResponseHealthReport(BaseModel):
    """Audit-friendly result for the SLM's pre-generation health gate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check_version: str = RESPONSE_HEALTH_CHECK_VERSION
    healthy: bool
    violations: tuple[EvidenceContractViolation, ...]

    @property
    def rejection_reason(self) -> str | None:
        if self.healthy:
            return None
        codes = ",".join(violation.value for violation in self.violations)
        return f"evidence_contract_violation:{codes}"


def check_response_health(packet: EvidencePacket) -> ResponseHealthReport:
    """Check cross-field invariants omitted from the frozen Pydantic model."""

    violations: list[EvidenceContractViolation] = []

    def add(violation: EvidenceContractViolation) -> None:
        if violation not in violations:
            violations.append(violation)

    if packet.identity.contract_version != SUPPORTED_EVIDENCE_CONTRACT_VERSION:
        add(EvidenceContractViolation.UNSUPPORTED_CONTRACT_VERSION)

    window = packet.feature_window
    if window.window_end < window.window_start:
        add(EvidenceContractViolation.WINDOW_DATE_ORDER_INVALID)
    if window.observed_days > window.expected_days:
        add(EvidenceContractViolation.OBSERVED_DAYS_EXCEED_EXPECTED)
    if not math.isfinite(window.value):
        add(EvidenceContractViolation.FEATURE_VALUE_NOT_FINITE)

    baseline = packet.baseline
    if baseline.value is not None and not math.isfinite(baseline.value):
        add(EvidenceContractViolation.BASELINE_VALUE_NOT_FINITE)

    if baseline.eligibility_status == EligibilityStatus.ELIGIBLE:
        if baseline.value is None:
            add(EvidenceContractViolation.ELIGIBLE_BASELINE_MISSING)
        if baseline.n_baseline_observations < 1:
            add(EvidenceContractViolation.ELIGIBLE_BASELINE_OBSERVATIONS_MISSING)
        if baseline.ineligible_reason is not None:
            add(EvidenceContractViolation.ELIGIBLE_INELIGIBLE_REASON_PRESENT)
        if packet.evidence is None:
            add(EvidenceContractViolation.ELIGIBLE_EVIDENCE_MISSING)
    else:
        if baseline.value is not None:
            add(EvidenceContractViolation.NON_ELIGIBLE_BASELINE_PRESENT)
        if packet.evidence is not None:
            add(EvidenceContractViolation.NON_ELIGIBLE_EVIDENCE_PRESENT)
        if not (baseline.ineligible_reason or "").strip():
            add(EvidenceContractViolation.NON_ELIGIBLE_REASON_MISSING)

    evidence = packet.evidence
    if evidence is not None:
        values = (
            evidence.within_person_deviation_estimate,
            evidence.confidence_interval_low,
            evidence.confidence_interval_high,
        )
        if not all(math.isfinite(value) for value in values):
            add(EvidenceContractViolation.EVIDENCE_VALUE_NOT_FINITE)
        elif evidence.confidence_interval_low > evidence.confidence_interval_high:
            add(EvidenceContractViolation.CONFIDENCE_INTERVAL_ORDER_INVALID)
        elif not (
            evidence.confidence_interval_low
            <= evidence.within_person_deviation_estimate
            <= evidence.confidence_interval_high
        ):
            add(EvidenceContractViolation.ESTIMATE_OUTSIDE_CONFIDENCE_INTERVAL)

    policy = packet.claim_policy
    if set(policy.prohibited_claim_ids) != set(ProhibitedClaimId):
        add(EvidenceContractViolation.PROHIBITED_CLAIM_SET_INCOMPLETE)
    if len(policy.approved_claim_ids) != len(set(policy.approved_claim_ids)):
        add(EvidenceContractViolation.APPROVED_CLAIM_IDS_DUPLICATED)
    if not policy.permitted_response_modes:
        add(EvidenceContractViolation.PERMITTED_RESPONSE_MODES_EMPTY)

    return ResponseHealthReport(
        healthy=not violations,
        violations=tuple(violations),
    )
