// Tests for NormalResponse.tsx (Week 5 Conversational Interface Lead
// task: "Integrate the UI against the real SLM stub; build the 'normal
// response' state fully" — see the component's own header comment).
//
// `respond` (frontend/src/api/client.ts) is mocked at the module
// boundary: it's a thin fetch wrapper around the real backend, and this
// is a frontend unit test, not an integration test against a running
// uvicorn server. The fixture response shapes mirror
// tests/slm/fixtures/week5_gps_eligible.json's SafeSLMResponse shape
// (response_mode/text/used_fallback/rejection_reason/model_tag/
// model_invoked) so the test exercises the same contract the real
// backend returns, not an invented one.
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { SafeSLMResponse } from '../../api/client'
import { RespondError, respond } from '../../api/client'
import { NormalResponse } from './NormalResponse'

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../api/client')>('../../api/client')
  return {
    ...actual,
    respond: vi.fn(),
  }
})

const mockedRespond = vi.mocked(respond)

const REAL_SHAPED_RESPONSE: SafeSLMResponse = {
  response_mode: 'normal',
  text: 'Your recent movement is about 0.8 SD below your personal baseline.',
  used_fallback: false,
  rejection_reason: null,
  model_tag: 'synthetic-shadow-v1',
  model_invoked: true,
}

beforeEach(() => {
  mockedRespond.mockReset()
})

describe('NormalResponse', () => {
  it('renders the idle state with an enabled button and no response card or error', () => {
    render(<NormalResponse />)

    expect(screen.getByRole('button', { name: /ask about my recent movement/i })).toBeEnabled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(document.querySelector('.response-card')).not.toBeInTheDocument()
  })

  it('shows a loading state and disables the button while the request is in flight', async () => {
    const user = userEvent.setup()
    let resolveRespond!: (value: SafeSLMResponse) => void
    mockedRespond.mockReturnValue(
      new Promise((resolve) => {
        resolveRespond = resolve
      }),
    )

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    const button = screen.getByRole('button', { name: /asking…/i })
    expect(button).toBeDisabled()

    resolveRespond(REAL_SHAPED_RESPONSE)
    await waitFor(() => expect(button).not.toBeDisabled())
  })

  it('renders the response card with real fixture-shaped data on success', async () => {
    const user = userEvent.setup()
    mockedRespond.mockResolvedValueOnce(REAL_SHAPED_RESPONSE)

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    await waitFor(() => {
      expect(screen.getByText(REAL_SHAPED_RESPONSE.text)).toBeInTheDocument()
    })

    const card = document.querySelector('.response-card')
    expect(card).toBeInTheDocument()
    expect(card).toHaveAttribute('data-response-mode', 'normal')
    expect(screen.getByText('normal')).toBeInTheDocument() // the mode badge
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('renders the error state when the backend is unreachable', async () => {
    const user = userEvent.setup()
    mockedRespond.mockRejectedValueOnce(new RespondError('request failed with status 503', 503))

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    expect(screen.getByRole('alert')).toHaveTextContent('request failed with status 503')
    expect(document.querySelector('.response-card')).not.toBeInTheDocument()
    // Button must be re-enabled after an error, not stuck disabled.
    expect(screen.getByRole('button', { name: /ask about my recent movement/i })).toBeEnabled()
  })

  it('renders a generic error message when a non-Error value is thrown', async () => {
    const user = userEvent.setup()
    mockedRespond.mockRejectedValueOnce('not an Error instance')

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('unknown error')
    })
  })

  it('calls respond with the fixed example evidence packet and the demo question', async () => {
    const user = userEvent.setup()
    mockedRespond.mockResolvedValueOnce(REAL_SHAPED_RESPONSE)

    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))

    await waitFor(() => expect(mockedRespond).toHaveBeenCalledTimes(1))
    const [evidencePacket, question] = mockedRespond.mock.calls[0]
    expect(question).toBe('How was my movement different from my recent baseline?')
    expect(evidencePacket).toMatchObject({
      feature_window: expect.objectContaining({ feature_id: 'gps_distance' }),
      baseline: expect.objectContaining({ eligibility_status: 'eligible' }),
    })
  })
})
