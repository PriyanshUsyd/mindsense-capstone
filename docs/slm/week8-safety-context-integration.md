# Week 8 SLM Safety and Context Integration

- Owner: Richard Zhao, SLM Integration Lead
- Date: 24 September 2026
- Base: `main@822214ca75e84279c21c9c04cda0a718976c00e9`
- Review branch: `Rz-week8` (Draft; approved-source retrieval remains pending)

## Problem and resulting behaviour

The [paired pilot](../evaluation/week7-rostered-pair-pilot-main.md) found that a
three-day question received a default GPS observed-window answer. The safe
diagnosis refusal also carried an inaccurate off-topic category. The new SLM
scope guard checks what can actually be answered before selecting data.

| Trigger | Week 8 behaviour |
| --- | --- |
| No feature words and no selected feature | Deterministic clarification; no GPS default, participant lookup or model call |
| Both supported features, or selected feature conflicts with the question | Clarification; no answer using a different feature |
| Explicit time range such as last 3 days, past couple of weeks, a date or today | State explicitly that the requested time range cannot be provided; do not substitute the packet's window |
| Contextual question with an explicit supported feature or a supplied packet | May proceed with that scope |
| “Based on my data, do you think I'm depressed?” | Deterministic `diagnosis_seeking` refusal |
| Crisis/prohibited question containing a date or ambiguous feature words | Crisis/prohibited policy retains priority |
| Healthy State B/uncertainty input | Preserve the approved descriptive response; uncertainty is not itself a failure |

`request_policy` is `0.3.0`. Two versioned deterministic templates explain scope
and time-window limitations. These are guardrail changes, not a zero/few-shot
experiment. Generation Prompt `0.4.13`, the existing generic/crisis/insufficient
templates, output grounding `0.1.1`, the frozen evidence contract, response
schema and model manifest remain unchanged.

The HTTP change only forwards the optional feature into SLM preflight and
requires a resolvable feature before participant lookup. Integration owns its
review. Unknown participants/features retain the existing HTTP validation path
when the request otherwise has a usable scope. No frontend implementation,
calendar-window calculation or statistical rule is added.

The English window detector is deliberately conservative and bounded. It is
not a general date parser, multilingual classifier or clinical detector.
Explicit periods, including fourteen days, are not assumed to match a packet
anchored to historical dates. Some otherwise benign requests will need to be
rephrased around the supplied observed window. This is visible in the response,
not a claim that the requested calendar period was implemented. Numeric
presentation precision and a richer window contract still need owner alignment.

## Context integration without new statistical claims

`backend/slm/context_responder.py` adds `PacketContextResponder`, an opt-in
consumer of existing `ContextItem`s. It uses the same loopback Ollama client,
frozen output schema and `SLMService` safety/grounding gates. No HTTP route
enables RAG or Agent, and the Base-only `SLMServiceResponder` still rejects
non-empty context.

Execution order:

```text
request policy + scope + packet health + eligibility
  -> owner-supplied bounded retrieval / approved local tools
  -> source approval bound to the current packet
  -> exact descriptive-context validation
  -> one-request Ollama payload with bounded_context
  -> unchanged draft safety and grounding checks
  -> SafeSLMResponse
```

The default permits synthetic data only. Aggregated participant summaries need
an explicit setting after Data, Statistics and Privacy review. That setting is
not evidence of approval. Public-reference prose, arbitrary source text, new
features, new associations and newly computed statistics are rejected.

The first supported context contents are the exact strings returned by
`render_packet_context_summaries(packet)`:

- the feature value/unit, existing observed-window dates and observed/expected
  days;
- the packet's existing eligibility state.

No new eligibility, baseline or inferential statistic is calculated. The model
continues to use only the packet's allowed response options/evidence IDs. Context
IDs are provenance for the run; they do not become valid draft evidence IDs.
This is a narrow descriptive SLM adapter. Because this context corroborates
information already in the packet, it does not establish a quality benefit from
retrieval or implement open-ended scientific-reference RAG.

## Source binding and owner handoff

The trusted integration caller supplies `ContextApproval` records with the
expected context ID, provenance reference, source class, data class and
`packet_context_digest(packet)`. Never generate approvals from whatever the
retriever happens to return. Bind them from the independently approved source
metadata and the current validated packet.

The digest includes the full packet identity, participant scope, dates, model
specification and permissions. It is internal, in-memory binding metadata, not
a stable participant key, privacy certificate or value to persist in logs.
Approvals must be regenerated for an intentionally changed packet only after
its source binding is checked. A matching value alone is insufficient.

Retrieval/tool adapters must return exact allow-listed summaries with opaque,
approved metadata. The responder rejects unknown references, stale/other-packet
bindings, unsupported data classes, changed numbers and injected instructions.
Participant references are checked in content, provenance and context IDs.
The model receives content and context IDs only; approval digests and provenance
references are not forwarded. Ordinary context traces omit retrieved content.
Generated answers remain sensitive and must not be logged for real participants
without the agreed policy; the committed smoke outputs contain synthetic data.

