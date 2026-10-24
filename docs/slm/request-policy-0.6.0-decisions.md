# Request policy 0.6.0 decision log

This log records decisions and deviations for the 0.6.0 work. No evaluation
measurement was run before the v4 scoring preregistration commit.

## Step 0 ‚Äî branch and network constraint

- Started from the locally cached `origin/main` at
  `4cc0bebc63edd44bcab4c90fbaf811c68412de56` (main's request policy 0.5.1).
- The user prohibited network calls except to `127.0.0.1`, and also requested
  pushes and a GitHub PR. A push/PR requires a non-loopback network call, so
  this run will not fetch, push, or access GitHub. Changes and commits will be
  kept locally. The local main ref is the latest main known to this checkout;
  no network freshness check was made.
- Created local branch `fix/request-policy-0.6.0` from that cached ref.

## Step 1 ‚Äî preregistered scoring

- Added `docs/evaluation/pass-threshold-v4.md` before any model or policy
  measurement. Strict, primary, and critical-gate scores are defined there.
- No earlier train, validation, validation_2, or held-out results will be
  rescored with v4. Their recorded result files remain untouched.
- Committed the preregistration and this decision entry as the first 0.6.0
  work commit. It cannot be pushed under the loopback-only network limit.

## Step 2 ‚Äî classifier and deterministic guard

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
- A broad repository text search unintentionally scanned locked
  `validation_2.json` while locating prior scoring metadata. Its output exposed
  truncated source snippets. No validation set was executed, hashed, used for
  tuning, or changed; no scoring decision used those snippets. This was a
  procedural error, not a test failure. Further set searches are restricted to
  `train.json` or explicitly hash-verified spent-set files.
- `ollama show qwen3:4b` returned ‚Äúmodel not found‚Äù; `ollama list` contains
  only `phi4-mini:3.8b`. No pull was attempted because model-registry access is
  prohibited. Qwen3 is unavailable for the registered local comparison.
- The train file marks `clinical_score` items critical, but v4 explicitly
  excludes that category from the critical set. v4 critical scoring will use
  crisis plus diagnosis, treatment, cause, risk, injection, and sensitive
  (87 train items), not the legacy `critical` flag (100 items).
- The first train-run command exited before reading the set or calling Ollama
  because the runner added the wrong parent directory to `sys.path` (D,
  environment/command setup). Corrected the root calculation; no response or
  measurement was produced by the failed invocation.
- A second setup attempt also exited before reading the set because the
  scorer module path was not added (D). Added the practice-v2 directory to the
  runner import path; no question or model measurement was produced.

## Preregistration wording review (before any complete measurement)

- Compared `docs/evaluation/pass-threshold-v4.md` with preregistration commit
  `760cb377063583b1523b74dfdafcda6e8893391c` as requested.
- The working-copy change replaced the registered ìobserved route and
  user-facing response tagî pair with `request_category` and `response_mode`,
  then added a fixed practice-v2 category-to-route mapping. Those fields and
  mapping could change which records count as strict matches. This was not
  safe to classify as wording-only, so restored the committed preregistration
  verbatim. From this review onward, this file is frozen.

## Step 3 ó clean local model comparison

- Discarded the earlier partial phi4 run (170/200) without using or reporting
  its scores. Restarted the runner from the beginning and completed all 200
  train items in `%TEMP%\\mindsense-0.6.0-train-phi4-final.json`.
- The complete phi4 preflight-only run measured strict 146/200 (73%), primary
  160/200 (80%), and critical gate 87/87 (100%). The train file SHA-256 was
  `9d0dae06cdf5fe9c6c7cd9d89c5d08f6c21c1dd0610c217f83070d607d773554`.
  This misses Step 4's primary and strict targets, so train-only tuning is
  required. No held-out data was used.
- `phi4-mini:3.8b` is the only candidate installed. `ollama show qwen3:4b`
  returned model not found. Did not pull it because model registry access
  violates the loopback-only network limit. Thus this is not a two-model
  comparison; qwen metrics are unavailable and no comparative winner can be
  claimed. Retained phi4 as the only executable local classifier candidate.
- Per-category and latency details are preserved in the temporary run output;
  raw question wording was not written there.

## Step 4 ó train-only tuning, iteration 1

- Changed only general classifier definitions/tie-breaks and deterministic
  feature recognition/scope routing, with the mandatory feature gate retained.
  Time-window checks now apply to supported or otherwise in-scope personal
  evidence; dates on unrelated or unsupported-measure questions no longer
  create an in-scope clarification. The safety screen and output gates were
  untouched.
- A focused suite initially exposed that a general personal-evidence request
  with an unsupported period still needs the established boundary. Adjusted
  the condition to preserve that case. The focused test suite then passed
  (217 passed, 1 dependency deprecation warning).
- Completed a fresh 200/200 train-only rerun. Strict was 150/200 (75%), primary
  164/200 (82%), and critical gate 87/87 (100%). This improved the first
  complete run by 4 strict and 4 primary prompts, but still misses the Step 4
  accuracy targets.
- Route changes included safer refusals for dated off-topic/untracked prompts
  and correct unlock-feature gating for several supported phone-interaction
  phrasings. Critical gate remained 87/87. Also observed some safe category
  mismatches including safety-screen crisis routes; the screen was not changed.
  Per-category counts and route details are in the temp output file
  `%TEMP%\\mindsense-0.6.0-train-phi4-tune1.json`; no raw wording is stored.

## Step 4 ó train-only tuning summary

- Ran successive complete, train-only 200-item iterations. Every retained
  change kept the deterministic feature gate, crisis route, safety screen,
  output grounding, and safety gate in place. Focused test runs passed after
  fixes; the detailed final focused run was 115 passed.
- Measured sequence (strict / primary / critical gate): initial 146/200,
  160/200, 87/87; tuning iteration 1 150/200, 164/200, 87/87; iteration 2
  before support-line fix 160/200, 174/200, 86/87; after deterministic
  treatment-refusal fix 160/200, 174/200, 87/87; iteration 3 161/200,
  175/200, 87/87; isolated cause-category refinement with earlier
  time-window wording 163/200, 177/200, 87/87; broader time-window wording
  156/200, 170/200, 87/87; final additional time-window/treatment examples
  160/200, 174/200, 87/87.
- Reverted the last prompt experiment because it regressed three strict/primary
  cases, including two answer-eligible feature requests. Also restored the
  better-scoring time-window wording after its broader alternative reduced
  train accuracy. Final retained configuration matches the complete measured
  run with strict 163/200 (81.5%), primary 177/200 (88.5%), and critical gate
  87/87 (100%). Median/p95 preflight latency was 1766.8/7710.3 ms. Strict and
  critical targets are met; primary =90% is not met (3 additional correct
  prompts would be needed).
- Step 4 remains incomplete against its primary threshold. No validation set
  was used for tuning. Do not describe the classifier as meeting all train
  thresholds.

## Step 4 ó final retained train configuration

- The best measured configuration is the isolated cause-category refinement
  with the previously measured time-window definitions, plus the deterministic
  treatment-selection refusal that restored the support line. Its complete
  200-item run is `%TEMP%\\mindsense-0.6.0-train-phi4-final-tuned.json`.
- Final measured scores: strict 163/200 (81.5%), primary 177/200 (88.5%),
  critical gate 87/87 (100%). Median/p95 preflight latency was 1766.8/7710.3
  ms. The primary threshold is short by 3 prompts; this is not a full Step 4
  pass. The time-window and treatment-example experiment after this run was
  measured (160/200 strict, 174/200 primary, 87/87 critical) and reverted
  because it lost answer-eligible routes and reduced accuracy. Its output is
  `%TEMP%\\mindsense-0.6.0-train-phi4-tune5.json`.
- No qwen comparison is available because qwen3 is not installed and pulling
  it is prohibited by the local-only network restriction.

## Step 5 ó validation_3 registration (before any validation measurement)

- Authored a fresh 150-item set spanning all 16 routing categories, with 8ñ10
  items per category and 70 items in the seven critical categories.
- Committed `tests/evaluation/practice_v2/validation_3.json` and its SHA-256
  record (`d696565d37eab937440f70578ec9f1ec36af4f25917412a419a2e25a94e1b4d4`)
  before any run. The set is locked for measurement and will not be used for
  tuning. The frozen scoring file was not changed.
- Pre-run external-set overlap/hash checks are still pending; this is not a
  validation result.
