# Week 5 SLM Shadow Build Report

**Owner:** Richard Zhao — SLM Integration

**Last verified:** 4 September 2026 (Australia/Sydney)

**Branch:** `Rz-week5`; depends on the unchanged Week 4 PR #1

**Model status:** `comparison_pending` — Phi baseline, Qwen challenger

## Scope and current status

This Week 5 shadow build provides a real, UI-independent response path from a
validated `EvidencePacket` to either a validated local-model response or a
deterministic safe response. It uses synthetic fixtures only and does not read
CES, raw sensing, participant-level PHQ-4, the Week 11 sealed prompts, or any
external model API.

| Required path | Result | Model invoked? |
|---|---|---:|
| Eligible synthetic GPS evidence, normal question, Phi baseline | `normal`; validated response | Yes |
| State A / missing data | deterministic `insufficient_data` template | No |
| Diagnosis-seeking question | deterministic `refusal` | No |
| Crisis/self-harm language | Australia-specific `crisis_aware_fallback` | No |
| Public prohibited-request development subset | 16/16 passed | No |

The 16/16 result comprises 14 registered high-severity cases and two privacy
extensions; report those groups separately. It is **not** Chonghao's confirmed
Week 5 suite, a joint human judgment result, or the Week 11 held-out evaluation.

### Evaluation-alignment amendment

The [evaluation alignment](week5-evaluation-alignment.md) now explicitly uses
Chonghao's existing eight-question plan. Six questions run; PHQ-4 comparison
and positive behavioural-wellbeing association remain uncovered pending a
shared contract extension. Policy 0.1.1 fixes the exact Q5 diagnosis question;
Prompt 0.4.8 requires feature-specific numerical baseline comparisons. Earlier
incomplete model outputs are preserved alongside the final 6/6 developer
checks, 14/14 high-severity and 2/2 privacy extension checks. All human ratings
remain blank. These changes form part of the Week 5 PR #2 amendment, not
a claim of completed joint acceptance.

## Implementation

- `backend/slm/request_policy.py` adds versioned, deterministic request
  routing for crisis language, diagnosis, causal inference, treatment advice,
  risk prediction, prompt injection, and sensitive-data requests.
- `SLMService` applies request routing before generation. Crisis and refusal
  responses therefore do not rely on the model recognising the unsafe input.
- State A missing-data packets use a versioned deterministic template and do
  not call the model. State B remains descriptive-only and must explicitly say
  that it is too early to compare.
- `backend/slm/runtime.py` creates a loopback-only service for a model tag that
  is present in `model_manifest.yaml`.
- `python -m backend.slm.shadow_cli` provides the UI-independent executable
  path. It accepts a validated packet file and question and prints the audited
  response JSON.
- Prompt `evidence_explainer` is now v0.4.8 (earlier `0cf49cf` snapshot: v0.4.3). The payload exposes the exact
  allowed evidence IDs, and the prompt requires an explicit uncertainty
  sentence and prohibits unsolicited clinical referral language.
- The deterministic output gate now verifies the uncertainty text itself; it
  does not trust only the model's Boolean declaration. It also rejects
  unsolicited directions to consult a clinician and enforces State B's
  insufficient-history disclosure.

No new Python dependency was added.

The [output-grounding amendment](week5-output-grounding.md) closes the two
additional audit gaps in the runtime gate: invented/misbound values and State B
comparisons hidden behind disclaimers. Grounding 0.1.1 binds values, feature,
units and claims to a bounded English grammar; unsupported wording falls back.
This deliberately limits conversational variety and is not a universal semantic
validator. Model-selected refusal cannot bypass the service-owned safety route.

### 4 September delivery hardening

- The transport rejects redirects as well as non-loopback endpoints and
  disables environment proxies. Synthetic loopback-server tests cover HTTP
  301, 302, 303, 307, and 308 without following the redirect.
- The model payload replaces `identity.participant_ref` with `redacted`
  without modifying the service's original evidence packet. Free-text
  questions and other contract identifiers still require caller-side
  minimisation; this is not a general anonymisation system.
- `benchmarks/slm_shadow_smoke.py` provides a reproducible four-path smoke
  command; its tests detect an unavailable model rather than counting a
  generic fallback as a successful real-model explanation.
- The Windows working copy of the sealed file was restored byte-for-byte
  from the already-sealed Git blob after checking both hashes. No prompt,
  recorded checksum, test logic, or Week 4 commit was changed.
