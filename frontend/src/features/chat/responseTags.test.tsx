import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { SafeSLMResponse } from '../../api/client'
import { getModelCatalog, respond } from '../../api/client'
import { NormalResponse } from './NormalResponse'
import { responseTag } from './responseTags'

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../api/client')>('../../api/client')
  return { ...actual, getModelCatalog: vi.fn(), respond: vi.fn() }
})

function base(overrides: Partial<SafeSLMResponse> = {}): SafeSLMResponse {
  return {
    answer_kind: null,
    fallback_prompt_sha256: null,
    generation_prompt_sha256: null,
    metrics: null,
    model_invoked: false,
    model_tag: null,
    rejection_reason: null,
    request_category: 'in_scope',
    request_disposition: 'allow',
    request_policy_version: '0.3.6',
    response_mode: 'uncertainty',
    text: 'Synthetic answer text',
    used_fallback: false,
    ...overrides,
  }
}

describe('responseTag mapping', () => {
  it.each([
    ['comparison_shown', 'normal', 'Compared with your usual', 'comparison'],
    ['no_clear_difference', 'uncertainty', 'No clear difference from your usual', 'pattern'],
    ['few_recent_days', 'uncertainty', 'Too few recent days recorded', 'pattern'],
    ['building_baseline', 'uncertainty', 'Still learning your usual', 'pattern'],
    ['not_enough_data', 'insufficient_data', 'Too little data so far', 'data'],
    ['general_limits', 'uncertainty', 'App limits explained', 'pattern'],
  ] as const)('answer_kind %s -> "%s"', (kind, mode, label, tone) => {
    expect(responseTag(base({ answer_kind: kind, response_mode: mode }))).toEqual({ label, tone })
  })

  it('crisis mode -> "Crisis support information"', () => {
    expect(
      responseTag(
        base({ response_mode: 'crisis_aware_fallback', request_category: 'crisis_self_harm' }),
      ),
    ).toEqual({ label: 'Crisis support information', tone: 'support' })
  })

  it.each([
    ['diagnosis_seeking', 'Not a diagnosis'],
    ['treatment_advice_seeking', 'Not medical advice'],
    ['clinical_score_request', 'No clinical scores'],
    ['causal_inference_seeking', 'Cause cannot be determined'],
    ['risk_prediction_seeking', 'Future risk cannot be predicted'],
    ['prompt_injection', 'Request not allowed'],
    ['sensitive_data_request', 'Privacy protected'],
    ['off_topic', 'Unrelated topic'],
    ['capability_question', 'What MindSense can do'],
    ['app_information', 'About MindSense'],
  ] as const)('request_category %s -> "%s"', (category, label) => {
    expect(
      responseTag(base({ response_mode: 'refusal', request_category: category })),
    ).toEqual({ label, tone: 'boundary' })
  })

  it.each([
    ['unsupported_time_window', 'Last 2 weeks only'],
    ['ambiguous_feature_request', 'Movement or phone unlocks?'],
    ['feature_request_mismatch', 'Movement or phone unlocks?'],
  ])('rejection_reason %s -> "%s"', (reason, label) => {
    expect(
      responseTag(base({ response_mode: 'generic_fallback', rejection_reason: reason })),
    ).toEqual({ label, tone: 'boundary' })
  })

  it.each(['model_timeout', 'grounding_claim_mismatch', 'evidence_source_unavailable'])(
    'any other generic_fallback (%s) -> "Couldn’t answer right now"',
    (reason) => {
      expect(
        responseTag(base({ response_mode: 'generic_fallback', rejection_reason: reason })),
      ).toEqual({ label: 'Couldn’t answer right now', tone: 'boundary' })
    },
  )

  it('falls back to a safe default for anything unmapped', () => {
    expect(responseTag(base())).toEqual({ label: 'MindSense response', tone: 'boundary' })
    expect(responseTag(base({ answer_kind: 'not_a_kind' as never }))).toEqual({
      label: 'MindSense response',
      tone: 'boundary',
    })
    expect(responseTag(base({ rejection_reason: 'constructor' }))).toEqual({
      label: 'MindSense response',
      tone: 'boundary',
    })
  })

  describe('order: answer_kind, crisis mode, request_category, rejection_reason', () => {
    it('answer_kind wins over everything else', () => {
      expect(
        responseTag(
          base({
            answer_kind: 'general_limits',
            request_category: 'off_topic',
            rejection_reason: 'unsupported_time_window',
          }),
        ).label,
      ).toBe('App limits explained')
    })

    it('crisis mode wins over request_category and rejection_reason', () => {
      expect(
        responseTag(
          base({
            response_mode: 'crisis_aware_fallback',
            request_category: 'diagnosis_seeking',
            rejection_reason: 'safety_screen_flagged',
          }),
        ).label,
      ).toBe('Crisis support information')
    })

    it('request_category wins over rejection_reason', () => {
      expect(
        responseTag(
          base({
            response_mode: 'refusal',
            request_category: 'off_topic',
            rejection_reason: 'unsupported_time_window',
          }),
        ).label,
      ).toBe('Unrelated topic')
    })

    it('rejection_reason wins over the generic fallback tag', () => {
      expect(
        responseTag(
          base({ response_mode: 'generic_fallback', rejection_reason: 'unsupported_time_window' }),
        ).label,
      ).toBe('Last 2 weeks only')
    })
  })
})

