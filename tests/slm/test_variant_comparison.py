from __future__ import annotations

from dataclasses import replace

import pytest

from backend.contracts.evidence import AssistantDraft, EvidencePacket, ResponseMode
from backend.slm.client import GenerationMetrics, GenerationResult
from backend.slm.output_grounding import render_grounded_example
from backend.slm.service import SLMService
from backend.slm.variants import (
    ContextDataClass,
    ContextItem,
    ContextSource,
    VariantKind,
    VariantRunner,
)
from benchmarks.slm_model_comparison import comparison_cases
from benchmarks.slm_variant_comparison import run_variant_comparison


class CaseAwareGenerator:
    def generate_draft(self, packet: EvidencePacket, question: str) -> GenerationResult:
        del question
        mode = packet.claim_policy.permitted_response_modes[0]
        draft = AssistantDraft(
            packet_id=packet.identity.packet_id,
            response_mode=mode,
            claim_ids_used=packet.claim_policy.approved_claim_ids,
            evidence_ids_referenced=(
                ()
                if mode == ResponseMode.REFUSAL
                else (packet.feature_window.feature_id,)
            ),
            text=(
                "This app cannot diagnose a condition."
                if mode == ResponseMode.REFUSAL
                else render_grounded_example(packet, mode)
            ),
            includes_uncertainty_statement=mode
            in {ResponseMode.NORMAL, ResponseMode.UNCERTAINTY},
        )
        return GenerationResult(
            draft=draft,
            model_tag="phi4-mini:3.8b",
            prompt_id="test",
            prompt_version="1.0.0",
            prompt_sha256="a" * 64,
            metrics=GenerationMetrics(total_duration_ns=1_000),
        )


class ContextAcceptingResponder:
    """Test double proving orchestration; not a production RAG responder."""

    def __init__(self) -> None:
        self.service = SLMService(CaseAwareGenerator())

    def respond(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        context_items: tuple[ContextItem, ...],
    ):
        del context_items
        return self.service.respond(packet, question)


class SyntheticRetriever:
    def retrieve(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        top_k: int,
        seed_context: tuple[ContextItem, ...],
    ):
        del packet, question, seed_context
        return (
            ContextItem(
                context_id="retrieved:synthetic:1",
                source=ContextSource.APPROVED_REFERENCE,
                data_classification=ContextDataClass.SYNTHETIC,
                content="Approved synthetic reference summary",
                provenance_ref="fixture:reference:1",
                relevance_score=0.8,
            ),
        )[:top_k]


class SyntheticSelector:
    def select_tools(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        allowed_tools: tuple[str, ...],
        max_tool_calls: int,
    ):
        del packet, question
        return allowed_tools[:max_tool_calls]


class SyntheticTool:
    name = "recent_summary"

    def run(self, packet: EvidencePacket, question: str):
        del packet, question
        return (
            ContextItem(
                context_id="tool:synthetic:1",
                source=ContextSource.TOOL_RESULT,
                data_classification=ContextDataClass.SYNTHETIC,
                content="Approved synthetic tool result",
                provenance_ref="fixture:tool:1",
                relevance_score=None,
            ),
        )


def _configured_runners():
    responder = ContextAcceptingResponder()
    retriever = SyntheticRetriever()
    selector = SyntheticSelector()
    tool = SyntheticTool()
    return {
        VariantKind.BASE_LLM: VariantRunner(responder),
        VariantKind.RAG: VariantRunner(responder, retriever=retriever),
        VariantKind.AGENT: VariantRunner(
            responder, tool_selector=selector, tools=(tool,)
        ),
        VariantKind.RAG_AGENT: VariantRunner(
            responder,
            retriever=retriever,
            tool_selector=selector,
            tools=(tool,),
        ),
    }


def test_harness_runs_same_synthetic_cases_for_all_four_variants():
    result = run_variant_comparison(_configured_runners())

    assert result["status"] == "completed"
    assert result["data_classification"] == "synthetic_only"
    assert result["comparison_controls"]["fixed_model_observed"] is True
    assert result["comparison_controls"]["observed_model_tags"] == ["phi4-mini:3.8b"]
    assert len(result["variants"]) == 4
    assert all(item["summary"]["runs"] == 3 for item in result["variants"])
    assert all(
        item["summary"]["quality_check_pass_rate"] == 1.0 for item in result["variants"]
    )

    by_variant = {item["variant"]: item for item in result["variants"]}
    assert by_variant["base_llm"]["summary"]["tool_call_count"] == 0
    assert by_variant["rag"]["summary"]["retrieved_or_tool_context_count"] == 2
    assert by_variant["rag"]["summary"]["retrieval_attempt_count"] == 2
    assert by_variant["agent"]["summary"]["tool_call_count"] == 2
    assert by_variant["agent"]["summary"]["tool_selection_attempt_count"] == 2
    assert by_variant["rag_agent"]["summary"]["tool_call_count"] == 2
    assert by_variant["rag_agent"]["summary"]["retrieval_attempt_count"] == 2


def test_harness_reports_owner_dependencies_as_incomplete_not_success():
    responder = ContextAcceptingResponder()
    runners = {variant: VariantRunner(responder) for variant in VariantKind}

    result = run_variant_comparison(runners)

    assert result["status"] == "incomplete"
    by_variant = {item["variant"]: item for item in result["variants"]}
    assert by_variant["base_llm"]["summary"]["completed"] == 3
    assert by_variant["rag"]["summary"]["configuration_required"] == 2
    assert by_variant["agent"]["summary"]["configuration_required"] == 2
    assert by_variant["rag_agent"]["summary"]["configuration_required"] == 2


def test_public_harness_rejects_non_synthetic_packets():
    case = comparison_cases()[0]
    changed_identity = case.packet.identity.model_copy(
        update={"participant_ref": "not-synthetic"}
    )
    changed_packet = case.packet.model_copy(update={"identity": changed_identity})

    with pytest.raises(ValueError, match="synthetic cases only"):
        run_variant_comparison(
            _configured_runners(), cases=(replace(case, packet=changed_packet),)
        )
