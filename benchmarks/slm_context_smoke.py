"""Functional SLM context smoke using synthetic adapters, not a quality study.

The in-memory source and deterministic tool selector here are test fixtures.
They do not provision a production store or complete Data/Privacy acceptance.
No prompting-method comparison or real participant data is involved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.slm.context_responder import (
    CONTEXT_POLICY_VERSION,
    ContextApproval,
    PacketContextResponder,
    packet_context_digest,
    render_packet_context_summaries,
)
from backend.slm.runtime import create_local_service, listed_model_tags
from backend.slm.variants import (
    ContextDataClass,
    ContextItem,
    ContextSource,
    VariantKind,
    VariantRequest,
    VariantRunner,
)
from benchmarks.slm_evaluation_alignment import provenance
from benchmarks.slm_prohibited_request_baseline import load_packet


class SyntheticRetriever:
    def __init__(self, item: ContextItem) -> None:
        self._item = item

    def retrieve(self, packet, question, *, top_k, seed_context):
        return (self._item,)[:top_k]


class SyntheticStateTool:
    name = "get_evidence_state"

    def __init__(self, item: ContextItem) -> None:
        self._item = item

    def run(self, packet, question):
        return (self._item,)


class SyntheticSelector:
    def select_tools(self, packet, question, *, allowed_tools, max_tool_calls):
        return ("get_evidence_state",) if "get_evidence_state" in allowed_tools else ()


def run_smoke(model_tag: str) -> dict:
    packet = load_packet()
    summaries = render_packet_context_summaries(packet)
    items = tuple(
        ContextItem(
            context_id=f"synthetic:week8:{index}",
            source=source,
            data_classification=ContextDataClass.SYNTHETIC,
            content=summaries[index],
            provenance_ref=f"fixture:week8/summary/{index}",
        )
        for index, source in enumerate(
            (ContextSource.PERSONAL_SUMMARY, ContextSource.TOOL_RESULT)
        )
    )
    approvals = tuple(
        ContextApproval(
            context_id=item.context_id,
            provenance_ref=item.provenance_ref,
            packet_sha256=packet_context_digest(packet),
            source=item.source,
            data_classification=item.data_classification,
        )
        for item in items
    )
    service = create_local_service(model_tag=model_tag)
    runner = VariantRunner(
        PacketContextResponder(service.client, approvals=approvals),
        retriever=SyntheticRetriever(items[0]),
        tool_selector=SyntheticSelector(),
        tools=(SyntheticStateTool(items[1]),),
    )
    records = []
    expected_counts = {
        VariantKind.RAG: 1,
        VariantKind.AGENT: 1,
        VariantKind.RAG_AGENT: 2,
    }
    for variant, count in expected_counts.items():
        result = runner.run(
            VariantRequest(
                variant=variant,
                packet=packet,
                question="How was my GPS movement different from my baseline?",
            )
        )
        records.append(
            {
                "variant": variant.value,
                "passed": (
                    not result.response.used_fallback
                    and result.response.model_invoked
                    and len(result.context_references) == count
                ),
                "context_count": len(result.context_references),
                "tool_names": [trace.tool_name for trace in result.tool_trace],
                "response": result.response.model_dump(mode="json"),
            }
        )
    source_provenance = provenance()
    root = Path(__file__).resolve().parents[1]
    for name in (
        "backend/slm/context_responder.py",
        "backend/slm/variants.py",
        "backend/slm/prompts/request_scope.yaml",
        "backend/slm/prompts/unsupported_window.yaml",
        "benchmarks/slm_context_smoke.py",
    ):
        source_provenance["sha256_raw_bytes"][name] = hashlib.sha256(
            (root / name).read_bytes()
        ).hexdigest()
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "synthetic_context_functional_smoke_not_method_comparison",
        "production_retrieval_ready": False,
        "provenance": source_provenance,
        "context_policy_version": CONTEXT_POLICY_VERSION,
        "model_tag": model_tag,
        "prompt_version": service.client.prompt.manifest.prompt_version,
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
    print(
        json.dumps(
            {key: result[key] for key in ("scope", "model_tag", "passed", "total")}
        )
    )
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
