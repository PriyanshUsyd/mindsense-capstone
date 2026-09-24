"""Opt-in SLM integration for packet-bound descriptive retrieval/tool context.

This boundary consumes owner-supplied ContextItems, not raw rows or a database.
It accepts only canonical summaries of the current validated EvidencePacket.
Approvals are trusted, request-scoped configuration; never derive them from
untrusted retriever output. Real source approval remains a role-owner decision.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.evidence import EligibilityStatus, EvidencePacket, ResponseMode
from backend.slm.client import OllamaClient
from backend.slm.output_grounding import render_grounded_response_option
from backend.slm.service import SafeSLMResponse, SLMService
from backend.slm.variants import (
    ContextDataClass,
    ContextItem,
    ContextSource,
    VariantConfigurationError,
    VariantExecutionError,
    VariantRunner,
)

CONTEXT_POLICY_VERSION = "0.1.0"
_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"
_PROVENANCE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/@-]*$"


class ContextApproval(BaseModel):
    """Internal source binding; never returned to the model or ordinary logs.

    The digest binds the full packet, including its opaque participant scope,
    dates, model spec and claim policy. It is not a privacy-review certificate
    or a persistent participant identifier.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    context_id: str = Field(min_length=1, max_length=96, pattern=_ID_PATTERN)
    provenance_ref: str = Field(
        min_length=1, max_length=200, pattern=_PROVENANCE_PATTERN
    )
    packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: ContextSource
    data_classification: ContextDataClass


def packet_context_digest(packet: EvidencePacket) -> str:
    """Compute an in-memory binding; do not persist it as a participant key."""

    encoded = json.dumps(
        packet.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def render_packet_context_summaries(packet: EvidencePacket) -> tuple[str, ...]:
    """Allow-listed descriptive content, with no independently computed evidence.

    The adapter can return either of these verbatim summaries. Public-reference
    prose, new statistical claims and arbitrary source text are not supported.
    """

    if not any(
        _has_grounded_option(packet, mode)
        for mode in packet.claim_policy.permitted_response_modes
    ):
        raise VariantExecutionError("context_packet_not_groundable")
    window = packet.feature_window
    return (
        (
            f"Observed feature summary: {window.feature_id} = {window.value} {window.unit}; "
            f"window {window.window_start.isoformat()} to {window.window_end.isoformat()}; "
            f"observed days {window.observed_days} of {window.expected_days}."
        ),
        f"Eligibility state: {packet.baseline.eligibility_status.value}.",
    )


def _has_grounded_option(packet: EvidencePacket, mode: ResponseMode) -> bool:
    try:
        render_grounded_response_option(packet, mode)
    except ValueError:
        return False
    return True


class _ContextOllamaClient(OllamaClient):
    """One-request client; transport remains solely in backend/slm/client.py."""

    def __init__(self, client: OllamaClient, items: tuple[ContextItem, ...]) -> None:
        super().__init__(
            client.config, transport=client.transport, prompt=client.prompt
        )
        self._context_items = items

    def build_payload(self, packet: EvidencePacket, question: str) -> dict[str, Any]:
        payload = super().build_payload(packet, question)
        user = json.loads(payload["messages"][1]["content"])
        user["context_policy_version"] = CONTEXT_POLICY_VERSION
        user["bounded_context"] = [
            {"context_id": item.context_id, "content": item.content}
            for item in self._context_items
        ]
        payload["messages"][1]["content"] = json.dumps(
            user, ensure_ascii=False, sort_keys=True
        )
        return payload


class PacketContextResponder:
    """Consume approved descriptive context through unchanged SLM output gates.

    The default accepts synthetic data only. Enabling aggregated summaries is
    an explicit integration setting after Data/Statistics/Privacy review, not
    an approval conferred by this constructor. No HTTP route enables this class.
    """

    def __init__(
        self,
        client: OllamaClient,
        *,
        approvals: Sequence[ContextApproval],
        allow_aggregated_summaries: bool = False,
    ) -> None:
        self._client = client
        self._base_service = SLMService(client)
        self._allow_aggregated = allow_aggregated_summaries
        self._approvals: dict[tuple[str, str], ContextApproval] = {}
        for approval in approvals:
            key = (approval.context_id, approval.provenance_ref)
            if key in self._approvals:
                raise VariantConfigurationError("duplicate_context_approval")
            self._approvals[key] = approval

    def respond(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        context_items: tuple[ContextItem, ...],
    ) -> SafeSLMResponse:
        if not self._base_service.check_response_health(packet).healthy or (
            packet.baseline.eligibility_status
            in {
                EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
                EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE,
            }
        ):
            return self._base_service.respond(packet, question)
        preflight = self._base_service.preflight_response(
            question, feature_id=packet.feature_window.feature_id
        )
        if preflight is not None:
            return preflight
        if not context_items:
            return self._base_service.respond(packet, question)

        validated = self._validate_context(packet, context_items)
        # A fresh client/service per request prevents context leaking to a later
        # participant or Base call, including after a failed generation.
        return SLMService(_ContextOllamaClient(self._client, validated)).respond(
            packet, question
        )

    def _validate_context(
        self, packet: EvidencePacket, items: tuple[ContextItem, ...]
    ) -> tuple[ContextItem, ...]:
        validated = VariantRunner.validate_context(packet, items, max_items=8)
        digest = packet_context_digest(packet)
        summaries = render_packet_context_summaries(packet)
        allowed_classes = {ContextDataClass.SYNTHETIC}
        if self._allow_aggregated:
            allowed_classes.add(ContextDataClass.AGGREGATED_PERSONAL_SUMMARY)
        for item in validated:
            approval = self._approvals.get((item.context_id, item.provenance_ref))
            if approval is None or (
                approval.packet_sha256 != digest
                or approval.source != item.source
                or approval.data_classification != item.data_classification
            ):
                raise VariantExecutionError("context_source_binding_mismatch")
            if item.source not in {
                ContextSource.PERSONAL_SUMMARY,
                ContextSource.TOOL_RESULT,
            }:
                raise VariantExecutionError("context_source_not_supported")
            if item.data_classification not in allowed_classes:
                raise VariantExecutionError("context_data_class_not_enabled")
            if item.content not in summaries:
                raise VariantExecutionError("context_not_grounded_in_packet")
        return validated
