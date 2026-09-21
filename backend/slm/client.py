"""Loopback-only Ollama client for schema-constrained SLM generation.

This is the only backend module permitted to perform a runtime network call.
The endpoint validator rejects every non-loopback URL before a request can be
constructed.
"""

from __future__ import annotations

import json
from typing import Any, Protocol
from urllib import error, request
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.contracts.evidence import (
    AssistantDraft,
    EligibilityStatus,
    EvidencePacket,
)
from backend.slm.output_grounding import render_grounded_response_option
from backend.slm.prompt_loader import LoadedEvidencePrompt, load_evidence_prompt

DEFAULT_OLLAMA_TIMEOUT_SECONDS = 180.0


class SLMClientError(RuntimeError):
    """Base error for safe, non-sensitive SLM client failures."""


class SLMUnavailableError(SLMClientError):
    """The local model runtime could not be reached."""


class SLMTimeoutError(SLMUnavailableError):
    """The local model runtime exceeded the configured response deadline."""


class SLMResponseError(SLMClientError):
    """The local runtime returned an invalid response."""


class OllamaClientConfig(BaseModel):
    """Pinned model and loopback endpoint configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_tag: str = Field(min_length=3)
    endpoint: str = "http://127.0.0.1:11434/api/chat"
    timeout_seconds: float = Field(
        default=DEFAULT_OLLAMA_TIMEOUT_SECONDS, gt=0.0, le=300.0
    )
    keep_alive: str = "5m"
    seed: int = Field(default=42, ge=0)

    @field_validator("model_tag")
    @classmethod
    def require_pinned_model_tag(cls, value: str) -> str:
        tag = value.strip()
        if ":" not in tag or tag.lower().endswith(":latest"):
            raise ValueError("model_tag must be an exact, non-latest tag")
        return tag

    @field_validator("endpoint")
    @classmethod
    def require_loopback_chat_endpoint(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "http":
            raise ValueError("the local Ollama endpoint must use http")
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("the Ollama endpoint must use a loopback host")
        if parsed.path.rstrip("/") != "/api/chat":
            raise ValueError("the Ollama endpoint must be /api/chat")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "the Ollama endpoint must not contain credentials or extras"
            )
        return value


class GenerationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_duration_ns: int | None = None
    load_duration_ns: int | None = None
    prompt_eval_count: int | None = None
    prompt_eval_duration_ns: int | None = None
    eval_count: int | None = None
    eval_duration_ns: int | None = None


class GenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    draft: AssistantDraft
    model_tag: str
    prompt_id: str
    prompt_version: str
    prompt_sha256: str
    metrics: GenerationMetrics


class JSONTransport(Protocol):
    def post_json(
        self, endpoint: str, payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]: ...


class RejectRedirects(request.HTTPRedirectHandler):
    """Never let a local response redirect inference traffic elsewhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SLMUnavailableError("local Ollama redirects are disabled")


