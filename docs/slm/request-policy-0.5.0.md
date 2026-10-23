# Request policy 0.5.0: safety coverage and bounded category routing

- **Written:** 23 October 2026 on `fix/chatbot-accuracy-0.5.0`.
- **Builds on:** [request policy 0.4.0](request-policy-0.4.0.md).
- **Status:** development change. The practice-v2 validation was run early by
  request after the train gate failed; it is not acceptance evidence.

## Crisis and violence

Deterministic crisis checks now cover reported hitting, grabbing, choking,
threats and control by a partner or someone at home; not feeling safe at home;
and a friend's disclosed self-harm. They run before the local model screen or
category router. The crisis template adds 1800RESPECT (1800 737 732) for
domestic, family and sexual violence support. Its number was checked against
the [official 1800RESPECT contact page](https://1800respect.org.au/calling-1800respect).
Lifeline, Suicide Call Back Service and 000 remain in the crisis template.

## Support line on every non-answer

The generic fallback, insufficient-data message, feature clarification and
unsupported-window message now include a GP or mental-health-professional
suggestion, Lifeline 13 11 14 and 000 for immediate danger. Existing refusal
templates retain their support lines. This intentionally supersedes the old
test assumption that the generic fallback must contain no Lifeline reference.
The generic message still does not claim the person is in crisis or include
the crisis-specific 1800RESPECT resource; the crisis route remains distinct.

## Local category router

When rules return off-topic or allow a request, the Ollama runtime asks
`phi4-mini:3.8b` once for one of 16 labels.
The prompt is versioned in `backend/slm/prompts/category_router.yaml`; the
response must be strict JSON. The call is loopback-only, temperature zero and
bounded to 30 seconds. An error, timeout or invalid response retains the
rules-only decision. Demo mode has no model router.

The model may add a crisis or refusal route, but it cannot promote an
off-topic request into a data answer. For a request the rules already allow,
an in-scope GPS or unlock label still requires the independent deterministic
feature check; otherwise the user receives a clarification. A model-only
feature-unclear label cannot turn an unrelated question into an evidence
clarification. Historical-window rejections are decided before model routing.
When refusal labels conflict, crisis takes precedence, followed by injection,
sensitive data, diagnosis, treatment, risk, cause and clinical score. The
existing safety screen runs before the router and can only add a crisis route.
Only labels keyed by message hashes are cached; message text is not logged.

## Tracked measure and historical scope

Screen time, sleep, step count and other untracked measures are not aliases
for phone unlock count. Questions asking for those measures now receive the
off-topic refusal with its support line, even when they mention a phone.
This is an intentional correction to the older test that inferred unlock
count from “screen time”; the app must not present a different measure as
though it were the one requested. Ordinary phone openings and checks remain
unlock-count terms. Named historical periods outside the observed recent
fortnight get the fixed window fallback, while “these two weeks” and “this
fortnight” refer to the supported observed span.

General privacy, causal, risk, diagnosis and injection cues were extended
without changing the crisis-screen escalation rule. Questions about a stopped
local model use a fixed app-information template that explains the actual
fallback behavior, rather than the unrelated data-use text.

## Injected benchmark isolation

The public synthetic variant-quality benchmark has an injected-transport mode
for deterministic developer tests. In that mode only, it now suspends the
live safety screen and category router while the injected generator runs,
then restores both. Previously it could make live Ollama classification calls
despite labelling the run `injected_transport_not_live`, changing the fixed
mapping according to local model availability. This does not change the app's
Ollama runtime, live benchmark mode, or their safety gates. The injected mode
is not evidence of live-model safety-screen performance.

## Verification boundaries

Version-pin tests move from 0.4.0 to 0.5.0 without removing their route,
template, model-invocation or privacy assertions. The generic-fallback test
now requires the support line while excluding crisis-specific resources.
The 200-question practice-v2 validation set was run once on 24 October 2026
after the full backend suite passed, but despite the train-only gate not
being met. The remaining frontend, lint and build checks also passed. No
rules, prompts or code were changed after that run. Its
failures and the unmet gate are recorded in
`docs/evaluation/results/practice-v2-results.md`.
