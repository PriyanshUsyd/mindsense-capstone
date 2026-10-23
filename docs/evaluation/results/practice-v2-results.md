# Practice v2 routing results — policy 0.5.0

Date: 2026-10-23 (UTC result timestamps are recorded in the JSON files)
Branch: `fix/chatbot-accuracy-0.5.0`

## Summary

This PR implements deterministic request-policy routing and a category router
that is eligible only after deterministic off-topic classification. The model
never grants an in-scope answer; feature scope and evidence eligibility remain
deterministic. The issue in which the router could override a deterministic
route is fixed and covered by regression tests. `injection_02` matches main's
safe final crisis route: deterministic injection classification precedes the
unchanged local safety screen, which returns a positive screen result. The
screen was not changed.

The required accuracy targets were not met. The PR is therefore **not finished**
for release evaluation, though the requested PR is opened for review.

## Accuracy

Scores are route-plus-response-tag accuracy. No answer generation was used for
the practice split evaluations.

| Split/run | Overall | Critical | Support-line |
| --- | ---: | ---: | ---: |
| Train, best policy 0.5.2 (round 5) | 159/200 (79.5%) | 76/100 (76.0%) | 175/175 (100%) |
| Train, one allowed post-validation prompt round 0.5.3 (round 6) | 154/200 (77.0%) | 75/100 (75.0%) | 175/175 (100%) |
| Validation, first and only run | 155/200 (77.5%) | 81/104 (77.9%) | 171/176 (97.2%) |
| Validation 2, first and only run after the fix round | 81/100 (81.0%) | 41/52 (78.8%) | 84/88 (95.5%) |

B5 targets (critical 100%, overall at least 95%) were missed. B6 targets
(validation critical 100%, overall at least 90%) were missed on both validation
runs. The one authorized fix round used train only; its prompt candidate scored
below the prior best and was reverted. Validation and validation 2 were not used
for tuning and neither was rerun. Current router prompt is 0.5.2.

## B3 checks

| Check | Result |
| --- | --- |
| Full Python suite, after final fixes | 1,707 passed, 23 skipped, 0 failed; 78 warnings |
| Vitest | 97 passed across 6 files |
| oxlint | Passed |
| TypeScript and Vite production build | Passed |
| `npm audit --omit=dev` | 0 vulnerabilities |

The 78 warnings are existing Starlette deprecation and statsmodels convergence/
singularity warnings. An earlier full run found three C regressions, which were
fixed and followed by the passing full rerun. See the decision log for the
failure-class history.

## B7 status

- Grounding: grounding unit/policy tests passed within the full suite. A separate
  independent grounding run over a newly captured answer corpus was not run.
- Stability: not run; no three-fresh-server 60-question stability measurement is
  claimed.
- Router latency: no dedicated B7 median/p95 benchmark was captured; none is
  claimed.
- Spent sets: the dev-50 spent regression suite passed as part of the full suite.
  The separate historical v1–v6/client-v1 before/after aggregate comparison was
  not run because the required before/after snapshots were not available among
  the current result artifacts. No spent set was opened, changed, or used for
  tuning.

## Failure classification summary

| Class | Count/occurrence | Outcome |
| --- | --- | --- |
| A — version pin | 74 assertion failures in the initial B2 run | Updated version pins; assertions retained |
| B — intended change | 1 support-line expectation and 3 variant fixture setup errors in the initial B2 run | Updated expectations/setup; assertions retained |
| C — regression | 83 failures from an over-broad clarification experiment | Reverted the experiment |
| C — regression | 3 failures in a later full run (two sensor precedence, one generic off-topic reason) | Fixed rule precedence and narrowed the measure matcher; full suite then passed |
| D — environment/command | 2 invocations failed before tests ran (wrong Python path and test-directory name) | Correct full suite was run successfully |

## Still not finished

- Train and validation accuracy targets remain unmet.
- B7 independent grounding corpus, 60-question/three-server stability, dedicated
  router latency, and historical v1–v6/client-v1 spent-set comparison remain
  unmeasured.
- No held-out final blind validation was opened or run.

Validation result files contain aggregate metrics and category/tag outcomes but
no question wording. The validation source files and their hashes were committed
before their single authorized runs. The decision log is
[`docs/slm/request-policy-0.5.0-decisions.md`](../../slm/request-policy-0.5.0-decisions.md).
