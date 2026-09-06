import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ResponseMode, SafeSLMResponse } from '../../api/client'
import { RespondError, respond } from '../../api/client'
import { NormalResponse } from './NormalResponse'

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../api/client')>('../../api/client')
  return { ...actual, respond: vi.fn() }
})

const mockedRespond = vi.mocked(respond)

function responseFor(responseMode: ResponseMode, text = `Backend ${responseMode} response`) {
  return {
    model_invoked: responseMode === 'normal' || responseMode === 'uncertainty',
    model_tag: responseMode === 'normal' ? 'synthetic-shadow-v1' : null,
    rejection_reason: responseMode === 'refusal' ? 'prohibited_claim' : null,
    response_mode: responseMode,
    text,
    used_fallback: responseMode.includes('fallback'),
  } satisfies SafeSLMResponse
}

const NORMAL_RESPONSE = responseFor(
  'normal',
  'Your recent movement is about 0.8 below your personal baseline.',
)

beforeEach(() => {
  mockedRespond.mockReset()
})

describe('NormalResponse', () => {
  it('starts with the wellbeing welcome state and an enabled quick question', () => {
    render(<NormalResponse />)

    expect(
      screen.getByRole('heading', { name: /understand your patterns, at your own pace/i }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ask about my recent movement/i })).toBeEnabled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows the seventh UI state, loading, while the request is in flight', async () => {
    const user = userEvent.setup()
    let resolveRespond!: (value: SafeSLMResponse) => void
    mockedRespond.mockReturnValue(
      new Promise((resolve) => {
        resolveRespond = resolve
      }),
    )

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    expect(screen.getByRole('status')).toHaveTextContent('Reviewing your local evidence')
    expect(screen.getByRole('button', { name: /asking…/i })).toBeDisabled()

    resolveRespond(NORMAL_RESPONSE)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /ask mindsense/i })).toBeEnabled()
    })
  })

  it('renders the fully wired normal state with evidence provenance', async () => {
    const user = userEvent.setup()
    mockedRespond.mockResolvedValueOnce(NORMAL_RESPONSE)

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    expect(await screen.findByText(NORMAL_RESPONSE.text)).toBeInTheDocument()
    expect(document.querySelector('[data-response-mode="normal"]')).toBeInTheDocument()
    expect(screen.getAllByText('Normal response')).toHaveLength(2)
    expect(screen.getByText('Synthetic demo data')).toBeInTheDocument()
    expect(screen.getByText('25 of 28 days (89%)')).toBeInTheDocument()
    expect(screen.getByText(/does not infer one/i)).toBeInTheDocument()
  })

  it('renders a recoverable local-only fallback when the API is unreachable', async () => {
    const user = userEvent.setup()
    mockedRespond.mockRejectedValueOnce(new RespondError('request failed with status 503', 503))

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('request failed with status 503')
    expect(alert).toHaveAttribute('data-response-mode', 'generic_fallback')
    expect(screen.getByRole('button', { name: /try again/i })).toBeEnabled()
    expect(screen.getByRole('button', { name: /ask mindsense/i })).toBeEnabled()
  })

  it('handles a non-Error rejection without exposing an empty state', async () => {
    const user = userEvent.setup()
    mockedRespond.mockRejectedValueOnce('not an Error instance')

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('unknown error')
  })

  it('calls Richard’s response route wrapper with the EvidencePacket and exact question', async () => {
    const user = userEvent.setup()
    mockedRespond.mockResolvedValueOnce(NORMAL_RESPONSE)

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    await waitFor(() => expect(mockedRespond).toHaveBeenCalledTimes(1))
    const [evidencePacket, question] = mockedRespond.mock.calls[0]
    expect(question).toBe('How was my movement different from my recent baseline?')
    expect(evidencePacket).toMatchObject({
      baseline: expect.objectContaining({ eligibility_status: 'eligible' }),
      feature_window: expect.objectContaining({ feature_id: 'gps_distance' }),
    })
  })

  it.each([
    'insufficient_data',
    'uncertainty',
    'refusal',
    'generic_fallback',
    'crisis_aware_fallback',
  ] as const)('maps backend response mode %s to its distinct UI state', async (mode) => {
    const user = userEvent.setup()
    const exactBackendText = `Exact backend text for ${mode}`
    mockedRespond.mockResolvedValueOnce(responseFor(mode, exactBackendText))

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    expect(await screen.findByText(exactBackendText)).toBeInTheDocument()
    expect(document.querySelector(`[data-response-mode="${mode}"]`)).toBeInTheDocument()
  })
})
