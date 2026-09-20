"""
Tests for backend/api/app.py — the shared HTTP wrapper around SLMService,
built 2026-09-05 to unblock Sheng Wang's Week 5 UI-integration task (no
commit from Sheng exists anywhere in this repo; see
docs/ui/chat-states-design.md and frontend/src/features/chat/App.tsx for
the explicit "filled in by Priyansh" labels).

FIXED 2026-09-16: `/respond` used to accept a client-supplied
`evidence_packet` dict and pass it straight to `SLMService.respond()`
without ever calling this codebase's own classification logic — see
`backend/statistics/participant_evidence.py` and this file's docstring
fix in app.py. The HTTP-contract tests below now cover the real
`participant_id` request shape; SLMService's own packet-driven behaviour
(eligible -> normal, missing evidence -> insufficient_data, prohibited
request -> refusal) is exercised directly against `SLMService`, one layer
down from HTTP, using the same fixtures as before — that behaviour did not
change, only how the packet reaches it.

Uses the deterministic demo client (no real Ollama daemon required), same
pattern as benchmarks/slm_prohibited_request_baseline.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.api.app import (
    DeterministicDemoClient,
    create_app,
    create_runtime_service,
)
from backend.contracts.evidence import (
    ApprovedClaimId,
    AssistantDraft,
    EvidencePacket,
    ResponseMode,
)
from backend.slm.client import OllamaClient
from backend.slm.output_grounding import render_grounded_example
from backend.statistics.participant_evidence import UnknownFeature, UnknownParticipant

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "slm" / "fixtures"


def _load_packet(name: str) -> EvidencePacket:
    raw = json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    return EvidencePacket.model_validate_json(json.dumps(raw))


def test_health_endpoint():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_models_endpoint_exposes_only_manifest_candidates():
    client = TestClient(create_app(runtime_name="ollama"))

    resp = client.get("/models")

    assert resp.status_code == 200
    assert resp.json() == {
        "runtime": "ollama",
        "selection_enabled": True,
        "default_model_tag": "phi4-mini:3.8b",
        "available_model_tags": ["phi4-mini:3.8b", "qwen3:4b"],
    }


def test_runtime_selector_keeps_the_demo_client_as_the_safe_default(monkeypatch):
    monkeypatch.delenv("MINDSENSE_SLM_RUNTIME", raising=False)

    service = create_runtime_service()

    assert isinstance(service.client, DeterministicDemoClient)


def test_runtime_selector_connects_the_api_to_richards_pinned_ollama_client():
    service = create_runtime_service("ollama")

    assert isinstance(service.client, OllamaClient)
    assert service.client.config.model_tag == "phi4-mini:3.8b"
    assert service.client.config.endpoint == "http://127.0.0.1:11434/api/chat"


def test_runtime_selector_rejects_an_unknown_runtime():
    with pytest.raises(ValueError, match="MINDSENSE_SLM_RUNTIME"):
        create_runtime_service("cloud")


class _FakeOllamaTransport:
    def __init__(self, draft: AssistantDraft) -> None:
        self.draft = draft
        self.calls: list[tuple[str, dict[str, Any], float]] = []

    def post_json(
        self, endpoint: str, payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]:
        self.calls.append((endpoint, payload, timeout_seconds))
        return {
            "message": {"role": "assistant", "content": self.draft.model_dump_json()},
            "total_duration": 1_000,
            "eval_count": 24,
        }


# --- SLMService behaviour, one layer below HTTP (packet-driven, unchanged
# by this fix — only how the packet reaches SLMService changed) ------------


def test_respond_runs_through_the_configured_ollama_client_without_real_network():
    packet = _load_packet("week5_gps_eligible.json")
    draft = AssistantDraft(
        packet_id=packet.identity.packet_id,
        response_mode=ResponseMode.NORMAL,
        claim_ids_used=(
            ApprovedClaimId.OBSERVATION_OF_DEVIATION,
            ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
        ),
        evidence_ids_referenced=(packet.feature_window.feature_id,),
        text=render_grounded_example(packet, ResponseMode.NORMAL),
        includes_uncertainty_statement=True,
    )
    service = create_runtime_service("ollama")
    assert isinstance(service.client, OllamaClient)
    transport = _FakeOllamaTransport(draft)
    service.client.transport = transport

    response = service.respond(
        packet, "How was my movement different from my recent baseline?"
    )

    assert response.response_mode == "normal"
    assert response.model_invoked is True
    assert response.model_tag == "phi4-mini:3.8b"
    assert response.text == draft.text
    assert len(transport.calls) == 1
    endpoint, payload, _ = transport.calls[0]
    assert endpoint == "http://127.0.0.1:11434/api/chat"
    assert payload["model"] == "phi4-mini:3.8b"


def test_respond_returns_a_real_normal_response_for_eligible_evidence():
    service = create_runtime_service("demo")
    packet = _load_packet("week5_gps_eligible.json")

    response = service.respond(
        packet, "How was my movement different from my recent baseline?"
    )

    assert response.response_mode == "normal"
    assert response.model_invoked is True
    assert response.used_fallback is False
    # The text must genuinely reflect this packet's own values (grounded),
    # not be hardcoded copy — see backend/slm/output_grounding.py.
    assert "3.8" in response.text or "3.80" in response.text


def test_respond_returns_insufficient_data_for_missing_evidence():
    service = create_runtime_service("demo")
    packet = _load_packet("week5_gps_missing.json")

    response = service.respond(packet, "How am I doing?")

    assert response.response_mode == "insufficient_data"
    assert response.model_invoked is False


def test_respond_routes_a_prohibited_request_to_deterministic_refusal_without_invoking_the_model():
    service = create_runtime_service("demo")
    packet = _load_packet("week5_gps_eligible.json")

    response = service.respond(packet, "Diagnose me with depression.")

    assert response.response_mode == "refusal"
    assert response.model_invoked is False
    assert response.used_fallback is True


# --- HTTP contract: /respond builds the real packet server-side ----------


def test_respond_builds_the_real_packet_server_side_not_from_the_client(monkeypatch):
    """The core of this fix: the HTTP body carries only an identifier, and
    the packet handed to SLMService is whatever the real builder returns —
    never something the client could shape by sending a different body."""
    fixture_packet = _load_packet("week5_gps_eligible.json")
    calls: list[tuple[str, str]] = []

    def fake_build_evidence_packet(
        participant_id: str, feature_id: str = "gps_distance"
    ):
        calls.append((participant_id, feature_id))
        return fixture_packet

    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", fake_build_evidence_packet
    )
    client = TestClient(create_app())

    resp = client.post(
        "/respond",
        json={
            "participant_id": "u42",
            "question": "How was my movement different from my recent baseline?",
            "feature_id": "gps_distance",
        },
    )

    assert resp.status_code == 200
    assert calls == [("u42", "gps_distance")]
    body = resp.json()
    assert body["response_mode"] == "normal"
    assert "3.8" in body["text"] or "3.80" in body["text"]


def test_respond_resolves_the_local_demo_alias_only_inside_the_backend(monkeypatch):
    fixture_packet = _load_packet("week5_gps_eligible.json")
    built_for: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "backend.api.app.select_local_demo_participant",
        lambda feature_id="gps_distance": "resolved-local-participant",
    )

    def fake_build_evidence_packet(
        participant_id: str, feature_id: str = "gps_distance"
    ):
        built_for.append((participant_id, feature_id))
        return fixture_packet

    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", fake_build_evidence_packet
    )
    client = TestClient(create_app())

    resp = client.post(
        "/respond",
        json={
            "participant_id": "local-demo",
            "question": "How was my movement different from my recent baseline?",
            "feature_id": "gps_distance",
        },
    )

    assert resp.status_code == 200
    assert built_for == [("resolved-local-participant", "gps_distance")]
    assert "resolved-local-participant" not in resp.text


def test_respond_infers_feature_before_resolving_the_local_demo_alias(monkeypatch):
    fixture_packet = _load_packet("week5_gps_eligible.json")
    selected_for: list[str] = []
    built_for: list[tuple[str, str]] = []

    def fake_select_local_demo_participant(feature_id: str) -> str:
        selected_for.append(feature_id)
        return "resolved-local-participant"

    def fake_build_evidence_packet(participant_id: str, feature_id: str):
        built_for.append((participant_id, feature_id))
        return fixture_packet

    monkeypatch.setattr(
        "backend.api.app.select_local_demo_participant",
        fake_select_local_demo_participant,
    )
    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", fake_build_evidence_packet
    )
    client = TestClient(create_app())

    resp = client.post(
        "/respond",
        json={
            "participant_id": "local-demo",
            "question": "How has my phone-unlock activity changed?",
        },
    )

    assert resp.status_code == 200
    assert selected_for == ["unlock_count"]
    assert built_for == [("resolved-local-participant", "unlock_count")]


def test_respond_selects_a_manifest_model_only_in_ollama_mode(monkeypatch):
    fixture_packet = _load_packet("week5_gps_eligible.json")
    selected: list[str | None] = []

    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet",
        lambda participant_id, feature_id="gps_distance": fixture_packet,
    )

    def fake_create_local_service(*, model_tag=None, **kwargs):
        del kwargs
        selected.append(model_tag)
        return create_runtime_service("demo")

    monkeypatch.setattr(
        "backend.api.app.create_local_service", fake_create_local_service
    )
    client = TestClient(create_app(runtime_name="ollama"))

    resp = client.post(
        "/respond",
        json={
            "participant_id": "u42",
            "question": "How was my movement different from my recent baseline?",
            "model_tag": "qwen3:4b",
        },
    )

    assert resp.status_code == 200
    assert selected == ["qwen3:4b"]


def test_respond_rejects_model_selection_in_demo_mode_before_building_packet(
    monkeypatch,
):
    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet",
        lambda *args, **kwargs: pytest.fail("packet builder must not run"),
    )
    client = TestClient(create_app(runtime_name="demo"))

    resp = client.post(
        "/respond",
        json={
            "participant_id": "u42",
            "question": "How am I doing?",
            "model_tag": "qwen3:4b",
        },
    )

    assert resp.status_code == 422
    assert "ollama runtime" in resp.json()["detail"]


def test_respond_rejects_unlisted_model_before_building_packet(monkeypatch):
    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet",
        lambda *args, **kwargs: pytest.fail("packet builder must not run"),
    )
    client = TestClient(create_app(runtime_name="ollama"))

    resp = client.post(
        "/respond",
        json={
            "participant_id": "u42",
            "question": "How am I doing?",
            "model_tag": "unlisted:1b",
        },
    )

    assert resp.status_code == 422
    assert "pinned comparison candidates" in resp.json()["detail"]


def test_respond_defaults_feature_id_to_gps_distance_when_omitted(monkeypatch):
    """"How am I doing?" matches neither feature's keywords, so with
    feature_id omitted this exercises infer_feature_from_question's
    ambiguous fallback, not a hardcoded default."""
    fixture_packet = _load_packet("week5_gps_eligible.json")
    calls: list[tuple[str, str]] = []

    def fake_build_evidence_packet(
        participant_id: str, feature_id: str = "gps_distance"
    ):
        calls.append((participant_id, feature_id))
        return fixture_packet

    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", fake_build_evidence_packet
    )
    client = TestClient(create_app())

    resp = client.post(
        "/respond", json={"participant_id": "u42", "question": "How am I doing?"}
    )

    assert resp.status_code == 200
    assert calls == [("u42", "gps_distance")]


def test_respond_infers_unlock_count_from_an_unlock_question_when_feature_id_omitted(
    monkeypatch,
):
    """FIXED 2026-09-20: the week 8 pilot bug — an unlock-related question
    used to still be answered from gps_distance because /respond never read
    the question text. feature_id omitted here so inference actually runs."""
    fixture_packet = _load_packet("week5_gps_eligible.json")
    calls: list[tuple[str, str]] = []

    def fake_build_evidence_packet(
        participant_id: str, feature_id: str = "gps_distance"
    ):
        calls.append((participant_id, feature_id))
        return fixture_packet

    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", fake_build_evidence_packet
    )
    client = TestClient(create_app())

    resp = client.post(
        "/respond",
        json={
            "participant_id": "u42",
            "question": "How has my phone-unlock activity changed over the past couple of weeks?",
        },
    )

    assert resp.status_code == 200
    assert calls == [("u42", "unlock_count")]


def test_respond_honours_an_explicit_feature_id_over_inference(monkeypatch):
    """An explicit feature_id (tooling/tests) still wins even when the
    question text points elsewhere — inference only fills the gap."""
    fixture_packet = _load_packet("week5_gps_eligible.json")
    calls: list[tuple[str, str]] = []

    def fake_build_evidence_packet(
        participant_id: str, feature_id: str = "gps_distance"
    ):
        calls.append((participant_id, feature_id))
        return fixture_packet

    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", fake_build_evidence_packet
    )
    client = TestClient(create_app())

    resp = client.post(
        "/respond",
        json={
            "participant_id": "u42",
            "question": "How has my phone-unlock activity changed?",
            "feature_id": "gps_distance",
        },
    )

    assert resp.status_code == 200
    assert calls == [("u42", "gps_distance")]


def test_respond_returns_404_for_an_unknown_participant(monkeypatch):
    def fake_build_evidence_packet(
        participant_id: str, feature_id: str = "gps_distance"
    ):
        raise UnknownParticipant(
            f"no sensing rows for participant_id {participant_id!r}"
        )

    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", fake_build_evidence_packet
    )
    client = TestClient(create_app())

    resp = client.post(
        "/respond",
        json={"participant_id": "not-a-real-uid", "question": "How am I doing?"},
    )

    assert resp.status_code == 404


def test_respond_returns_422_for_an_unknown_feature_id(monkeypatch):
    def fake_build_evidence_packet(
        participant_id: str, feature_id: str = "gps_distance"
    ):
        raise UnknownFeature(f"unknown feature_id {feature_id!r}")

    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", fake_build_evidence_packet
    )
    client = TestClient(create_app())

    resp = client.post(
        "/respond",
        json={
            "participant_id": "u42",
            "question": "How am I doing?",
            "feature_id": "bogus",
        },
    )

    assert resp.status_code == 422


def test_respond_rejects_a_malformed_request_body():
    client = TestClient(create_app())
    resp = client.post("/respond", json={"question": "missing the participant id"})
    assert resp.status_code == 422


def test_respond_rejects_a_client_supplied_evidence_packet():
    """Regression guard for the exact vulnerability being fixed: the old
    `evidence_packet` field must now be rejected outright (extra='forbid'),
    not silently ignored."""
    client = TestClient(create_app())
    resp = client.post(
        "/respond",
        json={
            "evidence_packet": {"baseline": {"eligibility_status": "eligible"}},
            "question": "How am I doing?",
        },
    )
    assert resp.status_code == 422
