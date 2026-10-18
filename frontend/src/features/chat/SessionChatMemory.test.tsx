import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SafeSLMResponse } from '../../api/client'
import { NormalResponse } from './NormalResponse'

// Session chat memory with the real API client: fetch is stubbed so the exact
// /respond request bodies can be inspected.

const QUESTIONS = {
  movement: 'How far did I travel recently?',
  unlocks: 'Show my phone unlock count.',
  diagnosis: 'Do I have ADHD?',
}

function reply(question: string): SafeSLMResponse {
  const refusal = question === QUESTIONS.diagnosis
  return {
    fallback_prompt_sha256: refusal ? 'f'.repeat(64) : null,
    generation_prompt_sha256: refusal ? null : 'a'.repeat(64),
    metrics: null,
    model_invoked: !refusal,
    model_tag: refusal ? null : 'phi4-mini:3.8b',
    rejection_reason: refusal ? 'diagnosis_request_detected' : null,
    request_category: refusal ? 'diagnosis_seeking' : 'in_scope',
    request_disposition: refusal ? 'refuse' : 'allow',
    request_policy_version: '0.3.6',
    response_mode: refusal ? 'refusal' : 'uncertainty',
    text: `Synthetic answer to: ${question}`,
    used_fallback: refusal,
  }
}

let requestBodies: Record<string, unknown>[]