describe('rendered tags', () => {
  beforeEach(() => {
    vi.mocked(getModelCatalog).mockRejectedValue(new Error('no catalog'))
    vi.mocked(respond).mockReset()
  })

  it.each([
    [base({ answer_kind: 'comparison_shown', response_mode: 'normal', model_invoked: true }), 'Compared with your usual', 'comparison'],
    [base({ answer_kind: 'no_clear_difference' }), 'No clear difference from your usual', 'pattern'],
    [base({ answer_kind: 'not_enough_data', response_mode: 'insufficient_data' }), 'Too little data so far', 'data'],
    [base({ response_mode: 'crisis_aware_fallback', request_category: 'crisis_self_harm', request_disposition: 'crisis' }), 'Crisis support information', 'support'],
    [base({ response_mode: 'refusal', request_category: 'risk_prediction_seeking', request_disposition: 'refuse' }), 'Future risk cannot be predicted', 'boundary'],
    [base({ response_mode: 'generic_fallback', rejection_reason: 'feature_request_mismatch' }), 'Movement or phone unlocks?', 'boundary'],
    [base({ response_mode: 'generic_fallback', rejection_reason: 'model_timeout', used_fallback: true }), 'Couldn’t answer right now', 'boundary'],
  ])('shows the tag on the answer card (%#)', async (response, label, tone) => {
    const user = userEvent.setup()
    vi.mocked(respond).mockResolvedValueOnce(response)
    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))
    await screen.findByText('Synthetic answer text')

    const badge = document.querySelector('.chat-thread .response-mode-badge')
    expect(badge).toHaveTextContent(label)
    expect(badge).toHaveAttribute('data-tone', tone)
    // The Details line is unchanged.
    expect(screen.getByTestId('response-details')).toHaveTextContent(
      `Details: response_mode=${response.response_mode} · rejection_reason=${
        response.rejection_reason ?? 'none'
      } · model_tag=${response.model_tag ?? 'none'} · policy=0.3.6`,
    )
  })
})

describe('card styling follows the tag', () => {
  beforeEach(() => {
    vi.mocked(getModelCatalog).mockRejectedValue(new Error('no catalog'))
    vi.mocked(respond).mockReset()
  })

  it.each([
    [base({ answer_kind: 'comparison_shown', response_mode: 'uncertainty', model_invoked: true }), 'comparison'],
    [base({ answer_kind: 'no_clear_difference' }), 'pattern'],
    [base({ answer_kind: 'few_recent_days' }), 'pattern'],
    [base({ answer_kind: 'building_baseline' }), 'pattern'],
    [base({ answer_kind: 'general_limits' }), 'pattern'],
    [base({ answer_kind: 'not_enough_data', response_mode: 'insufficient_data' }), 'data'],
    [base({ response_mode: 'crisis_aware_fallback', request_category: 'crisis_self_harm', request_disposition: 'crisis' }), 'support'],
    [base({ response_mode: 'refusal', request_category: 'off_topic', request_disposition: 'refuse' }), 'boundary'],
    [base({ response_mode: 'generic_fallback', rejection_reason: 'model_timeout', used_fallback: true }), 'boundary'],
  ])('sets the card tone (%#)', async (response, tone) => {
    const user = userEvent.setup()
    vi.mocked(respond).mockResolvedValueOnce(response)
    render(<NormalResponse />)
    await user.click(screen.getByRole('button', { name: /ask about my recent movement/i }))
    await screen.findByText('Synthetic answer text')

    const card = document.querySelector('.chat-thread .state-card')
    expect(card).toHaveAttribute('data-tone', tone)
    expect(card).toHaveAttribute('data-response-mode', response.response_mode)
  })
})
