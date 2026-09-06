import { useState, type ReactNode } from 'react'

import type { SafeSLMResponse } from '../../api/client'
import { BrandMark } from '../../components/BrandMark'

export interface EvidenceSummaryView {
  baseline: string
  coverage: string
  currentValue: string
  evidenceStrength: string
  featureLabel: string
  timeWindow: string
  uncertainty: readonly string[]
}

interface QuestionProps {
  question: string
}

interface ResponseProps extends QuestionProps {
  message: string
}

function QuestionBubble({ question }: QuestionProps) {
  return <p className="message message--user">{question}</p>
}

function AssistantMessage({ children }: { children: ReactNode }) {
  return (
    <div className="assistant-row">
      <BrandMark compact />
      <div className="message message--assistant">{children}</div>
    </div>
  )
}

interface WelcomeStateProps {
  disabled: boolean
  onAsk: (question: string) => void
}

const quickQuestions = [
  {
    accent: 'movement',
    description: 'Compare GPS distance with my own baseline',
    question: 'How was my movement different from my recent baseline?',
    title: 'Ask about my recent movement',
  },
  {
    accent: 'unlock',
    description: 'Explore the other locked Tier 1 feature',
    question: 'How did my phone unlock activity compare with my baseline?',
    title: 'Explore my unlock pattern',
  },
  {
    accent: 'evidence',
    description: 'See the evidence strength and limitations',
    question: 'How confident is this insight?',
    title: 'Understand the evidence',
  },
] as const

export function WelcomeState({ disabled, onAsk }: WelcomeStateProps) {
  return (
    <section className="welcome-state" aria-labelledby="welcome-title">
      <div className="welcome-copy">
        <p className="eyebrow">Your data, made understandable</p>
        <h1 id="welcome-title">Understand your patterns, at your own pace</h1>
        <p>
          Ask about changes in your tracked behaviour. MindSense compares you with your
          own history and clearly explains the limits of each answer.
        </p>
      </div>

      <div className="welcome-card">
        <BrandMark compact />
        <div>
          <strong>Start with a recent pattern</strong>
          <p>Choose a question below or write your own.</p>
        </div>
      </div>

      <div className="quick-question-grid">
        {quickQuestions.map((item) => (
          <button
            className="quick-question"
            data-accent={item.accent}
            disabled={disabled}
            key={item.title}
            onClick={() => onAsk(item.question)}
            type="button"
          >
            <span className="quick-question-icon" aria-hidden="true" />
            <span>
              <strong>{item.title}</strong>
              <small>{item.description}</small>
            </span>
            <span className="quick-question-arrow" aria-hidden="true">
              →
            </span>
          </button>
        ))}
      </div>

      <p className="non-diagnostic-note">Thoughtful insights, never a diagnosis.</p>
    </section>
  )
}

export function LoadingState({ question }: QuestionProps) {
  return (
    <section className="chat-thread" aria-live="polite" aria-busy="true">
      <QuestionBubble question={question} />
      <div className="assistant-row">
        <BrandMark compact />
        <div className="loading-card" role="status">
          <strong>Reviewing your local evidence</strong>
          <p>Checking data coverage, your personal baseline, and permitted claims.</p>
          <div className="loading-lines" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <small>The response is generated locally on this device.</small>
        </div>
      </div>
    </section>
  )
}

interface NormalStateProps extends QuestionProps {
  evidence: EvidenceSummaryView
  response: SafeSLMResponse
}

