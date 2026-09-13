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

    await respond({ identity: { participant_ref: 'synthetic-only' } }, 'Synthetic question')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/respond',
      expect.objectContaining({
        method: 'POST',
        redirect: 'error',
      }),
    )
  })
})