beforeEach(() => {
  requestBodies = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/models')) {
        return {
          ok: true,
          json: async () => ({
            runtime: 'demo',
            selection_enabled: false,
            default_model_tag: 'phi4-mini:3.8b',
            available_model_tags: ['phi4-mini:3.8b'],
          }),
        }
      }
      const body = JSON.parse(String(init?.body)) as Record<string, unknown>
      requestBodies.push(body)
      return { ok: true, json: async () => reply(String(body.question)) }
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function textbox() {
  return screen.getByRole('textbox', { name: /ask mindsense about your behavioural data/i })
}

async function ask(user: ReturnType<typeof userEvent.setup>, question: string) {
  await user.clear(textbox())
  await user.type(textbox(), question)
  await user.click(screen.getByRole('button', { name: /ask mindsense/i }))
  await screen.findByText(`Synthetic answer to: ${question}`)
}

function sessionList() {
  return screen.getByRole('region', { name: /chats from this session/i })
}

function sessionButtons() {
  return within(sessionList()).queryAllByRole('button', { name: /\d{1,2}:\d{2}/ })
}

async function threeChats(user: ReturnType<typeof userEvent.setup>) {
  await ask(user, QUESTIONS.movement)
  await ask(user, QUESTIONS.diagnosis)
  await user.click(screen.getByRole('button', { name: /new chat/i }))
  await ask(user, QUESTIONS.unlocks)
  await user.click(screen.getByRole('button', { name: /new chat/i }))
  await ask(user, 'What uncertainty should I keep in mind?')
}

describe('session chat memory', () => {
  it('lists every chat newest first, titled by its first question, with a time', async () => {
    const user = userEvent.setup()
    render(<NormalResponse />)
    expect(within(sessionList()).getByText(/will appear here/i)).toBeInTheDocument()

    await threeChats(user)

    const titles = sessionButtons().map(
      (button) => button.querySelector('.session-chat__title')?.textContent,
    )
    expect(titles).toEqual([
      'What uncertainty should I keep in mind?',
      QUESTIONS.unlocks,
      QUESTIONS.movement,
    ])
    for (const button of sessionButtons()) {
      expect(button.querySelector('time')).toHaveAttribute('datetime')
    }
    expect(sessionButtons()[0]).toHaveAttribute('aria-current', 'true')
  })

  it('reopens an earlier chat with all its turns, badges and Details lines', async () => {
    const user = userEvent.setup()
    render(<NormalResponse />)
    await threeChats(user)

    await user.click(within(sessionList()).getByRole('button', { name: /how far did i travel/i }))

    expect(screen.getByText(`Synthetic answer to: ${QUESTIONS.movement}`)).toBeInTheDocument()
    expect(screen.getByText(`Synthetic answer to: ${QUESTIONS.diagnosis}`)).toBeInTheDocument()
    expect(screen.getByText('Not a diagnosis')).toBeInTheDocument()
    const details = screen.getAllByTestId('response-details')
    expect(details).toHaveLength(2)
    expect(details[1]).toHaveTextContent('rejection_reason=diagnosis_request_detected')
    expect(screen.queryByText(`Synthetic answer to: ${QUESTIONS.unlocks}`)).not.toBeInTheDocument()

    await user.click(within(sessionList()).getByRole('button', { name: /show my phone unlock/i }))
    expect(screen.getByText(`Synthetic answer to: ${QUESTIONS.unlocks}`)).toBeInTheDocument()
    expect(screen.queryByText(`Synthetic answer to: ${QUESTIONS.movement}`)).not.toBeInTheDocument()

    // A follow-up question is added to the reopened chat only.
    await ask(user, 'How confident is this?')
    await user.click(within(sessionList()).getByRole('button', { name: /how far did i travel/i }))
    expect(screen.queryByText('Synthetic answer to: How confident is this?')).not.toBeInTheDocument()
    expect(sessionButtons()).toHaveLength(3)
  })

  it('asks before ending the session, then clears every chat', async () => {
    const user = userEvent.setup()
    render(<NormalResponse />)
    await threeChats(user)

    await user.click(screen.getByRole('button', { name: /^end session$/i }))
    const confirm = screen.getByRole('alertdialog', { name: /confirm end session/i })
    await user.click(within(confirm).getByRole('button', { name: /cancel/i }))
    expect(sessionButtons()).toHaveLength(3)

    await user.click(screen.getByRole('button', { name: /^end session$/i }))
    await user.click(screen.getByRole('button', { name: /yes, end session/i }))

    expect(sessionButtons()).toHaveLength(0)
    expect(within(sessionList()).getByText(/will appear here/i)).toBeInTheDocument()
    expect(screen.queryByText(/synthetic answer to/i)).not.toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /understand your patterns, at your own pace/i }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^end session$/i })).not.toBeInTheDocument()
  })

  it('opens the session sidebar as a slide-over from the Chats button', async () => {
    // The button and panel styling only apply below 900 px (CSS); jsdom has no
    // media queries, so this checks the panel's behaviour.
    const user = userEvent.setup()
    render(<NormalResponse />)
    await threeChats(user)

    const toggle = screen.getByRole('button', { name: /^chats$/i })
    const sidebar = document.getElementById('session-sidebar')
    expect(toggle).toHaveAttribute('aria-controls', 'session-sidebar')
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(sidebar).not.toHaveClass('sidebar--open')

    await user.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(sidebar).toHaveClass('sidebar--open')
    await user.click(screen.getByRole('button', { name: /close chats/i }))
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(sidebar).not.toHaveClass('sidebar--open')

    // The backdrop closes it too.
    await user.click(toggle)
    await user.click(screen.getByTestId('sidebar-backdrop'))
    expect(sidebar).not.toHaveClass('sidebar--open')

    // Picking a chat reopens it and closes the panel.
    await user.click(toggle)
    await user.click(within(sessionList()).getByRole('button', { name: /how far did i travel/i }))
    expect(sidebar).not.toHaveClass('sidebar--open')
    expect(screen.getByText(`Synthetic answer to: ${QUESTIONS.movement}`)).toBeInTheDocument()

    // End session is reachable from the panel and closes it.
    await user.click(toggle)
    await user.click(screen.getByRole('button', { name: /^end session$/i }))
    await user.click(screen.getByRole('button', { name: /yes, end session/i }))
    expect(sidebar).not.toHaveClass('sidebar--open')
    expect(sessionButtons()).toHaveLength(0)
  })

  it('keeps nothing after the page is reloaded (remount)', async () => {
    const user = userEvent.setup()
    const view = render(<NormalResponse />)
    await threeChats(user)
    view.unmount()

    render(<NormalResponse />)
    expect(sessionButtons()).toHaveLength(0)
    expect(screen.queryByText(/synthetic answer to/i)).not.toBeInTheDocument()
  })

  it('never calls a browser storage API', async () => {
    const storageCalls = [
      vi.spyOn(Storage.prototype, 'setItem'),
      vi.spyOn(Storage.prototype, 'getItem'),
      vi.spyOn(Storage.prototype, 'removeItem'),
      vi.spyOn(Storage.prototype, 'clear'),
      vi.spyOn(Storage.prototype, 'key'),
    ]
    const indexedDbOpen = vi.fn()
    vi.stubGlobal('indexedDB', { open: indexedDbOpen, deleteDatabase: indexedDbOpen })
    const cachesOpen = vi.fn()
    vi.stubGlobal('caches', { open: cachesOpen, match: cachesOpen, delete: cachesOpen })
    const cookieSet = vi.spyOn(document, 'cookie', 'set')
    const cookieGet = vi.spyOn(document, 'cookie', 'get')
    const serviceWorkerRegister = vi.fn()
    Object.defineProperty(navigator, 'serviceWorker', {
      configurable: true,
      value: { register: serviceWorkerRegister },
    })

    try {
      const user = userEvent.setup()
      const view = render(<NormalResponse />)
      await threeChats(user)
      await user.click(within(sessionList()).getByRole('button', { name: /how far did i travel/i }))
      await user.click(screen.getByRole('button', { name: /^end session$/i }))
      await user.click(screen.getByRole('button', { name: /yes, end session/i }))
      view.unmount()

      for (const spy of storageCalls) expect(spy).not.toHaveBeenCalled()
      expect(indexedDbOpen).not.toHaveBeenCalled()
      expect(cachesOpen).not.toHaveBeenCalled()
      expect(cookieSet).not.toHaveBeenCalled()
      expect(cookieGet).not.toHaveBeenCalled()
      expect(serviceWorkerRegister).not.toHaveBeenCalled()
    } finally {
      Reflect.deleteProperty(navigator, 'serviceWorker')
    }
  })

  it('sends only the current question to /respond, with no history', async () => {
    const user = userEvent.setup()
    render(<NormalResponse />)
    await threeChats(user)
    await user.click(within(sessionList()).getByRole('button', { name: /how far did i travel/i }))
    await ask(user, 'Anything else I should know?')

    await waitFor(() => expect(requestBodies).toHaveLength(5))
    expect(requestBodies.map((body) => body.question)).toEqual([
      QUESTIONS.movement,
      QUESTIONS.diagnosis,
      QUESTIONS.unlocks,
      'What uncertainty should I keep in mind?',
      'Anything else I should know?',
    ])
    for (const body of requestBodies) {
      expect(Object.keys(body).sort()).toEqual(['participant_id', 'question'])
      expect(JSON.stringify(body)).not.toContain('Synthetic answer')
    }
  })
})
