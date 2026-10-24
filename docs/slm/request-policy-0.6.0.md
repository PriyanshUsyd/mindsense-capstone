# Request policy 0.6.0

Policy 0.6.0 adds a separate, local Ollama request classifier while retaining
deterministic authorization for every in-scope answer. The classifier chooses
among the versioned categories in
`backend/slm/prompts/request_classifier_0_6_0.yaml`; it cannot independently
authorize an answer. A response still needs a supported deterministic feature
match, an allowed evidence window, and the unchanged output grounding and
safety gates.

## Request flow

1. Deterministic crisis rules run first.
2. The unchanged safety screen runs next; a positive or unclear result keeps
   the crisis-aware response.
3. The local classifier selects a request category. Invalid output, timeout,
   or low-confidence disagreement follows the fail-closed policy.
4. Deterministic high-precision injection, sensitive-data, and time-window
   guards retain priority. The feature guard independently checks GPS or
   phone-unlock evidence before generation.
5. Safe templates handle refusals, crisis responses, and feature
   clarifications. The model does not write those responses.

The answer-writing model remains `phi4-mini:3.8b`. The classifier model is
selected separately from manifest-listed candidates.

## Clarification paths do not call answer generation

When a request has no deterministic GPS or phone-unlock feature, the service
returns the deterministic `ambiguous_feature_request` clarification before
retrieval and answer generation. The classifier can identify a possible
feature, but that guess does not authorize a generated answer. This is why the
variant-quality injected answer transport now observes 24 calls instead of
36: the 12 `plan_q4` repetitions (three repetitions across four variants) are
deterministic clarifications and make zero answer-generation transport calls.
The request classifier may still run to identify the request; the 24 count is
specifically the answer-generation transport. The evaluation retains all 288
variant records and explicitly checks all 12 no-generation outcomes.

## Version and scoring

The v4 scoring rules are preregistered in
`docs/evaluation/pass-threshold-v4.md` and are frozen. See
`docs/slm/request-policy-0.6.0-decisions.md` for measured runs, deviations,
hash verification, and remaining limitations.