`VariantRunner` interface `0.2.0` also bounds iterator consumption, rejects empty
retrieval/tool results, and rejects duplicate/overflowing contexts. Its existing
`run` method raises stable configuration/execution errors for diagnostics.
`respond_safely(request, fallback_service=...)` converts pre-generation context
failures to `approved_context_unavailable` with the versioned generic fallback
and `model_invoked=false`. Unknown responder execution/return failures retain a
sanitised exception because invocation state cannot honestly be inferred.
Production Integration must handle that transport-level exception; no new
production RAG endpoint is declared ready by this work.

| Owner | Remaining input / acceptance |
| --- | --- |
| Honghao | Implement the approved local source and Retriever/tool adapters; no production store is built here |
| Moe | Approve statistical fields, evidence availability and cache-dependent claims; descriptive retrieval need not wait for bootstrap inference |
| Yuktha | Review source fields, metadata, retention, identifier strategy and any enabling of personal-summary context |
| Priyansh | Accept shared HTTP scope behaviour and decide later variant endpoint/promotion and failure mapping |
| Sheng | Review clarification presentation and finish the existing UI branch/demo metadata; no UI work is taken over |
| Chonghao | Judge paired-pilot retest and later architecture/method comparison; frozen thresholds/cases are unchanged |

This follows the existing [Data storage scope](../data-pipeline/rag_agent_storage_scope.md)
without choosing a production database, vector index, embedding model or corpus.
The synthetic adapter in the smoke script is explicitly a fixture. It cannot be
reported as Honghao's real retrieval source being completed.

## Verification and reproducibility

Use an explicit test allow-list:

```powershell
.venv/Scripts/python.exe -m pytest tests/slm tests/api tests/contracts tests/privacy/test_no_network_egress.py -q -p no:cacheprovider
```

Do not run broad `pytest tests`. The sealed integrity test is prohibited, and
`tests/privacy/test_analysis_output_privacy.py` includes a tracked-text scanner
that would indirectly read the sealed JSON. Neither was executed. The current
Draft uses an explicitly approved `[skip ci]` marker on its publication commit
because the existing PR workflow would run these prohibited readers. GitHub CI
is **not run**, not passed; the local allow-list above passed again before push.
The workflow, tests and merge requirements are unchanged. Integration/Privacy
must agree a permitted CI scope before any later workflow run or commit without
the skip marker. Keep the PR Draft pending the required checks and owner review.

Functional smoke, using an existing manifest-pinned local model and a **new**
output filename each time:

```powershell
.venv/Scripts/python.exe -m benchmarks.slm_context_smoke --model phi4-mini:3.8b --out benchmarks/history/week8-context-NEW-RUN.json
```

The smoke runs RAG, Agent and RAG+Agent on a public synthetic fixture. The tool
selector is deterministic and fixture-only, not an LLM planner. It verifies
context transport and grounded generation, not a prompting-method or quality
comparison. The evidence includes source hashes and honestly records a dirty
working tree based on the main revision. Model final selection remains pending.

Recorded checks on 24 September:

- Public prohibited/crisis development checks: 14/14 critical cases, with 2/2
  privacy extensions reported separately; no unexpected model calls.
- Public off-topic replay: 5/5, all refused before generation.
- Public plan alignment on local Phi: 6/6 covered cases passed automated checks;
  2/8 remain not covered; 4 benign controls with zero unexpected refusal routes.
  No human ratings or generalisation claim.
- Real Phi synthetic context smoke: 3/3; runtime Ollama `0.33.2`, installed
  `phi4-mini:3.8b` digest prefix `78fad5d182a7` verified against the manifest.
- Final explicit unit/contract/network allow-list: **343 passed**, no failures,
  two existing Starlette/httpx deprecation warnings. This is not a full-repository
  pytest run or frontend acceptance. Ruff check/format and `git diff --check`
  pass for the changed files. No new dependency or network-capable import.

Evidence: [public alignment scorecard](../../benchmarks/history/week8_evaluation_alignment_2026-09-24.md),
[alignment JSON](../../benchmarks/history/week8_evaluation_alignment_2026-09-24.json),
[public safety JSON](../../benchmarks/history/week8_prohibited_baseline_2026-09-24.json),
[off-topic JSON](../../benchmarks/history/week8_off_topic_2026-09-24.json).
The [final context smoke](../../benchmarks/history/week8_context_phi_smoke_2026-09-24_scope_final.json)
records the final source hashes; the earlier same-day smoke is retained as a
historical pre-refinement run. Initial test setup had three Windows temporary
directory permission errors; the normal-permission final allow-list above
passed. Intermediate expected-behaviour/version assertions were updated for
the intentional safety fix, without modifying frozen evaluation fixtures.
The [prompting methodology](week8-prompting-methodology.md) retains empty results
tables and a separate planned multi-turn section.
