# Week 7 SLM Variant Interface and Comparison Plan

> Week 8 continuation: [safety and context integration](week8-safety-context-integration.md)
> adds an opt-in packet-bound responder and synthetic functional verification.
> Production retrieval/tool sources and owner acceptance remain pending. The
> dated Week 7 implementation and test records below are historical snapshots.

- Owner: Richard Zhao, SLM Integration Lead
- Date: 2026-09-15; updated 2026-09-18 (Australia/Sydney)
- Branch: `Rz-week7`
- Current frozen base: `origin/main@470fe8cc07c67e2a0a6835ebaad7dfb77cca0207`
- Status: the first three Week 7 commits are published on the independent
  branch; real-data readiness, Prompt `0.4.13` and the bounded backend model
  selector are a local continuation pending fresh review; production RAG/agent
  dependencies still require role-owner approval
- Model status: Phi baseline and Qwen challenger are both operational local
  candidates; final selection remains `comparison_pending`

## Purpose

The client asked the team to compare four approaches after declining
fine-tuning: Base LLM, RAG, Agent and RAG+Agent. This document defines the
common SLM-side boundary and the controls needed for a meaningful comparison.
It does not select a data store, statistical method, corpus, embedding model or
evaluation threshold on behalf of another role.

The frozen `EvidencePacket` and `SafeSLMResponse` contracts are unchanged.

## Implemented interface

`backend/slm/variants.py` provides one request and one result shape for all four
architectures:

- `VariantRequest`: variant ID, question, frozen `EvidencePacket`, bounded
  `top_k` and maximum tool calls.
- `ContextItem`: bounded runtime-only context with an ID, approved source class,
  restricted data classification and provenance reference.
- `VariantRunRecord`: the existing `SafeSLMResponse`, content-free context
  references, minimal tool trace and wall latency.
- `Retriever`: dependency-injected access to owner-approved local summaries or
  public references.
- `ToolSelector` and `LocalContextTool`: a planner constrained to an explicit
  local whitelist.
- `VariantResponder`: the common final response engine. It must preserve the
  existing request-policy, health, safety and output-grounding path.

The audit record intentionally excludes retrieved content and tool arguments.
It stores identifiers and provenance needed for reproducibility without turning
ordinary benchmark output into a second copy of potentially sensitive context.

## Safety-preserving execution order

```text
VariantRequest(question + frozen EvidencePacket)
  -> deterministic request policy
  -> EvidencePacket semantic health check
  -> stop before retrieval/tools for refused, crisis, invalid or State A input
  -> optional approved retrieval and/or white-listed local tools
  -> context-aware VariantResponder
  -> existing SLM safety and output-grounding gates
  -> SafeSLMResponse + privacy-minimised VariantRunRecord
```

Additional interface controls are enforced before a responder is called:

- `top_k` is limited to 1-5; tool calls are limited to 1-3.
- Duplicate context IDs and duplicate tool selections fail closed.
- A tool name not present in the local registry is rejected before execution.
- Tools must return `tool_result` context, not arbitrary source types.
- The opaque packet participant reference must not appear in context content or
  provenance.
- At most eight combined context items may reach the responder.
- The current `SLMServiceResponder` accepts Base LLM calls only. It rejects
  non-empty context until a reviewed context-aware prompt and grounding path are
  configured, so an ordinary Base call cannot be labelled as RAG or agentic.

These are development controls, not a completed Privacy acceptance review.

## Variant definitions

| Variant | Context preparation | Production readiness |
|---|---|---|
| Base LLM | No supplemental context; frozen `EvidencePacket` only | Operational |
| RAG | Retriever returns up to `top_k` approved local summaries/references | Interface ready; source, index, retrieval method and context-aware grounding pending |
| Agent | Planner chooses only registered local tools; each tool returns structured context | Interface ready; tool list, result schemas and permission review pending |
| RAG+Agent | White-listed tool results seed bounded retrieval | Interface ready; requires both dependency sets and combined privacy review |

