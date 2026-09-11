# Week 6 SLM Integration Report

**Owner:** Richard Zhao — SLM Integration

**Last verified:** 11 September 2026 (Australia/Sydney)

**Branch:** `Rz-week6`, based on `origin/main` at `e7a2538`

**Status:** implementation and development verification complete; published to
`origin/Rz-week6`, with PR review and joint acceptance still pending

**Model status:** `comparison_pending` — Phi baseline, Qwen challenger

## Scope and ownership boundary

This work implements Richard's Week 6 SLM scope: iterate the Week 5 prompt,
make the fallback paths operational for the newly supplied off-topic cases,
and add a deterministic response health-check tied to explicit evidence-contract
violations. It does not modify the frozen shared `EvidencePacket` model, the
shared HTTP API, Statistics/Data code, UI code, or Evaluation's registered
threshold. Priyansh still owns the shared API/integration wrapper, Sheng owns UI,
and the relevant joint review remains pending.

Phi-4 Mini remains the current baseline and Qwen remains the challenger. This
work does not make a final model selection. Ollama is the local runtime, not the
model decision.

## New off-topic request and real-model finding

The five exact questions supplied on 2026-09-11 are frozen in
[`week6_off_topic_questions.json`](../../benchmarks/fixtures/week6_off_topic_questions.json).
Every run uses the existing `eligible_above_baseline` synthetic packet; no CES
participant row, sealed question, or sensitive record is used.

The unmodified `origin/main` stack (`request policy 0.1.1`, Prompt `0.4.8`,
grounding `0.1.1`) failed all five real local Phi runs. All requests were
classified `allow/in_scope`. Phi did not answer weather, geography, poetry,
arithmetic, or cooking, but it also did not refuse: it substituted the same
phone-unlock comparison for every question. The comparison was grounded in the
packet, so the output validator accepted it. Result: **0/5 correct refusals**,
below the registered 90% soft off-topic threshold. The exact drafts, route,
model digest, prompt hash, and Ollama timings are retained in
[`slm_week6_off_topic_phi_prompt048_baseline_results.json`](../../benchmarks/slm_week6_off_topic_phi_prompt048_baseline_results.json)
and its
[`scorecard`](../../benchmarks/slm_week6_off_topic_phi_prompt048_baseline_scorecard.md).

## Week 6 implementation

Request policy `0.2.0` adds the explicit `off_topic` category. Crisis and
existing prohibited-request rules retain priority. Ordinary allowed questions
must contain both a MindSense feature signal and evidence-analysis intent;
small contextual prompts already used by the product/evaluation fixtures are
separately enumerated. Unmatched or ambiguous requests fail closed to the
versioned generic template before model generation. Tests include the five
supplied questions, the existing benign/in-scope controls, rule-priority cases,
and near misses such as “Can you recommend a phone?” and “How is the weather at
my GPS location?”.

Prompt `0.4.10` adds defense-in-depth instructions not to answer unrelated
requests or replace them with unsolicited evidence. If an off-topic turn ever
bypasses policy, the model must return a refusal signal with no claim or
evidence references; SLMService replaces model-authored refusal text with the
approved generic template. Direct real-Phi probes deliberately bypassed policy.
The intermediate Prompt `0.4.9` and final Prompt `0.4.10` each produced refusal
mode for all five questions, with no substituted evidence and no requested
off-topic answer. The raw drafts are retained in the
[`0.4.9 probe`](../../benchmarks/slm_week6_off_topic_phi_prompt049_direct_probe_results.json)
and the
[`0.4.10 final probe`](../../benchmarks/slm_week6_off_topic_phi_prompt0410_direct_probe_results.json).
These raw texts are diagnostic only and are never participant-facing.

