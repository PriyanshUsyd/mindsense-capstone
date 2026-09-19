from __future__ import annotations

import pytest

from backend.contracts.evidence import (
    ApprovedClaimId,
    AssistantDraft,
    EvidencePacket,
    ResponseMode,
)
from backend.slm.client import GenerationMetrics, GenerationResult
from backend.slm.output_grounding import render_grounded_example
from backend.slm.service import SLMService
from backend.slm.variants import (
    ContextDataClass,
    ContextItem,
    ContextSource,
    SLMServiceResponder,
    VariantConfigurationError,
    VariantExecutionError,
    VariantKind,
    VariantRequest,
    VariantRunner,
)


class SafeGenerator:
    def generate_draft(self, packet: EvidencePacket, question: str) -> GenerationResult:
        del question
        draft = AssistantDraft(
            packet_id=packet.identity.packet_id,
            response_mode=ResponseMode.NORMAL,
            claim_ids_used=(
                ApprovedClaimId.OBSERVATION_OF_DEVIATION,
                ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
            ),
            evidence_ids_referenced=(packet.feature_window.feature_id,),
            text=render_grounded_example(packet, ResponseMode.NORMAL),
            includes_uncertainty_statement=True,
        )
        return GenerationResult(
            draft=draft,
            model_tag="phi4-mini:3.8b",
            prompt_id="test",
            prompt_version="1.0.0",
            prompt_sha256="a" * 64,
            metrics=GenerationMetrics(total_duration_ns=1_000),
        )


class RecordingResponder:
    def __init__(self) -> None:
        self.context_calls: list[tuple[ContextItem, ...]] = []
        self.service = SLMService(SafeGenerator())

    def respond(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        context_items: tuple[ContextItem, ...],
    ):
        self.context_calls.append(context_items)
        return self.service.respond(packet, question)


class StaticRetriever:
    def __init__(self, items: tuple[ContextItem, ...]) -> None:
        self.items = items
        self.calls = 0
        self.seed_context: tuple[ContextItem, ...] | None = None

    def retrieve(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        top_k: int,
        seed_context: tuple[ContextItem, ...],
    ):
        del packet, question
        self.calls += 1
        self.seed_context = seed_context
        return self.items[:top_k]


class FixedSelector:
    def __init__(self, selected: tuple[str, ...]) -> None:
        self.selected = selected
        self.calls = 0

    def select_tools(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        allowed_tools: tuple[str, ...],
        max_tool_calls: int,
    ):
        del packet, question, allowed_tools
        self.calls += 1
        return self.selected[:max_tool_calls]


class StaticTool:
    name = "recent_summary"

    def __init__(self, items: tuple[ContextItem, ...]) -> None:
        self.items = items
        self.calls = 0

    def run(self, packet: EvidencePacket, question: str):
        del packet, question
        self.calls += 1
        return self.items


class FailingResponder:
    def respond(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        context_items: tuple[ContextItem, ...],
    ):
        del packet, question, context_items
        raise RuntimeError("sensitive implementation detail")


def _retrieved_context(content: str = "Approved synthetic reference summary"):
    return ContextItem(
        context_id="retrieved:1",
        source=ContextSource.APPROVED_REFERENCE,
        data_classification=ContextDataClass.SYNTHETIC,
        content=content,
        provenance_ref="fixture:approved_reference:1",
        relevance_score=0.9,
    )


def _tool_context():
    return ContextItem(
        context_id="tool:recent_summary:1",
        source=ContextSource.TOOL_RESULT,
        data_classification=ContextDataClass.SYNTHETIC,
        content="Approved synthetic recent summary",
        provenance_ref="fixture:tool_result:1",
        relevance_score=None,
    )


def _request(variant: VariantKind, packet: EvidencePacket, question: str | None = None):
    return VariantRequest(
        variant=variant,
        question=question or "How was my phone unlock activity different?",
        packet=packet,
    )


def test_base_variant_uses_existing_safe_service_without_context(
    eligible_packet: EvidencePacket,
):
    runner = VariantRunner(SLMServiceResponder(SLMService(SafeGenerator())))

    result = runner.run(_request(VariantKind.BASE_LLM, eligible_packet))

    assert result.variant == VariantKind.BASE_LLM
    assert result.response.response_mode == ResponseMode.NORMAL
    assert result.context_references == ()
    assert result.tool_trace == ()


def test_rag_requires_an_owner_approved_retriever(eligible_packet: EvidencePacket):
    runner = VariantRunner(RecordingResponder())

    with pytest.raises(VariantConfigurationError) as caught:
        runner.run(_request(VariantKind.RAG, eligible_packet))

    assert caught.value.reason_code == "approved_retriever_not_configured"


