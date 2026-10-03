"""Request-scoped composition for the reviewed canonical packet source.

The API supplies the Data-owned retriever. Source bindings below describe its
fixed contract independently of returned items; they are not privacy approval
or permission to add a new store, corpus or statistical calculation.
"""

from itertools import islice

from backend.contracts.evidence import EvidencePacket
from backend.slm.client import OllamaClient
from backend.slm.context_responder import (
    ContextApproval,
    PacketContextResponder,
    packet_context_digest,
)
from backend.slm.variants import (
    ContextDataClass,
    ContextItem,
    ContextSource,
    Retriever,
    VariantExecutionError,
    VariantRunner,
)

PACKET_TOOL_NAME = "get_packet_summary"
_SUMMARY_LIMIT = 2


class PacketSummaryTool:
    """Expose the existing two descriptive summaries as one bounded local tool."""

    name = PACKET_TOOL_NAME

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    def run(self, packet: EvidencePacket, question: str) -> tuple[ContextItem, ...]:
        items = tuple(
            islice(
                self._retriever.retrieve(
                    packet, question, top_k=_SUMMARY_LIMIT, seed_context=()
                ),
                _SUMMARY_LIMIT + 1,
            )
        )
        validated = VariantRunner.validate_context(
            packet, items, max_items=_SUMMARY_LIMIT
        )
        if any(item.source != ContextSource.PERSONAL_SUMMARY for item in validated):
            raise VariantExecutionError("packet_tool_source_mismatch")
        # Preserve the source's metadata under a separate namespace. Unknown
        # identifiers remain unknown and cannot acquire a trusted binding here.
        return tuple(
            ContextItem(
                context_id=f"tool:{item.context_id}",
                provenance_ref=f"tool:{item.provenance_ref}",
                source=ContextSource.TOOL_RESULT,
                data_classification=item.data_classification,
                content=item.content,
                relevance_score=item.relevance_score,
            )
            for item in validated
        )


class PacketToolSelector:
    """Deterministic single-tool selection, not an autonomous model planner."""

    def select_tools(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        allowed_tools: tuple[str, ...],
        max_tool_calls: int,
    ) -> tuple[str, ...]:
        del packet, question
        if max_tool_calls < 1 or PACKET_TOOL_NAME not in allowed_tools:
            return ()
        return (PACKET_TOOL_NAME,)


def create_packet_variant_runner(
    client: OllamaClient,
    packet: EvidencePacket,
    *,
    retriever: Retriever,
    allow_aggregated_summaries: bool = False,
) -> VariantRunner:
    """Bind the known source before execution, without invoking retrieval.

    The caller explicitly retains or enables the reviewed integration setting
    for aggregated summaries. Construction itself confers no owner sign-off.
    """

    digest = packet_context_digest(packet)
    approvals = tuple(
        ContextApproval(
            context_id=f"{prefix}packet-summary:{index}",
            provenance_ref=f"{prefix}evidence-packet:canonical-summary:{index}",
            packet_sha256=digest,
            source=source,
            data_classification=ContextDataClass.AGGREGATED_PERSONAL_SUMMARY,
        )
        for prefix, source in (
            ("", ContextSource.PERSONAL_SUMMARY),
            ("tool:", ContextSource.TOOL_RESULT),
        )
        for index in range(1, _SUMMARY_LIMIT + 1)
    )
    return VariantRunner(
        PacketContextResponder(
            client,
            approvals=approvals,
            allow_aggregated_summaries=allow_aggregated_summaries,
        ),
        retriever=retriever,
        tool_selector=PacketToolSelector(),
        tools=(PacketSummaryTool(retriever),),
    )
