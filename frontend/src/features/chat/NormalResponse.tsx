import { useState } from 'react'
import { respond, type EvidencePacket, type SafeSLMResponse } from '../../api/client'

// Week 5 "normal response" state, integrated against the real SLM stub via
// backend/api/app.py. Filled in by Priyansh Khandelwal (Integration/QA) —
// Sheng Wang did not deliver this, per Weekly_Plan.md Week 5: "Integrate
// the UI against the real SLM stub; build the 'normal response' state
// fully." No commit from Sheng exists anywhere in this repository as of
// 2026-09-05.
//
// Mirrors tests/slm/fixtures/week5_gps_eligible.json (kept in sync by
// hand for this minimal demo — see backend/api/app.py's own note about
// scripts/export_openapi.py not existing yet, which is the real fix for
// this once it's built).
const EXAMPLE_ELIGIBLE_GPS_PACKET: EvidencePacket = {
  identity: {
    contract_version: '1.0.0',
    packet_id: 'synthetic_week5_gps_001',
    model_spec_id: 'synthetic-shadow-v1',
    generated_at: '2026-09-01T12:00:00Z',
    participant_ref: 'synthetic-only',
  },
  feature_window: {
    feature_id: 'gps_distance',
    unit: 'kilometres_per_day',
    window_start: '2026-08-01',
    window_end: '2026-08-28',
    value: 3.8,
    observed_days: 25,
    expected_days: 28,
    coverage_ratio: 0.8928571428571429,
    platform: 'android',
    quality_flags: [],
  },
  baseline: {
    method: 'trailing person-mean, 28-day window',
    value: 4.6,
    n_baseline_observations: 4,
    eligibility_status: 'eligible',
    ineligible_reason: null,
  },
  evidence: {
    within_person_deviation_estimate: -0.8,
    confidence_interval_low: -1.4,
    confidence_interval_high: -0.2,
    direction: 'below_baseline',
    evidence_strength: 'moderate',
  },
  uncertainty: {
    item_level: ['moderate evidence strength'],
    packet_level: ['synthetic development fixture; not participant data'],
  },
  claim_policy: {
    approved_claim_ids: ['observation_of_deviation', 'uncertainty_disclosure', 'non_diagnostic_boundary'],
    prohibited_claim_ids: ['diagnosis', 'causal_explanation', 'treatment_or_crisis_advice', 'risk_prediction'],
    permitted_response_modes: ['normal', 'uncertainty'],
  },
}

type LoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; response: SafeSLMResponse }

export function NormalResponse() {
  const [state, setState] = useState<LoadState>({ status: 'idle' })

  async function handleAsk() {
    setState({ status: 'loading' })
    try {
      const response = await respond(
        EXAMPLE_ELIGIBLE_GPS_PACKET,
        'How was my movement different from my recent baseline?',
      )
      setState({ status: 'success', response })
    } catch (err) {
      setState({
        status: 'error',
        message: err instanceof Error ? err.message : 'unknown error',
      })
    }
  }

  return (
    <section id="normal-response-demo">
      <h2>Normal response (Week 5)</h2>
      <p>
        Calls the real backend at <code>backend/api/app.py</code>, which runs the
        request through the real <code>SLMService</code> (safety gate, output
        grounding, and all) — this is not a hardcoded string.
      </p>
      <button type="button" onClick={handleAsk} disabled={state.status === 'loading'}>
        {state.status === 'loading' ? 'Asking…' : 'Ask about my recent movement'}
      </button>

      {state.status === 'error' && (
        <p role="alert" className="response-error">
          Could not reach the local API ({state.message}). Is
          <code> uvicorn backend.api.app:app</code> running?
        </p>
      )}

      {state.status === 'success' && (
        <div className="response-card" data-response-mode={state.response.response_mode}>
          <span className="response-mode-badge">{state.response.response_mode}</span>
          <p>{state.response.text}</p>
        </div>
      )}
    </section>
  )
}
