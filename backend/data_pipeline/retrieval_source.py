"""Approved packet-bound retrieval source for Week 8 RAG integration.

This module exposes only canonical descriptive summaries from the current
validated EvidencePacket. It does not read raw sensing rows, query a database,
or calculate new statistical evidence.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.contracts.evidence import EvidencePacket
from backend.slm.context_responder import render_packet_context_summaries
from backend.slm.variants import (
    ContextDataClass,
    ContextItem,
    ContextSource,
)


class ApprovedPacketRetriever:
    """Retrieve canonical summaries from the current EvidencePacket only."""

    def retrieve(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        top_k: int,
        seed_context: tuple[ContextItem, ...],
    ) -> Sequence[ContextItem]:
        # The current Week 8 source is packet-bound. Question text and agent
        # seed context must not introduce new facts into the retrieval source.
        del question, seed_context

        summaries = render_packet_context_summaries(packet)

        items = tuple(
            ContextItem(
                context_id=f"packet-summary:{index}",
                source=ContextSource.PERSONAL_SUMMARY,
                data_classification=ContextDataClass.AGGREGATED_PERSONAL_SUMMARY,
                content=content,
                provenance_ref=f"evidence-packet:canonical-summary:{index}",
                relevance_score=None,
            )
            for index, content in enumerate(summaries, start=1)
        )

        return items[:top_k]