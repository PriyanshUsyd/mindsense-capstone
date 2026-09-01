from backend.contracts.evidence import (
    AssistantDraft,
    EligibilityStatus,
    EvidencePacket,
    ResponseMode,
)
from backend.slm.client import (
    GenerationMetrics,
    GenerationResult,
    SLMUnavailableError,
)
from backend.slm.request_policy import RequestCategory, RequestDisposition
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


class MustNotRunGenerator:
    def generate_draft(self, packet: EvidencePacket, question: str) -> GenerationResult:
        raise AssertionError("prohibited requests must not reach the local model")


def test_valid_draft_becomes_response(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    response = SLMService(StubGenerator(_generation(valid_draft))).respond(
        eligible_packet, "What changed?"
    )

    assert response.used_fallback is False
    assert response.response_mode == ResponseMode.NORMAL
    assert response.text == valid_draft.text
    assert response.request_disposition == RequestDisposition.ALLOW
    assert response.request_category == RequestCategory.IN_SCOPE
    assert response.model_invoked is True


def test_client_failure_uses_versioned_generic_fallback(
    eligible_packet: EvidencePacket,
):
    response = SLMService(FailingGenerator()).respond(eligible_packet, "What changed?")

    assert response.used_fallback is True
    assert response.response_mode == ResponseMode.GENERIC_FALLBACK
    assert response.rejection_reason == "model_generation_failed"
    assert response.fallback_prompt_sha256
    assert response.model_invoked is True


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


def test_diagnosis_request_is_refused_before_model_call(
    eligible_packet: EvidencePacket,
):
    response = SLMService(MustNotRunGenerator()).respond(
        eligible_packet, "Can you diagnose me with depression?"
    )

    assert response.response_mode == ResponseMode.REFUSAL
    assert response.request_disposition == RequestDisposition.REFUSE
    assert response.request_category == RequestCategory.DIAGNOSIS_SEEKING
    assert response.rejection_reason == "diagnosis_request_detected"
    assert response.model_invoked is False
    assert response.model_tag is None
    assert response.fallback_prompt_sha256


def test_crisis_request_uses_versioned_crisis_template_before_model_call(
    eligible_packet: EvidencePacket,
):
    response = SLMService(MustNotRunGenerator()).respond(
        eligible_packet, "I want to kill myself."
    )

    assert response.response_mode == ResponseMode.CRISIS_AWARE_FALLBACK
    assert response.request_disposition == RequestDisposition.CRISIS
    assert response.request_category == RequestCategory.CRISIS_SELF_HARM
    assert response.rejection_reason == "crisis_language_detected"
    assert response.model_invoked is False
    assert "13 11 14" in response.text
    assert response.fallback_prompt_sha256


def test_state_a_missing_data_uses_deterministic_template_before_model_call(
    eligible_packet: EvidencePacket,
):
    packet = eligible_packet.model_copy(
        update={
            "baseline": eligible_packet.baseline.model_copy(
                update={
                    "value": None,
                    "n_baseline_observations": 0,
                    "eligibility_status": (
                        EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW
                    ),
                    "ineligible_reason": "no eligible observations",
                }
            ),
            "evidence": None,
        }
    )
    response = SLMService(MustNotRunGenerator()).respond(
        packet, "How was my movement different from my baseline?"
    )

    assert response.response_mode == ResponseMode.INSUFFICIENT_DATA
    assert response.used_fallback is False
    assert response.rejection_reason is None
    assert response.model_invoked is False
    assert "not enough data" in response.text.lower()
    assert response.fallback_prompt_sha256
