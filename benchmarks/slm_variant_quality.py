"""Fixed public rubric-review package for the four current packet variants.

Reuses the Evaluation-approved public mapping and existing production gates.
This prepares developer evidence, never human ratings or held-out results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import statistics
import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import yaml

from backend.data_pipeline.retrieval_source import ApprovedPacketRetriever
from backend.slm.packet_variants import create_packet_variant_runner
from backend.slm.runtime import (
    MODEL_MANIFEST_PATH,
    create_local_service,
    listed_model_tags,
)
from backend.slm.service import SLMService
from backend.slm.variants import (
    SLMServiceResponder,
    VariantError,
    VariantKind,
    VariantRequest,
    VariantRunner,
)
from benchmarks.slm_evaluation_alignment import ROOT, provenance, run_alignment
from benchmarks.slm_packet_api_smoke import ObservedTransport

REPETITIONS = 3
PROTOCOL = "docs/slm/week9-variant-quality-comparison.md"
EXTRA_SOURCES = (
    PROTOCOL,
    "benchmarks/slm_variant_quality.py",
    "benchmarks/slm_packet_api_smoke.py",
    "backend/slm/packet_variants.py",
    "backend/slm/variants.py",
    "backend/slm/context_responder.py",
    "backend/slm/response_health.py",
    "backend/slm/prompts/request_scope.yaml",
    "backend/slm/prompts/unsupported_window.yaml",
    "backend/data_pipeline/retrieval_source.py",
    "docs/evaluation/response-quality-rubric-v0.1.md",
    "docs/evaluation/team-session-runbook-v0.1.md",
    "docs/evaluation/participant-questionnaire-v0.2.md",
)
GROUPS = ("source_plan", "guardrail_high_severity", "guardrail_privacy_extension")
RUBRIC_ITEMS = (
    "data_faithfulness",
    "personal_baseline",
    "wellbeing_boundary",
    "association_vs_causation",
    "uncertainty_or_insufficient_evidence",
    "correct_response_route",
    "no_prohibited_disclosure",
)
EXPECTED_CONTEXT = {
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


class PacketVariantReviewService:
    """Create a fresh packet binding per response; keep benchmark traces only."""

    def __init__(self, service: SLMService, variant: VariantKind, observer):
        self.service = service
        self.variant = variant
        self.observer = observer
        self.traces: list[dict] = []

    def respond(self, packet, question):
        if packet.identity.participant_ref != "synthetic-only":
            raise ValueError("quality review accepts fixed synthetic packets only")
        runner = (
            VariantRunner(SLMServiceResponder(self.service))
            if self.variant == VariantKind.BASE_LLM
            else create_packet_variant_runner(
                self.service.client,
                packet,
                retriever=ApprovedPacketRetriever(),
                allow_aggregated_summaries=True,
            )
        )
        request = VariantRequest(
            variant=self.variant, packet=packet, question=question, top_k=3
        )
        before = len(self.observer.context_ids)
        started = perf_counter()
        trace = {
            "packet_id": packet.identity.packet_id,
            "execution_error": None,
            "context_references": [],
            "tool_trace": [],
        }
        try:
            run = runner.run(request)
            response = run.response
            trace.update(
                context_references=[
                    r.model_dump(mode="json") for r in run.context_references
                ],
                tool_trace=[r.model_dump(mode="json") for r in run.tool_trace],
                retrieval_attempted=run.retrieval_attempted,
                tool_selection_attempted=run.tool_selection_attempted,
            )
        except VariantError as exc:
            # Retain the failure and a safe response; never count this as success.
            trace["execution_error"] = exc.reason_code
            response = self.service.context_unavailable_response(question)
        trace["wall_latency_ms"] = round((perf_counter() - started) * 1000, 3)
        trace["model_call_context_ids"] = self.observer.context_ids[before:]
        self.traces.append(trace)
        return response


def runtime_metadata(model_tag: str) -> dict:
    """Verify the installed candidate without downloading or exposing host paths."""
    executable = shutil.which("ollama")
    if executable is None:
        raise ValueError("installed Ollama executable must be on PATH")

    def command(*args):
        return subprocess.run(
            [executable, *args], check=True, capture_output=True, text=True, timeout=20
        ).stdout.strip()

    candidates = yaml.safe_load(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))[
        "comparison_candidates"
    ]
    expected = next(
        c["registry_digest_prefix"] for c in candidates if c["model_tag"] == model_tag
    )
    installed = {
        row.split()[0]: row.split()[1]
        for row in command("list").splitlines()[1:]
        if row.strip()
    }
    if installed.get(model_tag) != expected:
        raise ValueError("installed model digest does not match the pinned manifest")
    loaded = [row.split()[0] for row in command("ps").splitlines()[1:] if row.strip()]
    return {
        "ollama_version": command("--version"),
        "model_digest_prefix": expected,
        "digest_precision": "installed CLI prefix, not a full digest",
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "models_loaded_before_run": loaded,
    }


def summarize_variant(records: list[dict]) -> dict:
    groups = {}
    for group in GROUPS:
        rows = [r for r in records if r["group"] == group]
        executed = [r for r in rows if r["execution_status"] == "executed"]
        ids = sorted({r["case"]["case_id"] for r in executed})
        groups[group] = {
            "executed_runs": len(executed),
            "automated_passed_runs": sum(
                r["automated_checks_passed"] for r in executed
            ),
            "unique_executed_cases": len(ids),
            "cases_passing_all_repetitions": sum(
                all(
                    r["automated_checks_passed"]
                    for r in executed
                    if r["case"]["case_id"] == case_id
                )
                for case_id in ids
            ),
            "not_covered_case_ids": sorted(
                {
                    r["case"]["case_id"]
                    for r in rows
                    if r["execution_status"] == "not_covered"
                }
            ),
        }
    generated = [r for r in records if r["response"] and r["response"]["model_invoked"]]
    subsequent = [
        r["trace"]["wall_latency_ms"] for r in generated if r["model_call_order"] != 1
    ]
    first = [
        r["trace"]["wall_latency_ms"] for r in generated if r["model_call_order"] == 1
    ]
    return {
        "groups": groups,
        "model_invocations": len(generated),
        "first_generation_ms": first[0] if first else None,
        "subsequent_generation_count": len(subsequent),
        "subsequent_generation_median_ms": round(statistics.median(subsequent), 3)
        if subsequent
        else None,
        "execution_errors": sum(
            bool(r.get("trace", {}).get("execution_error")) for r in records
        ),
        "human_quality_pass_rate": None,
        "human_review_status": "not_assessed",
    }


def run_quality_comparison(
    *,
    model_tag: str = "phi4-mini:3.8b",
    service: SLMService | None = None,
    on_checkpoint: Callable[[dict], None] | None = None,
) -> dict:
    """Run the unchanged public mapping in rotated architecture blocks."""
    metadata = provenance()
    metadata["sha256_raw_bytes"].update(
        {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in EXTRA_SOURCES
        }
    )
    injected = service is not None
    runtime = (
        {"verification": "injected_transport_not_live"}
        if injected
        else runtime_metadata(model_tag)
    )
    service = service or create_local_service(model_tag=model_tag, timeout_seconds=180)
    original = service.client.transport
    observer = ObservedTransport(original)
    service.client.transport = observer
    result = {
        "schema_version": "1.0.0",
        "protocol_version": "week9-public-variant-quality-1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running_human_review_pending",
        "scope": "public_synthetic_developer_rubric_package_not_human_evaluation",
        "execution_backend": "injected_transport_not_live"
        if injected
        else "local_ollama",
        "requested_model_tag": model_tag,
        "runtime": runtime,
        "client_config": service.client.config.model_dump(mode="json"),
        "provenance": metadata,
        "controls": {
            "repetitions": REPETITIONS,
            "variant_orders": [],
            "temperature": 0,
            "same_public_mapping_and_fixtures": True,
            "packet_binding": "new_runner_per_response",
            "top_k": 3,
            "warmup": "none; first actual generation recorded separately",
            "timing": "SLM runner only, excluding HTTP, CES construction and human time",
            "duplicate_evidence": "plan_q1 and plan_q7 share unlock_eligible",
        },
        "records": [],
    }
    model_calls = 0
    try:
        for repetition in range(REPETITIONS):
            variants = list(VariantKind)
            order = variants[repetition:] + variants[:repetition]
            result["controls"]["variant_orders"].append([v.value for v in order])
            for variant in order:
                adapter = PacketVariantReviewService(service, variant, observer)
                alignment = run_alignment(model_tag=model_tag, service=adapter)
                traces = iter(adapter.traces)
                for record in alignment["records"]:
                    record.update(
                        variant=variant.value,
                        repetition=repetition + 1,
                        model_call_order=None,
                    )
                    record["rubric_review"] = {item: None for item in RUBRIC_ITEMS}
                    if record["response"] is not None:
                        trace = next(traces)
                        record["trace"] = trace
                        expected = (
                            [EXPECTED_CONTEXT[variant]]
                            if record["case"]["expected_model_invoked"]
                            else []
                        )
                        response = record["response"]
                        record["checks"]["model_context_matches_variant"] = (
                            trace["model_call_context_ids"] == expected
                        )
                        record["checks"]["no_execution_error"] = (
                            trace["execution_error"] is None
                        )
                        record["checks"]["fixed_model"] = (
                            not response["model_invoked"]
                            or response["model_tag"] == model_tag
                        )
                        record["automated_checks_passed"] = record[
                            "automated_checks_passed"
                        ] and all(record["checks"].values())
                        if response["model_invoked"]:
                            model_calls += 1
                            record["model_call_order"] = model_calls
                    result["records"].append(record)
                if on_checkpoint:
                    on_checkpoint(result)
    finally:
        service.client.transport = original
    result["summaries"] = {
        v.value: summarize_variant(
            [r for r in result["records"] if r["variant"] == v.value]
        )
        for v in VariantKind
    }
    result["status"] = (
        "development_checks_failed_human_review_pending"
        if any(r["automated_checks_passed"] is False for r in result["records"])
        else "development_checks_passed_human_review_pending"
    )
    result["response_comparison"] = {
        case_id: len(
            {
                r["response"]["text"]
                for r in result["records"]
                if r["case"]["case_id"] == case_id and r["response"]
            }
        )
        for case_id in sorted({r["case"]["case_id"] for r in result["records"]})
    }
    return result


def render_review(result: dict) -> str:
    lines = [
        "# Week 9 Four-Variant Public Response Review",
        "",
        f"Status: {result['status']}",
        f"Model: {result['requested_model_tag']}; repeats: {REPETITIONS}",
        f"Code head: {result['provenance']['git_head']}",
        "",
        "Automated evidence is not a human rubric decision. No human ratings have been entered.",
        "Use docs/evaluation/response-quality-rubric-v0.1.md and the locked thresholds.",
        "Richard and Chonghao must independently lock judgments before discussing disagreements.",
        "Keep N/A reasons, failures and repeats. Do not pool safety, privacy or Not covered into standard quality.",
        "The paired JSON retains every exact response, packet, trace, failure and source hash.",
        "This is a synthetic developer review, not ME-P02 or the ten-dimension human questionnaire.",
        "",
        "| Variant | Source-plan cases passing all repeats | Critical cases | Privacy extension | Model calls | Human quality |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for variant, summary in result["summaries"].items():
        rates = [
            f"{summary['groups'][g]['cases_passing_all_repetitions']}/{summary['groups'][g]['unique_executed_cases']}"
            for g in GROUPS
        ]
        lines.append(
            f"| {variant} | {' | '.join(rates)} | {summary['model_invocations']} | NOT ASSESSED |"
        )
    for case_id in result["response_comparison"]:
        rows = [r for r in result["records"] if r["case"]["case_id"] == case_id]
        case = rows[0]["case"]
        lines += [
            "",
            f"## {case_id} ({rows[0]['group']})",
            "",
            case["question"],
            "",
            f"Review criteria: {case['review_criteria']}",
            "",
        ]
        if not rows[0]["response"]:
            lines += [
                f"NOT COVERED: {case['blocked_reason']}",
                "Excluded from every denominator; no model execution.",
            ]
            continue
        packet = rows[0]["evidence_packet"]
        lines += [
            f"Synthetic packet: {packet['identity']['packet_id']}; {packet['feature_window']['feature_id']}; value {packet['feature_window']['value']}; baseline {packet['baseline']['value']}.",
            "",
        ]
        for variant in VariantKind:
            selected = [r for r in rows if r["variant"] == variant.value]
            lines += [f"### {variant.value}", ""]
            texts = {}
            for row in selected:
                texts.setdefault(row["response"]["text"], []).append(row["repetition"])
            for response_text, repetitions in texts.items():
                lines += [
                    f"Exact response for repeats {repetitions}:",
                    "",
                    *["> " + line for line in response_text.splitlines()],
                    "",
                ]
            lines += [
                "| Repeat | Mode | Model invoked | Fallback | Automated checks | Error / rejection |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            for row in selected:
                response = row["response"]
                reason = (
                    row["trace"]["execution_error"]
                    or response["rejection_reason"]
                    or "none"
                )
                lines.append(
                    f"| {row['repetition']} | {response['response_mode']} | {response['model_invoked']} | {response['used_fallback']} | {row['automated_checks_passed']} | {reason} |"
                )
            lines += [
                "",
                "| Rubric requirement | Richard Pass/Fail/N/A + reason | Chonghao Pass/Fail/N/A + reason |",
                "| --- | --- | --- |",
            ]
            lines += [
                f"| {item} | NOT ASSESSED | NOT ASSESSED |" for item in RUBRIC_ITEMS
            ]
            lines += ["", "Joint decision / disagreement resolution: NOT ASSESSED", ""]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", choices=listed_model_tags(), default="phi4-mini:3.8b"
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scorecard", type=Path, required=True)
    args = parser.parse_args(argv)
    paths = [args.out.resolve(), args.scorecard.resolve()]
    if paths[0] == paths[1] or any(p.exists() for p in paths):
        parser.error(
            "use distinct new paths; previous evidence must never be overwritten"
        )
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    # Checkpoints belong only to this newly reserved output, not historical runs.
    with args.out.open("x", encoding="utf-8") as handle:

        def checkpoint(result):
            handle.seek(0)
            json.dump(result, handle, indent=2)
            handle.write("\n")
            handle.truncate()
            handle.flush()
            print(
                json.dumps(
                    {
                        "records_saved": len(result["records"]),
                        "status": result["status"],
                    }
                ),
                flush=True,
            )

        result = run_quality_comparison(model_tag=args.model, on_checkpoint=checkpoint)
        checkpoint(result)
    with args.scorecard.open("x", encoding="utf-8") as handle:
        handle.write(render_review(result))
    return int(result["status"].startswith("development_checks_failed"))


if __name__ == "__main__":
    raise SystemExit(main())
