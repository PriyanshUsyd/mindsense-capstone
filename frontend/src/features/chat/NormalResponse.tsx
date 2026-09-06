import { useState } from 'react'

import { respond, type EvidencePacket, type SafeSLMResponse } from '../../api/client'
import { AppShell } from '../../components/AppShell'
import {
  CrisisAwareFallbackState,
  GenericFallbackState,
  InsufficientDataState,
  LoadingState,
  NormalState,
  RefusalState,
  UncertaintyState,
  WelcomeState,
  type EvidenceSummaryView,
} from './ChatStates'

// Synthetic fixture matching the frozen Week 5 EvidencePacket contract.
// It exercises the same /respond route as participant data without exposing
// personal information in the frontend demo.
const EXAMPLE_ELIGIBLE_GPS_PACKET = {
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
    approved_claim_ids: [
      'observation_of_deviation',
      'uncertainty_disclosure',
      'non_diagnostic_boundary',
    ],
    prohibited_claim_ids: [
      'diagnosis',
      'causal_explanation',
      'treatment_or_crisis_advice',
      'risk_prediction',
    ],
    permitted_response_modes: ['normal', 'uncertainty'],
  },
} satisfies EvidencePacket

const DEFAULT_QUESTION = 'How was my movement different from my recent baseline?'

const featureWindow = EXAMPLE_ELIGIBLE_GPS_PACKET.feature_window
const baseline = EXAMPLE_ELIGIBLE_GPS_PACKET.baseline
const dateFormatter = new Intl.DateTimeFormat('en-AU', {
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
  year: 'numeric',
})

const EVIDENCE_SUMMARY: EvidenceSummaryView = {
  baseline: `${baseline.value} km/day`,
  coverage:
    `${featureWindow.observed_days} of ${featureWindow.expected_days} days ` +
    `(${Math.round(featureWindow.coverage_ratio * 100)}%)`,
  currentValue: `${featureWindow.value} km/day`,
  evidenceStrength:
    EXAMPLE_ELIGIBLE_GPS_PACKET.evidence.evidence_strength[0].toUpperCase() +
    EXAMPLE_ELIGIBLE_GPS_PACKET.evidence.evidence_strength.slice(1),
  featureLabel: 'GPS distance',
  timeWindow:
    `${dateFormatter.format(new Date(featureWindow.window_start))} – ` +
    dateFormatter.format(new Date(featureWindow.window_end)),
  uncertainty: EXAMPLE_ELIGIBLE_GPS_PACKET.uncertainty.packet_level,
}

type LoadState =
  | { status: 'idle' }
  | { status: 'loading'; question: string }
  | { status: 'error'; message: string; question: string }
  | { status: 'success'; question: string; response: SafeSLMResponse }

const responseLabels: Record<SafeSLMResponse['response_mode'], string> = {
  crisis_aware_fallback: 'Safety support',
  generic_fallback: 'Fallback',
  insufficient_data: 'More data needed',
  normal: 'Normal response',
  refusal: 'Safe boundary',
  uncertainty: 'Uncertain evidence',
}

export function NormalResponse() {
  const [draft, setDraft] = useState(DEFAULT_QUESTION)
  const [state, setState] = useState<LoadState>({ status: 'idle' })

  async function handleAsk(rawQuestion = draft) {
    const question = rawQuestion.trim()
    if (!question || state.status === 'loading') return

    setDraft(question)
    setState({ status: 'loading', question })

    try {
      const response = await respond(EXAMPLE_ELIGIBLE_GPS_PACKET, question)
      setState({ status: 'success', question, response })
    } catch (error) {
      setState({
        status: 'error',
        message: error instanceof Error ? error.message : 'unknown error',
        question,
      })
    }
  }

  function renderConversation() {
    if (state.status === 'idle') {
      return <WelcomeState disabled={false} onAsk={handleAsk} />
    }

    if (state.status === 'loading') {
      return <LoadingState question={state.question} />
    }

    if (state.status === 'error') {
      return (
        <GenericFallbackState
          message="MindSense could not reach the local response service. Your data was not sent to an external service."
          onRetry={() => handleAsk(state.question)}
          question={state.question}
          technicalDetail={state.message}
        />
      )
    }

    const { question, response } = state
    switch (response.response_mode) {
      case 'normal':
        return (
          <NormalState evidence={EVIDENCE_SUMMARY} question={question} response={response} />
        )
      case 'insufficient_data':
        return <InsufficientDataState message={response.text} question={question} />
      case 'uncertainty':
        return <UncertaintyState message={response.text} question={question} />
      case 'refusal':
        return <RefusalState message={response.text} question={question} />
      case 'generic_fallback':
        return (
          <GenericFallbackState
            message={response.text}
            onRetry={() => handleAsk(question)}
            question={question}
          />
        )
      case 'crisis_aware_fallback':
        return <CrisisAwareFallbackState message={response.text} question={question} />
    }
  }

  const status =
    state.status === 'loading'
      ? { label: 'Reviewing evidence', tone: 'working' as const }
      : state.status === 'success'
        ? {
            label: responseLabels[state.response.response_mode],
            tone:
              state.response.response_mode === 'normal'
                ? ('normal' as const)
                : state.response.response_mode === 'crisis_aware_fallback' ||
                    state.response.response_mode === 'refusal'
                  ? ('boundary' as const)
                  : ('caution' as const),
          }
        : state.status === 'error'
          ? { label: 'Local service unavailable', tone: 'caution' as const }
          : { label: 'Ready', tone: 'ready' as const }

  return (
    <AppShell statusLabel={status.label} statusTone={status.tone}>
      <div className="conversation-scroll">{renderConversation()}</div>

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault()
          void handleAsk()
        }}
      >
        <label className="sr-only" htmlFor="chat-question">
          Ask MindSense about your behavioural data
        </label>
        <textarea
          disabled={state.status === 'loading'}
          id="chat-question"
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask about your recent patterns…"
          rows={1}
          value={draft}
        />
        <button
          className="send-button"
          disabled={state.status === 'loading' || draft.trim().length === 0}
          type="submit"
        >
          <span>{state.status === 'loading' ? 'Asking…' : 'Ask MindSense'}</span>
          <span aria-hidden="true">↑</span>
        </button>
        <p>
          <span aria-hidden="true">⌁</span> Processed locally · MindSense explains patterns,
          not diagnoses
        </p>
      </form>
    </AppShell>
  )
}