The production-style service benchmark now gives **5/5 correct deterministic
refusals**, with `request_category=off_topic`, `response_mode=refusal`,
`used_fallback=true`, and `model_invoked=false`; therefore the 90% threshold is
met. Full records and the exact generic fallback text are in
[`slm_week6_off_topic_phi_prompt0410_results.json`](../../benchmarks/slm_week6_off_topic_phi_prompt0410_results.json)
and its
[`scorecard`](../../benchmarks/slm_week6_off_topic_phi_prompt0410_scorecard.md).
The original result remains an execution-time snapshot from a dirty worktree.
The additive
[`clean post-commit replay`](../../benchmarks/slm_week6_off_topic_phi_prompt0410_postcommit_replay_results.json)
and matching
[`scorecard`](../../benchmarks/slm_week6_off_topic_phi_prompt0410_postcommit_replay_scorecard.md)
repeat the same 5/5 service result at committed head `f8ae5e9`, with all eight
recorded source hashes matching. Historical evidence was not overwritten.

During development, the first cold Prompt `0.4.9` four-path smoke passed 3/4:
the eligible GPS draft omitted its evidence reference and was safely converted
to the generic fallback with `grounding_evidence_reference_missing`. A warm
rerun passed 4/4. Prompt `0.4.10` therefore adds an exact metadata requirement
for the State C evidence reference instead of hiding the cold-start failure.
After that change, three consecutive cold eligible-GPS runs passed 3/3. The
archived final cold four-path run passed 4/4 and is stored in
[`slm_week6_phi_prompt0410_cold_shadow_smoke_results.json`](../../benchmarks/slm_week6_phi_prompt0410_cold_shadow_smoke_results.json).

## Deterministic response health-check

[`response_health.py`](../../backend/slm/response_health.py) version `0.1.0`
checks semantic invariants that the frozen Pydantic shape does not enforce. It
has stable machine-readable violation codes for:

- unsupported contract version, reversed windows, and observed days exceeding
  expected days;
- non-finite feature, baseline, estimate, or confidence-interval values;
- eligible packets missing baseline history/evidence or carrying a contradictory
  ineligible reason;
- non-eligible packets carrying comparison state or missing their reason;
- reversed confidence intervals or estimates outside their interval; and
- incomplete prohibited-claim sets, duplicated approved claims, or empty
  permitted response modes.

`SLMService.respond()` runs this check after crisis/prohibited/off-topic request
routing and before insufficient-data/model handling. A violation returns the
versioned generic fallback with a stable reason such as
`evidence_contract_violation:window_date_order_invalid`, and reports
`model_invoked=false`. Crisis routing intentionally keeps priority even if a
packet is unhealthy. `SLMService.check_response_health(packet)` exposes the
same read-only report for Priyansh's later API/health wiring without changing
the shared API in this branch.

## Verification

- Fixed off-topic service benchmark: 5/5, threshold 90% met, no model calls.
- Real Phi Prompt 0.4.10 direct defense probe: 5/5 refusal signals.
- Real Phi Prompt 0.4.10 cold four-path smoke: 4/4 (normal GPS model response,
  deterministic insufficient-data, generic refusal, crisis-aware fallback).
- Clean post-commit off-topic replay: 5/5, with 8/8 recorded source hashes
  matching the committed implementation.
- SLM plus end-to-end Evidence flow tests: 201 passed.
- Full repository pytest in an isolated `.venv`: 336 passed, 29 skipped, 0
  failed. The skips remain environment/data-dependent; warnings include the
  existing Starlette `httpx2` deprecation and Statistics convergence warnings.
- Ruff check and format check pass for all changed Python files.
- `git diff --check` passes.

The local `.venv` and empty `dataset/` directory used to satisfy the repository
test environment are ignored and are not delivery files.

The reviewed Week 6 scope was pushed to `origin/Rz-week6` at `4cae1b4` after
separate user confirmation. No pull request, merge, reviewer request, or
teammate message had been created when this report status was corrected.

## Integration and Week 7 handoff

Consumers should rely on `SafeSLMResponse`, not raw model text. Off-topic and
prohibited turns return deterministic generic wording with `model_invoked=false`;
crisis turns return the crisis-aware template; invalid evidence returns
`generic_fallback` plus its violation code. No client should display a raw
Prompt 0.4.10 refusal draft.

The local Week 7 demo machine currently has Ollama `0.33.2` and
`phi4-mini:3.8b` digest
`78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753`.
The real normal path was rechecked successfully. Richard can keep the machine
booted and ready; demo coordination and hosting remain Priyansh's task as
communicated separately.
