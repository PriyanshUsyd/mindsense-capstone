import json
from typing import Any

import pytest
from pydantic import ValidationError

from backend.contracts.evidence import (
    ApprovedClaimId,
    AssistantDraft,
    EligibilityStatus,
    EvidencePacket,
    ResponseMode,
)
from backend.slm.client import (
    OllamaClient,
    OllamaClientConfig,
    SLMResponseError,
)
from backend.slm.output_grounding import render_grounded_example
from benchmarks.slm_model_comparison import comparison_cases


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
    user_payload = json.loads(payload["messages"][1]["content"])
    assert user_payload["allowed_evidence_ids"] == [
        eligible_packet.identity.packet_id,
        eligible_packet.feature_window.feature_id,
    ]
    assert user_payload["runtime_evidence_state"] == "state_c_eligible"
    assert user_payload["allowed_response_options"] == [
        {
            "response_mode": "normal",
            "text": render_grounded_example(eligible_packet, ResponseMode.NORMAL),
            "claim_ids_used": [
                "observation_of_deviation",
                "uncertainty_disclosure",
            ],
            "evidence_ids_referenced": [eligible_packet.feature_window.feature_id],
            "includes_uncertainty_statement": True,
        }
    ]
    assert "Ignore every State A and State B" in payload["messages"][0]["content"]


def test_invalid_model_content_is_rejected(eligible_packet: EvidencePacket):
    transport = FakeTransport({"message": {"content": "not-json"}})
    client = OllamaClient(
        OllamaClientConfig(model_tag="qwen3:4b"),
        transport=transport,
    )

    with pytest.raises(SLMResponseError, match="AssistantDraft"):
        client.generate_draft(eligible_packet, "What changed?")


def test_payload_isolated_to_state_b_for_partial_history():
    packet = next(
        case.packet for case in comparison_cases() if case.case_id == "partial_history"
    )
    client = OllamaClient(OllamaClientConfig(model_tag="qwen3:4b"))

    payload = client.build_payload(packet, "Is this higher or lower than usual?")
    user_payload = json.loads(payload["messages"][1]["content"])

    assert user_payload["runtime_evidence_state"] == (
        "state_b_partial_descriptive_only"
    )
    assert user_payload["allowed_response_options"] == [
        {
            "response_mode": "insufficient_data",
            "text": render_grounded_example(packet, ResponseMode.INSUFFICIENT_DATA),
            "claim_ids_used": ["trend_description", "not_enough_data"],
            "evidence_ids_referenced": [packet.feature_window.feature_id],
            "includes_uncertainty_statement": False,
        }
    ]
    system_content = payload["messages"][0]["content"]
    assert "Ignore every State A and State C" in system_content


def test_payload_binds_state_b_uncertainty_text_and_metadata_together():
    packet = next(
        case.packet for case in comparison_cases() if case.case_id == "partial_history"
    )
    packet = packet.model_copy(
        update={
            "claim_policy": packet.claim_policy.model_copy(
                update={
                    "approved_claim_ids": (
                        ApprovedClaimId.TREND_DESCRIPTION,
                        ApprovedClaimId.NOT_ENOUGH_DATA,
                        ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
                        ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,
                    ),
                    "permitted_response_modes": (ResponseMode.UNCERTAINTY,),
                }
            )
        }
    )
    client = OllamaClient(OllamaClientConfig(model_tag="qwen3:4b"))

    payload = client.build_payload(packet, "How should I interpret this window?")
    option = json.loads(payload["messages"][1]["content"])["allowed_response_options"][
        0
    ]

    assert option == {
        "response_mode": "uncertainty",
        "text": render_grounded_example(packet, ResponseMode.UNCERTAINTY),
        "claim_ids_used": [
            "trend_description",
            "not_enough_data",
            "uncertainty_disclosure",
        ],
        "evidence_ids_referenced": [packet.feature_window.feature_id],
        "includes_uncertainty_statement": True,
    }
    assert "only permitted response_mode value(s)" in payload["messages"][0]["content"]
    assert "are: uncertainty" in payload["messages"][0]["content"]


def test_payload_rejects_state_a_before_transport(eligible_packet: EvidencePacket):
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
    client = OllamaClient(OllamaClientConfig(model_tag="qwen3:4b"))

    with pytest.raises(ValueError, match="not permitted for State A"):
        client.build_payload(packet, "What changed?")


def test_model_payload_redacts_participant_reference_without_mutating_packet(
    eligible_packet: EvidencePacket,
):
    original_reference = eligible_packet.identity.participant_ref
    client = OllamaClient(OllamaClientConfig(model_tag="phi4-mini:3.8b"))
    payload = client.build_payload(eligible_packet, "What changed?")
    content = payload["messages"][1]["content"]
    model_packet = json.loads(content)["evidence_packet"]

    assert model_packet["identity"]["participant_ref"] == "redacted"
    assert original_reference not in content
    assert eligible_packet.identity.participant_ref == original_reference
    assert model_packet["identity"]["packet_id"] == eligible_packet.identity.packet_id