export function NormalState({ evidence, question, response }: NormalStateProps) {
  const [feedback, setFeedback] = useState<'yes' | 'partly' | 'no' | null>(null)

  return (
    <section className="chat-thread" aria-live="polite">
      <QuestionBubble question={question} />
      <AssistantMessage>
        <span className="response-mode-badge">Normal response</span>
        <p>{response.text}</p>
      </AssistantMessage>

      <article className="evidence-card response-card" data-response-mode="normal">
        <header>
          <div>
            <p className="eyebrow">Evidence behind this insight</p>
            <h2>{evidence.featureLabel}</h2>
          </div>
          <span className="fixture-badge">Synthetic demo data</span>
        </header>

        <dl className="evidence-grid">
          <div>
            <dt>Observed value</dt>
            <dd>{evidence.currentValue}</dd>
          </div>
          <div>
            <dt>Personal baseline</dt>
            <dd>{evidence.baseline}</dd>
          </div>
          <div>
            <dt>Coverage</dt>
            <dd>{evidence.coverage}</dd>
          </div>
          <div>
            <dt>Evidence strength</dt>
            <dd>
              <span className="strength-badge">{evidence.evidenceStrength}</span>
            </dd>
          </div>
        </dl>

        <div className="evidence-details">
          <p>
            <strong>Window:</strong> {evidence.timeWindow}
          </p>
          <p>
            <strong>Wellbeing relationship:</strong> Not included in this Week 5
            evidence packet, so the UI does not infer one.
          </p>
          {evidence.uncertainty.map((item) => (
            <p key={item}>
              <strong>Limit:</strong> {item}
            </p>
          ))}
        </div>

        <p className="association-note">
          Association only. This interface does not make causal, diagnostic, treatment,
          or risk-prediction claims.
        </p>
      </article>

      <section className="feedback-card" aria-label="Response feedback">
        <div>
          <strong>Was this insight clear and useful?</strong>
          <p>Your feedback can support the later human evaluation.</p>
        </div>
        {feedback ? (
          <p className="feedback-thanks" role="status">
            Feedback recorded: {feedback}.
          </p>
        ) : (
          <div className="feedback-actions">
            {(['yes', 'partly', 'no'] as const).map((value) => (
              <button key={value} onClick={() => setFeedback(value)} type="button">
                {value[0].toUpperCase() + value.slice(1)}
              </button>
            ))}
          </div>
        )}
      </section>
    </section>
  )
}

function StateCard({
  children,
  label,
  message,
  mode,
  question,
  role = 'status',
}: ResponseProps & {
  children?: ReactNode
  label: string
  mode: SafeSLMResponse['response_mode']
  role?: 'alert' | 'status'
}) {
  return (
    <section className="chat-thread" aria-live={role === 'alert' ? 'assertive' : 'polite'}>
      <QuestionBubble question={question} />
      <article className={`state-card state-card--${mode}`} data-response-mode={mode} role={role}>
        <span className="state-card-icon" aria-hidden="true" />
        <div>
          <span className="response-mode-badge">{label}</span>
          <p>{message}</p>
          {children}
        </div>
      </article>
    </section>
  )
}

export function InsufficientDataState({ message, question }: ResponseProps) {
  return (
    <StateCard
      label="Not enough data yet"
      message={message}
      mode="insufficient_data"
      question={question}
    >
      <p className="state-boundary">
        No baseline comparison or chart is shown until the required history is
        available.
      </p>
    </StateCard>
  )
}

export function UncertaintyState({ message, question }: ResponseProps) {
  return (
    <StateCard
      label="Uncertain evidence"
      message={message}
      mode="uncertainty"
      question={question}
    >
      <p className="state-boundary">
        Treat this as a limited observation, not a diagnosis, cause, or prediction.
      </p>
    </StateCard>
  )
}

export function RefusalState({ message, question }: ResponseProps) {
  return (
    <StateCard
      label="Outside MindSense’s scope"
      message={message}
      mode="refusal"
      question={question}
    />
  )
}

interface FallbackProps extends ResponseProps {
  onRetry?: () => void
  technicalDetail?: string
}

export function GenericFallbackState({
  message,
  onRetry,
  question,
  technicalDetail,
}: FallbackProps) {
  return (
    <StateCard
      label="Unable to answer safely"
      message={message}
      mode="generic_fallback"
      question={question}
      role="alert"
    >
      {technicalDetail && <p className="technical-detail">Local API: {technicalDetail}</p>}
      {onRetry && (
        <button className="secondary-button" onClick={onRetry} type="button">
          Try again
        </button>
      )}
    </StateCard>
  )
}

export function CrisisAwareFallbackState({ message, question }: ResponseProps) {
  return (
    <StateCard
      label="Immediate support information"
      message={message}
      mode="crisis_aware_fallback"
      question={question}
      role="alert"
    >
      <p className="state-boundary">
        This version-controlled message is displayed verbatim from the backend safety
        route; the frontend does not rewrite it.
      </p>
    </StateCard>
  )
}
