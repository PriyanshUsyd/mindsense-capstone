"""
Shared HTTP wrapper around SLMService — Priyansh Khandelwal (Integration/QA)'s
own Integration/QA scope, per Richard Zhao's Week 5 handoff note
(docs/slm/week5-integration-evaluation-handoff.md): "Priyansh/Integration
owns the shared HTTP wrapper and acceptance contract; Sheng should
integrate through that wrapper."

This did not exist anywhere in the repo until 2026-09-05 — `backend/api/`
was only a README placeholder. Built now specifically to unblock Sheng
Wang's Week 5 task ("Integrate the UI against the real SLM stub; build the
'normal response' state fully" — Weekly_Plan.md), since without an HTTP
endpoint there was nothing for a frontend to call.

Deliberately minimal: one endpoint, loopback-only by default (matches the
project's local-first privacy stance — see privacy/privacy_architecture_principles.md),
no auth/session/multi-turn state.

FIXED 2026-09-16: `/respond` now takes a `participant_id`, builds the real
`EvidencePacket` server-side via
`backend.statistics.participant_evidence.build_evidence_packet` (which
calls Moe Tanaka's tested `classify_state` / `evidence.py` classification
logic against the real CES pipeline output), and only then hands that
packet to `SLMService.respond()` — every safety/grounding/fallback rule
already enforced there still applies unchanged. Previously this endpoint
accepted a client-supplied `evidence_packet` dict, schema-validated it, and
passed it straight through — meaning a caller could assert any
`eligibility_status` / `evidence_strength` and the backend would believe
it; see git history for the prior contract.

The default `MINDSENSE_SLM_RUNTIME=demo` uses a deterministic client so tests
and UI setup do not require Ollama. Set `MINDSENSE_SLM_RUNTIME=ollama` when
starting Uvicorn to enable Richard's manifest-bounded local model selector.
The optional `model_tag` request field can select only a pinned comparison
candidate; `/models` exposes the bounded catalog for frontend integration.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

from backend.contracts.evidence import (
    ApprovedClaimId,
    AssistantDraft,
    EvidencePacket,
    ResponseMode,
)
from backend.slm.client import GenerationMetrics, GenerationResult
from backend.slm.output_grounding import render_grounded_example
from backend.slm.request_policy import infer_feature_from_question
from backend.slm.runtime import (
    create_local_service,
    default_model_tag,
    listed_model_tags,
)
from backend.slm.service import SafeSLMResponse, SLMService
from backend.statistics.participant_evidence import (
    UnknownFeature,
    UnknownParticipant,
    build_evidence_packet,
)

SLM_RUNTIME_ENV = "MINDSENSE_SLM_RUNTIME"


class DeterministicDemoClient:
    """Stub SLM client for local demo/dev use — never talks to any network
    or model daemon. Mirrors benchmarks/slm_prohibited_request_baseline.py's
    ObservableSafeStub: returns a grounded draft built directly from the
    real EvidencePacket's own values, so the response text genuinely
    reflects the request rather than being hardcoded copy.

    FIXED 2026-09-16: this used to hardcode `response_mode=NORMAL` and
    `claim_ids_used=(OBSERVATION_OF_DEVIATION, UNCERTAINTY_DISCLOSURE)`
    unconditionally — invisible while `/respond` only ever received the one
    ELIGIBLE-with-evidence fixture packet. Once `/respond` started building
    real packets (`backend.statistics.participant_evidence`), a real
    PARTIAL_DESCRIPTIVE_ONLY packet (State B, or State C with no defensible
    per-person evidence — see `participant_evidence.py`) hit this and
    always failed closed to `generic_fallback`
    (`grounding_claim_mismatch`/`model_generation_failed`), because NORMAL
    mode and OBSERVATION_OF_DEVIATION are neither permitted nor approved
    for that packet. This now picks the mode/claims `output_grounding.py`'s
    grammar actually supports for the packet's real eligibility status,
    restricted to what its own `claim_policy` permits."""

    def generate_draft(self, packet: EvidencePacket, question: str) -> GenerationResult:
        del question
        mode, claim_ids = self._select_mode_and_claims(packet)
        draft = AssistantDraft(
            packet_id=packet.identity.packet_id,
            response_mode=mode,
            claim_ids_used=claim_ids,
            evidence_ids_referenced=(packet.feature_window.feature_id,),
            text=render_grounded_example(packet, mode),
            includes_uncertainty_statement=ApprovedClaimId.UNCERTAINTY_DISCLOSURE
            in claim_ids,
        )
        return GenerationResult(
            draft=draft,
            model_tag="demo-stub:1.0",
            prompt_id="week5-api-demo-stub",
            prompt_version="1.0.0",
            prompt_sha256="0" * 64,
            metrics=GenerationMetrics(),
        )

    @staticmethod
    def _select_mode_and_claims(
        packet: EvidencePacket,
    ) -> tuple[ResponseMode, tuple[ApprovedClaimId, ...]]:
        from backend.contracts.evidence import EligibilityStatus

        permitted = set(packet.claim_policy.permitted_response_modes)
        status = packet.baseline.eligibility_status

        if status == EligibilityStatus.ELIGIBLE:
            if ResponseMode.NORMAL in permitted:
                return ResponseMode.NORMAL, (
                    ApprovedClaimId.OBSERVATION_OF_DEVIATION,
                    ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
                )
            if ResponseMode.UNCERTAINTY in permitted:
                return ResponseMode.UNCERTAINTY, (
                    ApprovedClaimId.OBSERVATION_OF_DEVIATION,
                    ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
                )
        elif status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY:
            if ResponseMode.UNCERTAINTY in permitted:
                return ResponseMode.UNCERTAINTY, (
                    ApprovedClaimId.TREND_DESCRIPTION,
                    ApprovedClaimId.NOT_ENOUGH_DATA,
                    ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
                )
            if ResponseMode.INSUFFICIENT_DATA in permitted:
                return ResponseMode.INSUFFICIENT_DATA, (
                    ApprovedClaimId.TREND_DESCRIPTION,
                    ApprovedClaimId.NOT_ENOUGH_DATA,
                )
        raise ValueError(
            f"demo stub cannot ground a response for eligibility_status={status!r} "
            f"with permitted_response_modes={packet.claim_policy.permitted_response_modes!r}"
        )


class RespondRequest(BaseModel):
    """FIXED 2026-09-16 — this request used to carry a client-supplied
    `evidence_packet: dict`, validated (schema only) and passed straight to
    `SLMService.respond()` without ever calling this codebase's own
    classification logic (`backend.statistics.eligibility.classify_state`,
    `backend.statistics.evidence`) — meaning the client could assert any
    `eligibility_status` / `evidence_strength` it wanted and the backend
    would believe it. The request now carries only a `participant_id` (and
    optional `feature_id` and manifest-bounded `model_tag`); the packet is always built server-side by
    `backend.statistics.participant_evidence.build_evidence_packet` from
    the real CES pipeline output, never accepted from the caller.

    FIXED 2026-09-20: `feature_id` used to default to `"gps_distance"`, and
    the frontend sent that literal on every request — so a question about
    phone unlocks was still answered from GPS evidence, because nothing in
    the request path ever read the question text to pick a feature.
    `feature_id` is now optional; when a caller omits it, `/respond` infers
    the feature from the question via
    `backend.slm.request_policy.infer_feature_from_question`. A caller that
    still sends an explicit `feature_id` (tooling, tests) keeps full
    control — inference only fills the gap when none is given."""

    model_config = ConfigDict(extra="forbid")

    participant_id: str
    question: str
    feature_id: str | None = None
    model_tag: str | None = None


class ModelCatalogResponse(BaseModel):
    """Read-only catalog used by the frontend to render a bounded selector."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime: str
    selection_enabled: bool
    default_model_tag: str
    available_model_tags: tuple[str, ...]


