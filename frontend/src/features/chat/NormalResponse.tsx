import { useEffect, useRef, useState } from 'react'

import { respond, type SafeSLMResponse } from '../../api/client'
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

// FIXED 2026-09-16: this component used to build a hardcoded
// EXAMPLE_ELIGIBLE_GPS_PACKET (eligibility_status/evidence_strength pinned
// client-side) and send THAT on every request — meaning classify_state and
// backend/statistics/evidence.py were never actually exercised by a real
// request. `/respond` now builds the real EvidencePacket server-side from
// `participant_id` (see backend/statistics/participant_evidence.py); the
// browser only sends which participant is asking, never their evidence.
//
// There is no auth/session system yet (see AppShell), so there is no real
// signed-in participant to read this id from — DEMO_PARTICIPANT_ID is a
// real CES uid used as a placeholder until one exists, exactly the same
// dev-only role the old synthetic packet played, just narrowed to an
// identifier instead of fabricated evidence.
const DEMO_PARTICIPANT_ID = '1ff6d7f34acb354430e7323a35ff7703'
const DEFAULT_FEATURE_ID = 'gps_distance'

const DEFAULT_QUESTION = 'How was my movement different from my recent baseline?'

// The evidence numbers shown alongside a NORMAL response are still a
// placeholder: `SafeSLMResponse` (backend/slm/service.py) does not return
// the EvidencePacket it was generated from, only the drafted text — so the
// browser has no real per-request values to render here yet. Left generic
// rather than reusing the old fixture's fabricated numbers, which would
// misrepresent real per-participant data as if it were shown. Wiring real
// numbers into this panel needs `SafeSLMResponse` extended to carry a
// packet summary — out of this fix's scope (participant_evidence.py /
// app.py's request contract), flagged for whoever owns
// backend/slm/service.py next.
const EVIDENCE_SUMMARY: EvidenceSummaryView = {
  baseline: 'see response text',
  coverage: 'see response text',
  currentValue: 'see response text',
  evidenceStrength: 'see response text',
  featureLabel: 'GPS distance',
  timeWindow: 'see response text',
  uncertainty: ['Evidence figures are computed from this participant’s real data on the backend; this panel does not yet echo them back.'],
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
      const response = await respond(DEMO_PARTICIPANT_ID, question, DEFAULT_FEATURE_ID)
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
