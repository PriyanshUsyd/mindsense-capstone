# Progress Report Evidence Register

Use this register to connect every report claim to verifiable evidence. Do not add participant-identifying data or raw evaluation responses.

| Report section | Evidence required | Owner | Current status | PR / commit / file |
|---|---|---|---|---|
| Data pipeline and final features | GPS and phone-unlock pipeline, cleaning and dataset provisioning | Honghao Li | Available in part — verify latest merged state | `backend/data_pipeline/`, `docs/data-pipeline/tier1_feature_pipeline.md`, `docs/data-pipeline/gps_feature_pipeline.md`, `docs/data-pipeline/ces_local_provisioning.md`; per-machine preflight results TBC (team to confirm) |
| Personal baseline and statistics | Model specification, calibration notes and bootstrap caching | Moe Tanaka | Bootstrap cache merged (PR #49, #62); `/respond` SE wiring deferred (`no_claim` baseline) | `docs/statistics/preregistration.md`, `Week5_Statistical_Analysis_Deliverable.md`, `backend/statistics/bootstrap_cache.py`, `docs/statistics/week7-calibration-concerns.md` |
| Local model and safety | Guardrail, fallback and grounding evidence | Richard Zhao | Available in part; final model `phi4-mini:3.8b` recorded 2026-10-16 | `backend/slm/model_manifest.yaml`, `backend/slm/output_grounding.py`, `docs/slm/week8-safety-context-integration.md`, `docs/evaluation/week8-fallback-e2e.md`, `tests/slm/test_dev_50q.py` |
| Four-variant comparison | Real held-out Base/RAG/Agentic/RAG+Agent results | Richard Zhao | Pending — held-out results do not exist yet; development-only comparison available | Development evidence: `docs/slm/week9-variant-quality-comparison.md`; held-out results: none yet |
| UI integration | UI hardening, demo-machine verification and session issues | Sheng Wang | Available in part; local model selector merged after rc-eval-2 (PR #78) | `docs/ui/week8-ui-hardening.md`, `docs/ui/demo-machine-verification-2026-09-21.md`, `docs/ui/week9-evaluation-ui-issues.md` |
| Privacy and security | RC-build privacy verification | Yuktha Naveen | Pending final sign-off (no sign-off on rc-eval-2 or the final build yet) | Week 9 re-check: `docs/privacy/master-test-register.md` (`c7505c4`), `docs/privacy/local-demo-privacy-check.md`; final sign-off: none yet |
| Evaluation sessions | 3-session evaluation (all 8 members; replaces the ME-P01–P04 pair plan), pass thresholds and aggregated evidence | Chonghao Shen | Sessions ran on rc-eval-2; dates, attendance and session-to-evidence mapping TBC (team to confirm); thresholds not yet calculated | `docs/evaluation/week8-main-evaluation-roster.md`, `docs/evaluation/evidence/main-evaluation/ME-P01/ME-P01.pdf`, `docs/evaluation/evidence/main-evaluation/ME-P04/`, `docs/evaluation/results/main-evaluation/pass-threshold-summary.md` (Pending) |
| Questionnaire summary | Median, range and valid N per category; critical failures and repeated patterns | Moe Tanaka / Chonghao Shen | Pending — no ratings recorded yet | `scripts/summarize_session_responses.py`; `docs/evaluation/results/main-evaluation/session-responses.csv` (header only) |
| Report coordination | Draft integration, evidence checking and final formatting | Honglin Lu | In progress | `docs/progress-report/draft.md` |

## Evidence-handling rules

- Use merged PR links or commit SHAs where possible.
- Mark unmerged or unverified work as pending.
- Exclude participant names, individual ratings and raw questionnaire responses.
- Keep raw screenshots and raw `/respond` JSON local (not committed). Per-question `notes.md` with the Details line is committed; see `docs/evaluation/evidence/main-evaluation/README.md`.
- Record only aggregated evaluation results approved by the privacy lead.
- Do not claim clinical validity, diagnosis or causation.

## Outstanding requests

- [ ] Confirm the latest merged data-pipeline commit.
- [ ] Confirm the bootstrap-cache PR and deferred wiring decision.
- [ ] Add real four-variant comparison tables when available.
- [ ] Add final RC-build privacy sign-off.
- [ ] Add the 3 sessions' dates and attendance (TBC (team to confirm)), pass/fail outcomes and aggregated questionnaire statistics.
- [ ] Add final UI issue status after the evaluation sessions.
