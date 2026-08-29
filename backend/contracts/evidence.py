"""
Shared Evidence Contract (Statistics -> SLM) — DRAFT, contract-v1.0.0 candidate.

STATUS: Built to fill a Week 4 gap (no contract file existed in the repo as of
2026-08-29). This is a DRAFT scaffold following build-reference.md Section 5
exactly. It still needs the actual freeze/sign-off described there:

    "Any change after [contract freeze] requires sign-off from the Data,
    Statistics, SLM, UI, and Integration/QA leads together, plus a valid
    fixture, an invalid fixture, and a regenerated OpenAPI export."

Do NOT treat this file as frozen. Priyansh still needs to run the actual
freeze meeting and tag `contract-v1.0.0` with Moe, Richard, Sheng, and
Honghao's sign-off before Wednesday of Week 4, per Weekly_Plan.md.

All models are strict Pydantic v2: extra="forbid", frozen=True, per
build-reference.md Section 3 (locked stack) and Section 5.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

_STRICT = ConfigDict(extra="forbid", frozen=True, strict=True)


# ---------------------------------------------------------------------------
# Claim policy — the actual safety mechanism (build-reference.md Section 5)
# ---------------------------------------------------------------------------

class ApprovedClaimId(str, Enum):
    OBSERVATION_OF_DEVIATION = "observation_of_deviation"
    WITHIN_PERSON_ASSOCIATION = "within_person_association"
    TREND_DESCRIPTION = "trend_description"
    UNCERTAINTY_DISCLOSURE = "uncertainty_disclosure"
    NOT_ENOUGH_DATA = "not_enough_data"
    NON_DIAGNOSTIC_BOUNDARY = "non_diagnostic_boundary"


class ProhibitedClaimId(str, Enum):
    DIAGNOSIS = "diagnosis"
    CAUSAL_EXPLANATION = "causal_explanation"
    TREATMENT_OR_CRISIS_ADVICE = "treatment_or_crisis_advice"
    RISK_PREDICTION = "risk_prediction"


class ResponseMode(str, Enum):
    NORMAL = "normal"
    INSUFFICIENT_DATA = "insufficient_data"
    UNCERTAINTY = "uncertainty"
    REFUSAL = "refusal"
    GENERIC_FALLBACK = "generic_fallback"
    CRISIS_AWARE_FALLBACK = "crisis_aware_fallback"


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE_INSUFFICIENT_WINDOW = "ineligible_insufficient_window"
    INELIGIBLE_INSUFFICIENT_BASELINE = "ineligible_insufficient_baseline"


class EvidenceStrength(str, Enum):
    """Not a made-up confidence score — must be derived from actual CI width
    / p-value banding by the Statistics lead's model (see skills/statistics-mixedlm.md)."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class Direction(str, Enum):
    ABOVE_BASELINE = "above_baseline"
    BELOW_BASELINE = "below_baseline"
    NO_CLEAR_DIRECTION = "no_clear_direction"


class Platform(str, Enum):
    IOS = "ios"
    ANDROID = "android"


# ---------------------------------------------------------------------------
# Field groups (build-reference.md Section 5 "Required field groups")
# ---------------------------------------------------------------------------

class PacketIdentity(BaseModel):
    model_config = _STRICT

    contract_version: str = Field(description='e.g. "1.0.0"')
    packet_id: str
    model_spec_id: str = Field(
        description="Versioned id for the exact MixedLM spec used; changes "
        "whenever eligibility threshold or model spec changes (see skills/statistics-mixedlm.md)."
    )
    generated_at: datetime
    participant_ref: str = Field(
        description="Opaque reference — NEVER the raw CES uid (skills/privacy-security.md)."
    )


class FeatureWindow(BaseModel):
    model_config = _STRICT

    feature_id: str = Field(description='e.g. "gps_distance" or "unlock_count"')
    unit: str
    window_start: date
    window_end: date
    value: float
    observed_days: int = Field(ge=0)
    expected_days: int = Field(gt=0)
    coverage_ratio: float = Field(ge=0.0, le=1.0)
    platform: Platform
    quality_flags: tuple[str, ...] = Field(default_factory=tuple)


class PersonalBaseline(BaseModel):
    model_config = _STRICT

    method: str = Field(description='e.g. "trailing person-mean, N prior eligible windows"')
    value: float | None
    n_baseline_observations: int = Field(ge=0)
    eligibility_status: EligibilityStatus
    ineligible_reason: str | None = None


class StatisticalEvidence(BaseModel):
    model_config = _STRICT

    within_person_deviation_estimate: float
    confidence_interval_low: float
    confidence_interval_high: float
    direction: Direction
    evidence_strength: EvidenceStrength


class UncertaintyReasons(BaseModel):
    model_config = _STRICT

    item_level: tuple[str, ...] = Field(default_factory=tuple)
    packet_level: tuple[str, ...] = Field(default_factory=tuple)


class ClaimPolicy(BaseModel):
    model_config = _STRICT

    approved_claim_ids: tuple[ApprovedClaimId, ...]
    prohibited_claim_ids: tuple[ProhibitedClaimId, ...] = tuple(ProhibitedClaimId)
    permitted_response_modes: tuple[ResponseMode, ...]


class EvidencePacket(BaseModel):
    """The full contract object the Statistics lead produces and the SLM
    Integration lead consumes. Never hand the SLM raw model output or raw
    CES rows — only this validated object (skills/slm-ollama.md)."""

    model_config = _STRICT

    identity: PacketIdentity
    feature_window: FeatureWindow
    baseline: PersonalBaseline
    evidence: StatisticalEvidence | None = Field(
        default=None,
        description="None when baseline.eligibility_status is not ELIGIBLE — "
        "there is nothing statistically valid to report yet.",
    )
    uncertainty: UncertaintyReasons
    claim_policy: ClaimPolicy


class AssistantDraft(BaseModel):
    """What the SLM must return, schema-constrained, temperature=0
    (skills/slm-ollama.md). Validated a second time before becoming a response."""

    model_config = _STRICT

    packet_id: str
    response_mode: ResponseMode
    claim_ids_used: tuple[ApprovedClaimId, ...]
    evidence_ids_referenced: tuple[str, ...]
    text: str
    includes_uncertainty_statement: bool
