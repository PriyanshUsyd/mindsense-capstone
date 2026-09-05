"""Safe orchestration from EvidencePacket to a user-facing local response."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from backend.contracts.evidence import EligibilityStatus, EvidencePacket, ResponseMode
from backend.slm.client import (
    GenerationMetrics,
    GenerationResult,
    SLMClientError,
)
from backend.slm.prompt_loader import (
    DEFAULT_CRISIS_FALLBACK,
    DEFAULT_INSUFFICIENT_DATA_TEMPLATE,
    LoadedFallbackPrompt,
    load_fallback_prompt,
)
from backend.slm.request_policy import (
    RequestCategory,
    RequestDisposition,
    RequestPolicyDecision,
    classify_request,
)
from backend.slm.safety_gate import validate_draft


class DraftGenerator(Protocol):
    def generate_draft(
        self, packet: EvidencePacket, question: str
    ) -> GenerationResult: ...


class SafeSLMResponse(BaseModel):
    """Final response metadata retained for audit and evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response_mode: ResponseMode
    text: str
    used_fallback: bool
    rejection_reason: str | None
    model_tag: str | None
    generation_prompt_sha256: str | None
    fallback_prompt_sha256: str | None
    metrics: GenerationMetrics | None
    request_disposition: RequestDisposition
    request_category: RequestCategory
    request_policy_version: str
    model_invoked: bool


class SLMService:
    """Validate every model draft or return the versioned safe fallback."""

    def __init__(
        self,
        client: DraftGenerator,
        *,
        generic_fallback: LoadedFallbackPrompt | None = None,
        crisis_fallback: LoadedFallbackPrompt | None = None,
        insufficient_data_template: LoadedFallbackPrompt | None = None,
    ) -> None:
        self.client = client
        self.generic_fallback = generic_fallback or load_fallback_prompt()
        self.crisis_fallback = crisis_fallback or load_fallback_prompt(
            DEFAULT_CRISIS_FALLBACK
        )
        self.insufficient_data_template = (
            insufficient_data_template
            or load_fallback_prompt(DEFAULT_INSUFFICIENT_DATA_TEMPLATE)
        )
        if (
            self.generic_fallback.manifest.response_mode
            != ResponseMode.GENERIC_FALLBACK
        ):
            raise ValueError("generic fallback manifest has the wrong response_mode")
        if (
            self.crisis_fallback.manifest.response_mode
            != ResponseMode.CRISIS_AWARE_FALLBACK
        ):
            raise ValueError("crisis fallback manifest has the wrong response_mode")
        if (
            self.insufficient_data_template.manifest.response_mode
            != ResponseMode.INSUFFICIENT_DATA
        ):
            raise ValueError(
                "insufficient-data template manifest has the wrong response_mode"
            )

    def respond(self, packet: EvidencePacket, question: str) -> SafeSLMResponse:
        request_decision = classify_request(question)
        if request_decision.disposition != RequestDisposition.ALLOW:
            return self._policy_response(request_decision)
        if packet.baseline.eligibility_status in {
            EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
            EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE,
        }:
            return self._insufficient_data_response(request_decision)

        try:
            generation = self.client.generate_draft(packet, question)
        except (SLMClientError, ValueError):
            return self._fallback(
                "model_generation_failed", request_decision=request_decision
            )

        draft = generation.draft
        if draft.response_mode == ResponseMode.REFUSAL:
            return self._fallback(
                "model_must_not_select_refusal",
                request_decision=request_decision,
                generation=generation,
            )
        if draft.response_mode == ResponseMode.CRISIS_AWARE_FALLBACK:
            return self._fallback(
                "model_must_not_select_crisis_fallback",
                request_decision=request_decision,
                generation=generation,
            )
        if draft.response_mode == ResponseMode.GENERIC_FALLBACK:
            return self._fallback(
                "model_requested_fallback",
                request_decision=request_decision,
                generation=generation,
            )

        is_valid, rejection = validate_draft(packet, draft)
        if not is_valid:
            return self._fallback(
                str(rejection),
                request_decision=request_decision,
                generation=generation,
            )

        return SafeSLMResponse(
            response_mode=draft.response_mode,
            text=draft.text,
            used_fallback=False,
            rejection_reason=None,
            model_tag=generation.model_tag,
            generation_prompt_sha256=generation.prompt_sha256,
            fallback_prompt_sha256=None,
            metrics=generation.metrics,
            request_disposition=request_decision.disposition,
            request_category=request_decision.category,
            request_policy_version=request_decision.policy_version,
            model_invoked=True,
        )

    def _policy_response(self, decision: RequestPolicyDecision) -> SafeSLMResponse:
        if decision.disposition == RequestDisposition.CRISIS:
            template = self.crisis_fallback
            response_mode = ResponseMode.CRISIS_AWARE_FALLBACK
        else:
            template = self.generic_fallback
            response_mode = ResponseMode.REFUSAL

        return SafeSLMResponse(
            response_mode=response_mode,
            text=template.manifest.text,
            used_fallback=True,
            rejection_reason=decision.reason_code,
            model_tag=None,
            generation_prompt_sha256=None,
            fallback_prompt_sha256=template.sha256,
            metrics=None,
            request_disposition=decision.disposition,
            request_category=decision.category,
            request_policy_version=decision.policy_version,
            model_invoked=False,
        )

    def _insufficient_data_response(
        self, decision: RequestPolicyDecision
    ) -> SafeSLMResponse:
        template = self.insufficient_data_template
        return SafeSLMResponse(
            response_mode=ResponseMode.INSUFFICIENT_DATA,
            text=template.manifest.text,
            used_fallback=False,
            rejection_reason=None,
            model_tag=None,
            generation_prompt_sha256=None,
            fallback_prompt_sha256=template.sha256,
            metrics=None,
            request_disposition=decision.disposition,
            request_category=decision.category,
            request_policy_version=decision.policy_version,
            model_invoked=False,
        )

    def _fallback(
        self,
        reason: str,
        *,
        request_decision: RequestPolicyDecision,
        generation: GenerationResult | None = None,
    ) -> SafeSLMResponse:
        return SafeSLMResponse(
            response_mode=ResponseMode.GENERIC_FALLBACK,
            text=self.generic_fallback.manifest.text,
            used_fallback=True,
            rejection_reason=reason,
            model_tag=generation.model_tag if generation else None,
            generation_prompt_sha256=(generation.prompt_sha256 if generation else None),
            fallback_prompt_sha256=self.generic_fallback.sha256,
            metrics=generation.metrics if generation else None,
            request_disposition=request_decision.disposition,
            request_category=request_decision.category,
            request_policy_version=request_decision.policy_version,
            model_invoked=True,
        )
