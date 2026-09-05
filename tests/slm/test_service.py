from backend.contracts.evidence import AssistantDraft, EvidencePacket, ResponseMode
from backend.slm.client import (
    GenerationMetrics,
    GenerationResult,
    SLMUnavailableError,
)
from backend.slm.service import SLMService


def _generation(draft: AssistantDraft) -> GenerationResult:
    return GenerationResult(
        draft=draft,
        model_tag="phi4-mini:3.8b",
        prompt_id="evidence_explainer",
        prompt_version="0.1.0",
        prompt_sha256="a" * 64,
        metrics=GenerationMetrics(total_duration_ns=1_000),
    )


class StubGenerator:
    def __init__(self, generation: GenerationResult) -> None:
        self.generation = generation

    def generate_draft(self, packet: EvidencePacket, question: str) -> GenerationResult:
        return self.generation


class FailingGenerator:
    def generate_draft(self, packet: EvidencePacket, question: str) -> GenerationResult:
        raise SLMUnavailableError("offline")


def test_valid_draft_becomes_response(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    response = SLMService(StubGenerator(_generation(valid_draft))).respond(
        eligible_packet, "What changed?"
    )

    assert response.used_fallback is False
    assert response.response_mode == ResponseMode.NORMAL
    assert response.text == valid_draft.text


def test_client_failure_uses_versioned_generic_fallback(
    eligible_packet: EvidencePacket,
):
    response = SLMService(FailingGenerator()).respond(eligible_packet, "What changed?")

    assert response.used_fallback is True
    assert response.response_mode == ResponseMode.GENERIC_FALLBACK
    assert response.rejection_reason == "model_generation_failed"
    assert response.fallback_prompt_sha256


def test_prohibited_phrase_uses_fallback(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    unsafe = valid_draft.model_copy(
        update={"text": "Your phone use caused your anxiety."}
    )
    response = SLMService(StubGenerator(_generation(unsafe))).respond(
        eligible_packet, "Why did this happen?"
    )

    assert response.used_fallback is True
    assert response.rejection_reason == "prohibited_phrase_detected"


def test_model_cannot_select_crisis_fallback(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    unsafe = valid_draft.model_copy(
        update={"response_mode": ResponseMode.CRISIS_AWARE_FALLBACK}
    )
    response = SLMService(StubGenerator(_generation(unsafe))).respond(
        eligible_packet, "question"
    )

    assert response.used_fallback is True
    assert response.rejection_reason == "model_must_not_select_crisis_fallback"
