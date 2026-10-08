# Progress Report Evidence Register

Use this register to connect every report claim to verifiable evidence. Do not add participant-identifying data or raw evaluation responses.

| Report section | Evidence required | Owner | Current status | PR / commit / file |
|---|---|---|---|---|
| Data pipeline and final features | GPS and phone-unlock pipeline, cleaning and dataset provisioning | Honghao Li | Available in part — verify latest merged state | Pending link |
| Personal baseline and statistics | Model specification, calibration notes and bootstrap caching | Moe Tanaka | Cache work in progress; `/respond` SE wiring deferred | Pending link |
| Local model and safety | Guardrail, fallback and grounding evidence | Richard Zhao | Available in part | Pending link |
| Four-variant comparison | Real held-out Base/RAG/Agentic/RAG+Agent results | Richard Zhao | Pending | Pending link |
| UI integration | UI hardening, demo-machine verification and session issues | Sheng Wang | Available in part; session updates pending | Pending link |
| Privacy and security | RC-build privacy verification | Yuktha Naveen | Pending final sign-off | Pending link |
| Evaluation sessions | ME-P01–P04 completion, pass thresholds and aggregated evidence | Chonghao Shen | Pending | Pending link |
| Questionnaire summary | Median, range and valid N per category; critical failures and repeated patterns | Moe Tanaka / Chonghao Shen | Pending session completion | Pending link |
| Report coordination | Draft integration, evidence checking and final formatting | Honglin Lu | In progress | `docs/progress-report/draft.md` |

## Evidence-handling rules

- Use merged PR links or commit SHAs where possible.
- Mark unmerged or unverified work as pending.
- Exclude participant names, individual ratings and raw questionnaire responses.
- Keep raw screenshots and raw `/respond` JSON local.
- Record only aggregated evaluation results approved by the privacy lead.
- Do not claim clinical validity, diagnosis or causation.

## Outstanding requests

- [ ] Confirm the latest merged data-pipeline commit.
- [ ] Confirm the bootstrap-cache PR and deferred wiring decision.
- [ ] Add real four-variant comparison tables when available.
- [ ] Add final RC-build privacy sign-off.
- [ ] Add ME-P01–P04 dates, pass/fail outcomes and aggregated questionnaire statistics.
- [ ] Add final UI issue status after the evaluation sessions.
