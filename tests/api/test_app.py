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

from fastapi.testclient import TestClient

from backend.api.app import create_app

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "slm" / "fixtures"


def _load_packet(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_health_endpoint():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


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