def test_rag_passes_bounded_context_but_logs_only_references(
    eligible_packet: EvidencePacket,
):
    item = _retrieved_context(content="Sensitive-to-runtime synthetic content")
    responder = RecordingResponder()
    runner = VariantRunner(responder, retriever=StaticRetriever((item,)))

    result = runner.run(_request(VariantKind.RAG, eligible_packet))

    assert responder.context_calls == [(item,)]
    assert result.context_references[0].context_id == item.context_id
    assert "content" not in result.context_references[0].model_dump()
    assert result.tool_trace == ()


def test_agent_executes_only_selected_whitelisted_local_tools(
    eligible_packet: EvidencePacket,
):
    tool_item = _tool_context()
    tool = StaticTool((tool_item,))
    selector = FixedSelector((tool.name,))
    responder = RecordingResponder()
    runner = VariantRunner(responder, tool_selector=selector, tools=(tool,))

    result = runner.run(_request(VariantKind.AGENT, eligible_packet))

    assert tool.calls == 1
    assert responder.context_calls == [(tool_item,)]
    assert result.tool_trace[0].tool_name == tool.name
    assert result.tool_trace[0].context_ids == (tool_item.context_id,)


def test_rag_agent_seeds_retrieval_with_whitelisted_tool_results(
    eligible_packet: EvidencePacket,
):
    tool_item = _tool_context()
    retrieved_item = _retrieved_context()
    tool = StaticTool((tool_item,))
    retriever = StaticRetriever((retrieved_item,))
    responder = RecordingResponder()
    runner = VariantRunner(
        responder,
        retriever=retriever,
        tool_selector=FixedSelector((tool.name,)),
        tools=(tool,),
    )

    result = runner.run(_request(VariantKind.RAG_AGENT, eligible_packet))

    assert retriever.seed_context == (tool_item,)
    assert responder.context_calls == [(tool_item, retrieved_item)]
    assert [ref.context_id for ref in result.context_references] == [
        tool_item.context_id,
        retrieved_item.context_id,
    ]


def test_off_topic_request_skips_retrieval_before_safe_refusal(
    eligible_packet: EvidencePacket,
):
    retriever = StaticRetriever((_retrieved_context(),))
    runner = VariantRunner(
        SLMServiceResponder(SLMService(SafeGenerator())), retriever=retriever
    )

    result = runner.run(
        _request(VariantKind.RAG, eligible_packet, question="What is 2 + 2?")
    )

    assert retriever.calls == 0
    assert result.response.response_mode == ResponseMode.REFUSAL
    assert result.response.model_invoked is False
    assert result.context_references == ()


def test_unapproved_agent_tool_is_rejected_before_execution(
    eligible_packet: EvidencePacket,
):
    approved_tool = StaticTool((_tool_context(),))
    runner = VariantRunner(
        RecordingResponder(),
        tool_selector=FixedSelector(("unknown_tool",)),
        tools=(approved_tool,),
    )

    with pytest.raises(VariantExecutionError) as caught:
        runner.run(_request(VariantKind.AGENT, eligible_packet))

    assert caught.value.reason_code == "unapproved_tool_selected"
    assert approved_tool.calls == 0


def test_context_exposing_packet_participant_ref_is_rejected(
    eligible_packet: EvidencePacket,
):
    leaked = _retrieved_context(
        content=f"Reference {eligible_packet.identity.participant_ref} appeared"
    )
    responder = RecordingResponder()
    runner = VariantRunner(responder, retriever=StaticRetriever((leaked,)))

    with pytest.raises(VariantExecutionError) as caught:
        runner.run(_request(VariantKind.RAG, eligible_packet))

    assert caught.value.reason_code == "participant_reference_in_context"
    assert responder.context_calls == []


def test_base_service_adapter_cannot_masquerade_as_context_aware_rag(
    eligible_packet: EvidencePacket,
):
    runner = VariantRunner(
        SLMServiceResponder(SLMService(SafeGenerator())),
        retriever=StaticRetriever((_retrieved_context(),)),
    )

    with pytest.raises(VariantConfigurationError) as caught:
        runner.run(_request(VariantKind.RAG, eligible_packet))

    assert caught.value.reason_code == "context_aware_responder_not_configured"


def test_responder_failures_are_replaced_by_stable_reason_codes(
    eligible_packet: EvidencePacket,
):
    runner = VariantRunner(FailingResponder())

    with pytest.raises(VariantExecutionError) as caught:
        runner.run(_request(VariantKind.BASE_LLM, eligible_packet))

    assert caught.value.reason_code == "responder_execution_failed"
    assert "sensitive implementation detail" not in str(caught.value)
