"""Functional HTTP/packet-source smoke with synthetic data and real local Ollama.

Only packet construction is replaced with public synthetic cases. The actual
API, Data retriever, SLM tool/runner, transport and output gates are exercised.
This is neither a prompting-method experiment nor personal-data acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.app import create_app
from backend.contracts.evidence import ApprovedClaimId, ResponseMode
from backend.slm.runtime import create_local_service, listed_model_tags
from backend.slm.variants import VariantKind
from benchmarks.slm_evaluation_alignment import provenance
from benchmarks.slm_model_comparison import comparison_cases
from benchmarks.slm_prohibited_request_baseline import load_packet


class ObservedTransport:
    """Retain context identifiers/counts only; delegate all I/O to the client."""

    def __init__(self, transport):
        self._transport = transport
        self.context_ids = []

    def post_json(self, endpoint, payload, timeout_seconds):
        user = json.loads(payload["messages"][1]["content"])
        self.context_ids.append(
            [item["context_id"] for item in user.get("bounded_context", [])]
        )
        return self._transport.post_json(endpoint, payload, timeout_seconds)


def run_smoke(model_tag: str) -> dict:
    service = create_local_service(model_tag=model_tag)
    observed = ObservedTransport(service.client.transport)
    service.client.transport = observed
    eligible = load_packet()
    partial = comparison_cases()[1].packet
    partial = partial.model_copy(
        update={
            "claim_policy": partial.claim_policy.model_copy(
                update={
                    "permitted_response_modes": (ResponseMode.UNCERTAINTY,),
                    "approved_claim_ids": partial.claim_policy.approved_claim_ids
                    + (ApprovedClaimId.UNCERTAINTY_DISCLOSURE,),
                }
            )
        }
    )
    cases = (
        (
            "eligible_gps",
            eligible,
            ResponseMode.NORMAL,
            "How was my movement different from my recent baseline?",
        ),
        (
            "descriptive_unlock",
            partial,
            ResponseMode.UNCERTAINTY,
            "How was my phone unlock activity different from my usual pattern?",
        ),
    )
    expected_context_ids = {
        VariantKind.BASE_LLM: [],
        VariantKind.RAG: ["packet-summary:1", "packet-summary:2"],
        VariantKind.AGENT: ["tool:packet-summary:1", "tool:packet-summary:2"],
        VariantKind.RAG_AGENT: [
            "tool:packet-summary:1",
            "tool:packet-summary:2",
            "packet-summary:1",
            "packet-summary:2",
        ],
    }
    records = []
    with TestClient(create_app(service)) as api:
        for case_id, packet, expected_mode, question in cases:
            for variant in VariantKind:
                before = len(observed.context_ids)
                with patch(
                    "backend.api.app.build_evidence_packet", return_value=packet
                ):
                    response = api.post(
                        "/respond",
                        json={
                            "participant_id": "synthetic-api-smoke",
                            "feature_id": packet.feature_window.feature_id,
                            "question": question,
                            "variant": variant.value,
                        },
                    )
                body = response.json()
                calls = observed.context_ids[before:]
                passed = (
                    response.status_code == 200
                    and body.get("response_mode") == expected_mode.value
                    and body.get("used_fallback") is False
                    and body.get("model_invoked") is True
                    and calls == [expected_context_ids[variant]]
                    and response.headers.get("cache-control") == "no-store"
                )
                records.append(
                    {
                        "case_id": case_id,
                        "variant": variant.value,
                        "passed": passed,
                        "http_status": response.status_code,
                        "model_call_context_ids": calls,
                        "response": body,
                    }
                )
                print(
                    json.dumps(
                        {
                            "case_id": case_id,
                            "variant": variant.value,
                            "passed": passed,
                            "rejection_reason": body.get("rejection_reason"),
                        }
                    ),
                    flush=True,
                )
    source_provenance = provenance()
    root = Path(__file__).resolve().parents[1]
    for name in (
        "backend/api/app.py",
        "backend/slm/packet_variants.py",
        "backend/slm/context_responder.py",
        "backend/slm/variants.py",
        "backend/data_pipeline/retrieval_source.py",
        "backend/slm/prompts/request_scope.yaml",
        "backend/slm/prompts/unsupported_window.yaml",
        "benchmarks/slm_packet_api_smoke.py",
    ):
        source_provenance["sha256_raw_bytes"][name] = hashlib.sha256(
            (root / name).read_bytes()
        ).hexdigest()
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "synthetic_http_packet_source_functional_smoke",
        "real_participant_data_used": False,
        "personal_data_acceptance": False,
        "model_tag": model_tag,
        "provenance": source_provenance,
        "passed": sum(record["passed"] for record in records),
        "total": len(records),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", choices=listed_model_tags(), default="phi4-mini:3.8b"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("use a new output path; existing evidence must not be overwritten")
    result = run_smoke(args.model)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({key: result[key] for key in ("model_tag", "passed", "total")}))
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
