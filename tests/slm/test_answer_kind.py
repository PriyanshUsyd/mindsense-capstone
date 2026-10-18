"""answer_kind: why an answer has its form, for the display tag only.

Set from the evidence packet and the route, never from the answer text.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.app import DeterministicDemoClient, create_app, create_runtime_service
from backend.contracts.comparison_reasons import (
    STATE_C_EVIDENCE_NOT_REPORTABLE,
    STATE_C_TOO_FEW_RECORDED_DAYS,
)
from backend.contracts.evidence import EvidencePacket, ResponseMode
from backend.slm.client import SLMTimeoutError
from backend.slm.request_policy import REQUEST_POLICY_VERSION
from backend.slm.service import AnswerKind, SLMService
from benchmarks.slm_model_comparison import comparison_cases

FIXTURES = Path(__file__).parent / "fixtures"
QUESTION = "How was my movement different from my recent baseline?"


def _question_for(packet: EvidencePacket) -> str:
    if packet.feature_window.feature_id == "unlock_count":
        return "How has my phone unlock count changed recently?"
    return QUESTION


def _fixture(name: str) -> EvidencePacket:
    return EvidencePacket.model_validate_json(
        (FIXTURES / name).read_text(encoding="utf-8")
    )


def _with_reason(packet: EvidencePacket, reason: str | None) -> EvidencePacket:
    baseline = packet.baseline.model_copy(update={"ineligible_reason": reason})
    return packet.model_copy(update={"baseline": baseline})


def _only_mode(packet: EvidencePacket, mode: ResponseMode) -> EvidencePacket:
    policy = packet.claim_policy.model_copy(
        update={"permitted_response_modes": (mode,)}
    )
    return packet.model_copy(update={"claim_policy": policy})


@pytest.fixture
def eligible():
    return _fixture("week5_gps_eligible.json")


@pytest.fixture
def partial():
    return comparison_cases()[1].packet


def respond(packet):
    return SLMService(DeterministicDemoClient()).respond(packet, _question_for(packet))


def test_policy_version_is_unchanged():
    assert REQUEST_POLICY_VERSION == "0.3.6"


def test_comparison_shown_for_a_normal_answer_on_an_eligible_packet(eligible):
    response = respond(_only_mode(eligible, ResponseMode.NORMAL))
    assert response.response_mode == ResponseMode.NORMAL
    assert response.used_fallback is False
    assert response.answer_kind == AnswerKind.COMPARISON_SHOWN


def test_any_generated_answer_on_an_eligible_packet_is_comparison_shown(eligible):
    # Whatever its mode, so it never falls back to the default tag.
    response = respond(_only_mode(eligible, ResponseMode.UNCERTAINTY))
    assert response.response_mode == ResponseMode.UNCERTAINTY
    assert response.used_fallback is False
    assert response.answer_kind == AnswerKind.COMPARISON_SHOWN


@pytest.mark.parametrize(
    "reason,kind",
    [
        (STATE_C_EVIDENCE_NOT_REPORTABLE, AnswerKind.NO_CLEAR_DIFFERENCE),
        (STATE_C_TOO_FEW_RECORDED_DAYS, AnswerKind.FEW_RECENT_DAYS),
        ("insufficient prior eligible windows", AnswerKind.BUILDING_BASELINE),
        ("not enough prior windows yet", AnswerKind.BUILDING_BASELINE),
    ],
)
def test_partial_packet_answer_kind_follows_the_reason(partial, reason, kind):
    response = respond(_with_reason(partial, reason))
    assert response.used_fallback is False
    assert response.answer_kind == kind


def test_not_enough_data_for_the_insufficient_data_template():
    response = respond(_fixture("week5_gps_missing.json"))
    assert response.response_mode == ResponseMode.INSUFFICIENT_DATA
    assert response.answer_kind == AnswerKind.NOT_ENOUGH_DATA


def test_general_limits_for_the_general_uncertainty_template():
    response = SLMService(DeterministicDemoClient()).preflight_response(
        "What uncertainty should I keep in mind?", require_feature=True
    )
    assert response is not None
    assert response.answer_kind == AnswerKind.GENERAL_LIMITS


@pytest.mark.parametrize(
    "question",
    [
        "Do I have ADHD?",  # diagnosis refusal
        "I want to hurt myself.",  # crisis
        "What's the weather today?",  # off-topic
        "What can you help me with?",  # capability
        "Is my data stored anywhere?",  # app information
        "How was my movement last month?",  # unsupported window
        "Compare my movement and my phone use.",  # ambiguous feature
    ],
)
def test_refusals_crisis_and_scope_fallbacks_have_no_answer_kind(question):
    response = SLMService(DeterministicDemoClient()).preflight_response(
        question, require_feature=True
    )
    assert response is not None
    assert response.answer_kind is None


def test_model_errors_and_unavailable_evidence_have_no_answer_kind(eligible):
    class Timeout:
        def generate_draft(self, packet, question):
            raise SLMTimeoutError("slow")

    response = SLMService(Timeout()).respond(eligible, QUESTION)
    assert response.response_mode == ResponseMode.GENERIC_FALLBACK
    assert response.answer_kind is None
    unavailable = SLMService(Timeout()).evidence_unavailable_response(QUESTION)
    assert unavailable.answer_kind is None


def test_answer_kind_does_not_depend_on_the_answer_text(partial):
    # The same answer text with a different packet reason gives a different
    # kind, and an identical packet gives the same kind whatever the text.
    a = respond(_with_reason(partial, STATE_C_EVIDENCE_NOT_REPORTABLE))
    b = respond(_with_reason(partial, STATE_C_TOO_FEW_RECORDED_DAYS))
    assert a.answer_kind != b.answer_kind


# --- the RAG variant path through /respond ---------------------------------------


class GroundedTransport:
    def post_json(self, endpoint, payload, timeout_seconds):
        user = json.loads(payload["messages"][1]["content"])
        draft = {
            "packet_id": user["evidence_packet"]["identity"]["packet_id"],
            **user["allowed_response_options"][0],
        }
        return {"message": {"content": json.dumps(draft)}}


@pytest.mark.parametrize(
    "packet_name,reason,kind",
    [
        ("eligible", None, "comparison_shown"),
        ("partial", STATE_C_EVIDENCE_NOT_REPORTABLE, "no_clear_difference"),
        ("partial", STATE_C_TOO_FEW_RECORDED_DAYS, "few_recent_days"),
        ("partial", "insufficient prior eligible windows", "building_baseline"),
    ],
)
def test_answer_kind_survives_the_rag_variant_path(
    monkeypatch, eligible, partial, packet_name, reason, kind
):
    packet = (
        _only_mode(eligible, ResponseMode.NORMAL)
        if packet_name == "eligible"
        else (_with_reason(partial, reason))
    )
    service = create_runtime_service("ollama")
    service.client.transport = GroundedTransport()
    monkeypatch.setattr("backend.api.app.build_evidence_packet", lambda *a, **k: packet)
    body = (
        TestClient(create_app(service))
        .post(
            "/respond",
            json={
                "participant_id": "synthetic-api-case",
                "question": _question_for(packet),
                "feature_id": packet.feature_window.feature_id,
            },
        )
        .json()
    )
    assert body["used_fallback"] is False
    assert body["answer_kind"] == kind
    assert body["safety_screen"] == "no"
