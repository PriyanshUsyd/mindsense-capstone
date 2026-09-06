import type { ReactNode } from 'react'

import { BrandMark } from './BrandMark'

type StatusTone = 'ready' | 'working' | 'normal' | 'caution' | 'boundary'

interface AppShellProps {
  children: ReactNode
  statusLabel: string
  statusTone: StatusTone
}

const navigation = [
  { symbol: '●', label: 'Today' },
  { symbol: '✦', label: 'Chat', active: true },
  { symbol: '↗', label: 'My patterns' },
  { symbol: '✓', label: 'Privacy' },
]

export function AppShell({ children, statusLabel, statusTone }: AppShellProps) {
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
          <strong>Activity this week</strong>
          <span>Current conversation</span>
        </div>
        <div className="recent-chat">
          <strong>Unlock pattern</strong>
          <span>Previous conversation</span>
        </div>

        <section className="privacy-card" aria-label="Privacy summary">
          <span className="privacy-check" aria-hidden="true">
            ✓
          </span>
          <strong>Private by design</strong>
          <p>Local SLM. Personal data stays on this device.</p>
        </section>
      </aside>

      <main className="chat-panel">
        <header className="chat-header">
          <BrandMark compact />
          <div className="chat-heading">
            <strong>MindSense assistant</strong>
            <span>Understand your own behavioural patterns</span>
          </div>
          <div className="header-badges">
            <span className="local-badge">Local SLM · on device</span>
            <span className="state-badge" data-tone={statusTone}>
              {statusLabel}
            </span>
          </div>
        </header>

        {children}
      </main>
    </div>
  )
}
