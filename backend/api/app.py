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
no auth/session/multi-turn state. It is a thin pass-through to
SLMService.respond() — every safety/grounding/fallback rule already
enforced there applies unchanged; this file adds no new logic of its own
beyond request/response shaping.

By default, uses a deterministic stub client (same pattern as
benchmarks/slm_prohibited_request_baseline.py's ObservableSafeStub and
backend/slm/shadow_cli.py), NOT a live Ollama call — so `npm run dev` +
this API can demonstrate the real "normal response" flow end-to-end
without requiring Ollama installed. Pass a real client
(backend.slm.runtime.create_local_service()) via create_app(service=...)
to use the real local model instead; nothing about the HTTP contract
changes either way.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, ValidationError

from backend.contracts.evidence import EvidencePacket
from backend.slm.client import GenerationMetrics, GenerationResult
from backend.slm.output_grounding import render_grounded_example
from backend.contracts.evidence import ApprovedClaimId, AssistantDraft, ResponseMode
from backend.slm.service import SafeSLMResponse, SLMService


class DeterministicDemoClient:
    """Stub SLM client for local demo/dev use — never talks to any network
    or model daemon. Mirrors benchmarks/slm_prohibited_request_baseline.py's
    ObservableSafeStub: returns a grounded NORMAL draft built directly from
    the real EvidencePacket's own values, so the response text genuinely
    reflects the request rather than being hardcoded copy."""

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
            model_tag="demo-stub:1.0",
            prompt_id="week5-api-demo-stub",
            prompt_version="1.0.0",
            prompt_sha256="0" * 64,
            metrics=GenerationMetrics(),
        )


class RespondRequest(BaseModel):
    """`evidence_packet` is deliberately a plain dict here, not a typed
    `EvidencePacket` field. `EvidencePacket` is a strict=True model
    (backend/contracts/evidence.py) - Pydantic v2's strict mode only
    permits ISO date/datetime strings and string enum values in its JSON
    validation path (`model_validate_json`), not when FastAPI hands it an
    already-parsed Python dict for a nested field. Validating the nested
    packet explicitly via model_validate_json below (not model_validate)
    keeps the same strict contract without silently loosening it here."""

    model_config = ConfigDict(extra="forbid")

    evidence_packet: dict
    question: str


def create_app(service: SLMService | None = None) -> FastAPI:
    app = FastAPI(title="MindSense local SLM API", version="0.1.0")

    # Loopback-only local dev server per the project's privacy stance —
    # this allows the Vite dev server's own origin, nothing else.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["POST"],
        allow_headers=["*"],
    )

    active_service = service or SLMService(DeterministicDemoClient())

    @app.post("/respond", response_model=SafeSLMResponse)
    def respond(payload: RespondRequest) -> SafeSLMResponse:
        try:
            packet = EvidencePacket.model_validate_json(json.dumps(payload.evidence_packet))
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=json.loads(exc.json())) from exc
        try:
            return active_service.respond(packet, payload.question)
        except Exception as exc:  # noqa: BLE001 - never leak internals to the UI
            raise HTTPException(status_code=500, detail="local generation failed") from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
