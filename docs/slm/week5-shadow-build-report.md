# Week 5 SLM Shadow Build Report

**Owner:** Richard Zhao — SLM Integration Lead  
**Date:** 1 September 2026 (Australia/Sydney)  
**Branch:** `Rz-week5` (local only; not pushed)  
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

The 16/16 result meets the pre-registered 100% high-severity threshold for
this provisional public development subset. It is **not** Chonghao's final
suite, a joint human judgment result, or the Week 11 held-out evaluation.

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
- Prompt `evidence_explainer` is now v0.4.3. The payload exposes the exact
  allowed evidence IDs, and the prompt requires an explicit uncertainty
  sentence and prohibits unsolicited clinical referral language.
- The deterministic output gate now verifies the uncertainty text itself; it
  does not trust only the model's Boolean declaration. It also rejects
  unsolicited directions to consult a clinician and enforces State B's
  insufficient-history disclosure.

No new Python dependency was added.

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

- Focused SLM plus evidence-flow suite: 85 passed.
- Full repository pytest: 168 passed, 8 skipped; the sole raw run failure is
  the already documented Windows CRLF checksum mismatch for the sealed prompt
  file. The sealed prompts were not used for model evaluation.
- Ruff passes on every changed Python file. A repository-wide Ruff scan still
  reports 10 pre-existing findings in Data/contract/frontend/statistics test
  files outside this SLM change.
- `git diff --check` passes.

## Remaining team-owned acceptance

1. Priyansh/Integration should review the runtime interface and own the
   FastAPI wrapper and endpoint acceptance contract; this branch deliberately
   does not edit `backend/api/`.
2. Sheng should integrate the UI through the agreed API, not by depending on
   SLM internals.
3. Chonghao and Richard still need to run Chonghao's final non-held-out Week 5
   suite together and record 2–3 human-judgment disagreements.
4. The crisis trigger taxonomy and participant-facing wording need Evaluation,
   client, and applicable study-governance approval before any human pilot.
5. Moe/Priyansh should confirm the cold-start/evidence contract and versioning
   process. The fixtures here are synthetic contract consumers, not real
   statistical output.

