# Week 9 public four-variant quality comparison

Owner: Richard Zhao, SLM Integration  
Protocol: `week9-public-variant-quality-1`  
Date: 6 October 2026  
Status: Technical protocol; independent human review required

## Scope and decision

This continues the Week 7 architecture comparison and closes the technical
evidence gap raised during Week 8. Week 9 also requires a reproducible SLM and
Prompt configuration and actual evaluation evidence for the Progress Report.
This protocol supplies exact responses for developer rubric review. It does not
record an ME-P02 session or replace the ten-dimension participant questionnaire.

The four implementations are Base LLM, RAG, Agentic and RAG+Agent. The current
retriever supplies two canonical summaries of the current EvidencePacket. The
agent uses the existing deterministic, bounded packet-summary tool. These are
not an independent historical corpus or an autonomous multi-step planner.
Identical responses are a legitimate result and cannot demonstrate an advantage
of retrieval or agent reasoning.

The public synthetic developer scope follows the existing
[response rubric](../evaluation/response-quality-rubric-v0.1.md). A live local
model run is distinct from a fake-transport test, but neither establishes
generalisation to real participants. No CES rows or sensitive personal summaries
are loaded. No sealed prompts or integrity test are accessed.

## Fixed conditions, declared before execution

- Use `phi4-mini:3.8b`, installed digest prefix `78fad5d182a7`, as the baseline
  candidate. This is not a final model-selection decision. Do not compare models
  and architecture effects within this run.
- Keep generation Prompt `0.4.13`, request policy `0.3.1`, grounding `0.1.1`,
  EvidencePacket `1.0.0`, temperature `0`, seed `42`, and a 180-second call timeout.
  Record raw-byte hashes of the protocol, implementation, mapping, fixtures,
  prompts and applicable evaluation documents.
- Reuse the original eight plan questions and unchanged public mapping in
  `benchmarks/fixtures/week5_evaluation_alignment.json`. Q2 (PHQ-4 change) and
  Q8 (positive association) remain **Not covered**; do not invent new evidence.
- Include the unchanged 14 high-severity and two privacy-extension cases from
  `benchmarks/fixtures/week5_prohibited_requests.json`, reporting each group
  separately. Q1 and Q7 share one unlock fixture; repeated wording is not
  independent evidence coverage.
- Run three repetitions of every case in every architecture. Rotate block order
  from Base/RAG/Agent/RAG+Agent, then RAG/Agent/RAG+Agent/Base, then
  Agent/RAG+Agent/Base/RAG. Three rotations are not a fully balanced latency
  experiment. There are 288 planned records: 264 executed and 24 Not covered;
  36 expected generation calls, with deterministic handling for the remainder.
- Use a fresh packet-bound runner for every response and the existing production
  policy, safety and grounding gates. Verify the actual model payload receives
  zero, two, two or four context IDs, respectively, on generation-eligible cases.
- Do not warm up by discarding a result. Preserve the first actual generation
  separately, plus individual subsequent timings and Ollama metrics. Timings
  cover the runner, not HTTP, CES construction, UI or human time. Do not derive a
  statistical latency ranking from this small run.
- Retain every failure and repetition. Do not rerun selectively or change cases,
  thresholds, product prompts or response policy after inspecting results.

## Execution and outputs

From the repository root, with Git and the installed Ollama executable on PATH:

```powershell
.\.venv\Scripts\python.exe -m benchmarks.slm_variant_quality --model phi4-mini:3.8b --out benchmarks/history/week9_variant_quality_phi_2026-10-06.json --scorecard benchmarks/history/week9_variant_quality_phi_2026-10-06.md
```

Both output paths must be new. The JSON is checkpointed after each complete
variant block and preserves source hashes, Git head and dirty status, runtime
metadata, config, full synthetic packets, exact user-facing responses, model
metrics, context provenance and tool traces. A `running` status is incomplete
evidence, never a completed evaluation. Source hashes distinguish local changes
from the recorded Git head; a dirty tree must not be described as a clean commit.

The Markdown scorecard groups identical repeats for readability; the JSON keeps
each individual record. Automated success means the existing routing and selected
faithfulness checks passed, including the actual variant-context check. It is not
a complete human quality pass. The CLI exits nonzero on failed automated checks.
Transport-injected unit tests are explicitly labelled as non-live evidence.

The historical `slm_variant_comparison` CLI remains the original dependency-status
harness. This configured entry point is the one to use for the current packet
implementations; historical results are not rewritten.

## Independent review and completion criteria

Richard and Chonghao independently record Pass/Fail/N/A with reasons against all
seven requirements in the existing rubric, then lock their judgments before
discussing disagreements. If repeats differ, rate each distinct response and
identify its run IDs. Never let one favourable repeat hide a failure. Keep the
original run output immutable and retain separately attributable review records.

Report standard quality, high-severity safety and privacy extensions separately.
Use the locked 90% standard and 100% high-severity thresholds from
[pass-threshold.md](../evaluation/pass-threshold.md). Exclude Not-covered cases
from denominators and identify shared fixtures. Repetitions are a stability check,
not additional independent cases. Human ratings and joint decisions stay
`NOT ASSESSED` until their actual reviewers supply them.

Technical completion requires reproducible live outputs, complete provenance,
trace checks, preserved failures and a usable review package. The quality task is
not fully closed until independent reviews and disagreement resolution are
recorded. ME-P02 remains a separate Richard/Sheng session under the
[session runbook](../evaluation/team-session-runbook-v0.1.md), with questionnaires,
responses and screenshots; record the architecture actually used in that session.

## Prompting-method documentation boundary

Zero-shot versus few-shot remains methodology documentation only, as required
for Week 8. Running current architectures under the unchanged production prompt
does not authorise a prompt-method experiment.

### Planned multi-turn method

Keep multi-turn as a separate planned method in
[the Week 8 methodology document](week8-prompting-methodology.md). This run contains
independent single-turn requests with fresh packet binding and no conversation
memory. Multi-turn execution, prompt changes and associated evaluation require
their own agreed scope and are not included here.
