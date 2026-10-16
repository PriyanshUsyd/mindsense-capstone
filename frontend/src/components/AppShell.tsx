import type { ReactNode } from 'react'

import { BrandMark } from './BrandMark'

type StatusTone = 'ready' | 'working' | 'normal' | 'caution' | 'boundary'

interface AppShellProps {
  children: ReactNode
  compactBanner?: boolean
  modelLabel?: string
  modelSelector?: ReactNode
  onNewConversation?: () => void
  statusLabel: string
  statusTone: StatusTone
}

export function AppShell({
  children,
  compactBanner = false,
  modelLabel = 'Processed locally',
  modelSelector,
  onNewConversation,
  statusLabel,
  statusTone,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="MindSense sidebar">
        <BrandMark />

        <p className="eyebrow sidebar-heading">Your space</p>
        <div className="nav-list" aria-label="Current MindSense section">
          <div className="nav-item nav-item--active" aria-current="page">
            <span className="nav-symbol" aria-hidden="true">
              ◌
            </span>
            <span>Chat</span>
          </div>
        </div>

        <div className="sidebar-spirit" aria-hidden="true">
          <span className="sidebar-spirit__glow" />
          <BrandMark compact />
          <span className="sidebar-spirit__leaf sidebar-spirit__leaf--one" />
          <span className="sidebar-spirit__leaf sidebar-spirit__leaf--two" />
        </div>

        <section className="privacy-card" aria-label="Privacy summary">
          <span className="privacy-check" aria-hidden="true">
            ✓
          </span>
          <strong>Private by design</strong>
          <p>Your data stays on this device. Processed locally, always.</p>
        </section>

        <p className="sidebar-signoff"><span aria-hidden="true">◆</span> A calmer, kinder you.</p>
      </aside>

      <main className="chat-panel">
        <header className="chat-header">
          <div className="header-identity">
            <BrandMark compact />
            <div className="chat-heading">
              <strong>MindSense assistant</strong>
              <span>A little space to understand yourself</span>
            </div>
          </div>
          <div className="header-badges">
            {onNewConversation && (
              <button className="new-conversation-button" onClick={onNewConversation} type="button">
                <span aria-hidden="true">＋</span>
                New conversation
              </button>
            )}
            {modelSelector}
            <span className="local-badge">{modelLabel}</span>
            <span className="state-badge" data-tone={statusTone}>
              {statusLabel}
            </span>
          </div>
        </header>

        <section
          aria-label="MindSense wellbeing reminder"
          className={compactBanner ? 'wellbeing-banner wellbeing-banner--compact' : 'wellbeing-banner'}
        >
          <span className="floating-leaf floating-leaf--one" aria-hidden="true" />
          <span className="floating-leaf floating-leaf--two" aria-hidden="true" />
          <span className="floating-leaf floating-leaf--three" aria-hidden="true" />
          <p className="wellbeing-banner__lead">
            <span>Same data.</span>
            <strong>A kinder you.</strong>
          </p>
          <p className="wellbeing-banner__note">
            <span>Small insights</span>
            <strong>brighter days</strong>
          </p>
        </section>

        {children}
      </main>
    </div>
  )
}
