from typing import Any

import pytest
from pydantic import ValidationError

from backend.contracts.evidence import AssistantDraft, EvidencePacket
from backend.slm.client import (
    OllamaClient,
    OllamaClientConfig,
    SLMResponseError,
)


class FakeTransport:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, Any], float]] = []

    def post_json(
        self, endpoint: str, payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]:
        self.calls.append((endpoint, payload, timeout_seconds))
        return self.response


def _response_for(draft: AssistantDraft) -> dict[str, Any]:
    return {
        "message": {"role": "assistant", "content": draft.model_dump_json()},
        "total_duration": 1_000,
        "prompt_eval_count": 100,
        "eval_count": 50,
    }


def test_config_rejects_non_loopback_endpoint():
    with pytest.raises(ValidationError, match="loopback"):
        OllamaClientConfig(
            model_tag="phi4-mini:3.8b",
            endpoint="http://example.com/api/chat",
        )


@pytest.mark.parametrize("model_tag", ["phi4-mini", "phi4-mini:latest"])
def test_config_rejects_unpinned_model_tags(model_tag):
    with pytest.raises(ValidationError, match="exact"):
        OllamaClientConfig(model_tag=model_tag)


def test_payload_is_schema_constrained_and_deterministic(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    transport = FakeTransport(_response_for(valid_draft))
    client = OllamaClient(
        OllamaClientConfig(model_tag="phi4-mini:3.8b"),
        transport=transport,
    )

    result = client.generate_draft(eligible_packet, "What changed?")

    assert result.draft == valid_draft
    assert result.prompt_sha256
    endpoint, payload, timeout = transport.calls[0]
    assert endpoint == "http://127.0.0.1:11434/api/chat"
    assert timeout == 120.0
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"] == {"temperature": 0, "seed": 42}
    assert payload["format"] == AssistantDraft.model_json_schema()
    assert eligible_packet.identity.packet_id in payload["messages"][1]["content"]


def test_invalid_model_content_is_rejected(eligible_packet: EvidencePacket):
    transport = FakeTransport({"message": {"content": "not-json"}})
    client = OllamaClient(
        OllamaClientConfig(model_tag="qwen3:4b"),
        transport=transport,
    )

    with pytest.raises(SLMResponseError, match="AssistantDraft"):
        client.generate_draft(eligible_packet, "What changed?")
