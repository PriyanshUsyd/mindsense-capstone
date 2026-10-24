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
- A broad repository text search unintentionally scanned locked
  `validation_2.json` while locating prior scoring metadata. Its output exposed
  truncated source snippets. No validation set was executed, hashed, used for
  tuning, or changed; no scoring decision used those snippets. This was a
  procedural error, not a test failure. Further set searches are restricted to
  `train.json` or explicitly hash-verified spent-set files.
- `ollama show qwen3:4b` returned “model not found”; `ollama list` contains
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
- The working-copy change replaced the registered “observed route and
  user-facing response tag” pair with `request_category` and `response_mode`,
  then added a fixed practice-v2 category-to-route mapping. Those fields and
  mapping could change which records count as strict matches. This was not
  safe to classify as wording-only, so restored the committed preregistration
  verbatim. From this review onward, this file is frozen.

## Step 3 — clean local model comparison

- Restarted the runner from the beginning and completed all 200 train items
  in `%TEMP%\\mindsense-0.6.0-train-phi4-final.json`. The incomplete run was
  discarded; none of its partial progress or scores is reported.
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

## Step 4 — train-only tuning, iteration 1

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

## Step 4 — train-only tuning summary

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
  (complete run: strict 156/200, primary 85%, critical 87/87); final additional time-window/treatment examples
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

## Step 4 — final retained train configuration

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

## Step 5 — validation_3 registration (before any validation measurement)

- Authored a fresh 150-item set spanning all 16 routing categories, with 8–10
  items per category and 70 items in the seven critical categories.
- Committed `tests/evaluation/practice_v2/validation_3.json` and its SHA-256
  record (`d696565d37eab937440f70578ec9f1ec36af4f25917412a419a2e25a94e1b4d4`)
  before any run. The set is locked for measurement and will not be used for
  tuning. The frozen scoring file was not changed.
- Pre-run external-set overlap/hash checks are still pending; this is not a
  validation result.

- Pre-run five-word-overlap checking found duplicated five-grams in the first
  registered draft. No model run occurred. Rewrote only the affected new-set
  questions without inspecting or printing the collided spent wording,
  regenerated the SHA-256, and repeated the check. The second scan found one
  remaining collision with validation_2 (validation item ID only); rewrote
  that item and regenerated the SHA-256 again. The final overlap scan must be
  clean before the first validation_3 run.

- Final validation_3 SHA-256 `c30ff9980681174757bcfff51451e32f2fb43bf4b23a2e145dbf0bf61904cfb3`
  matched the committed sidecar. A five-word shingle comparison was performed
  after hash verification and before any model run. The final set had zero
  five-word-overlapping question IDs against practice v1 (300 items),
  practice-v2 train (200), the hash-verified v1-v4, v6-v7 and client v1 sets,
  and the committed-hash v2 validation and validation_2 sets. The check emitted
  counts and IDs only, never source question wording.
- v5 remains unavailable as previously directed. v8 exists locally but has no
  committed hash document in this checkout, so it was not read or used.

- Final post-revision overlap scan passed with zero five-word overlap item
  pairs against every available, hash-verified practice/spent file checked.
  The v3 set is now eligible for its single run; its final hash is recorded in
  `tests/evaluation/practice_v2/validation_3.sha256`.

## Full-suite decision: preflight clarifications (2026-10-24)

- The full backend suite initially reported 1,875 passed, 23 skipped, and four failures in `tests/slm/test_prompting_comparison.py`. The four failures traced to the benchmark calling `SLMService.respond()` directly and bypassing deterministic API preflight for plan_q4, plan_q6, and the supplemental partial-history case.
- Classified as B (intended safer policy behavior), based on `docs/slm/request-policy-0.6.0.md`: when the deterministic feature check cannot select a supported feature, the service returns a clarification without answer generation. The cases were already expected to clarify in the alignment manifest; the prompting harness did not mirror that application flow.
- Updated the prompting harness to run `preflight_response(..., require_feature=True)` before `respond()`. Updated the pre-registered protocol's expected answer-generation calls from 24 to 12 to account for the three clarification paths across both prompt conditions and three repetitions. Added an assertion over all 18 clarification rows (three paths x two conditions x three repetitions) that they return `ambiguous_feature_request`, invoke no answer model, and make no answer transport calls. Existing response-safety checks remain enabled.
- Focused verification after the change: prompting comparison, variant quality, evaluation alignment, request classifier, and privacy tests: 63 passed. Frontend tests: 97 passed; oxlint and production build passed. The final full backend rerun passed: 1,880 passed, 23 skipped, 78 warnings.

## Step 3 clean restart and Step 6 results (2026-10-24)

- Restarted the train classifier runner from its beginning and completed all
  200 phi4 items. The clean run is in `%TEMP%\\mindsense-0.6.0-step3-phi4-clean.json`.
  It reproduced strict 163/200 (81.5%), primary 177/200 (88.5%), and critical
  gate 87/87 (100%); median/p95 latency was 1,900.4/12,447.5 ms. The train
  SHA-256 matched `9d0dae06cdf5fe9c6c7cd9d89c5d08f6c21c1dd0610c217f83070d607d773554`.
  Primary remains three prompts below the Step 4 target. No held-out prompts
  were used for tuning.
- `ollama show qwen3:4b` returned model not found. No pull was attempted; the
  loopback-only restriction prevents registry access. Qwen has no measured
  accuracy or latency, and phi4 is not claimed as a comparative winner.
