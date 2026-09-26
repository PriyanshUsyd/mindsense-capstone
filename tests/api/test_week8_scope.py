"""SLM scope checks at the shared HTTP boundary, with synthetic data only."""

import pytest
from fastapi.testclient import TestClient

from backend.api.app import create_app
from benchmarks.slm_prohibited_request_baseline import load_packet


@pytest.mark.parametrize(
    "question,reason",
    [
        ("How am I doing?", "ambiguous_feature_request"),
        ("What changed in my GPS and unlock data?", "ambiguous_feature_request"),
        (
            "What's changed in my behavior over the last 3 days?",
            "unsupported_time_window",
        ),
        (
            "How has my phone-unlock activity changed over the past couple of weeks?",
            "unsupported_time_window",
        ),
        ("Based on my data, do you think I'm depressed?", "diagnosis_request_detected"),
    ],
)
def test_pilot_boundaries_stop_before_alias_resolution_or_data_load(
    monkeypatch, question, reason
):
    def forbidden(*args, **kwargs):
        pytest.fail("ambiguous or prohibited input must not read participant data")

    monkeypatch.setattr("backend.api.app.build_evidence_packet", forbidden)
    monkeypatch.setattr("backend.api.app.select_local_demo_participant", forbidden)
    result = TestClient(create_app()).post(
        "/respond", json={"participant_id": "local-demo", "question": question}
    )
    assert result.status_code == 200
    assert result.json()["rejection_reason"] == reason
    assert result.json()["model_invoked"] is False


def test_explicit_feature_scopes_a_contextual_question(monkeypatch):
    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", lambda *a, **kw: load_packet()
    )
    response = TestClient(create_app()).post(
        "/respond",
        json={
            "participant_id": "synthetic-only",
            "question": "What changed?",
            "feature_id": "gps_distance",
        },
    )
    assert response.status_code == 200
    assert response.json()["used_fallback"] is False


def test_wrong_feature_returned_by_adapter_is_not_answered(monkeypatch):
    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", lambda *a, **kw: load_packet()
    )
    response = TestClient(create_app()).post(
        "/respond",
        json={
            "participant_id": "synthetic-only",
            "question": "What changed in my unlock data?",
        },
    )
    assert response.status_code == 200
    assert response.json()["rejection_reason"] == "feature_request_mismatch"
    assert response.json()["model_invoked"] is False


def test_empty_selected_feature_does_not_bypass_ambiguity_preflight(monkeypatch):
    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet",
        lambda *a, **kw: pytest.fail("blank scope must not reach the packet builder"),
    )
    response = TestClient(create_app()).post(
        "/respond",
        json={
            "participant_id": "synthetic-only",
            "question": "What changed?",
            "feature_id": "",
        },
    )
    assert response.status_code == 200
    assert response.json()["rejection_reason"] == "ambiguous_feature_request"
