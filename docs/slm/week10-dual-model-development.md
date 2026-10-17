# Week 10 dual-model development evidence

Date: 18 October 2026. Scope: SLM integration development evidence for
`phi4-mini:3.8b` and `qwen3:4b`. Human quality ratings remain unassessed.

## Week 10 local delivery status after the safety repair

The new policy 0.3.5 repair passes **20/20 fixed development cases on each
model**, improving from 11/20 on each model without changing the cases or
behavioural expectations. It made three genuine ordinary-feature model calls
per model; all crisis/diagnosis requests in that set stopped before data/model
access. There are 691 distinct passing engineering tests. See the
[repair, provenance and limitations](week10-safety-development.md).

| Original work item | Local evidence now available | Remaining boundary |
| --- | --- | --- |
| Guardrail/response quality fixes | Scoped policy 0.3.5 repair and both-model development regression | Formal independent safety acceptance remains open; the prior formal failure record is unchanged. |
| Zero-shot/few-shot comparison | Retained Phi run plus the Qwen extension below | No new human quality ratings or supported superiority claim. |
| Standalone multi-turn experiment | Both models have the existing six-scenario benchmark results | Known 14/15 and 13/15 results remain; the experiment is not promoted into the app or relabelled as fully passing. |
| Cross-message leakage review | Existing synthetic checks and both-model numeric-leakage results; current API isolation tests pass | Automated checks do not constitute a new joint human privacy sign-off on this repair. |
| Four architecture variants | Retained paired Phi/Qwen development evidence | Historical versions remain explicit; no rerun or new human acceptance is claimed. |

The local technical work is prepared for review. Formal acceptance, outstanding
human review and publication are separate gates, so this document does not mark
every Week 10 acceptance requirement complete. The repair did not change
existing prompts, model defaults, API, statistics, privacy logic or workflows.

## Evidence coverage and attribution

| Work item | Phi evidence retained | Qwen evidence | Attribution and limit |
| --- | --- | --- | --- |
| Four architecture variants | 6 October: 264 executed, 24 not covered, 36 model calls | 9 October: the same execution counts | Richard's existing comparison; no rerun. Packet-summary retrieval and constrained answers do not establish a RAG/agent advantage. |
| Zero-shot/few-shot (Base) | 9 October: 168 executed, 12 not covered, 24 model calls; 84 identical Z/F pairs | New 18 October run: matching counts, all automated checks pass, 84 identical Z/F pairs | Original method and Phi evidence retained; the new adapter extends the fixed method to Qwen. Different source versions prevent a controlled cross-model superiority claim. |
| Standalone multi-turn | 16 October: stateless 14/15, bounded history 13/15, no detected foreign-number leakage | New 18 October run: stateless 14/15, bounded history 13/15, no detected foreign-number leakage | The existing harness was implemented by Integration/QA from the prior method plan. This contribution adds the Qwen run and its provenance, without claiming authorship of that harness. |
| Final safety acceptance | PR #91 reports a failed Phi v2 run | No Qwen v2 run identified in that PR | Development checks do not substitute for final safety acceptance. |

Historical references: [variant comparison](week9-variant-quality-comparison.md),
[prompting methodology](week8-prompting-methodology.md),
[final SLM methodology](final-slm-methodology.md).

## New Qwen runs

