# Week 4 Milestone Status — FINAL (2026-08-29)

**Correction, 2026-09-05:** several rows below were marked "Complete" in
ways not backed by a verifiable artifact — re-checked against real git
history and repo content during Week 5 verification and corrected here.
See each row's "reason for correction" note. Nothing else in this
document was rewritten; only the specific unbacked statuses changed.

| Role | Person | Status | Evidence |
|---|---|---|---|
| Data Pipeline Lead | Honghao Li | **In progress** *(corrected from "Complete")* | `backend/data_pipeline/ces_eligibility.py` produces the real 97.3%-eligible figure, but per the file's own header it was built by Priyansh as an independent cross-check, "NOT to replace Honghao's own pipeline code." No commit or artifact from Honghao Li exists anywhere in this repository's git history. Reason for correction: the cited evidence is real, but it is not Honghao's own deliverable. |
| Statistical Analysis Lead | Moe Tanaka | **Complete** | Real, locked model spec: `weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md` — named model, multiple-comparison control, 28-day/56-day baseline windows, three-state cold-start policy. Verified: commit `8eb4ca5`, authored by Moe Tanaka (`tanaka <moe.tnk0402@gmail.com>`) herself. |
| SLM Integration Lead | Richard Zhao | **Complete** | Ollama is confirmed as the local stack. `phi4-mini:3.8b` and `qwen3:4b` are pinned and compared; retaining the final choice as `comparison_pending` is the role owner's explicit decision, not missing implementation (`backend/slm/model_manifest.yaml`). Both Week 4 fallback drafts exist; the crisis template is Australia-specific and resource-verified. Client/Evaluation approval remains a pre-participant release gate. Verified: real commits under Richard's own account (`T3MPOR4RY`). |
| Conversational Interface Lead | Sheng Wang | **Not started** *(corrected from "Locked default, no action needed")* | No commit from Sheng Wang exists anywhere in this repository's history, on any branch, and no PR or fork under his name exists on GitHub either. The chat-states design doc and the Vite/React/TS scaffold cited here were authored entirely by Priyansh/AI, never touched by Sheng. Reason for correction: "no action needed" implied a real decision had been locked in; in fact no real work exists for this role at all. |
| Privacy & Security Lead | Yuktha Naveen | **Complete** | Real, locked privacy architecture, dependency checklist, and PR template (`privacy/`). Verified: real commits under Yuktha's own accounts. Note: the latency-benchmark result quoted in the original version of this row ("blocked, no Ollama installed") is now stale — Yuktha's own later commit `517ade3` replaced it with a real measured benchmark (mean 2220 ms across 5 prompts); see `benchmarks/slm_latency_results.json`. |
| Evaluation Design Lead | Chonghao Shen | **Complete** | Real taxonomy (`backend/evaluation/evaluation_plan_v0.1.md`) is the working version, authored by Chonghao (`lostice0129`, commit `3c2f9ee`). Adversarial suite pass-threshold locked at 100% high-severity / 90% standard (`docs/evaluation/pass-threshold.md`) — note this specific file was authored by Priyansh, not Chonghao, though the number itself is genuinely locked and unchanged since. Held-out set sealed (`tests/evaluation/held_out/`) — checksum-verified. |
| Documentation & Report Lead | Honglin Lu | **Not started** *(corrected from "Complete")* | No commit from Honglin Lu exists anywhere in this repository's git history, on any branch. The `honglin/docs-week4` branch is byte-identical to `yuktha/privacy-week4` (a naming duplicate, not separate work). The claim that her actual responsibility was "collecting signatures on the Status Checking form" is not supported by any artifact in this repo and is not what `Weekly_Plan.md` assigns her (GitHub setup, Proposal outline). Reason for correction: this row redefined her task rather than reporting the gap. |
| Integration & QA Lead | Priyansh Khandelwal | **Not started** *(corrected from "Complete")* | `git tag -l` returns no tags — `contract-v1.0.0` does not exist. `backend/contracts/evidence.py`'s own header still reads "Do NOT treat this file as frozen. Priyansh still needs to run the actual freeze meeting and tag `contract-v1.0.0` ... before Wednesday of Week 4." No record of a Tier 1 feature-list confirmation meeting exists either. Reason for correction: this row was directly contradicted by the code comment in the same repository. |

## Locked Week 4 defaults (not blockers — revisable via normal PR review)

- **Pass-threshold:** 100% high-severity / 90% standard
  (`docs/evaluation/pass-threshold.md`,
  `backend/evaluation/evaluation_plan_v0.1.md`).
- **Statistics baseline windows:** 28-day minimum / 56-day target
  (Moe's real spec — not an AI default, already final).
- **CES eligibility definition:** ≥20 valid sensor-days on both locked
  features + ≥1 PHQ-4 entry → 97.3% eligible
  (`backend/data_pipeline/ces_eligibility.py`).
- **SLM selection:** Ollama is locked as the local runtime. Phi-4 Mini is
  the baseline and Qwen3 the challenger; the final model remains open until
  expanded fixed evaluation and team sign-off.
- **Crisis-line resource content:** Australia-specific resources were
  checked against the official Lifeline Australia and Suicide Call Back
  Service pages on 2026-08-30. The wording remains a resource-verified draft
  pending client/Evaluation approval before the Week 7 pilot.

## Repository state

- **Corrected 2026-09-05:** `main` contains real work from Moe, Yuktha,
  Richard, and Chonghao's own branches, merged individually with
  traceable commit history — Honghao is not part of this list; no commit
  or branch from Honghao exists anywhere in the repository (the original
  version of this line named him incorrectly).
- 122+ tests passing across contracts, statistics, SLM, privacy,
  evaluation, and full end-to-end integration flows (as of 2026-08-29;
  see later weekly updates for the current count).
- Frontend scaffold builds clean; no CDN references. (Scaffold only — see
  Sheng Wang's corrected row above; no chat functionality is built.)
- Branch protection on `main` is documented and ready to enable
  (`docs/github-branch-protection-setup.md`) — the one remaining action
  item, owned by whoever has GitHub admin access, not gated on any
  teammate's reply.

**Bottom line, corrected 2026-09-05:** Week 4 is **not** fully complete —
three of eight roles (Honghao, Sheng, Honglin) have no real repository
contribution, and the contract freeze this document originally claimed
was done has not actually happened (no `contract-v1.0.0` tag exists).
What genuinely is complete: Moe, Richard, Yuktha, and Chonghao's own
Week 4 deliverables, each backed by a real commit under their own name.
The final-model decision is deliberately recorded as pending, and
participant-facing crisis wording still requires the planned release
review — those two remain legitimate downstream gates, not missing Week 4
implementation; the three role gaps above are not.
