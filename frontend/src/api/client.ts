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
  generation_prompt_sha256: string | null
  fallback_prompt_sha256: string | null
  metrics: GenerationMetrics | null
  request_disposition: 'allow' | 'refuse' | 'crisis'
  request_category:
    | 'in_scope'
    | 'crisis_self_harm'
    | 'diagnosis_seeking'
    | 'causal_inference_seeking'
    | 'treatment_advice_seeking'
    | 'risk_prediction_seeking'
    | 'prompt_injection'
    | 'sensitive_data_request'
  request_policy_version: string
  model_invoked: boolean
}

export interface GenerationMetrics {
  total_duration_ns: number | null
  load_duration_ns: number | null
  prompt_eval_count: number | null
  prompt_eval_duration_ns: number | null
  eval_count: number | null
  eval_duration_ns: number | null
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

// FIXED 2026-09-16: this used to send a hardcoded EvidencePacket (the
// browser asserting its own eligibility_status/evidence_strength) on every
// request. `/respond` now builds the real packet server-side from
// `participant_id` via backend/statistics/participant_evidence.py — the
// browser only ever identifies WHICH participant is asking, never what
// their evidence looks like.
//
// FIXED 2026-09-20: this used to also send a hardcoded `feature_id`
// ('gps_distance') on every request, so any question — no matter what it
// actually asked about — was answered from GPS evidence. `feature_id` is
// now an optional override: when omitted, the backend infers the feature
// from the question text itself (backend/slm/request_policy.py's
// `infer_feature_from_question`). Callers that need to force a specific
// feature (e.g. a future feature picker) may still pass one explicitly.
export async function respond(
  participantId: string,
  question: string,
  featureId?: string,
): Promise<SafeSLMResponse> {
  const res = await fetch(`${API_BASE_URL}/respond`, {
    method: 'POST',
    redirect: 'error',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      participant_id: participantId,
      question,
      ...(featureId ? { feature_id: featureId } : {}),
    }),
  })

  if (!res.ok) {
    throw new RespondError(`request failed with status ${res.status}`, res.status)
  }

  return (await res.json()) as SafeSLMResponse
}
