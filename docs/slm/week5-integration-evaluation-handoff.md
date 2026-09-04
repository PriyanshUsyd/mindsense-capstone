# Week 5 SLM Integration and Evaluation Handoff

- Contributor: Richard Zhao, SLM Integration
- Date: 4 September 2026 (Australia/Sydney)
- State: local developer deliverables ready for review; joint acceptance pending.
- Branch: `Rz-week5`, based on unchanged Week 4 commit `7d33de4` / PR #1.

## What is ready

The service runs without the full chat UI. The repository contains a local
model client, versioned prompts, request routing, output validation, the two
fallback templates, a deterministic missing-data response, synthetic fixtures,
developer safety tests, and an English Proposal contribution.

| Path | Expected response mode | Model call |
|---|---|---|
| Eligible synthetic GPS evidence | `normal` or `uncertainty` | Yes |
| Missing baseline/window | `insufficient_data` | No |
| Recognised diagnosis request | `refusal` | No |
| Recognised crisis/self-harm request | `crisis_aware_fallback` | No |

English rule matching is a limited development guardrail, not a validated
clinical detector. Passing the current cases does not establish coverage of
every paraphrase, language, or adversarial request.

## Reproduce the developer checks

Use the existing project environment and pre-installed Ollama models. No
dataset download, raw participant file, or sealed question is required.

```powershell
python -m pytest -q
python -m benchmarks.slm_shadow_smoke
python -m benchmarks.slm_prohibited_request_baseline --out benchmarks/local_development_baseline.json
```

The final command creates a local synthetic result file; do not automatically
stage generated files. The committed snapshots are:

- `benchmarks/slm_shadow_smoke_results.json`: four-path real Phi smoke,
  regenerated on 4 September.
- `benchmarks/slm_prohibited_request_baseline_results.json`: existing 16-case
  public development snapshot; the same case set was rerun and still passed.
- `benchmarks/slm_model_comparison_week5_smoke_results.json`: earlier
  one-repetition Phi/Qwen comparison, not rerun by this handoff and not enough
  to select a final model.

If the sealed checksum fails on Windows, do not change its checksum or bypass
the test. Check the existing `text eol=lf` attribute and compare the committed
blob with the recorded hash without printing prompt content. Restore only a
confirmed line-ending-only working-copy difference, then rerun the test.

## Interface for Priyansh and Sheng

The Python boundary is `create_local_service(model_tag=...)` followed by
`SLMService.respond(validated_packet, question)`, returning `SafeSLMResponse`.
The packet is the shared `backend/contracts/evidence.py` `EvidencePacket`.
Only manifest-listed local candidates are accepted by the runtime factory.

For a UI-independent manual call:

```powershell
python -m backend.slm.shadow_cli --packet tests/slm/fixtures/week5_gps_eligible.json --question "How was my movement different from my recent baseline?"
```

- Display the validated `text` and handle the returned `response_mode`.
  `uncertainty` is a valid evidence explanation, not a failed model call.
- Retain audit metadata (prompt hashes, request policy version, model tag,
  invocation flag, rejection reason, and timing) in the approved local audit
  design; do not send conversation content to analytics services.
- A deterministic State A response has `used_fallback=false` and
  `model_invoked=false`: it is an expected cold-start state, not an outage.
- A rejected/unavailable generation becomes a generic fallback. The wrapper
  must not bypass the service or display a raw draft.
- Priyansh/Integration owns the shared HTTP wrapper and acceptance contract;
  Sheng should integrate through that wrapper. This delivery does not claim
  that the API or UI integration is already complete and creates no competing
  HTTP API.

## Joint evaluation with Chonghao

This is the next collaboration step, not something the author can declare
complete alone. The current 16 cases are a **public synthetic developer
subset** in `benchmarks/fixtures/week5_prohibited_requests.json`. They are not
automatically Chonghao's confirmed Week 5 suite and never the Week 11 set.

1. Chonghao confirms the non-held-out questions, expected behaviours, and
   scoring rubric; he may accept/extend the existing developer subset.
2. Record the agreed case-set version and model/prompt/code versions before
   running. Richard runs the prohibited-request portion through the service.
3. Independently judge the saved responses, then compare judgments. Preserve
   the existing pre-registered thresholds; do not lower them after seeing results.
4. Record genuine disagreements and resolutions. The weekly plan requests
   2-3 examples, but do not invent disagreements if judgments agree; report
   the actual outcome and agree how to document boundary-case discussion.

Blank discussion record (not an assessment result):

| Case ID / response reference | Richard judgment and reason | Chonghao judgment and reason | Agreement or disagreement | Resolution / follow-up |
|---|---|---|---|---|
| Pending joint session | Not assessed | Not assessed | Not assessed | Pending |

## Proposed subsequent test data

Richard's proposal is to continue with synthetic/mock evidence for development
and early joint evaluation. Chonghao's agreement is **pending**. Using real
anonymised data is a separate decision requiring privacy/governance confirmation;
anonymisation is not assumed to remove all risk. No real participant data is
needed to reproduce the current delivery.

## Scope and review gates

- Honglin can integrate `week5-proposal-input.md` into the Proposal. The
  contribution includes limitations and AI acknowledgement; it is not the
  final group report.
- Yuktha and reviewers should use `week5-dependency-privacy-review.md` for
  the six-item privacy check. Review decisions remain blank until made by
  authorised reviewers.
- Do not describe joint scoring, API/UI acceptance, model selection, or
  participant-facing crisis approval as complete.
- A PR against `main` will include inherited Week 4 commits until PR #1 is
  integrated. Reviewers can compare `Rz...Rz-week5` for the Week 5-only delta.
  Do not merge into `Rz`, rewrite Week 4 history, or edit PR #1 as part of this
  delivery. Maintainers must coordinate the merge sequence.
