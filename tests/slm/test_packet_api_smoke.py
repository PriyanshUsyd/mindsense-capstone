"""Ensure the functional smoke reaches generation for both public packet states."""

import json

from backend.slm.runtime import create_local_service
from benchmarks import slm_packet_api_smoke


class FixtureTransport:
    def post_json(self, endpoint, payload, timeout_seconds):
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


def test_http_smoke_covers_both_generated_states_without_real_network(monkeypatch):
    service = create_local_service(model_tag="phi4-mini:3.8b")
    service.client.transport = FixtureTransport()
    monkeypatch.setattr(
        slm_packet_api_smoke, "create_local_service", lambda **_: service
    )
    result = slm_packet_api_smoke.run_smoke("phi4-mini:3.8b")
    assert result["passed"] == result["total"] == 8
    assert result["real_participant_data_used"] is False
    assert {row["response"]["response_mode"] for row in result["records"]} == {
        "normal",
        "uncertainty",
    }
