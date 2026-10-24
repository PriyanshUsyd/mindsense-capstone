# Request policy 0.6.0 decision log

This log records decisions and deviations for the 0.6.0 work. No evaluation
measurement was run before the v4 scoring preregistration commit.

## Step 0 — branch and network constraint

- Started from the locally cached `origin/main` at
  `4cc0bebc63edd44bcab4c90fbaf811c68412de56` (main's request policy 0.5.1).
- The user prohibited network calls except to `127.0.0.1`, and also requested
  pushes and a GitHub PR. A push/PR requires a non-loopback network call, so
  this run will not fetch, push, or access GitHub. Changes and commits will be
  kept locally. The local main ref is the latest main known to this checkout;
  no network freshness check was made.
- Created local branch `fix/request-policy-0.6.0` from that cached ref.

## Step 1 — preregistered scoring

- Added `docs/evaluation/pass-threshold-v4.md` before any model or policy
  measurement. Strict, primary, and critical-gate scores are defined there.
- No earlier train, validation, validation_2, or held-out results will be
  rescored with v4. Their recorded result files remain untouched.
- Committed the preregistration and this decision entry as the first 0.6.0
  work commit. It cannot be pushed under the loopback-only network limit.

## Step 2 — classifier and deterministic guard

- Replaced the production off-topic category router with a versioned local
  JSON request classifier. The existing answer model remains separate from
  the classifier model; the initial classifier baseline is `phi4-mini:3.8b`.
- Chose a 0.70 initial confidence threshold. Below it, the classifier makes
  two more calls with deterministic, question-specific label-order shuffles
  and uses a majority. If three valid votes disagree, it chooses the safest
  observed refusal by the requested priority; an in-scope vote cannot win that
  disagreement. Invalid JSON or a timeout returns no classification.
- Crisis rules run before the unchanged safety screen. The classifier runs
  after the screen and before the full deterministic guard. Injection,
  sensitive-data, and explicit unsupported-window rules retain precedence.
- A model in-scope label proceeds only if the deterministic policy already
  allows the request and the independently inferred feature matches the
  label. A classifier failure preserves a matching deterministic refusal or
  fails closed to off-topic; it cannot enable generation.
- Added new classifier examples from scratch. They were not copied from
  practice or spent sets. Output grounding and `validate_draft` were not
  changed. Existing 0.5.1 test assertions were version-updated, not removed.
- The production runtime now uses the new classifier. The old category-router
  implementation remains as a compatibility test seam; the runtime does not
  call it.
