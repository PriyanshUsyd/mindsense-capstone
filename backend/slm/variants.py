"""Common Week 7 orchestration boundary for SLM architecture variants.

This module deliberately sits outside the frozen ``EvidencePacket`` contract.
It prepares bounded retrieval/tool context and records an audit trace, while a
``VariantResponder`` remains responsible for producing the final
``SafeSLMResponse`` through the existing request policy, health, safety and
grounding gates.

No concrete data store, statistical tool, embedding model or scientific corpus
is selected here. Those dependencies must be supplied by their role owners.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from enum import Enum
from itertools import islice
from time import perf_counter
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.contracts.evidence import EligibilityStatus, EvidencePacket
from backend.slm.request_policy import (
    RequestDisposition,
    classify_request,
    request_scope_rejection,
)
from backend.slm.response_health import check_response_health
from backend.slm.service import SafeSLMResponse, SLMService

VARIANT_INTERFACE_VERSION = "0.2.0"
_STRICT = ConfigDict(extra="forbid", frozen=True, strict=True)
_CONTEXT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"
_PROVENANCE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/@-]*$"
_TOOL_NAME_PATTERN = r"^[a-z][a-z0-9_]{1,63}$"


class VariantKind(str, Enum):
    """The four client-requested architectures under one interface."""

    BASE_LLM = "base_llm"
    RAG = "rag"
    AGENT = "agent"
    RAG_AGENT = "rag_agent"


class ContextSource(str, Enum):
    """Approved high-level source classes; raw participant rows are absent."""

    PERSONAL_SUMMARY = "personal_summary"
    APPROVED_REFERENCE = "approved_reference"
    TOOL_RESULT = "tool_result"


class ContextDataClass(str, Enum):
    """Data classes permitted at the variant boundary."""

    SYNTHETIC = "synthetic"
    AGGREGATED_PERSONAL_SUMMARY = "aggregated_personal_summary"
    APPROVED_PUBLIC_REFERENCE = "approved_public_reference"


class ToolCallStatus(str, Enum):
    COMPLETED = "completed"


class VariantError(RuntimeError):
    """Base error carrying a stable, non-sensitive audit reason."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class VariantConfigurationError(VariantError):
    """A required owner-approved variant dependency is not configured."""


class VariantExecutionError(VariantError):
    """A configured dependency violated the bounded execution contract."""


class ContextItem(BaseModel):
    """One bounded context item supplied to a context-aware responder.

    ``content`` is intentionally excluded from ``VariantRunRecord`` so an
    ordinary benchmark/result log contains provenance identifiers, not the
    retrieved text itself.
    """

    model_config = _STRICT

    context_id: str = Field(min_length=1, max_length=96, pattern=_CONTEXT_ID_PATTERN)
    source: ContextSource
    data_classification: ContextDataClass
    content: str = Field(min_length=1, max_length=1_000)
    provenance_ref: str = Field(
        min_length=1, max_length=200, pattern=_PROVENANCE_PATTERN
    )
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("content")
    @classmethod
    def reject_blank_or_control_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("context content must not be blank")
        if any(ord(character) < 32 and character not in "\n\t" for character in value):
            raise ValueError("context content contains control characters")
        return stripped


class ContextReference(BaseModel):
    """Content-free provenance retained in comparison output."""

    model_config = _STRICT

    context_id: str
    source: ContextSource
    data_classification: ContextDataClass
    provenance_ref: str
    relevance_score: float | None

    @classmethod
    def from_item(cls, item: ContextItem) -> ContextReference:
        return cls(
            context_id=item.context_id,
            source=item.source,
            data_classification=item.data_classification,
            provenance_ref=item.provenance_ref,
            relevance_score=item.relevance_score,
        )


class ToolExecutionTrace(BaseModel):
    """Minimal tool audit record; arguments and returned text are not logged."""

    model_config = _STRICT

    tool_name: str = Field(pattern=_TOOL_NAME_PATTERN)
    status: ToolCallStatus = ToolCallStatus.COMPLETED
    context_ids: tuple[str, ...]


class VariantRequest(BaseModel):
    """Shared input for all four variants."""

    model_config = _STRICT

    variant: VariantKind
    question: str = Field(min_length=1, max_length=2_000)
    packet: EvidencePacket
    top_k: int = Field(default=3, ge=1, le=5)
    max_tool_calls: int = Field(default=2, ge=1, le=3)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        return stripped


class VariantRunRecord(BaseModel):
    """Shared output and privacy-minimised audit trace."""

    model_config = _STRICT

    interface_version: str = VARIANT_INTERFACE_VERSION
    variant: VariantKind
    response: SafeSLMResponse
    context_references: tuple[ContextReference, ...]
    tool_trace: tuple[ToolExecutionTrace, ...]
    retrieval_attempted: bool
    tool_selection_attempted: bool
    wall_latency_ms: float = Field(ge=0.0)


