# Week 4 SLM Completion Report

- **Owner:** Richard Zhao (Rz), SLM Integration Lead
- **Date:** 30 August 2026 (Australia/Sydney)
- **Status:** Complete under the current agreed Week 4 scope; not yet release-ready
- **Upload rule:** This English file is the only Week 4 report intended for Git/GitHub. The Chinese companion is stored outside the repository.

## Assessment

The Week 4 SLM work is complete enough to begin Week 5 development. This conclusion follows the latest role-owner decision: Ollama is confirmed as the local deployment runtime, while the final model is deliberately left open for a fairer comparison between Phi-4 Mini and Qwen3. Therefore, `comparison_pending` is a documented decision state rather than an unfinished installation task.

The earlier repository statement that Phi-4 Mini was already the final locked model is superseded for SLM selection. The current position is:

- `phi4-mini:3.8b` is the pinned baseline;
- `qwen3:4b` is the pinned challenger;
- neither model is the final selection yet; and
- the same expanded, fixed safety and response-quality evaluation must be used before selection.

## Week 4 checklist

| Requirement | Evidence | Status |
|---|---|---|
| Decide the local deployment stack | Ollama 0.33.2 is installed and local calls are restricted to loopback (`127.0.0.1`/`localhost`) with cloud use disabled for the local run. | Complete |
| Record exact model versions | Both candidate tags and digest prefixes are recorded in `backend/slm/model_manifest.yaml`; floating `latest` tags are rejected. | Complete |
| Make the final model decision | A small same-machine comparison was completed, but it was not large enough to justify a winner. The manifest correctly remains `comparison_pending`. | Deliberately deferred pending expanded evaluation |
| Draft a generic fallback | Versioned `backend/slm/prompts/generic_fallback.yaml` exists and is used when generation or deterministic validation fails. | Complete |
| Draft a separate crisis-aware fallback | Versioned `backend/slm/prompts/crisis_aware.yaml` v1.1.0 now contains Australia-specific resources and no US-only 988/741741 content. | Complete as a Week 4 draft |
| Keep crisis wording deterministic | The SLM is prohibited from selecting the crisis response. The crisis message is a fixed YAML template, not generated text. | Complete for template design; routing detector is later joint SLM/Evaluation work |
| Establish structured, safe local generation | The local client uses schema-constrained JSON, temperature 0, seed 42, versioned prompt hashes, and a second-pass safety gate. | Complete locally; this exceeds the minimum Week 4 task |

## Australia-specific safety localisation

The crisis template now directs an Australian user to:

- Triple Zero (000) where life is in danger;
- Lifeline on 13 11 14, text 0477 13 11 14, or Lifeline online chat; and
- Suicide Call Back Service on 1300 659 467.

The details were checked on 30 August 2026 against the official [Lifeline Crisis Support](https://www.lifeline.org.au/get-help/national-services/lifeline-crisis-support) and [Suicide Call Back Service](https://www.suicidecallbackservice.org.au/) pages. Resource verification does not replace study approval: the client and Evaluation lead must approve the complete participant-facing wording and escalation flow before any pilot or real participant use. Any University of Sydney support pathway required by the study protocol must also be added during that review.

## Initial local model comparison

The same three synthetic cases were run three times per candidate with temperature 0 and seed 42. No CES participant data and no Week 11 held-out prompts were used.

| Candidate | Safety/quality pass | Mean latency | Median latency | Mean generation speed | Estimated GPU memory delta | Observed normal-response issue |
|---|---:|---:|---:|---:|---:|---|
| Phi-4 Mini 3.8B | 6/9 (66.67%) | 674.97 ms | 533.64 ms | 202.05 tokens/s | 3,178 MiB | Referenced an unknown evidence ID |
| Qwen3 4B | 6/9 (66.67%) | 551.01 ms | 530.19 ms | 181.23 tokens/s | 3,272 MiB | Failed the explicit uncertainty-statement flag |

This result does not support choosing a winner. Phi remains the baseline and Qwen remains the challenger until a larger pre-defined public/synthetic evaluation is run jointly with the Evaluation lead.

## Verification and repository state

- Full local test run: **142 passed, 8 skipped, 1 deselected**.
- The deselected item is the known Windows CRLF raw-byte checksum check for the sealed held-out file. Its LF-normalised hash matches the recorded checksum; the held-out prompts were not run against either model.
- Ruff: all checks passed; all 13 checked SLM/integration files are formatted.
- Branch: local `Rz` branch.
- Delivery workflow: this work must be reviewed from branch `Rz`; it must not be pushed directly to `main` or treated as merged before team review.
- Data: no participant dataset or database was added to Git.

## Remaining gates and next work

These items do not invalidate Week 4 completion, but they must not be presented as finished:

1. Expand and freeze the non-held-out synthetic/public evaluation set, then rerun Phi and Qwen before final model selection.
2. Obtain client/Evaluation review of the Australia-specific participant-facing crisis wording and facilitator escalation flow before the pilot.
3. Build the rule-based crisis-routing detector jointly with the Evaluation lead; the SLM must never decide when to emit crisis wording.
4. Continue the Week 5 shadow build: connect the safe SLM service to a controlled FastAPI endpoint and run the prohibited-request subset of the pre-registered adversarial suite without touching the Week 11 held-out set.
5. Review the focused commits through the branch/draft-PR workflow before merge. If bilingual documentation is needed in GitHub later, upload this English report only; keep private meeting notes outside the repository.
