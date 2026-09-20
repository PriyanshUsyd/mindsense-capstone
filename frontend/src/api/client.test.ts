import { afterEach, describe, expect, it, vi } from 'vitest'

import { respond } from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('respond transport privacy', () => {
  it('uses only the loopback API and refuses redirects', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      json: async () => ({
        model_invoked: false,
        model_tag: null,
        rejection_reason: null,
        response_mode: 'generic_fallback',
        text: 'Synthetic response',
        used_fallback: true,
      }),
      ok: true,
    })
    vi.stubGlobal('fetch', fetchMock)

    await respond('synthetic-participant', 'Synthetic question')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/respond',
      expect.objectContaining({
        method: 'POST',
        redirect: 'error',
        body: JSON.stringify({
          participant_id: 'synthetic-participant',
          question: 'Synthetic question',
        }),
      }),
    )
  })

  it('includes feature_id only when explicitly overridden', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      json: async () => ({
        model_invoked: false,
        model_tag: null,
        rejection_reason: null,
        response_mode: 'generic_fallback',
        text: 'Synthetic response',
        used_fallback: true,
      }),
      ok: true,
    })
    vi.stubGlobal('fetch', fetchMock)

    await respond('synthetic-participant', 'Synthetic question', 'unlock_count')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/respond',
      expect.objectContaining({
        body: JSON.stringify({
          participant_id: 'synthetic-participant',
          question: 'Synthetic question',
          feature_id: 'unlock_count',
        }),
      }),
    )
  })
})