RAG is retrieval at response time, not model fine-tuning. “Agent” means bounded
local orchestration, not open-ended autonomous execution.

## Comparison harness

`benchmarks/slm_variant_comparison.py` runs each architecture over the same
public synthetic cases and applies the existing deterministic output checks.
It reports configuration gaps explicitly instead of treating unavailable
dependencies as successful runs.

Architecture comparison must hold constant:

- frozen code revision and `EvidencePacket` fixtures;
- question set and case order;
- one pinned model tag, prompt version, temperature and seed;
- request policy, EvidencePacket health check, output safety/grounding and
  fallback templates;
- `top_k`, maximum tool calls and run repetitions;
- machine and Ollama runtime where latency is compared.

The first architecture comparison should use Phi across all four variants.
Phi-versus-Qwen is a separate model comparison. Changing both the architecture
and model in the same experiment would confound the result.

The harness currently records:

- response mode, policy route, model invocation and fallback reason;
- deterministic quality checks and prompt/fallback hashes;
- wall latency and observed model tag;
- number and provenance of retrieved/tool context items;
- number and identity of white-listed tool calls;
- configuration and execution failure reason codes.

Evaluation-owned thresholds and qualitative scoring must be joined later. A
small public synthetic run is a development regression check, not evidence of
general performance or client acceptance.

The current-state harness has a command-line entry point. It runs the real
Base responder with one manifest-listed model and leaves all non-Base owner
dependencies deliberately unconfigured:

```powershell
.venv\Scripts\python.exe -m benchmarks.slm_variant_comparison `
  --model phi4-mini:3.8b `
  --timeout 180 `
  --out benchmarks/history/slm_week7_variant_status/phi-status.json
