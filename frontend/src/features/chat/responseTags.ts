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
  comparison_shown: { label: 'Compared with your usual', tone: 'comparison' },
  no_clear_difference: {
    label: 'No clear difference from your usual',
    tone: 'pattern',
  },
  few_recent_days: { label: 'Too few recent days recorded', tone: 'pattern' },
  building_baseline: { label: 'Still learning your usual', tone: 'pattern' },
  not_enough_data: { label: 'Too little data so far', tone: 'data' },
  general_limits: { label: 'App limits explained', tone: 'pattern' },
}

export const SUPPORT_TAG: ResponseTag = { label: 'Crisis support information', tone: 'support' }

export const CATEGORY_TAGS: Partial<Record<SafeSLMResponse['request_category'], ResponseTag>> = {
  diagnosis_seeking: { label: 'Not a diagnosis', tone: 'boundary' },
  treatment_advice_seeking: { label: 'Not medical advice', tone: 'boundary' },
  clinical_score_request: { label: 'No clinical scores', tone: 'boundary' },
  causal_inference_seeking: { label: 'Cause cannot be determined', tone: 'boundary' },
  risk_prediction_seeking: { label: 'Future risk cannot be predicted', tone: 'boundary' },
  prompt_injection: { label: 'Request not allowed', tone: 'boundary' },
  sensitive_data_request: { label: 'Privacy protected', tone: 'boundary' },
  off_topic: { label: 'Unrelated topic', tone: 'boundary' },
  capability_question: { label: 'What MindSense can do', tone: 'boundary' },
  app_information: { label: 'About MindSense', tone: 'boundary' },
}

const PICK_ONE_FEATURE: ResponseTag = {
  label: 'Movement or phone unlocks?',
  tone: 'boundary',
}

export const REJECTION_TAGS: Record<string, ResponseTag> = {
  unsupported_time_window: { label: 'Last 2 weeks only', tone: 'boundary' },
  ambiguous_feature_request: PICK_ONE_FEATURE,
  feature_request_mismatch: PICK_ONE_FEATURE,
}

export const FALLBACK_TAG: ResponseTag = {
  label: 'Couldn’t answer right now',
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
