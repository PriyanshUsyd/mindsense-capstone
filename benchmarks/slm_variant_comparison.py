"""Common comparison harness for Base LLM, RAG, Agent and RAG+Agent.

The harness accepts dependency-injected ``VariantRunner`` instances so the
same synthetic cases and scoring logic can be used without selecting another
role's data store, statistical tool, corpus or evaluation threshold.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.slm.runtime import create_local_service, listed_model_tags
from backend.slm.variants import (
    VARIANT_INTERFACE_VERSION,
    SLMServiceResponder,
    VariantConfigurationError,
    VariantExecutionError,
    VariantKind,
    VariantRequest,
    VariantRunner,
)
from benchmarks.slm_model_comparison import (
    ComparisonCase,
    comparison_cases,
    evaluate_output,
    percentile,
)


def summarize_variant_records(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    completed = [record for record in records if record["status"] == "completed"]
    latencies = [float(record["wall_latency_ms"]) for record in completed]
    quality_passed = sum(bool(record["quality_check_pass"]) for record in completed)
    errors = Counter(
        str(record["reason_code"])
        for record in records
        if record["reason_code"] is not None
    )
    return {
        "runs": len(records),
        "completed": len(completed),
        "configuration_required": sum(
            record["status"] == "configuration_required" for record in records
        ),
        "execution_failed": sum(
            record["status"] == "execution_failed" for record in records
        ),
        "quality_check_pass_count": quality_passed,
        "quality_check_pass_rate": (
            round(quality_passed / len(completed), 4) if completed else None
        ),
        "fallback_count": sum(bool(record["used_fallback"]) for record in completed),
        "model_invocation_count": sum(
            bool(record["model_invoked"]) for record in completed
        ),
        "retrieval_attempt_count": sum(
            bool(record["retrieval_attempted"]) for record in completed
        ),
        "tool_selection_attempt_count": sum(
            bool(record["tool_selection_attempted"]) for record in completed
        ),
        "retrieved_or_tool_context_count": sum(
            int(record["context_count"]) for record in completed
        ),
        "tool_call_count": sum(int(record["tool_call_count"]) for record in completed),
        "reason_counts": dict(sorted(errors.items())),
        "wall_latency_ms": {
            "mean": round(statistics.mean(latencies), 2) if latencies else None,
            "median": round(statistics.median(latencies), 2) if latencies else None,
            "p95": round(percentile(latencies, 0.95), 2) if latencies else None,
        },
    }


def run_variant_comparison(
    runners: Mapping[VariantKind, VariantRunner],
    *,
    cases: Sequence[ComparisonCase] | None = None,
) -> dict[str, Any]:
    """Run all four variants over one fixed public synthetic case set."""

    expected_variants = set(VariantKind)
    if set(runners) != expected_variants:
        raise ValueError("runners must contain each Week 7 variant exactly once")
    selected_cases = tuple(cases or comparison_cases())
    if not selected_cases:
        raise ValueError("at least one comparison case is required")
    if any(
        case.packet.identity.participant_ref != "synthetic-only"
        for case in selected_cases
    ):
        raise ValueError("the public variant harness accepts synthetic cases only")

    variants: list[dict[str, Any]] = []
    observed_model_tags: set[str] = set()
    total_configuration_required = 0
    total_execution_failed = 0

    for variant in VariantKind:
        records: list[dict[str, Any]] = []
        for case in selected_cases:
            try:
                run = runners[variant].run(
                    VariantRequest(
                        variant=variant,
                        question=case.question,
                        packet=case.packet,
                    )
                )
            except VariantConfigurationError as exc:
                total_configuration_required += 1
                records.append(_error_record(case, "configuration_required", exc))
                continue
            except VariantExecutionError as exc:
                total_execution_failed += 1
                records.append(_error_record(case, "execution_failed", exc))
                continue

            response = run.response
            quality_checks = evaluate_output(case, response)
            if response.model_tag is not None:
                observed_model_tags.add(response.model_tag)
            records.append(
                {
                    "case_id": case.case_id,
                    "purpose": case.purpose,
                    "status": "completed",
                    "reason_code": None,
                    "response_mode": response.response_mode.value,
                    "request_disposition": response.request_disposition.value,
                    "request_category": response.request_category.value,
                    "model_tag": response.model_tag,
                    "model_invoked": response.model_invoked,
                    "used_fallback": response.used_fallback,
                    "rejection_reason": response.rejection_reason,
                    "generation_prompt_sha256": response.generation_prompt_sha256,
                    "fallback_prompt_sha256": response.fallback_prompt_sha256,
                    "quality_checks": quality_checks,
                    "quality_check_pass": all(quality_checks.values()),
                    "wall_latency_ms": round(run.wall_latency_ms, 2),
                    "context_count": len(run.context_references),
                    "retrieval_attempted": run.retrieval_attempted,
                    "tool_selection_attempted": run.tool_selection_attempted,
                    "context_references": [
                        reference.model_dump(mode="json")
                        for reference in run.context_references
                    ],
                    "tool_call_count": len(run.tool_trace),
                    "tool_trace": [
                        trace.model_dump(mode="json") for trace in run.tool_trace
                    ],
                    "text": response.text,
                }
            )
        variants.append(
            {
                "variant": variant.value,
                "summary": summarize_variant_records(records),
                "records": records,
            }
        )

    fixed_model_observed = len(observed_model_tags) <= 1
    if total_execution_failed or not fixed_model_observed:
        status = "failed"
    elif total_configuration_required:
        status = "incomplete"
    else:
        status = "completed"
    return {
        "schema_version": "1.0.0",
        "variant_interface_version": VARIANT_INTERFACE_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "scope": "public_synthetic_architecture_comparison_not_client_evaluation",
        "data_classification": "synthetic_only",
        "comparison_controls": {
            "same_cases_for_each_variant": True,
            "same_frozen_evidence_packets": True,
            "same_request_policy_and_safety_response_contract_required": True,
            "fixed_model_required": True,
            "observed_model_tags": sorted(observed_model_tags),
            "fixed_model_observed": fixed_model_observed,
            "architecture_and_model_comparisons_separated": True,
        },
        "case_ids": [case.case_id for case in selected_cases],
        "variants": variants,
    }


def build_runtime_runners(
    *, model_tag: str, timeout_seconds: float
) -> dict[VariantKind, VariantRunner]:
    """Build the honest current-state runners around one pinned local model.

    Only Base LLM is configured here. The other variants intentionally retain
    their explicit dependency gaps until the responsible owners supply an
    approved retriever, tool selector and tool registry.
    """

    service = create_local_service(
        model_tag=model_tag,
        timeout_seconds=timeout_seconds,
    )
    responder = SLMServiceResponder(service)
    return {variant: VariantRunner(responder) for variant in VariantKind}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the public synthetic Week 7 four-variant status harness. "
            "Base LLM uses the selected local model; unavailable owner "
            "dependencies are reported as configuration_required."
        )
    )
    parser.add_argument(
        "--model",
        choices=listed_model_tags(),
        default="phi4-mini:3.8b",
    )
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.out.exists():
        parser.error(f"refusing to overwrite existing result: {args.out}")

    result = run_variant_comparison(
        build_runtime_runners(
            model_tag=args.model,
            timeout_seconds=args.timeout,
        )
    )
    result["runtime_settings"] = {
        "requested_model_tag": args.model,
        "timeout_seconds": args.timeout,
        "non_base_dependencies": "unconfigured_owner_inputs",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.out),
                "status": result["status"],
                "runtime_settings": result["runtime_settings"],
                "variants": [
                    {
                        "variant": item["variant"],
                        "summary": item["summary"],
                    }
                    for item in result["variants"]
                ],
            },
            indent=2,
        )
    )
    return 1 if result["status"] == "failed" else 0


def _error_record(
    case: ComparisonCase,
    status: str,
    error: VariantConfigurationError | VariantExecutionError,
) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "purpose": case.purpose,
        "status": status,
        "reason_code": error.reason_code,
        "response_mode": None,
        "request_disposition": None,
        "request_category": None,
        "model_tag": None,
        "model_invoked": False,
        "used_fallback": False,
        "rejection_reason": None,
        "generation_prompt_sha256": None,
        "fallback_prompt_sha256": None,
        "quality_checks": {},
        "quality_check_pass": False,
        "wall_latency_ms": None,
        "context_count": 0,
        "retrieval_attempted": False,
        "tool_selection_attempted": False,
        "context_references": [],
        "tool_call_count": 0,
        "tool_trace": [],
        "text": None,
    }


if __name__ == "__main__":
    raise SystemExit(main())
