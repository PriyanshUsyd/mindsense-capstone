import { useEffect, useRef, useState } from 'react'

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

// Synthetic fixture matching the frozen EvidencePacket contract. The browser
// sends this minimum evidence object to FastAPI; only the backend may call the
// local Ollama model.
const EXAMPLE_ELIGIBLE_GPS_PACKET = {
  identity: {
    contract_version: '1.0.0',
    packet_id: 'synthetic_week6_gps_001',
    model_spec_id: 'synthetic-shadow-v1',
    generated_at: '2026-09-07T12:00:00Z',
    participant_ref: 'synthetic-only',
  },
  feature_window: {
    feature_id: 'gps_distance',
    unit: 'kilometres_per_day',
    window_start: '2026-08-10',
    window_end: '2026-09-06',
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

interface ConversationTurn {
  id: number
  question: string
  response: SafeSLMResponse
}

interface RequestFailure {
  message: string
  question: string
}

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
  const [turns, setTurns] = useState<ConversationTurn[]>([])
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)
  const [requestFailure, setRequestFailure] = useState<RequestFailure | null>(null)
  const requestInFlight = useRef(false)
  const nextTurnId = useRef(1)
  const conversationEnd = useRef<HTMLDivElement>(null)

  useEffect(() => {
    conversationEnd.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [pendingQuestion, requestFailure, turns])

  async function handleAsk(rawQuestion = draft) {
    const question = rawQuestion.trim()
    if (!question || requestInFlight.current) return

    requestInFlight.current = true
    setDraft(question)
    setRequestFailure(null)
    setPendingQuestion(question)

    try {
      const response = await respond(EXAMPLE_ELIGIBLE_GPS_PACKET, question)
      const turn = { id: nextTurnId.current, question, response }
      nextTurnId.current += 1
      setTurns((currentTurns) => [...currentTurns, turn])
      setDraft('')
    } catch (error) {
      setRequestFailure({
        message: error instanceof Error ? error.message : 'unknown error',
        question,
      })
    } finally {
      requestInFlight.current = false
      setPendingQuestion(null)
    }
  }

  function handleNewConversation() {
    if (requestInFlight.current) return
    setTurns([])
    setRequestFailure(null)
    setPendingQuestion(null)
    setDraft(DEFAULT_QUESTION)
    nextTurnId.current = 1
  }

  function renderTurn(turn: ConversationTurn) {
    const { question, response } = turn
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

  const latestResponse = turns.at(-1)?.response
  const latestModelTag = turns.findLast((turn) => turn.response.model_tag)?.response.model_tag
  const status = pendingQuestion
    ? { label: 'Reviewing evidence', tone: 'working' as const }
    : requestFailure
      ? { label: 'Local service unavailable', tone: 'caution' as const }
      : latestResponse
        ? {
            label: responseLabels[latestResponse.response_mode],
            tone:
              latestResponse.response_mode === 'normal'
                ? ('normal' as const)
                : latestResponse.response_mode === 'crisis_aware_fallback' ||
                    latestResponse.response_mode === 'refusal'
                  ? ('boundary' as const)
                  : ('caution' as const),
          }
        : { label: 'Ready', tone: 'ready' as const }

  const showWelcome = turns.length === 0 && !pendingQuestion && !requestFailure

  return (
    <AppShell
      modelLabel={latestModelTag ? `Local model · ${latestModelTag}` : undefined}
      onNewConversation={
        turns.length > 0 && !pendingQuestion ? handleNewConversation : undefined
      }
      statusLabel={status.label}
      statusTone={status.tone}
    >
      <div className="conversation-scroll">
        {showWelcome && <WelcomeState disabled={false} onAsk={handleAsk} />}

        {turns.map((turn) => (
          <div className="conversation-turn" key={turn.id}>
            {renderTurn(turn)}
          </div>
        ))}

        {pendingQuestion && <LoadingState question={pendingQuestion} />}

        {requestFailure && (
          <GenericFallbackState
            message="MindSense could not reach the local response service. Your data was not sent to an external service."
            onRetry={() => handleAsk(requestFailure.question)}
            question={requestFailure.question}
            technicalDetail={requestFailure.message}
          />
        )}
        <div ref={conversationEnd} />
      </div>

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
          disabled={pendingQuestion !== null}
          id="chat-question"
          maxLength={2000}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault()
              event.currentTarget.form?.requestSubmit()
            }
          }}
          placeholder="Ask another question about your recent patterns…"
          rows={1}
          value={draft}
        />
        <button
          className="send-button"
          disabled={pendingQuestion !== null || draft.trim().length === 0}
          type="submit"
        >
          <span>{pendingQuestion ? 'Asking…' : 'Ask MindSense'}</span>
          <span aria-hidden="true">↑</span>
        </button>
        <p>
          <span aria-hidden="true">⌁</span> Enter to send · Shift+Enter for a new line ·
          Processed locally
        </p>
      </form>
    </AppShell>
  )
}
