import type { ReactNode } from 'react'

import { BrandMark } from './BrandMark'

type StatusTone = 'ready' | 'working' | 'normal' | 'caution' | 'boundary'

interface AppShellProps {
  children: ReactNode
  modelLabel?: string
  onNewConversation?: () => void
  statusLabel: string
  statusTone: StatusTone
}

const navigation = [
  { symbol: '⌂', label: 'Today' },
  { symbol: '◌', label: 'Chat', active: true },
  { symbol: '▥', label: 'My patterns' },
  { symbol: '◇', label: 'Privacy' },
]

export function AppShell({
  children,
  modelLabel = 'Processed locally',
  onNewConversation,
  statusLabel,
  statusTone,
}: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <BrandMark />

        <p className="eyebrow sidebar-heading">Your space</p>
        <nav className="nav-list" aria-label="MindSense sections">
          {navigation.map((item) => (
            <div
              className={`nav-item${item.active ? ' nav-item--active' : ''}`}
              aria-current={item.active ? 'page' : undefined}
              key={item.label}
            >
              <span className="nav-symbol" aria-hidden="true">
                {item.symbol}
              </span>
              <span>{item.label}</span>
            </div>
          ))}
        </nav>

        <div className="sidebar-divider" />
        <p className="eyebrow">Recent chats</p>
        <div className="recent-chat recent-chat--active">
          <span className="recent-chat-icon" aria-hidden="true">◯</span>
          <span>
            <strong>Activity this week</strong>
            <small>Current conversation</small>
          </span>
        </div>
        <div className="recent-chat">
          <span className="recent-chat-icon" aria-hidden="true">◯</span>
          <span>
            <strong>Unlock pattern</strong>
            <small>Previous conversation</small>
          </span>
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
            <span className="local-badge">{modelLabel}</span>
            <span className="state-badge" data-tone={statusTone}>
              {statusLabel}
            </span>
          </div>
        </header>

        <section className="wellbeing-banner" aria-label="MindSense wellbeing reminder">
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
