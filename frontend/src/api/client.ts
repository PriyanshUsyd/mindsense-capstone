// Thin fetch wrapper for backend/api/app.py's /respond endpoint.
//
// Built 2026-09-05 by Priyansh Khandelwal (Integration/QA) to unblock
// Sheng Wang's Week 5 task ("Integrate the UI against the real SLM stub" -
// Weekly_Plan.md). No commit from Sheng exists anywhere in this repo as of
// this date.
//
// Per build-reference.md Section 8, request/response types here are meant
// to be regenerated from the backend's OpenAPI export once
// scripts/export_openapi.py exists - it doesn't yet, so these are
// hand-written for now and should be treated as provisional.

export type ResponseMode =
  | 'normal'
  | 'uncertainty'
  | 'insufficient_data'
  | 'refusal'
  | 'generic_fallback'
  | 'crisis_aware_fallback'

export interface SafeSLMResponse {
  response_mode: ResponseMode
  text: string
  used_fallback: boolean
  rejection_reason: string | null
  model_tag: string | null
  model_invoked: boolean
}

// The evidence packet's exact shape is owned by backend/contracts/evidence.py
// (a strict Pydantic model); the frontend does not re-validate it, it just
// passes through whatever a validated packet from the backend looks like.
export type EvidencePacket = Record<string, unknown>

const API_BASE_URL = 'http://127.0.0.1:8000'

export class RespondError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export async function respond(
  evidencePacket: EvidencePacket,
  question: string,
): Promise<SafeSLMResponse> {
  const res = await fetch(`${API_BASE_URL}/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ evidence_packet: evidencePacket, question }),
  })

  if (!res.ok) {
    throw new RespondError(`request failed with status ${res.status}`, res.status)
  }

  return (await res.json()) as SafeSLMResponse
}
