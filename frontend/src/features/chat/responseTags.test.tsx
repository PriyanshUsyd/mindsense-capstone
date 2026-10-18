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
    ['comparison_shown', 'normal', 'Compared with your own baseline', 'comparison'],
    ['no_clear_difference', 'uncertainty', 'Enough history · no clear difference to report', 'pattern'],
    ['few_recent_days', 'uncertainty', 'Enough history · too few recent days recorded', 'pattern'],
    ['building_baseline', 'uncertainty', 'Still building your baseline', 'pattern'],
    ['not_enough_data', 'insufficient_data', 'Not enough data yet', 'data'],
    ['general_limits', 'uncertainty', 'How to read these results', 'pattern'],
  ] as const)('answer_kind %s -> "%s"', (kind, mode, label, tone) => {
    expect(responseTag(base({ answer_kind: kind, response_mode: mode }))).toEqual({ label, tone })
  })

  it('crisis mode -> "Support is available"', () => {
    expect(
      responseTag(
        base({ response_mode: 'crisis_aware_fallback', request_category: 'crisis_self_harm' }),
      ),
    ).toEqual({ label: 'Support is available', tone: 'support' })
  })

  it.each([
    ['diagnosis_seeking', 'Can’t diagnose from phone data'],
    ['treatment_advice_seeking', 'Can’t give treatment advice'],
    ['clinical_score_request', 'No clinical scores here'],
    ['causal_inference_seeking', 'Can’t tell what caused a change'],
    ['risk_prediction_seeking', 'Can’t predict what will happen'],
    ['prompt_injection', 'Can’t change how MindSense works'],
    ['sensitive_data_request', 'Private data stays private'],
    ['off_topic', 'Outside what MindSense tracks'],
    ['capability_question', 'What MindSense can do'],
    ['app_information', 'About MindSense'],
  ] as const)('request_category %s -> "%s"', (category, label) => {
    expect(
      responseTag(base({ response_mode: 'refusal', request_category: category })),
    ).toEqual({ label, tone: 'boundary' })
  })

  it.each([
    ['unsupported_time_window', 'Only the recent two weeks are available'],
    ['ambiguous_feature_request', 'Pick one: movement or phone unlocks'],
    ['feature_request_mismatch', 'Pick one: movement or phone unlocks'],
  ])('rejection_reason %s -> "%s"', (reason, label) => {
    expect(
      responseTag(base({ response_mode: 'generic_fallback', rejection_reason: reason })),
    ).toEqual({ label, tone: 'boundary' })
  })

  it.each(['model_timeout', 'grounding_claim_mismatch', 'evidence_source_unavailable'])(
    'any other generic_fallback (%s) -> "Couldn’t answer safely right now"',
    (reason) => {
      expect(
        responseTag(base({ response_mode: 'generic_fallback', rejection_reason: reason })),
      ).toEqual({ label: 'Couldn’t answer safely right now', tone: 'boundary' })
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
      ).toBe('How to read these results')
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
      ).toBe('Support is available')
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
      ).toBe('Outside what MindSense tracks')
    })

    it('rejection_reason wins over the generic fallback tag', () => {
      expect(
        responseTag(
          base({ response_mode: 'generic_fallback', rejection_reason: 'unsupported_time_window' }),
        ).label,
      ).toBe('Only the recent two weeks are available')
    })
  })
})

describe('rendered tags', () => {
  beforeEach(() => {
    vi.mocked(getModelCatalog).mockRejectedValue(new Error('no catalog'))
    vi.mocked(respond).mockReset()
  })

  it.each([
    [base({ answer_kind: 'comparison_shown', response_mode: 'normal', model_invoked: true }), 'Compared with your own baseline', 'comparison'],
    [base({ answer_kind: 'no_clear_difference' }), 'Enough history · no clear difference to report', 'pattern'],
    [base({ answer_kind: 'not_enough_data', response_mode: 'insufficient_data' }), 'Not enough data yet', 'data'],
    [base({ response_mode: 'crisis_aware_fallback', request_category: 'crisis_self_harm', request_disposition: 'crisis' }), 'Support is available', 'support'],
    [base({ response_mode: 'refusal', request_category: 'risk_prediction_seeking', request_disposition: 'refuse' }), 'Can’t predict what will happen', 'boundary'],
    [base({ response_mode: 'generic_fallback', rejection_reason: 'feature_request_mismatch' }), 'Pick one: movement or phone unlocks', 'boundary'],
    [base({ response_mode: 'generic_fallback', rejection_reason: 'model_timeout', used_fallback: true }), 'Couldn’t answer safely right now', 'boundary'],
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
