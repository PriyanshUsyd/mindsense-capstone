# Week 7 SLM Variant Interface and Comparison Plan

- Owner: Richard Zhao, SLM Integration Lead
- Date: 2026-09-15 (Australia/Sydney)
- Branch: `Rz-week7`
- Frozen base: `main@691d1fe9382e56d67e208207f89a9a1d71908b1c`
- Status: common interface and public synthetic harness implemented; production
  RAG/agent dependencies require role-owner review
- Model status: Phi operational baseline; Qwen challenger; final selection
  remains `comparison_pending`

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
  fallback. This proves boot/invocation, not baseline readiness.

Implementation verification after adding the interface and harness:

- New public interface/harness tests: 13 passed.
- Focused SLM/API/integration regression including the new tests: 223 passed,
  0 failed, with the same 2 dependency deprecation warnings.
- Ruff check passed for all new Python source and test files.

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