def _selected_runtime_name(runtime_name: str | None = None) -> str:
    selected = (
        (
            runtime_name
            if runtime_name is not None
            else os.environ.get(SLM_RUNTIME_ENV, "demo")
        )
        .strip()
        .lower()
    )
    if selected not in {"demo", "ollama"}:
        raise ValueError(f"{SLM_RUNTIME_ENV} must be 'demo' or 'ollama'")
    return selected


def create_runtime_service(
    runtime_name: str | None = None, *, model_tag: str | None = None
) -> SLMService:
    """Select an explicit local runtime without changing the HTTP contract.

    ``demo`` remains the safe default for tests and contributor setup.
    ``ollama`` uses Richard's manifest-pinned local model client and still
    fails closed through ``SLMService`` if the daemon is unavailable.
    """

    selected = _selected_runtime_name(runtime_name)
    if selected == "demo":
        if model_tag is not None:
            raise ValueError("model_tag selection requires the ollama runtime")
        return SLMService(DeterministicDemoClient())
    if selected == "ollama":
        return create_local_service(model_tag=model_tag)
    raise AssertionError("validated runtime name was not handled")


def create_app(
    service: SLMService | None = None, *, runtime_name: str | None = None
) -> FastAPI:
    app = FastAPI(title="MindSense local SLM API", version="0.1.0")

    # Loopback-only local dev server per the project's privacy stance —
    # this allows the Vite dev server's own origin, nothing else.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    selected_runtime = (
        "injected" if service is not None else _selected_runtime_name(runtime_name)
    )
    active_service = service or (
        create_runtime_service("demo") if selected_runtime == "demo" else None
    )

    def service_for(model_tag: str | None) -> SLMService:
        if active_service is not None:
            if model_tag is not None:
                raise ValueError("model_tag selection requires the ollama runtime")
            return active_service
        return create_runtime_service("ollama", model_tag=model_tag)

    @app.post("/respond", response_model=SafeSLMResponse)
    def respond(payload: RespondRequest) -> SafeSLMResponse:
        try:
            request_service = service_for(payload.model_tag)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        preflight = request_service.preflight_response(payload.question)
        if preflight is not None:
            return preflight

        feature_id = payload.feature_id or infer_feature_from_question(payload.question)
        try:
            packet = build_evidence_packet(
                payload.participant_id, feature_id=feature_id
            )
        except UnknownParticipant as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except UnknownFeature as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (FileNotFoundError, PermissionError):
            return request_service.evidence_unavailable_response(payload.question)
        try:
            return request_service.respond(packet, payload.question)
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail="local generation failed"
            ) from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/models", response_model=ModelCatalogResponse)
    def models() -> ModelCatalogResponse:
        return ModelCatalogResponse(
            runtime=selected_runtime,
            selection_enabled=selected_runtime == "ollama",
            default_model_tag=default_model_tag(),
            available_model_tags=listed_model_tags(),
        )

    return app


app = create_app()