Both runs used application source
`90930308c00cf5edbc565bcd6bac7d7f44590372`, Ollama 0.33.2,
request policy 0.3.4 and Qwen digest
`359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
The installed Phi digest was also checked:
`78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753`.
Neither the application configuration nor existing prompts, tests, policies or
team-maintained files were changed. The new adapter and its protocol were local
uncommitted additions when the runs were executed; the base SHA alone is not the
adapter version.

The [protocol](../../benchmarks/fixtures/week10_qwen_completion_protocol.json)
was saved before generation. The
[adapter](../../benchmarks/slm_week10_qwen_completion.py) validates the original
Z/F controls, changes only the model and experiment identifier in memory, and
uses the existing public synthetic fixtures. It invokes the original multi-turn
harness with Qwen, retaining each completed turn in an append-only local journal.
No held-out prompts or CES participant records were inputs to either run.

| Measure | Z | F |
| --- | ---: | ---: |
| Executed records | 84 | 84 |
| Not covered | 6 | 6 |
| Source-plan automatic checks | 18/18 | 18/18 |
| High-severity development checks | 42/42 | 42/42 |
| Privacy-extension checks | 6/6 | 6/6 |
| Off-topic checks | 15/15 | 15/15 |
| Supplemental State B | 3/3 | 3/3 |
| Model calls; schema/grounding accepted | 12; 12/12 | 12; 12/12 |
| Unexpected fallback / execution error | 0 / 0 | 0 / 0 |
| Benign unexpected refusals | 0/15 | 0/15 |

Three repetitions are repeated observations of fixed public cases, not new
independent cases. Source-plan Q2 and Q8 remain not covered. No response benefit
from these two demonstrations was observed under the constrained output method.
Human quality scores were not supplied and were not inferred from these checks.

| Multi-turn measure | Stateless | Bounded history |
| --- | ---: | ---: |
| Turns meeting every existing check | 14/15 | 13/15 |
| Feature-bound answers quoting the current value | 11/11 | 9/9 |
| Turns with detected foreign numbers | 0 | 0 |
| Clarification requests | 0 | 3 |
| `Cache-Control: no-store` | 15/15 | 15/15 |

The multi-turn run made 20 model calls. The existing scenario checks measure
selected numeric leakage, routing and value binding; zero detected numbers is
not a comprehensive privacy sign-off. Bounded history remains confined to the
benchmark. The application remains stateless.

## Local provenance and verification

Full responses, per-case journals and runtime records remain under ignored,
owner-only `outputs/week10-development/`. They are not part of this document.
No selective retry, discarded warm-up or replacement of failed turns occurred.

| Artifact | SHA-256 |
| --- | --- |
| Qwen prompting result | `6fbf9229dcc5b9bf2091f2c5e91419ffafa00950528822b802ec186baed4602c` |
| Qwen multi-turn result | `b68968527b6feb3c5994cfcf2fad046e6575906d7f327d2991585297bd3dd320` |
| Adapter bytes executed for both runs | `2045736fcec1527e194b7fdaf2279db91eba72dbbed8ee91092e357e1182ad48` |

The exact executed adapter is retained as `executed-adapter.py` beside each
local result. The working copy subsequently received formatting/import sorting
and the equivalent Python `UTC` alias cleanup; experiments were not rerun for
those changes. Original source hashes, complete journals, actual Qwen model
tags, blank human fields and owner-only file permissions were verified.
Two focused adapter tests use a fake transport to verify unchanged condition
controls and actual Qwen selection. They generate no model answers.

Reproduction entry points (do not rerun completed evidence by default):

```powershell
.venv/Scripts/python.exe -m pytest --confcutdir=tests/slm tests/slm/test_week10_qwen_completion.py -q
.venv/Scripts/python.exe -m benchmarks.slm_week10_qwen_completion preflight
# Each execution refuses an existing fixed output directory:
.venv/Scripts/python.exe -m benchmarks.slm_week10_qwen_completion prompting
.venv/Scripts/python.exe -m benchmarks.slm_week10_qwen_completion multiturn
```

## Separate final-safety evidence

[PR #91](https://github.com/PriyanshUsyd/mindsense-capstone/pull/91), open at
review time, supplies a 24-question v2 set and Moe Tanaka's Phi run on the same
application SHA and policy 0.3.4, using Ollama 0.40.2. The hash commitment is in
commit `e1be94209998d86e6e54f677b187e0a90c92c654`, before the reported run.
The remote prompt bytes match
`3cdc2ae11ccf71a535999ee8daeb419c2d2b19261f1b49d9e9c46597ea64264e`.

That PR reports critical safety **15/19 (fail)**, off-topic **2/2**, and
in-scope controls **3/3**. It contains no Qwen result. Those are the operator's
reported results, not a new Richard execution or independent personal rating.
The v2 set is already used on Phi. It was not executed here, and passing the
public development checks above does not resolve the reported safety failures.
