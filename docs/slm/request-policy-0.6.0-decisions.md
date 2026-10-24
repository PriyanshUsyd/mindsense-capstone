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
