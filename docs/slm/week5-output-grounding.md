# Week 5 Output Grounding Amendment

Owner: Richard Zhao, SLM Integration. Date: 4 September 2026 (Australia/Sydney).
Status: implemented and locally verified; Week 5 PR #2 peer review pending.
Versions: output grounding 0.1.1; evidence prompt 0.4.8; request policy 0.1.1.
No shared EvidencePacket/SafeSLMResponse schema change, new dependency, or final model selection.

## What was fixed

The cross-role audit reproduced two unsafe acceptances with test doubles, not
real model misconduct: a GPS value of 999 instead of supplied 3.8, and a State B
response claiming 80% above baseline while also saying "too early to compare".

The runtime safety gate now calls backend/slm/output_grounding.py before a
State B/C explanation can reach SLMService's final response. This is production
validation, unlike the earlier benchmark-only content checks.

- Bind current and baseline numeric slots separately to the packet using exact
  decimal equality, not presence in an unordered set or approximate tolerance.
- Bind the measured feature and unit through an explicit allowlist. Never
  interpolate arbitrary upstream labels or infer a unit conversion.
- Require the corresponding declared AND approved claim IDs and an evidence
  reference. Metadata alone never makes unsupported text acceptable.
- State C accepts two explicitly bounded English comparison sentence forms,
  both with current/baseline values, units and the fixed uncertainty statement.
- State B accepts only its current value and a no-comparison statement. A
  permitted uncertainty-mode variant must also include uncertainty wording
  and its claim ID. No baseline value or StatisticalEvidence may be present.
- Unsupported extra sentences, percentages, directions, wellbeing conclusions,
  numbers written as words, wrong units, swapped values and hidden characters
  fail closed. ASCII case/whitespace and equal decimal representations may vary.
- Non-finite/negative measurements, missing comparison baseline/evidence, or
  unknown feature/unit combinations fail closed.
- A model-selected refusal cannot bypass output validation; refusal, crisis and
  State A responses remain deterministic service-owned paths.

The model still generates AssistantDraft. No rejected draft is silently repaired
or replaced with a fabricated successful model answer; the service returns its
versioned generic fallback. Synthetic test generators use a rendering helper,
but the real model is not replaced by that helper.

## Deliberate scope and trade-off

This is a small controlled-language explanation surface, not general English
semantic validation or open-ended counselling. The two measured features are
unlock_count and gps_distance. Explicit supported unit mappings include
count_per_day/count and kilometres_per_day/km_per_day/km; the current public
live fixtures use per-day units. Unknown units fail rather than being guessed.

For example, the primary State C construction is:

> Your GPS distance was 3.8 kilometres per day, compared with your own baseline of 4.6 kilometres per day. This estimate is uncertain and should be interpreted cautiously.

State B:

> Your phone unlock count was 18 unlocks per day in the observed window. It is too early to compare with your own baseline.

A correct but unrecognised paraphrase may fall back. Broader conversational
usefulness needs human review and explicit, tested extensions; do not weaken
numeric bindings merely to improve a development score. Successful copying of
these constrained sentences does not establish general model quality or favour
Phi over Qwen.

State A bypasses generation in SLMService. Consumers must use the service,
not treat an isolated legacy metadata check as a complete application boundary.
Input schema validity is not proof of a real fitted model or statistical eligibility.

## Tests and preserved real runs

Before the fix, the first 59 focused tests produced 43 failures and 16 passes,
including both original audit counterexamples. After implementation and six
additional sentence-variant checks, all 65 focused tests pass.

Full suite: 265 passed, 8 skipped, no deselections or failures. Five skips require
real CES and three require the frontend environment. All 26 Python files in the
complete Week 5 delta pass Ruff/format; the earlier fix-only scope had 13 files.
Shared statistics code, evidence contract, evaluation
plan, registered thresholds and original 16-case fixture are unchanged.
The synthetic integration-test helper was updated to emit real bound values and
appropriate State B claim IDs; it no longer declares an unsupported association.
This does not turn that test into real data fitting, HTTP or UI acceptance.

Existing failed and successful snapshots were not overwritten:

| New snapshot in benchmarks/ | Versions | Outcome |
|---|---|---|
| slm_grounding_alignment_results.json / scorecard.md | Prompt 0.4.6, grounding 0.1.0 | 3/6 executable plan checks; three correct-looking replies rejected for missing claim metadata |
| slm_grounding_prompt047_results.json / scorecard.md | Prompt 0.4.7, grounding 0.1.0 | 5/6; one safe two-sentence paraphrase rejected by the original narrow grammar |
| slm_grounding_prompt048_results.json / scorecard.md | Prompt 0.4.8, grounding 0.1.1 | 6/6 executable plan checks; Q2/Q8 still not run |
| slm_grounding_shadow_smoke_results.json | Prompt 0.4.8 | 4/4 real-service paths |
| slm_grounding_phi_regression_results.json | Prompt 0.4.8 | 3/3 eligible, State B and refusal paths; Phi only |

The source-plan exports also preserve all 14 registered high-severity and two
privacy-extension checks, passed separately, with zero unexpected model calls.
They retain full synthetic service responses, source hashes, versions and blank
Richard/Chonghao/resolution fields. No joint scores or disagreements are invented.
No soft/off-topic tier was assessed. These public cases were used during
development; none of these scores is held-out or independent final validation.

The existing loopback Ollama 0.33.2 and pre-installed Phi digest prefix
78fad5d182a7 were used. No package/model was downloaded. Qwen was not rerun.
No participant data or sealed prompts were sent to a model. Existing automated
sealed integrity/structure checks are distinct from opening prompts for tuning.

## Reproduction and handoff

Run from the repository root with the existing environment:

    python -m pytest tests/slm/test_output_grounding.py -q
    python -m pytest -q
    python -m benchmarks.slm_evaluation_alignment --model phi4-mini:3.8b --out benchmarks/local_grounding_rerun.json --scorecard benchmarks/local_grounding_rerun.md

Use new result filenames; never overwrite prior evidence. The live alignment
export records output-grounding version and the grounding source hash, alongside
the prompt/request-policy versions and the dirty-worktree state.

Moe/Data/Integration must still confirm 7-day recent, 14-day PHQ-4 and prior
28/56-day baseline semantics and any missing provenance fields. Existing 28-day
synthetic feature windows remain legacy contract examples, not proof of that
production pipeline. No shared schema is changed here. Q2/Q8 remain uncovered.

Priyansh/Sheng should display only the final SafeSLMResponse and agree State A/B
versus eligible uncertainty mapping. Chonghao reviews the original eight-question
mapping and rates actual versioned answers independently. Yuktha/peer review and
participant-use approval remain outstanding. Honglin should use the updated SLM
Proposal input; the shared outline's old "no real-machine benchmark" statements
need correction by its owners, not an unannounced edit in this SLM amendment.

## Publication boundary

This amendment and the preceding evaluation alignment belong to the existing
Rz-week5 / PR #2 delivery. Historical result files preserve their execution-time
HEAD and dirty-worktree metadata, including runs based on 0cf49cf with local
changes. Week 4 branch/history/PR #1 remain unchanged. Publication is not
joint acceptance or approval to merge.

Before any push, show the exact Week 5 diff and checks and obtain the user's
separate confirmation. Only reviewed English technical artifacts belong in Git.
Private meeting notes in either language, any new Chinese content, participant
records, model weights, secrets and OneDrive working copies must not be staged.
