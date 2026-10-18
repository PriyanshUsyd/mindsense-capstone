import { useState, type ReactNode } from 'react'

import { BrandMark } from './BrandMark'

type StatusTone = 'ready' | 'working' | 'normal' | 'caution' | 'boundary'

export interface SessionChat {
  active: boolean
  id: number
  startedAt: Date
  title: string
}

interface AppShellProps {
  children: ReactNode
  compactBanner?: boolean
  modelLabel?: string
  modelSelector?: ReactNode
  onEndSession?: () => void
  onNewChat?: () => void
  onSelectChat?: (chatId: number) => void
  sessionBusy?: boolean
  sessionChats?: SessionChat[]
  statusLabel: string
  statusTone: StatusTone
}

function chatTime(startedAt: Date) {
  return startedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function AppShell({
  children,
  compactBanner = false,
  modelLabel = 'Processed locally',
  modelSelector,
  onEndSession,
  onNewChat,
  onSelectChat,
  sessionBusy = false,
  sessionChats = [],
  statusLabel,
  statusTone,
}: AppShellProps) {
  const [confirmingEnd, setConfirmingEnd] = useState(false)
  // Below 900 px the sidebar is hidden; the Chats button opens it as a
  // slide-over panel so the session list and End session stay reachable.
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <div
          aria-hidden="true"
          className="sidebar-backdrop"
          data-testid="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        aria-label="MindSense sidebar"
        className={sidebarOpen ? 'sidebar sidebar--open' : 'sidebar'}
        id="session-sidebar"
      >
        <div className="sidebar-top">
          <BrandMark />
          <button
            aria-label="Close chats"
            className="sidebar-close"
            onClick={() => setSidebarOpen(false)}
            type="button"
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>

        <p className="eyebrow sidebar-heading">Your space</p>
        <div className="nav-list" aria-label="Current MindSense section">
          <div className="nav-item nav-item--active" aria-current="page">
            <span className="nav-symbol" aria-hidden="true">
              ◌
            </span>
            <span>Chat</span>
          </div>
        </div>

        <section className="session-chats" aria-label="Chats from this session">
          <p className="eyebrow session-chats__heading">This session</p>
          {sessionChats.length === 0 ? (
            <p className="session-chats__empty">Your chats from this session will appear here.</p>
          ) : (
            <ul className="session-chats__list">
              {sessionChats.map((chat) => (
                <li key={chat.id}>
                  <button
                    aria-current={chat.active ? 'true' : undefined}
                    className={
                      chat.active
                        ? 'session-chat session-chat--active'
                        : 'session-chat'
                    }
                    disabled={sessionBusy}
                    onClick={() => {
                      setSidebarOpen(false)
                      onSelectChat?.(chat.id)
                    }}
                    title={chat.title}
                    type="button"
                  >
                    <span className="session-chat__title">{chat.title}</span>
                    <time className="session-chat__time" dateTime={chat.startedAt.toISOString()}>
                      {chatTime(chat.startedAt)}
                    </time>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {onEndSession &&
            (confirmingEnd ? (
              <div
                aria-label="Confirm end session"
                className="end-session-confirm"
                role="alertdialog"
              >
                <p>End this session? Every chat from this session will be cleared.</p>
                <div className="end-session-confirm__actions">
                  <button
                    className="end-session-confirm__yes"
                    disabled={sessionBusy}
                    onClick={() => {
                      setConfirmingEnd(false)
                      setSidebarOpen(false)
                      onEndSession()
                    }}
                    type="button"
                  >
                    Yes, end session
                  </button>
                  <button
                    className="end-session-confirm__cancel"
                    onClick={() => setConfirmingEnd(false)}
                    type="button"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button
                className="end-session-button"
                disabled={sessionBusy}
                onClick={() => setConfirmingEnd(true)}
                type="button"
              >
                End session
              </button>
            ))}
        </section>

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
          <p>
            Your data stays on this device. Processed locally. Chats are kept only while
            the app is open and cleared when you end the session, close or refresh.
          </p>
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
            <button
              aria-controls="session-sidebar"
              aria-expanded={sidebarOpen}
              className="chats-toggle"
              onClick={() => setSidebarOpen((open) => !open)}
              type="button"
            >
              <span aria-hidden="true">☰</span>
              Chats
            </button>
            {onNewChat && (
              <button className="new-conversation-button" onClick={onNewChat} type="button">
                <span aria-hidden="true">＋</span>
                New chat
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
