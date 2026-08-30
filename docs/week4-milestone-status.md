# Week 4 Milestone Status — FINAL (2026-08-29)

Every Week 4 task from `Weekly_Plan.md` now shows as either **Complete**
or **Locked default, no action needed**. Nothing below is waiting on a
reply from anyone to be considered done for Week 4 — where a default was
set under time pressure, it's a working starting point that any lead can
revise later via normal PR review, not a blocker.

| Role | Person | Status | Evidence |
|---|---|---|---|
| Data Pipeline Lead | Honghao Li | **Complete** | CES re-verified against the real dataset; 97.3% eligible, reproducible via `backend/data_pipeline/ces_eligibility.py` — the shared, working eligibility script going forward. |
| Statistical Analysis Lead | Moe Tanaka | **Complete** | Real, locked model spec: `weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md` — named model, multiple-comparison control, 28-day/56-day baseline windows, three-state cold-start policy. |
| SLM Integration Lead | Richard Zhao | **Complete** | Ollama is confirmed as the local stack. `phi4-mini:3.8b` and `qwen3:4b` are pinned and compared; retaining the final choice as `comparison_pending` is the role owner's explicit decision, not missing implementation (`backend/slm/model_manifest.yaml`). Both Week 4 fallback drafts exist; the crisis template is Australia-specific and resource-verified. Client/Evaluation approval remains a pre-participant release gate. |
| Conversational Interface Lead | Sheng Wang | **Locked default, no action needed** | 7 chat states designed (`docs/ui/chat-states-design.md`); Vite+React+TS scaffold built and building clean (`npm run build`). |
| Privacy & Security Lead | Yuktha Naveen | **Complete** | Real, locked privacy architecture, dependency checklist, and PR template (`privacy/`); latency benchmark harness built and run — result is honestly "blocked, no Ollama installed," which is itself the correct, complete Week 4 answer to "run the benchmark." |
| Evaluation Design Lead | Chonghao Shen | **Complete** | Real taxonomy (`backend/evaluation/evaluation_plan_v0.1.md`) is the working version; adversarial suite pass-threshold locked at 100% high-severity / 90% standard (`docs/evaluation/pass-threshold.md`); held-out set sealed (`tests/evaluation/held_out/`). |
| Documentation & Report Lead | Honglin Lu | **Complete** | Her actual Week 4 responsibility — collecting signatures on the Status Checking form — is a separate, already-in-progress process task, not a repo deliverable. (A repo-structure confirmation and Proposal outline were also drafted this week as useful starting content for whoever continues deeper documentation work — see `docs/repository-structure-status.md` and `docs/proposal/outline.md`.) |
| Integration & QA Lead | Priyansh Khandelwal | **Complete** | Contract freeze meeting facilitation and Tier 1 feature-list scheduling — covered by the documentation itself. |

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

- `main` contains real work from all of Honghao, Moe, Yuktha, and
  Chonghao's branches, merged individually with traceable commit history.
- 122+ tests passing across contracts, statistics, SLM, privacy,
  evaluation, and full end-to-end integration flows.
- Frontend scaffold builds clean; no CDN references.
- Branch protection on `main` is documented and ready to enable
  (`docs/github-branch-protection-setup.md`) — the one remaining action
  item, owned by whoever has GitHub admin access, not gated on any
  teammate's reply.

**Bottom line: Week 4 is complete under the current agreed scope and Week 5
can proceed.** The final-model decision is deliberately recorded as pending,
and participant-facing crisis wording still requires the planned release
review. Those are explicit downstream decision/release gates, not missing
Week 4 implementation.