- A separate [privacy spot-check](week5-dependency-privacy-review.md) and
  [integration/evaluation handoff](week5-integration-evaluation-handoff.md)
  accompany this Week 5 delivery. They do not claim retrospective approval
  of PR #1, which remains unchanged.

## Reproducible local evidence

### Happy path

```powershell
python -m backend.slm.shadow_cli `
  --packet tests/slm/fixtures/week5_gps_eligible.json `
  --question "How was my movement different from my recent baseline?" `
  --model phi4-mini:3.8b
```

The verified run returned `response_mode=normal`, `used_fallback=false`,
`model_invoked=true`, and no rejection. It correctly described synthetic GPS
distance as 3.8 km/day versus a 4.6 km/day baseline and explicitly said that
the estimate was uncertain and should be interpreted cautiously.

### Missing-data path

```powershell
python -m backend.slm.shadow_cli `
  --packet tests/slm/fixtures/week5_gps_missing.json `
  --question "How was my movement different from my recent baseline?" `
  --model phi4-mini:3.8b
```

The verified run returned `response_mode=insufficient_data` and
`model_invoked=false`; it did not guess or compare without a baseline.

### Prohibited-request baseline

```powershell
python -m benchmarks.slm_prohibited_request_baseline
```

Result: 16/16 passed, zero unexpected model calls. The machine-readable cases
and result are in `benchmarks/fixtures/week5_prohibited_requests.json` and
`benchmarks/slm_prohibited_request_baseline_results.json`.

## Phi/Qwen smoke comparison

The one-repetition Week 5 smoke result is stored in
`benchmarks/slm_model_comparison_week5_smoke_results.json`:

- Phi: 3/3 deterministic quality checks passed.
- Qwen: 1/3 passed. The eligible normal case failed safe because the model did
  not set the required uncertainty declaration; the partial-history case
  failed safe because it omitted the required insufficient-history wording.
- The diagnosis case was deterministically refused before either model ran.

This small, one-repetition smoke test does not justify final model selection.
Phi remains the baseline and Qwen remains the challenger.

## Verification

Current amendment: **265 passed, 8 skipped**, no failures/deselections,
reconfirmed before publication on 4 September. All 26 Python files in the
complete Week 5 delta pass Ruff/format. The suite includes 65 new
output-grounding regressions. Real Phi alignment checks
pass for all six executable source questions; the other two are not scored.
Four-path smoke remains 4/4 and the Phi eligible/State B/refusal regression
remains 3/3. Full results and the initial unsuccessful content checks are
linked from the output-grounding amendment, including strict-gate failures at
Prompt 0.4.6/0.4.7 and the current 0.4.8 run. No Qwen rerun or final selection is claimed.

The following is the earlier published `0cf49cf` verification record:

- Full repository pytest: 179 passed, 8 skipped, zero failures and no
  deselections after restoring the canonical LF working copy.
- Focused SLM/evidence-flow suite: 95 passed. The eight full-suite skips are
  five real-CES integration checks (dataset absent from this checkout) and
  three frontend checks (npm/dependencies unavailable to the test process).
  They are not completed data/UI integration tests.
- Four-path real Phi smoke: 4/4 passed on 4 September. The evidence case
  returned `normal`; the contract also permits `uncertainty`, so an eligible
  reply is not required to repeat identical text or mode on every run.
- Replay with `python -m benchmarks.slm_shadow_smoke`; the committed snapshot
  is `benchmarks/slm_shadow_smoke_results.json`. It uses only the public
  synthetic fixtures, not CES or sealed prompts.
- Ruff passes on every changed Python file. A repository-wide Ruff scan still
  reports 10 pre-existing findings in Data/contract/frontend/statistics test
  files outside this SLM change.
- Complete Week 5 whitespace validation against `7d33de4` passes, rather
  than checking only an empty uncommitted diff.

## Remaining team-owned acceptance

1. Priyansh/Integration should review the runtime interface and own the
   FastAPI wrapper and endpoint acceptance contract; this branch deliberately
   does not edit `backend/api/`.
2. Sheng should integrate the UI through the agreed API, not by depending on
   SLM internals.
3. Chonghao and Richard still need to confirm and run the non-held-out Week 5
   suite based on his existing plan and record genuine judgments/disagreements;
   do not invent 2–3 examples if no disagreements occur.
4. The crisis trigger taxonomy and participant-facing wording need Evaluation,
   client, and applicable study-governance approval before any human pilot.
5. Moe/Priyansh should confirm the cold-start/evidence contract and versioning
   process. The fixtures here are synthetic contract consumers, not real
   statistical output.
