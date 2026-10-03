"""Packet-source integration through HTTP, using only public synthetic fixtures."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.app import create_app, create_runtime_service
from backend.contracts.evidence import EvidencePacket
from backend.data_pipeline.retrieval_source import ApprovedPacketRetriever

FIXTURES = Path(__file__).resolve().parents[1] / "slm" / "fixtures"
QUESTION = "How was my movement different from my recent baseline?"


class RecordingTransport:
    def __init__(self):
        self.payloads = []

    def post_json(self, endpoint, payload, timeout_seconds):
        self.payloads.append(payload)
        user = json.loads(payload["messages"][1]["content"])
        draft = {
            "packet_id": user["evidence_packet"]["identity"]["packet_id"],
            **user["allowed_response_options"][0],
        }
        return {"message": {"content": json.dumps(draft)}}


def setup_api(monkeypatch, fixture="week5_gps_eligible.json"):
    packet = EvidencePacket.model_validate_json(
        (FIXTURES / fixture).read_text(encoding="utf-8")
    )
    service = create_runtime_service("ollama")
    transport = RecordingTransport()
    service.client.transport = transport
    monkeypatch.setattr(
        "backend.api.app.build_evidence_packet", lambda *args, **kwargs: packet
    )
    return TestClient(create_app(service)), transport, packet


def post(client, **changes):
    return client.post(
        "/respond",
        json={
            "participant_id": "synthetic-api-case",
            "question": QUESTION,
            "feature_id": "gps_distance",
            **changes,
        },
    )


def test_source_failure_returns_safe_response_without_model_call(monkeypatch):
    client, transport, _ = setup_api(monkeypatch)

    def fail(*args, **kwargs):
        raise RuntimeError("private-source-detail")

    monkeypatch.setattr(ApprovedPacketRetriever, "retrieve", fail)
    response = post(client)
    assert response.status_code == 200
    assert response.json()["rejection_reason"] == "approved_context_unavailable"
    assert response.json()["model_invoked"] is False
    assert response.headers["cache-control"] == "no-store"
    assert "private-source-detail" not in response.text
    assert transport.payloads == []


def test_insufficient_packet_skips_retrieval_before_safe_response(monkeypatch):
    client, transport, _ = setup_api(monkeypatch, "week5_gps_missing.json")
    calls = []

    def unexpected(*args, **kwargs):
        calls.append(True)
        raise AssertionError("State A must not retrieve")

    monkeypatch.setattr(ApprovedPacketRetriever, "retrieve", unexpected)
    response = post(client)
    assert response.status_code == 200
    assert response.json()["response_mode"] == "insufficient_data"
    assert response.json()["model_invoked"] is False
    assert calls == []
    assert transport.payloads == []


def test_returned_metadata_cannot_authorise_itself(monkeypatch):
    client, transport, _ = setup_api(monkeypatch)
    original = ApprovedPacketRetriever.retrieve

    def tamper(self, *args, **kwargs):
        items = original(self, *args, **kwargs)
        return (items[0].model_copy(update={"provenance_ref": "unreviewed:source"}),)

    monkeypatch.setattr(ApprovedPacketRetriever, "retrieve", tamper)
    response = post(client)
    assert response.status_code == 200
    assert response.json()["rejection_reason"] == "approved_context_unavailable"
    assert response.json()["model_invoked"] is False
    assert transport.payloads == []


@pytest.mark.parametrize(
    "variant,context_count,source_calls",
    [
        (None, 2, 1),
        ("base_llm", 0, 0),
        ("rag", 2, 1),
        ("agent", 2, 1),
        ("rag_agent", 4, 2),
    ],
)
def test_all_modes_use_bounded_source_and_unchanged_output_gates(
    monkeypatch, variant, context_count, source_calls
):
    client, transport, packet = setup_api(monkeypatch)
    original = ApprovedPacketRetriever.retrieve
    calls = []

    def record(self, *args, **kwargs):
        calls.append(kwargs)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ApprovedPacketRetriever, "retrieve", record)
    response = post(client, **({"variant": variant} if variant else {}))
    assert response.status_code == 200
    assert response.json()["used_fallback"] is False
    assert response.json()["model_invoked"] is True
    assert len(calls) == source_calls
    assert len(transport.payloads) == 1
    payload = transport.payloads[0]
    user = json.loads(payload["messages"][1]["content"])
    context = user.get("bounded_context", [])
    assert len(context) == context_count
    assert len({item["context_id"] for item in context}) == context_count
    assert all(set(item) == {"context_id", "content"} for item in context)
    assert packet.identity.participant_ref not in json.dumps(payload)
    if variant == "rag_agent":
        assert len(calls[1]["seed_context"]) == 2


@pytest.mark.parametrize("variant", ["rag", "agent", "rag_agent"])
def test_demo_rejects_context_mode_before_loading_data(monkeypatch, variant):
    def unexpected(*args, **kwargs):
        pytest.fail("unsupported runtime must not load participant data")

    monkeypatch.setattr("backend.api.app.build_evidence_packet", unexpected)
    response = post(TestClient(create_app(runtime_name="demo")), variant=variant)
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "changes",
    [
        {"variant": "private-unrecognised-mode"},
        {"question": " "},
        {"question": "x" * 2001},
    ],
)
def test_invalid_request_is_private_and_does_not_load_data(monkeypatch, changes):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid request must not load data")

    monkeypatch.setattr("backend.api.app.build_evidence_packet", unexpected)
    response = post(TestClient(create_app(runtime_name="demo")), **changes)
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid request body"}
    assert response.headers["cache-control"] == "no-store"


def test_openapi_exposes_optional_bounded_variant_without_changing_response():
    schema = create_app(runtime_name="demo").openapi()
    models = schema["components"]["schemas"]
    assert models["VariantKind"]["enum"] == ["base_llm", "rag", "agent", "rag_agent"]
    assert "variant" not in models["RespondRequest"]["required"]
    assert "bounded_context" not in models["SafeSLMResponse"]["properties"]
