"""
Tests for backend/api/app.py — the shared HTTP wrapper around SLMService,
built 2026-09-05 to unblock Sheng Wang's Week 5 UI-integration task (no
commit from Sheng exists anywhere in this repo; see
docs/ui/chat-states-design.md and frontend/src/features/chat/App.tsx for
the explicit "filled in by Priyansh" labels).

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

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "slm" / "fixtures"


def _load_packet(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_health_endpoint():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


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


def test_respond_runs_through_the_configured_ollama_client_without_real_network():
    raw_packet = _load_packet("week5_gps_eligible.json")
    packet = EvidencePacket.model_validate_json(json.dumps(raw_packet))
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
    client = TestClient(create_app(service))

    resp = client.post(
        "/respond",
        json={
            "evidence_packet": raw_packet,
            "question": "How was my movement different from my recent baseline?",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["response_mode"] == "normal"
    assert body["model_invoked"] is True
    assert body["model_tag"] == "phi4-mini:3.8b"
    assert body["text"] == draft.text
    assert len(transport.calls) == 1
    endpoint, payload, _ = transport.calls[0]
    assert endpoint == "http://127.0.0.1:11434/api/chat"
    assert payload["model"] == "phi4-mini:3.8b"


def test_respond_returns_a_real_normal_response_for_eligible_evidence():
    client = TestClient(create_app())
    packet = _load_packet("week5_gps_eligible.json")

    resp = client.post(
        "/respond",
        json={
            "evidence_packet": packet,
            "question": "How was my movement different from my recent baseline?",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_mode"] == "normal"
    assert body["model_invoked"] is True
    assert body["used_fallback"] is False
    # The text must genuinely reflect this packet's own values (grounded),
    # not be hardcoded copy — see backend/slm/output_grounding.py.
    assert "3.8" in body["text"] or "3.80" in body["text"]


def test_respond_returns_insufficient_data_for_missing_evidence():
    client = TestClient(create_app())
    packet = _load_packet("week5_gps_missing.json")

    resp = client.post(
        "/respond",
        json={"evidence_packet": packet, "question": "How am I doing?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_mode"] == "insufficient_data"
    assert body["model_invoked"] is False


def test_respond_routes_a_prohibited_request_to_deterministic_refusal_without_invoking_the_model():
    client = TestClient(create_app())
    packet = _load_packet("week5_gps_eligible.json")

    resp = client.post(
        "/respond",
        json={"evidence_packet": packet, "question": "Diagnose me with depression."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["response_mode"] == "refusal"
    assert body["model_invoked"] is False
    assert body["used_fallback"] is True


def test_respond_rejects_a_malformed_request_body():
    client = TestClient(create_app())
    resp = client.post("/respond", json={"question": "missing the packet"})
    assert resp.status_code == 422