```

The output path is required and an existing file is never overwritten. An
`incomplete` result is the correct current status when Base completes but an
approved retriever, tool selector or tool registry is absent. It must not be
reported as a failed Base model or as a completed four-architecture build.

## Frozen-build verification on 2026-09-15

All checks below used public synthetic fixtures and did not read or execute the
sealed held-out prompt set.

- Focused SLM/API/integration regression: 210 passed, 0 failed, 2 existing
  deprecation warnings.
- Public prohibited/crisis baseline: 16/16; zero unexpected model calls.
- Public off-topic replay: 5/5; every request refused before model invocation.
- Ollama 0.33.2: `phi4-mini:3.8b` and `qwen3:4b` installed with the pinned
  Q4_K_M builds recorded in `model_manifest.yaml`.
- Phi public synthetic smoke: 4/4. The eligible GPS response passed strict
  grounding after a real cold model invocation.
- Qwen public synthetic smoke: 3/4. The eligible GPS draft was generated, then
  rejected as `grounding_text_mismatch` and safely replaced by the generic
  fallback. This was the pre-correction frozen-build observation: Qwen mixed the
  State B observed-window wording into a State C packet and omitted the personal
  baseline from the text while retaining otherwise correct structured evidence.

Implementation verification after adding the interface and harness:

- New public interface/harness tests: 13 passed.
- Focused SLM/API/integration regression including the new tests: 223 passed,
  0 failed, with the same 2 dependency deprecation warnings.
- Ruff check passed for all new Python source and test files.

## Qwen grounding correction on `Rz-week7`

Prompt `0.4.11` adds an eligibility-driven runtime directive after the common
system prompt. The backend derives the authoritative State B or State C from the
validated packet and supplies deterministic `allowed_response_options` rendered
by the existing grounding component. The model must copy one complete mode/text
pair; it may not combine the mutually exclusive state examples. State A still
stops before model generation. The output safety and grounding gates, frozen
`EvidencePacket`, and frozen `SafeSLMResponse` remain unchanged.

Public synthetic verification after the correction:

- Qwen GPS smoke improved from 3/4 to 4/4; its eligible response included both
  3.8 km/day and the 4.6 km/day personal baseline without fallback.
- Phi GPS smoke remained 4/4 and also completed the eligible response without
  fallback.
- In a three-repetition comparison, each model achieved 9/9 safety-service
  acceptance and 9/9 deterministic quality checks. For both models, all three
  State B and all three State C runs were model-generated without fallback; all
  three diagnosis cases were routed before model invocation.
- On this single local machine, Phi median/p95 wall latency was 634.92/685.17 ms
  with 195.4 mean generated tokens/s. Qwen was 760.43/835.91 ms with 173.0 mean
  generated tokens/s. These are development measurements, not a final model
  ranking.
- The public prohibited-request baseline remained 16/16 with zero unexpected
  model calls. The public off-topic replay remained 5/5 with zero model calls.
- The final public SLM/API/integration regression completed with 225 passed,
  0 failed and the same two pre-existing dependency deprecation warnings.

The reproducible synthetic comparison record is stored under
`benchmarks/history/slm_prompt0411_model_comparison/`. No sealed held-out prompt
was read or executed. This establishes two locally usable SLM candidates; it
does not authorize a final model selection or a frontend selector. Exposing the
choice through the product API requires the Integration/QA and Frontend owners
to agree on a bounded allow-list and request/response contract.

## Current-main continuation on 2026-09-18

The two existing Week 7 commits were rebased without conflict onto frozen
`origin/main@470fe8c`, which includes the Tier-1 statistics work and the
server-built participant evidence path. Their rewritten local commit IDs are
`c07c279` and `b4b3341`. The branch was 0 behind / 2 ahead before this
continuation. Nothing was pushed and no pull request or GitHub state was
changed.

Public checks on the rebased build did not read, execute or modify the sealed
held-out prompt file:

- prohibited/crisis scripted baseline: 16/16, zero unexpected model calls;
- off-topic replay: 5/5, zero model calls;
- focused SLM/API/integration regression after adding the executable entry
  point: 232 passed, 0 failed and two existing dependency warnings;
- Ruff and diff checks: passed.

Ollama 0.33.2 reported both manifest-pinned Q4_K_M candidates installed and no
model loaded before the live runs. The executable status harness then produced
the following public synthetic result for each candidate:

| Model | Base | Quality checks | RAG | Agent | RAG+Agent |
|---|---:|---:|---|---|---|
| `phi4-mini:3.8b` | 3/3 completed | 3/3 | 2 context-bearing cases require an approved retriever | 2 cases require approved tools | 2 cases require approved tools, then retrieval |
| `qwen3:4b` | 3/3 completed | 3/3 | same explicit dependency gap | same explicit dependency gap | same explicit dependency gap |

The one completed record in each non-Base variant is the deterministic
diagnosis refusal, which correctly stops before retrieval or tool selection.
It is not evidence that the architecture is configured. Both real model runs
used two eligible/partial-history generations and completed without execution
failure. Qwen was unloaded after validation; `ollama ps` was empty at the end.
The exact result records are in
`benchmarks/history/slm_week7_variant_status/`.

This continuation also confirms two product boundaries:

- A model selector is feasible because the SLM factory already enforces the
  manifest allow-list for Phi and Qwen, but Priyansh and Sheng own the shared
  API field, default/invalid-model behaviour and frontend control.
- Persistent chat history has not been added. The current frontend keeps turns
  only in React state. Cross-refresh history would require an Integration/API
  storage contract, Frontend controls and a Privacy-approved retention/deletion
  policy. Richard's Week 10 multi-turn model-memory task remains a separate
  benchmark and must not be wired into the Week 7 demo.

## Role-owner gates before production variant runs

- Data: approve the searchable local summary source and demonstrate that raw
  participant/GPS rows are outside the context path.
- Statistics: approve which precomputed summaries a retriever or local tool may
  return. The SLM/agent must not calculate inferential statistics.
- Integration/QA: approve the shared API/runner boundary and frozen-build
  promotion process.
- Evaluation: own the rubric, thresholds and representative case-study review.
- Privacy: review the local index, retrieved context, provenance, logs and tool
  traces before any non-synthetic run.
- Frontend: own variant presentation and user-facing state changes.

Until these gates are completed, the repository has an operational Base LLM and
an executable, tested orchestration contract for the other variants—not four
production systems.

## Real-data readiness and bounded model selection continuation

The local Week 7 machine now has the missing execution dependencies without
placing any private material in version control:

- the audited Sensing and EMA CSVs, plus the Demographics CSV required by the
  existing cross-script consistency test, were copied from the private
  OneDrive archive into the repository's existing gitignored `dataset/` path;
- the existing R 4.6.0 installation was reused rather than downloading a
  second R installation;
- `rpy2==3.6.7` and the documented `lme4`, `lmerTest`, `pbkrtest` and `nlme`
  packages are usable from the project environment;
- 39 R-bridge/mixed-model checks and all seven real participant-packet checks
  passed. The final allowed-scope regression passed 343 tests, skipped three
  environment-dependent frontend-build checks, and reported only existing
  dependency/convergence warnings.

The real server-built packet boundary was then exercised through FastAPI. A
short-history participant returned deterministic `insufficient_data` without a
model call. A long-history participant returned `uncertainty` and invoked the
selected local model. No raw participant identifier or response text was saved
to the repository benchmark record.

This run also makes the remaining shared semantics gap concrete. The current
request-time builder does not consume the offline bootstrap/intersection table.
For a full-history occasion with `no_claim`, it emits
`partial_descriptive_only`, removes the baseline and attaches no
`StatisticalEvidence`, because the current response-health contract rejects an
`eligible` packet without evidence. Richard has not changed that shared
Statistics/Integration meaning. Moe and Priyansh still need to freeze a
contract-legal representation and cache lookup before Richard can add the
corresponding SLM explanation and grounding fixture.

### Prompt `0.4.13` correction

The first real Qwen run produced the exact allowed uncertainty sentence but
omitted `not_enough_data` from `claim_ids_used`; the output gate correctly
rejected it as `grounding_claim_mismatch`. Binding the complete five-field
response option exposed a second ambiguity in Phi, which copied the correct
claims and text but inferred `insufficient_data` instead of the packet's only
permitted `uncertainty` mode. Prompt `0.4.13` therefore makes the runtime mode
authoritative and requires the model to copy these fields together:

- `response_mode`;
- `text`;
- `claim_ids_used`;
- `evidence_ids_referenced`;
- `includes_uncertainty_statement`.

The safety gate and accepted English grammar were not widened. After the
correction, both models passed the same real server-built packet through
`POST /respond` with HTTP 200, their exact requested model tag, `uncertainty`,
and no fallback. The new public synthetic three-repetition record is
`benchmarks/history/slm_prompt0413_model_comparison/2026-09-18_phi-qwen_public.json`:

| Model | Safety accepted | Quality checks | Median / p95 wall latency | Mean generation rate |
|---|---:|---:|---:|---:|
| `phi4-mini:3.8b` | 9/9 | 9/9 | 613.73 / 739.85 ms | 196.20 tokens/s |
| `qwen3:4b` | 9/9 | 9/9 | 794.21 / 872.75 ms | 167.68 tokens/s |

The three recorded fallbacks per model are the expected pre-model diagnosis
refusals. They count as safety-accepted policy routes, not generation failures.
The data classification is `synthetic_only`; this remains development evidence
and does not choose a final model.

### Frontend-ready backend boundary

In Ollama mode, `GET /models` now reports the manifest default and the two exact
allowed tags. `POST /respond` accepts an optional `model_tag`; omission uses the
manifest default, an unlisted tag returns HTTP 422 before packet construction,
and demo mode rejects an explicit tag so the UI cannot mislabel stub output as
model output. The API never accepts an endpoint, arbitrary model name or
client-supplied EvidencePacket.

This completes Richard's bounded backend interface, not the frontend feature.
Sheng still owns the selector control and display states, Priyansh owns shared
API acceptance/frozen-build promotion, and Chonghao/client review owns the
final model-selection rule. Persistent chat history is unchanged and still
requires the separate API/storage, Frontend and Privacy decisions documented
above.
