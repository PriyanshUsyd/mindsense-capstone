import { useEffect, useRef, useState } from 'react'

import { RespondError, respond, type SafeSLMResponse } from '../../api/client'
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
} from './ChatStates'

// FIXED 2026-09-16: this component used to build a hardcoded
// EXAMPLE_ELIGIBLE_GPS_PACKET (eligibility_status/evidence_strength pinned
// client-side) and send THAT on every request — meaning classify_state and
// backend/statistics/evidence.py were never actually exercised by a real
// request. `/respond` now builds the real EvidencePacket server-side from
// `participant_id` (see backend/statistics/participant_evidence.py); the
// browser only sends which participant is asking, never their evidence.
//
// There is no auth/session system yet (see AppShell), so the browser sends a
// non-sensitive local alias. The backend resolves it to a suitable participant
// inside the local process; a raw CES identifier never enters tracked browser
// source, the production bundle, the HTTP request, or access logs.
const LOCAL_DEMO_PARTICIPANT_ALIAS = 'local-demo'

// FIXED 2026-09-20: this used to also hardcode `DEFAULT_FEATURE_ID =
// 'gps_distance'` and pass it on every request, so every question got
// answered from GPS evidence regardless of what was actually asked. The
// backend now infers the feature from the question text
// (backend/slm/request_policy.py's `infer_feature_from_question`), so the
// frontend no longer sends a feature_id at all.
const DEFAULT_QUESTION = 'How was my movement different from my recent baseline?'

interface ConversationTurn {
  id: number
  question: string
  response: SafeSLMResponse
}

interface RequestFailure {
  kind: 'network' | 'server' | 'unknown'
  message: string
  question: string
  status?: number
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
      const response = await respond(LOCAL_DEMO_PARTICIPANT_ALIAS, question)
      const turn = { id: nextTurnId.current, question, response }
      nextTurnId.current += 1
      setTurns((currentTurns) => [...currentTurns, turn])
      setDraft('')
    } catch (error) {
      if (error instanceof RespondError) {
        setRequestFailure({
          kind: 'server',
          message: error.message,
          question,
          status: error.status,
        })
      } else if (error instanceof TypeError) {
        setRequestFailure({ kind: 'network', message: error.message, question })
      } else {
        setRequestFailure({
          kind: 'unknown',
          message: error instanceof Error ? error.message : 'unknown error',
          question,
        })
      }
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
        return <NormalState question={question} response={response} />
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
      ? {
          label:
            requestFailure.kind === 'network'
              ? 'Local service unavailable'
              : 'Local processing failed',
          tone: 'caution' as const,
        }
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
            message={
              requestFailure.kind === 'network'
                ? 'MindSense could not reach the local response service. Check that the local API is running, then try again. Your data was not sent to an external service.'
                : 'The local response service received your request but could not complete it safely. You can try again after the local data or model service is ready. Your data was not sent to an external service.'
            }
            onRetry={() => handleAsk(requestFailure.question)}
            question={requestFailure.question}
            technicalDetail={
              requestFailure.status
                ? `HTTP ${requestFailure.status}: ${requestFailure.message}`
                : requestFailure.message
            }
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
        <span className="composer-mark" aria-hidden="true">⌁</span>
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
          Enter to send · Shift+Enter for a new line ·
          Processed locally
        </p>
      </form>
    </AppShell>
  )
}
