# Request policy 0.5.0 implementation decisions

This log records routing and evaluation decisions made while completing policy
0.5.0. It supplements [the policy specification](request-policy-0.5.0.md).

## 2026-10-23

| Decision | Evidence and rationale | Classification / result |
| --- | --- | --- |
| Keep 36 generated payloads; revert the 24-payload assertion. | A prior implementation treated every in-scope request with no lexical feature match as preflight clarification. The full backend run exposed 83 failures, including context, grounding, API, and policy regressions. This change was classified C and reverted. In the supported variant-quality harness, deterministic packet feature selection scopes the answer and all 36 model invocations remain. When API preflight has no selected feature, its existing `require_feature=True` boundary still asks for clarification. | C, reverted. |
| Category routing cannot override a deterministic specific-category or in-scope route. | Explicit user decision. Router eligibility is now limited to deterministic off-topic requests; an in-scope route bypasses it and the later deterministic feature checks remain in control. Stub tests cover in-scope with a feature, diagnosis, injection, and the off-topic-to-in-scope clarification handoff. | B, verified by focused tests; full suite rerun pending. |
| Preserve the `injection_02` crisis route on main. | Compared the case without printing its wording: main's deterministic classifier yields `prompt_injection`; its unchanged local safety screen returns `yes`; main's final route is crisis. The route is safe and the instruction says to keep main's crisis behavior when that is the baseline. No safety-screen code or order was changed. | A, verified baseline behavior; no change required. |
| Do not modify held-out or spent result content. | User's absolute limit; use only aggregate status and existing regression test IDs for this work. | Constraint. |

### B2 failure classifications and updates

The first full backend run on this branch reported 74 old-version pin failures
(A), one old generic-fallback support-line expectation (B), and three variant
quality fixture setup errors. The initial failure table was shown before those
assertions were updated. Version pins and the support-line assertion were
updated without removing checks. The later full backend run on the temporary
over-broad clarification change reported 83 failures; these were classified C,
and that routing change was reverted. Main's `injection_02` final route was
verified as crisis (rules classify prompt injection, local screen returns
`yes`), so the existing main behavior and safety-screen order were preserved.

After reverting that regression and keeping only the deterministic route guard,
the full backend suite passed: 1,702 passed, 23 skipped, 0 failed (78 warnings).
The focused router/alignment/variant suite passed 52 tests. Frontend checks
passed: npm audit reported 0 vulnerabilities, Vitest reported 97 passed,
oxlint passed, and the production build succeeded.

B4 verified the existing synthetic bootstrap cache without rebuilding it.
Ollama 0.40.8 has `phi4-mini:3.8b`; `/health` and `/models` report the synthetic
dataset and Ollama runtime. Local-demo GPS and unlock packets both report
eligible status, attached statistical evidence, and the normal response mode.
The captured backend log contained no `BootstrapCacheStale` or
`bootstrap_cache_unusable` warning.

B5 used the fresh `train.json` split only. Two diagnostic runs called the
category router directly: round 1 was 141/200 (70.5%) with critical 87/100;
round 2 with router prompt 0.5.1 was 151/200 (75.5%) with critical 91/100 and
support-line checks 175/175. Router prompt 0.5.2 round 3 scored 145/200
(72.5%) and critical 87/100, so it did not improve the direct-label result.
Production preflight round 4 was 151/200 (75.5%), critical 73/100, support
170/175; the fifth run after general deterministic boundary fixes scored
159/200 (79.5%), critical 76/100, support 175/175. These are route-plus-tag
scores with no answer generation. B5 thresholds (critical 100%, overall 95%)
remain unmet. The decisions to strengthen capability, causal, private-record,
time-window, and untracked-measure boundaries are generalized rule changes;
the train questions were not copied into rules, prompts, or tests.

B6 began with those B5 targets unmet under the user's instruction to continue.
The independent 200-question validation split and its SHA-256 were committed
before any validation execution. This is the first and only authorized run of
that split; no validation question text is included in logs or result records.
