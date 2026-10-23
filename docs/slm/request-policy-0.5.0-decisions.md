# Request policy 0.5.0 implementation decisions

This log records routing and evaluation decisions made while completing policy
0.5.0. It supplements [the policy specification](request-policy-0.5.0.md).

## 2026-10-23

| Decision | Evidence and rationale | Classification / result |
| --- | --- | --- |
| Keep the 36-to-24 generation-payload assertion change. | Under policy 0.5.0, the public alignment case `plan_q4` has no deterministic feature. It now receives `ambiguous_feature_request` clarification before evidence access; its 12 repetitions (4 variants × 3 runs) make no generation calls. The other 24 payloads remain, and the updated quality comparison passes. Its expected route is documented in the public evaluation mapping and points to the feature-clarification section of the policy doc. | B, verified: 12 clarification responses, 0 model calls for those records; focused suite passed. |
| Category routing cannot override deterministic specific categories or feature decisions. Broad in-scope requests without a deterministic feature get a deterministic clarification before router invocation. | Explicit user decision. Tests cover in-scope with a feature, diagnosis, injection, and feature ambiguity using a stub that would otherwise return `risk`; the router is not called and no generated answer is produced. This keeps ambiguous requests from becoming unsupported risk refusals or model-selected evidence routes. | B, verified by focused tests. |
| Preserve the `injection_02` crisis route on main. | Compared the case without printing its wording: main's deterministic classifier yields `prompt_injection`; its unchanged local safety screen returns `yes`; main's final route is crisis. The route is safe and the instruction says to keep main's crisis behavior when that is the baseline. No safety-screen code or order was changed. | A, verified baseline behavior; no change required. |
| Do not modify held-out or spent result content. | User's absolute limit; use only aggregate status and existing regression test IDs for this work. | Constraint. |

### B2 failure classifications and updates

The first full backend run on this branch reported 74 old-version pin failures
(A), one old generic-fallback support-line expectation (B), and three variant
quality fixture setup errors (B: clarification paths correctly skipped model
generation). The initial failure table was shown before those assertions were
updated. The version pins and support-line assertion were updated without
removing checks. The public plan mapping and payload counts now explicitly
record the clarification behavior. The focused category-router, evaluation
alignment, and variant-quality suite passes: 52 passed.
