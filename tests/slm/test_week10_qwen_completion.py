"""Verify the new adapter's model factor without real generation or sealed data."""

import json

from benchmarks import slm_prompting_comparison as original
from benchmarks import slm_week10_qwen_completion as adapter


class RecordingGroundedTransport:
    def __init__(self):
        self.payloads = []

    def post_json(self, endpoint, payload, timeout_seconds):
        self.payloads.append(payload)
        user = json.loads(payload["messages"][1]["content"])
        return {
            "message": {
                "content": json.dumps(
                    {
                        "packet_id": user["evidence_packet"]["identity"]["packet_id"],
                        **user["allowed_response_options"][0],
                    }
                )
            }
        }


def test_qwen_conditions_change_only_model_and_protocol_identifier():
    cases = original.load_public_cases()
    baseline, old_prompts = original.load_conditions(cases)
    extension, prompts = adapter.qwen_conditions(cases)
    assert {k for k in baseline if baseline[k] != extension[k]} == {
        "model_tag",
        "protocol_version",
    }
    assert extension["model_tag"] == "qwen3:4b"
    assert {k: p.sha256 for k, p in prompts.items()} == {
        k: p.sha256 for k, p in old_prompts.items()
    }
    assert original.MODEL == "phi4-mini:3.8b"


def test_actual_qwen_transport_preserves_conditions_and_human_blanks():
    transports = {k: RecordingGroundedTransport() for k in ("Z", "F")}
    result = adapter.run_prompting(transport_factory=transports.get)
    assert len(result["records"]) == 180
    assert sum(r["execution_status"] == "not_covered" for r in result["records"]) == 12
    for condition in ("Z", "F"):
        assert len(transports[condition].payloads) == 12
        for payload in transports[condition].payloads:
            assert payload["model"] == "qwen3:4b"
            assert payload["options"] == {"temperature": 0, "seed": 42}
            assert payload["think"] is False
            assert (original.DEMO_MARKER in payload["messages"][0]["content"]) == (
                condition == "F"
            )
    assert all(
        all(x is None for x in r["human_review"].values()) for r in result["records"]
    )
    assert result["source_hashes_still_match"]
    assert original.MODEL == "phi4-mini:3.8b"