class VariantResponder(Protocol):
    """Final response engine shared by Base, RAG and agent variants."""

    def respond(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        context_items: tuple[ContextItem, ...],
    ) -> SafeSLMResponse: ...


class Retriever(Protocol):
    """Owner-supplied retriever over approved local summaries/references."""

    def retrieve(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        top_k: int,
        seed_context: tuple[ContextItem, ...],
    ) -> Sequence[ContextItem]: ...


class ToolSelector(Protocol):
    """Bounded planner that may select only names exposed by the registry."""

    def select_tools(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        allowed_tools: tuple[str, ...],
        max_tool_calls: int,
    ) -> Sequence[str]: ...


class LocalContextTool(Protocol):
    """A white-listed local tool returning approved structured context."""

    name: str

    def run(self, packet: EvidencePacket, question: str) -> Sequence[ContextItem]: ...


class SLMServiceResponder:
    """Production adapter for the existing Base LLM service.

    It intentionally refuses non-empty context. This prevents the project from
    labelling a run as RAG/agentic before a reviewed context-aware prompt and
    grounding path exist.
    """

    def __init__(self, service: SLMService) -> None:
        self._service = service

    def respond(
        self,
        packet: EvidencePacket,
        question: str,
        *,
        context_items: tuple[ContextItem, ...],
    ) -> SafeSLMResponse:
        if context_items:
            raise VariantConfigurationError("context_aware_responder_not_configured")
        return self._service.respond(packet, question)