- The first spent-set verifier invocation had a mistyped expected SHA for v7;
  it reported a mismatch before parsing or using the file. Checked
  `docs/evaluation/results/held-out-v7-hash.md`, reran SHA-256, and confirmed
  the committed hash matched before using v7.
- A first validation grounding-check invocation omitted
  `MINDSENSE_DATASET_DIR=data/synthetic`; its comparison against the default
  dataset was invalid (environment error, class D). Re-ran the same check
  against `data/synthetic`: 15 answered validation responses, zero findings.
  The spent-set re-check also used `data/synthetic`: 23 answered responses
  across both runtimes, zero findings.
- Re-ran each available, hash-verified spent set once on the demo and Ollama
  for main `4cc0beb` and policy 0.6.0. v1-v4, client v1, v6, and v7 matched
  their committed hashes. v5 not re-checked (file held offline by another
  member). v8 was skipped because no committed hash document is present. All
  wording and responses stayed in temporary files; only IDs and aggregate
  routes were added to the results document.
- The spent-set critical safety score was 96/98 on both main and 0.6.0 for
  both runtimes. No critical response was answered; all critical responses
  had a support line. Demo had two crisis routes outside the crisis template
  on both main and 0.6.0; Ollama had zero of 28. The no-crisis-miss demo
  criterion therefore remains unmet.
- Route differences: 12 on demo and 63 on Ollama. No demo in-scope answer was
  lost; on Ollama, `v3#v3-19` changed from an answer on main to a safe
  feature-mismatch clarification, so the no-lost-answer criterion remains
  unmet. The full ID-only route table is in
  `docs/evaluation/results/validation-3-results.md`.
- Stability ran 60 train questions against three fresh Ollama-backed servers:
  180 responses, 120 pairwise route comparisons, zero route changes. All
  servers were terminated by the runner.
- `npm audit --offline` passed with zero vulnerabilities. `pip-audit` was not
  installed and no wheel was cached; no package or registry access was used.
  Full backend tests passed (1,880 passed, 23 skipped, 78 warnings); frontend
  Vitest passed 97 tests in six files, oxlint passed, and the production build
  passed. The frozen `pass-threshold-v4.md` remains unchanged.
- The user’s loopback-only network limit prevents push and opening the PR from
  this environment. No external network call was attempted.

## v3-19 single-feature guard correction (2026-10-24)

- The post-hoc spent-set route for `v3#v3-19` showed an Ollama in-scope answer
  on main becoming a `feature_request_mismatch` non-answer on 0.6.0. Inspection
  showed that a router feature label disagreeing with the single feature found
  deterministically caused the clarification.
- Removed that mismatch clarification. A deterministic feature result is
  authoritative when exactly one feature is found; the classifier cannot
  override it. Added a regression test for a deterministic unlock route paired
  with a conflicting GPS classifier label. Focused classifier suite passed:
  24 passed.
- Reverified hashes before loading v1-v4, client v1, v6 and v7; reran all 152
  prompts on demo and Ollama against the synthetic dataset. v5 remains offline;
  v8 remains skipped because there is no committed hash document. No in-scope
  answer was lost; critical-safe totals were 96/98 on main and 96/98 after the
  fix on each runtime. Spent grounding re-check covered 24 answered responses,
  zero findings. The two demo-only crisis route misses remain unchanged from
  main.
- Classification: C regression in the feature clarification guard, fixed to
  match deterministic feature routing on main while retaining model-off
  clarification when no feature is found. No safety or privacy check was
  weakened.

## Step 2 verification (2026-10-24)

- Full backend suite: 1,881 passed, 23 skipped, 78 warnings. Dedicated privacy
  and transport suite: 70 passed, 1 warning. Frontend Vitest: 97 passed in six
  files; oxlint and production build passed; offline npm audit found zero
  vulnerabilities. The privacy/security CI workflow installs and runs pip-audit;
  no local package download was attempted.
- The prior note that loopback-only rules blocked GitHub was superseded by the
  operator's correction: the restriction covers app runtime only. Git push and
  opening a PR are authorized.

## Held-out v9 one-time run (2026-10-24)

- Prompt file hash was committed before execution. The ten-record set was sent once, without retries, against the pushed PR branch head `913c3f00ddd23a22571db7efb316681de0b8bcce`; policy code was `89d2fbbbe63669bf404f2cb53827f86e9bc4457d`. The later result-record commit only adds IDs/categories and provenance.
- Runtime was the project `.venv`, Ollama `phi4-mini:3.8b`, and `data/synthetic`. The local-demo packets were eligible and mapped to user-facing `evidence_available` for GPS and unlocks. All ten HTTP responses were successful. Log scan found zero cache warnings.
- Scored exactly with `docs/evaluation/pass-threshold-v4.md` and `tests/evaluation/practice_v2/scoring_v4.py`: strict 10/10 (100%), primary 10/10 (100%), critical gate 8/8 (100%). Every critical item passed the no-answer, support-line and no-prohibited-claim conditions; every non-answer had its support line. The one answered response passed grounding (one checked, zero findings).
- The first scorer invocation used the source-set labels `inscope` and `appinfo`, which are not labels in the frozen scorer's practice schema, and stopped before scoring the final two rows. No model request was made by that invocation. Applied the already frozen aliases (`inscope` to `in_scope_unlocks`, `appinfo` to `app_info`) and scored the existing single run output; no prompt was rerun and no scoring rule changed.
- This was not blind evaluation: the set was written by the project coordinator, not a blind teammate, and the agent had seen it before the feature-guard correction. The result must not be represented as blind evidence. The committed results record contains IDs and categories only.
