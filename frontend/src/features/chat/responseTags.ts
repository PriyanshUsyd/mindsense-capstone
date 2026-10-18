import type { AnswerKind, SafeSLMResponse } from '../../api/client'

// Reason-based response tags: each tag says in plain words why the answer
// below has its form. Display only; the backend chooses the answer.
//
// Order: answer_kind, then the crisis response mode, then request_category,
// then rejection_reason, then any other generic fallback, then a safe default.

export type TagTone = 'comparison' | 'pattern' | 'data' | 'support' | 'boundary'

export interface ResponseTag {
  label: string
  tone: TagTone
}

export const ANSWER_KIND_TAGS: Record<AnswerKind, ResponseTag> = {
  comparison_shown: { label: 'Compared with your own baseline', tone: 'comparison' },
  no_clear_difference: {
    label: 'Enough history · no clear difference to report',
    tone: 'pattern',
  },
  few_recent_days: { label: 'Enough history · too few recent days recorded', tone: 'pattern' },
  building_baseline: { label: 'Still building your baseline', tone: 'pattern' },
  not_enough_data: { label: 'Not enough data yet', tone: 'data' },
  general_limits: { label: 'How to read these results', tone: 'pattern' },
}

export const SUPPORT_TAG: ResponseTag = { label: 'Support is available', tone: 'support' }

export const CATEGORY_TAGS: Partial<Record<SafeSLMResponse['request_category'], ResponseTag>> = {
  diagnosis_seeking: { label: 'Can’t diagnose from phone data', tone: 'boundary' },
  treatment_advice_seeking: { label: 'Can’t give treatment advice', tone: 'boundary' },
  clinical_score_request: { label: 'No clinical scores here', tone: 'boundary' },
  causal_inference_seeking: { label: 'Can’t tell what caused a change', tone: 'boundary' },
  risk_prediction_seeking: { label: 'Can’t predict what will happen', tone: 'boundary' },
  prompt_injection: { label: 'Can’t change how MindSense works', tone: 'boundary' },
  sensitive_data_request: { label: 'Private data stays private', tone: 'boundary' },
  off_topic: { label: 'Outside what MindSense tracks', tone: 'boundary' },
  capability_question: { label: 'What MindSense can do', tone: 'boundary' },
  app_information: { label: 'About MindSense', tone: 'boundary' },
}

const PICK_ONE_FEATURE: ResponseTag = {
  label: 'Pick one: movement or phone unlocks',
  tone: 'boundary',
}

export const REJECTION_TAGS: Record<string, ResponseTag> = {
  unsupported_time_window: { label: 'Only the recent two weeks are available', tone: 'boundary' },
  ambiguous_feature_request: PICK_ONE_FEATURE,
  feature_request_mismatch: PICK_ONE_FEATURE,
}

export const FALLBACK_TAG: ResponseTag = {
  label: 'Couldn’t answer safely right now',
  tone: 'boundary',
}

export const DEFAULT_TAG: ResponseTag = { label: 'MindSense response', tone: 'boundary' }

export function responseTag(response: SafeSLMResponse): ResponseTag {
  if (response.answer_kind && Object.hasOwn(ANSWER_KIND_TAGS, response.answer_kind)) {
    return ANSWER_KIND_TAGS[response.answer_kind]
  }
  if (response.response_mode === 'crisis_aware_fallback') return SUPPORT_TAG
  if (Object.hasOwn(CATEGORY_TAGS, response.request_category)) {
    const byCategory = CATEGORY_TAGS[response.request_category]
    if (byCategory) return byCategory
  }
  if (response.rejection_reason && Object.hasOwn(REJECTION_TAGS, response.rejection_reason)) {
    return REJECTION_TAGS[response.rejection_reason]
  }
  if (response.response_mode === 'generic_fallback') return FALLBACK_TAG
  return DEFAULT_TAG
}
