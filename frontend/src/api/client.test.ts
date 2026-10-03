import { afterEach, describe, expect, it, vi } from 'vitest'

import { respond, type SafeSLMResponse } from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('respond transport privacy', () => {
  it('accepts the backend off_topic request category in the provisional contract', () => {
    const response: SafeSLMResponse = {
      fallback_prompt_sha256: 'f'.repeat(64),
      generation_prompt_sha256: null,
      metrics: null,
      model_invoked: false,
      model_tag: null,
      rejection_reason: 'off_topic',
      request_category: 'off_topic',
      request_disposition: 'refuse',
      request_policy_version: '0.2.0',
      response_mode: 'refusal',
      text: 'Outside scope',
      used_fallback: true,
    }

    expect(response.request_category).toBe('off_topic')
  })

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