class VariantRunner:
    """Prepare one variant run without weakening the existing SLM gates."""

    def __init__(
        self,
        responder: VariantResponder,
        *,
        retriever: Retriever | None = None,
        tool_selector: ToolSelector | None = None,
        tools: Sequence[LocalContextTool] = (),
    ) -> None:
        self._responder = responder
        self._retriever = retriever
        self._tool_selector = tool_selector
        registry: dict[str, LocalContextTool] = {}
        for tool in tools:
            name = getattr(tool, "name", None)
            if (
                not isinstance(name, str)
                or re.fullmatch(_TOOL_NAME_PATTERN, name) is None
                or name in registry
            ):
                raise VariantConfigurationError("tool_registry_invalid")
            registry[name] = tool
        self._tools = registry

    def run(self, request: VariantRequest) -> VariantRunRecord:
        started = perf_counter()
        context_items: list[ContextItem] = []
        tool_trace: list[ToolExecutionTrace] = []
        retrieval_attempted = False
        tool_selection_attempted = False

        if self._may_prepare_context(request):
            if request.variant == VariantKind.RAG:
                retrieval_attempted = True
                context_items.extend(self._retrieve(request, seed_context=()))
            elif request.variant == VariantKind.AGENT:
                tool_selection_attempted = True
                tool_items, trace = self._run_tools(request)
                context_items.extend(tool_items)
                tool_trace.extend(trace)
            elif request.variant == VariantKind.RAG_AGENT:
                tool_selection_attempted = True
                tool_items, trace = self._run_tools(request)
                tool_trace.extend(trace)
                context_items.extend(tool_items)
                retrieval_attempted = True
                context_items.extend(
                    self._retrieve(request, seed_context=tuple(tool_items))
                )

        validated_context = self.validate_context(
            request.packet, context_items, max_items=8
        )
        try:
            response = self._responder.respond(
                request.packet,
                request.question,
                context_items=validated_context,
            )
        except VariantError:
            raise
        except Exception as exc:
            raise VariantExecutionError("responder_execution_failed") from exc
        if not isinstance(response, SafeSLMResponse):
            raise VariantExecutionError("responder_return_invalid")
        elapsed_ms = (perf_counter() - started) * 1_000
        return VariantRunRecord(
            variant=request.variant,
            response=response,
            context_references=tuple(
                ContextReference.from_item(item) for item in validated_context
            ),
            tool_trace=tuple(tool_trace),
            retrieval_attempted=retrieval_attempted,
            tool_selection_attempted=tool_selection_attempted,
            wall_latency_ms=elapsed_ms,
        )

    def respond_safely(
        self, request: VariantRequest, *, fallback_service: SLMService
    ) -> SafeSLMResponse:
        """Convert pre-generation context failures to the versioned safe response.

        ``run`` remains the diagnostic/benchmark interface. Unexpected responder
        failures still raise a sanitised error: their invocation state is not
        known and must not be recorded as a pre-model context failure.
        """

        try:
            return self.run(request).response
        except VariantError as exc:
            if exc.reason_code in {
                "responder_execution_failed",
                "responder_return_invalid",
            }:
                raise
            return fallback_service.context_unavailable_response(request.question)

    @staticmethod
    def _may_prepare_context(request: VariantRequest) -> bool:
        """Never retrieve or call tools before deterministic preflight gates."""

        decision = classify_request(request.question)
        if decision.disposition != RequestDisposition.ALLOW:
            return False
        if request_scope_rejection(
            request.question, feature_id=request.packet.feature_window.feature_id
        ):
            return False
        if not check_response_health(request.packet).healthy:
            return False
        return request.packet.baseline.eligibility_status not in {
            EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
            EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE,
        }

    def _retrieve(
        self,
        request: VariantRequest,
        *,
        seed_context: tuple[ContextItem, ...],
    ) -> tuple[ContextItem, ...]:
        if self._retriever is None:
            raise VariantConfigurationError("approved_retriever_not_configured")
        try:
            items = tuple(
                islice(
                    self._retriever.retrieve(
                        request.packet,
                        request.question,
                        top_k=request.top_k,
                        seed_context=seed_context,
                    ),
                    request.top_k + 1,
                )
            )
        except VariantError:
            raise
        except Exception as exc:
            raise VariantExecutionError("retriever_execution_failed") from exc
        if any(not isinstance(item, ContextItem) for item in items):
            raise VariantExecutionError("retriever_return_invalid")
        if len(items) > request.top_k:
            raise VariantExecutionError("retriever_exceeded_top_k")
        if not items:
            raise VariantExecutionError("retriever_returned_no_context")
        return items

    def _run_tools(
        self, request: VariantRequest
    ) -> tuple[tuple[ContextItem, ...], tuple[ToolExecutionTrace, ...]]:
        if self._tool_selector is None or not self._tools:
            raise VariantConfigurationError("approved_agent_tools_not_configured")
        allowed = tuple(sorted(self._tools))
        try:
            selected = tuple(
                islice(
                    self._tool_selector.select_tools(
                        request.packet,
                        request.question,
                        allowed_tools=allowed,
                        max_tool_calls=request.max_tool_calls,
                    ),
                    request.max_tool_calls + 1,
                )
            )
        except VariantError:
            raise
        except Exception as exc:
            raise VariantExecutionError("tool_selection_failed") from exc
        if any(not isinstance(name, str) for name in selected):
            raise VariantExecutionError("tool_selection_invalid")
        if len(selected) > request.max_tool_calls:
            raise VariantExecutionError("tool_selector_exceeded_limit")
        if len(selected) != len(set(selected)):
            raise VariantExecutionError("duplicate_tool_selection")
        if any(name not in self._tools for name in selected):
            raise VariantExecutionError("unapproved_tool_selected")
        if not selected:
            raise VariantExecutionError("no_agent_tool_selected")

        context_items: list[ContextItem] = []
        trace: list[ToolExecutionTrace] = []
        for name in selected:
            try:
                returned = tuple(
                    islice(self._tools[name].run(request.packet, request.question), 9)
                )
            except VariantError:
                raise
            except Exception as exc:
                raise VariantExecutionError("tool_execution_failed") from exc
            if any(not isinstance(item, ContextItem) for item in returned):
                raise VariantExecutionError("tool_return_invalid")
            if any(item.source != ContextSource.TOOL_RESULT for item in returned):
                raise VariantExecutionError("tool_returned_wrong_context_source")
            if not returned:
                raise VariantExecutionError("tool_returned_no_context")
            if len(context_items) + len(returned) > 8:
                raise VariantExecutionError("context_item_limit_exceeded")
            context_items.extend(returned)
            trace.append(
                ToolExecutionTrace(
                    tool_name=name,
                    context_ids=tuple(item.context_id for item in returned),
                )
            )
        return tuple(context_items), tuple(trace)

    @staticmethod
    def validate_context(
        packet: EvidencePacket,
        items: Sequence[ContextItem],
        *,
        max_items: int,
    ) -> tuple[ContextItem, ...]:
        if any(not isinstance(item, ContextItem) for item in items):
            raise VariantExecutionError("context_item_invalid")
        try:
            validated = tuple(
                ContextItem.model_validate(item.model_dump()) for item in items
            )
        except ValueError as exc:
            raise VariantExecutionError("context_item_invalid") from exc
        if len(validated) > max_items:
            raise VariantExecutionError("context_item_limit_exceeded")
        ids = tuple(item.context_id for item in validated)
        if len(ids) != len(set(ids)):
            raise VariantExecutionError("duplicate_context_id")
        participant_ref = packet.identity.participant_ref.strip().casefold()
        if participant_ref and any(
            participant_ref in item.content.casefold()
            or participant_ref in item.provenance_ref.casefold()
            or participant_ref in item.context_id.casefold()
            for item in validated
        ):
            raise VariantExecutionError("participant_reference_in_context")
        return validated