class UrllibLoopbackTransport:
    """Standard-library transport with proxies and redirects disabled."""

    _MAX_RESPONSE_BYTES = 2_000_000

    def post_json(
        self, endpoint: str, payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]:
        OllamaClientConfig.require_loopback_chat_endpoint(endpoint)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        opener = request.build_opener(request.ProxyHandler({}), RejectRedirects())
        try:
            with opener.open(req, timeout=timeout_seconds) as response:
                raw = response.read(self._MAX_RESPONSE_BYTES + 1)
        except TimeoutError as exc:
            raise SLMTimeoutError("local Ollama request timed out") from exc
        except error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise SLMTimeoutError("local Ollama request timed out") from exc
            raise SLMUnavailableError("local Ollama request failed") from exc
        except OSError as exc:
            raise SLMUnavailableError("local Ollama request failed") from exc

        if len(raw) > self._MAX_RESPONSE_BYTES:
            raise SLMResponseError("local Ollama response exceeded the size limit")
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SLMResponseError("local Ollama returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise SLMResponseError("local Ollama response must be a JSON object")
        return parsed


class OllamaClient:
    """Generate one validated-shape AssistantDraft from one EvidencePacket."""

    def __init__(
        self,
        config: OllamaClientConfig,
        *,
        transport: JSONTransport | None = None,
        prompt: LoadedEvidencePrompt | None = None,
    ) -> None:
        self.config = config
        self.transport = transport or UrllibLoopbackTransport()
        self.prompt = prompt or load_evidence_prompt()

    def build_payload(self, packet: EvidencePacket, question: str) -> dict[str, Any]:
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("question must not be empty")
        if len(clean_question) > 2_000:
            raise ValueError("question exceeds the 2000-character limit")

        runtime_state, state_directive, response_options = (
            self._runtime_state_and_response_options(packet)
        )
        schema = AssistantDraft.model_json_schema()
        system_content = (
            f"{self.prompt.manifest.system_text}\n\n"
            f"{state_directive}\n\n"
            "AssistantDraft JSON schema:\n"
            f"{json.dumps(schema, ensure_ascii=False, sort_keys=True)}"
        )
        packet_payload = packet.model_dump(mode="json")
        # The service keeps the original contract, but the model does not need
        # this participant-level reference. This does not anonymise free text.
        packet_payload["identity"]["participant_ref"] = "redacted"
        user_content = json.dumps(
            {
                "question": clean_question,
                "runtime_evidence_state": runtime_state,
                "allowed_response_options": response_options,
                "allowed_evidence_ids": [
                    packet.identity.packet_id,
                    packet.feature_window.feature_id,
                ],
                "evidence_packet": packet_payload,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return {
            "model": self.config.model_tag,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "stream": False,
            "format": schema,
            "think": False,
            "keep_alive": self.config.keep_alive,
            "options": {"temperature": 0, "seed": self.config.seed},
        }

    def _runtime_state_and_response_options(
        self, packet: EvidencePacket
    ) -> tuple[str, str, list[dict[str, object]]]:
        eligibility = packet.baseline.eligibility_status
        directives = self.prompt.manifest.runtime_state_directives
        if eligibility == EligibilityStatus.ELIGIBLE:
            runtime_state = "state_c_eligible"
            directive = directives.eligible
        elif eligibility == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY:
            runtime_state = "state_b_partial_descriptive_only"
            directive = directives.partial_descriptive_only
        else:
            raise ValueError("model generation is not permitted for State A")

        options: list[dict[str, object]] = []
        for mode in packet.claim_policy.permitted_response_modes:
            try:
                option = render_grounded_response_option(packet, mode)
            except ValueError:
                continue
            options.append(option)
        if not options:
            raise ValueError("packet has no grounded model response option")
        allowed_modes = ", ".join(str(option["response_mode"]) for option in options)
        final_directive = (
            f"{directive.strip()}\n\n"
            "FINAL RUNTIME CONSTRAINT: the only permitted response_mode value(s) "
            f"for this request are: {allowed_modes}. Copy the response_mode from "
            "the selected allowed_response_options entry exactly; do not infer a "
            "different mode from the state name or sentence wording."
        )
        return runtime_state, final_directive, options

    def generate_draft(self, packet: EvidencePacket, question: str) -> GenerationResult:
        payload = self.build_payload(packet, question)
        response = self.transport.post_json(
            self.config.endpoint, payload, self.config.timeout_seconds
        )
        message = response.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise SLMResponseError("local Ollama response is missing message content")

        try:
            draft = AssistantDraft.model_validate_json(message["content"])
        except ValidationError as exc:
            raise SLMResponseError(
                "local model output did not match AssistantDraft"
            ) from exc

        metrics = GenerationMetrics(
            total_duration_ns=_optional_int(response.get("total_duration")),
            load_duration_ns=_optional_int(response.get("load_duration")),
            prompt_eval_count=_optional_int(response.get("prompt_eval_count")),
            prompt_eval_duration_ns=_optional_int(response.get("prompt_eval_duration")),
            eval_count=_optional_int(response.get("eval_count")),
            eval_duration_ns=_optional_int(response.get("eval_duration")),
        )
        return GenerationResult(
            draft=draft,
            model_tag=self.config.model_tag,
            prompt_id=self.prompt.manifest.prompt_id,
            prompt_version=self.prompt.manifest.prompt_version,
            prompt_sha256=self.prompt.sha256,
            metrics=metrics,
        )


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
