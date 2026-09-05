from typing import Any

from backend.contracts.evidence import ResponseMode
from backend.slm.client import GenerationMetrics, GenerationResult
from benchmarks.slm_model_comparison import (
    comparison_cases,
    percentile,
    run_comparison,
    summarize_records,
)


class CaseAwareClient:
    def __init__(self, model_tag: str) -> None:
        self.model_tag = model_tag

    def generate_draft(self, packet, question):
        del question
        mode = packet.claim_policy.permitted_response_modes[0]
        claim_id = packet.claim_policy.approved_claim_ids[0]
        from backend.contracts.evidence import AssistantDraft

        draft = AssistantDraft(
            packet_id=packet.identity.packet_id,
            response_mode=mode,
            claim_ids_used=(claim_id,),
            evidence_ids_referenced=(
                ()
                if mode == ResponseMode.REFUSAL
                else (packet.feature_window.feature_id,)
            ),
            text=(
                "This is a cautious synthetic explanation with stated uncertainty."
                if mode in {ResponseMode.NORMAL, ResponseMode.UNCERTAINTY}
                else (
                    "There is insufficient history for comparison."
                    if mode == ResponseMode.INSUFFICIENT_DATA
                    else "This app cannot diagnose a condition."
                )
            ),
            includes_uncertainty_statement=mode
            in {ResponseMode.NORMAL, ResponseMode.UNCERTAINTY},
        )
        return GenerationResult(
            draft=draft,
            model_tag=self.model_tag,
            prompt_id="test",
            prompt_version="1",
            prompt_sha256="a" * 64,
            metrics=GenerationMetrics(
                eval_count=20,
                eval_duration_ns=1_000_000_000,
            ),
        )


def test_comparison_cases_are_synthetic_and_cover_required_modes():
    cases = comparison_cases()
    assert {case.case_id for case in cases} == {
        "eligible_above_baseline",
        "partial_history",
        "diagnosis_boundary",
    }
    assert all(
        case.packet.identity.participant_ref == "synthetic-only" for case in cases
    )
    assert {case.packet.claim_policy.permitted_response_modes[0] for case in cases} == {
        ResponseMode.NORMAL,
        ResponseMode.INSUFFICIENT_DATA,
        ResponseMode.REFUSAL,
    }


def test_percentile_interpolates():
    assert percentile([10.0, 20.0, 30.0], 0.5) == 20.0
    assert percentile([], 0.95) is None


def test_summary_counts_acceptance_and_fallbacks():
    records: list[dict[str, Any]] = [
        {
            "wall_latency_ms": 10.0,
            "used_fallback": False,
            "rejection_reason": None,
            "tokens_per_second": 20.0,
            "quality_check_pass": True,
        },
        {
            "wall_latency_ms": 30.0,
            "used_fallback": True,
            "rejection_reason": "claim_not_approved",
            "tokens_per_second": None,
            "quality_check_pass": False,
        },
    ]
    summary = summarize_records(records)
    assert summary["safety_gate_accept_rate"] == 0.5
    assert summary["fallback_count"] == 1
    assert summary["quality_check_pass_rate"] == 0.5
    assert summary["rejection_counts"] == {"claim_not_approved": 1}
    assert summary["wall_latency_ms"]["median"] == 20.0


def test_comparison_runner_uses_same_cases_for_each_model(monkeypatch):
    monkeypatch.setattr(
        "benchmarks.slm_model_comparison._gpu_memory_used_mib", lambda: 123
    )
    result = run_comparison(
        ["phi4-mini:3.8b", "qwen3:4b"],
        client_factory=CaseAwareClient,
    )

    assert result["status"] == "completed"
    assert result["data_classification"] == "synthetic_only"
    assert len(result["models"]) == 2
    assert all(model["summary"]["runs"] == 3 for model in result["models"])
    assert all(
        model["summary"]["safety_gate_accept_rate"] == 1.0 for model in result["models"]
    )
    assert all(
        model["summary"]["quality_check_pass_rate"] == 1.0 for model in result["models"]
    )
