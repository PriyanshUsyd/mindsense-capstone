"""Safe orchestration from EvidencePacket to a user-facing local response."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from backend.contracts.evidence import EvidencePacket, ResponseMode
from backend.slm.client import (
    GenerationMetrics,
    GenerationResult,
    SLMClientError,
)
from backend.slm.prompt_loader import LoadedFallbackPrompt, load_fallback_prompt
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


class SLMService:
    """Validate every model draft or return the versioned safe fallback."""

    def __init__(
        self,
        client: DraftGenerator,
        *,
        generic_fallback: LoadedFallbackPrompt | None = None,
    ) -> None:
        self.client = client
        self.generic_fallback = generic_fallback or load_fallback_prompt()
        if (
            self.generic_fallback.manifest.response_mode
            != ResponseMode.GENERIC_FALLBACK
        ):
            raise ValueError("generic fallback manifest has the wrong response_mode")

    def respond(self, packet: EvidencePacket, question: str) -> SafeSLMResponse:
        try:
            generation = self.client.generate_draft(packet, question)
        except (SLMClientError, ValueError):
            return self._fallback("model_generation_failed")

        draft = generation.draft
        if draft.response_mode == ResponseMode.CRISIS_AWARE_FALLBACK:
            return self._fallback(
                "model_must_not_select_crisis_fallback", generation=generation
            )
        if draft.response_mode == ResponseMode.GENERIC_FALLBACK:
            return self._fallback("model_requested_fallback", generation=generation)

        is_valid, rejection = validate_draft(packet, draft)
        if not is_valid:
            return self._fallback(str(rejection), generation=generation)

        return SafeSLMResponse(
            response_mode=draft.response_mode,
            text=draft.text,
            used_fallback=False,
            rejection_reason=None,
            model_tag=generation.model_tag,
            generation_prompt_sha256=generation.prompt_sha256,
            fallback_prompt_sha256=None,
            metrics=generation.metrics,
        )

    def _fallback(
        self,
        reason: str,
        *,
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
        )
