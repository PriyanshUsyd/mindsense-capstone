# MindSense — Weekly Plan (Weeks 4–12)

This is the technical, precise version of the plan — point your AI tools at this file, alongside `build-reference.md`, so every part of the project stays consistent. A simplified plain-English version of this same plan also exists for quick human reference, but this file is the authoritative one for implementation detail.

## The 8 Roles

| Role | Person |
|---|---|
| Data Pipeline Lead | Honghao Li |
| Statistical Analysis Lead | Moe Tanaka |
| SLM Integration Lead | Richard Zhao |
| Conversational Interface Lead | Sheng Wang |
| Privacy & Security Lead | Yuktha Naveen |
| Evaluation Design Lead | Chonghao Shen |
| Documentation & Report Lead | Honglin Lu |
| Integration & QA Lead | Priyansh Khandelwal |

Roles are fixed for the entire project, Week 4 through Week 12.

**Status, 16 October 2026 (`95e3171`).** Every item below is Done with an
evidence link or Closed with a reason. Three items stay open until the final
freeze: the held-out safety check (Week 11, SLM), the privacy sign-off with the
offline test (Weeks 8 and 12, Privacy), and the final freeze tag
([release checklist §11](docs/release/release-candidate-checklist.md#11-remaining-before-freeze),
[final-submission-checklist.md](docs/release/final-submission-checklist.md)).

---

## Week 4 — Scope & Risk Lock

Every foundational decision that gates later work gets made concretely this week, not just researched.

| Person | Task | Status (16 Oct 2026) |
|---|---|---|
| **Honghao Li** (Data) | Re-verify CES against the real, current copy of the data (participant count, PHQ-4 repeat density, feature completeness). Confirm the fallback dataset (Corona Health) by Wednesday if CES fails any check. | Done: [ces-reverification.md](docs/data-pipeline/ces-reverification.md) |
| **Moe Tanaka** (Stats) | Name the exact statistical model now: mixed-effects with person-level random intercepts, person-mean-centred predictors. Define the minimum baseline window as a specific number of days. Draft the three-state cold-start policy: below-window = templated "not enough data" only; partial history = descriptive summary with explicit "too early to compare" language; full history = comparative statements allowed. | Done: [model-and-coldstart-spec.md](docs/statistics/model-and-coldstart-spec.md), [Week 4 deliverable](weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md) |
| **Richard Zhao** (SLM) | Confirm Ollama + phi4-mini:3.8b as the local model. Design TWO fallback templates: a generic refusal, and a separate crisis-aware template with real helpline/support-resource content, drafted now. | Done: [crisis_aware.yaml](backend/slm/prompts/crisis_aware.yaml), [generic_fallback.yaml](backend/slm/prompts/generic_fallback.yaml), [week4-slm-completion-report.md](docs/slm/week4-slm-completion-report.md) |
| **Sheng Wang** (UI) | Design (not build yet) the 7 required chat states: normal, insufficient-data/cold-start, uncertainty, refusal, generic fallback, crisis-aware fallback. Set up the Vite + React + TypeScript scaffold. | Done: [chat-states-design.md](docs/ui/chat-states-design.md), [frontend/](frontend/README.md) |
| **Yuktha Naveen** (Privacy) | Draft privacy/architecture principles (network calls, telemetry, logs, dependencies). Run the real-machine SLM latency benchmark. Establish the ongoing rule: any PR adding a new dependency includes a 10-minute privacy spot-check in its description. | Done: [privacy_architecture_principles.md](privacy/privacy_architecture_principles.md), [Week 4 report](docs/privacy/week4-privacy-lead-report.pdf), [PR spot-check template](.github/pull_request_template.md) |
| **Chonghao Shen** (Evaluation) | Freeze the adversarial taxonomy and expected response class per case. Pre-register the pass-threshold rule now (e.g. high-severity categories 100%; softer categories a fixed percentage). Set aside 20-30 prompts as a held-out set, never touched until Week 11. Draft a one-page participant information sheet and a facilitator crisis-response script. | Done: [adversarial-taxonomy.md](docs/evaluation/adversarial-taxonomy.md), [pass-threshold.md](docs/evaluation/pass-threshold.md), [held-out set](tests/evaluation/held_out/README.md), [information sheet](docs/evaluation/participant-information-sheet.md), [crisis script](docs/evaluation/crisis-response-script.md) |
| **Honglin Lu** (Docs) | Set up the GitHub repo, branch protection, and skeleton per the repository structure in `build-reference.md`. Begin the Proposal outline. | Done: [repo setup and branch protection](docs/week4-repo-setup-and-branch-protection.md), [proposal outline](docs/proposal/outline.md) |
| **Priyansh Khandelwal** (Integration/QA) | Facilitate the evidence contract freeze meeting — tag `contract-v1.0.0` by Wednesday. Schedule the Tier 1 feature-list confirmation for Wednesday of Week 5. Hard cap confirmed: maximum 2 cross-platform features (GPS distance, unlock events) unless a third genuinely meets the same standard. | Done: tag `contract-v1.0.0` (`8adddce`), [freeze-decision.md](freeze-decision.md), [feature-list-signoff.md](feature-list-signoff.md) |

**SLM decision update (2026-08-30):** the row above records the original Week 4 plan. The role owner has not approved Phi-4 Mini as the final model. Ollama is confirmed as the local runtime; `phi4-mini:3.8b` remains the pinned baseline and `qwen3:4b` the pinned challenger until a larger fixed evaluation supports a final choice.

---

## Week 5 — Group Proposal Report Due (Sep 6)

Narrow vertical slice: happy path + missing-data case only. Safety logic for prohibited requests is tested now, at the model/template layer, independent of the UI.

| Person | Task | Status (16 Oct 2026) |
|---|---|---|
| **Honghao Li** | Build ONE feature end-to-end (GPS distance), including real cleaning (timestamp alignment, missing-sensor handling, outlier filtering). Confirm the final 2-feature Tier 1 list against the real schema by Wednesday. | Done: [gps_feature_pipeline.md](docs/data-pipeline/gps_feature_pipeline.md), [feature-list-signoff.md](feature-list-signoff.md) |
| **Moe Tanaka** | Implement baseline/evidence logic for that one feature using the named statistical model. | Done: [Week 5 deliverable](Week5_Statistical_Analysis_Deliverable.md), `backend/statistics/evidence.py` |
| **Richard Zhao** | Build the SLM stub and both fallback templates as a shadow build. Run the prohibited-request portion of the adversarial suite against the model/template layer this week. | Done: [week5-shadow-build-report.md](docs/slm/week5-shadow-build-report.md), `benchmarks/slm_prohibited_request_baseline.py` |
| **Sheng Wang** | Integrate the UI against the real SLM stub; build the "normal response" state fully. Rough sketches of other states are fine but not required to work yet. | Done: [NormalResponse.tsx](frontend/src/features/chat/NormalResponse.tsx), [NormalResponse.test.tsx](frontend/src/features/chat/NormalResponse.test.tsx) |
| **Yuktha Naveen** | Document the privacy architecture; confirm Week 4's latency and dependency-audit results. | Done: [Week 5 report](docs/privacy/week5-privacy-security-report.pdf), [post-merge dependency review](privacy/week5_post_merge_dependency_review.md) |
| **Chonghao Shen** | Finalise the suite (held-out set stays untouched) and run it internally for a baseline reading. Jointly with Richard, judge baseline responses together and document 2-3 cases where judgment differed. | Done: [week5-development-review.md](docs/evaluation/week5-development-review.md); the joint review agreed on every reviewed case, so no differing cases arose |
| **Honglin Lu** | Compile the Group Proposal Report — primary focus this week. Include the AI Acknowledgement statement. | Done: [Group Proposal.md](docs/proposal/Group%20Proposal.md), [ai-acknowledgement.md](docs/proposal/ai-acknowledgement.md) |
| **Priyansh Khandelwal** | Confirm the vertical slice works for the happy path and a missing-data case. Confirm Week 5 prohibited-request tests pass even without full UI. Sign off the final 2-feature list. Review/merge PRs; submit the Proposal. | Done: [Week 4-5 verification](docs/verification/week4-5-fresh-check-2026-09-05.md), [feature-list-signoff.md](feature-list-signoff.md), [submitted proposal](docs/proposal/CS62_Group_Proposal.pdf) |

---

## Week 6 — Build Tier 1, Freeze

Implement the signed-off feature list. Hard freeze at week's end. Build both fallback UI states and the actual cold-start rules — not just placeholders.

| Person | Task | Status (16 Oct 2026) |
|---|---|---|
| **Honghao Li** | Implement the signed-off 2-feature set fully. Hard freeze at week's end. Anything beyond it is Tier 2/stretch. | Done: [tier1_feature_pipeline.md](docs/data-pipeline/tier1_feature_pipeline.md), [final-pipeline-methodology.md](docs/data-pipeline/final-pipeline-methodology.md) |
| **Moe Tanaka** | Extend baseline/evidence logic to both features. Write the three-state cold-start policy into actual working logic. | Done: `backend/statistics/eligibility.py`, `participant_evidence.py`, [final-statistical-methodology.md](docs/statistics/final-statistical-methodology.md) §4 |
| **Richard Zhao** | Iterate prompts using the Week 5 baseline against the pre-registered thresholds. Both fallback templates become fully functional. Build the deterministic response health-check tied to explicit evidence-contract violations. | Done: [week6-integration-report.md](docs/slm/week6-integration-report.md), `backend/slm/response_health.py` |
| **Sheng Wang** | Build the cold-start, insufficient-data, refusal, and both fallback UI states — visually distinct from each other and from normal responses. | Done: [ChatStates.tsx](frontend/src/features/chat/ChatStates.tsx), [visual-distinctness test](frontend/src/features/chat/ChatStates.visualDistinctness.test.tsx) |
| **Yuktha Naveen** | Jointly with Priyansh Khandelwal, build the automated privacy/regression check and a lightweight per-PR gate (build + integration test + guardrail subset). | Done: [privacy-security-ci.yml](.github/workflows/privacy-security-ci.yml) (4 stages), [ci-pipeline-guide.md](docs/privacy/ci-pipeline-guide.md) |
| **Chonghao Shen** | Draft and internally test the evaluation rubric, built directly around the client's 10 named criteria (see build-reference.md Section 9: accuracy/faithfulness, comprehensibility, usefulness, perceived personal relevance, trust, uncertainty communication, correlation-vs-causation distinction, inappropriate mental-health inference, usability, privacy perceptions) - not a rubric invented independently of the spec. Finalise the evaluation-data-source decision (synthetic vs. de-identified real extract). Draft the one-page session runbook. Increase planned pilot to 4-5 participants.<br>**[Superseded 2026-09-11]:** the client (Tianyi Zhang) confirmed no ethics approval exists for recruiting participants from outside the 8-person team. This line did not proceed — no external recruitment occurred. From Week 7 onward, all evaluation runs team-only using rostered pairs (see below). | Done: [rubric](docs/evaluation/response-quality-rubric-v0.1.md), [runbook](docs/evaluation/team-session-runbook-v0.1.md), [data-source decision](docs/evaluation/week6-client-evaluation-readiness.md). 4-5 participant pilot: Closed, superseded on 2026-09-11 (see row) |
| **Honglin Lu** | Update documentation to reflect the frozen Tier 1 architecture. | Done: [frozen-tier1-architecture.md](docs/architecture/frozen-tier1-architecture.md) |
| **Priyansh Khandelwal** | Review/merge PRs; run integration tests confirming the complete Tier 1 set and both fallback UI states work end-to-end. Confirm the adversarial suite runs as a scripted/batch process. | Done: `tests/integration/`, [week6-test-freeze-and-baseline.md](docs/evaluation/week6-test-freeze-and-baseline.md) |

---

## Week 7 — Pilot

Pilot (team-only, rostered pairs drawn from the 8 team members) against a frozen build, using the tested rubric and session runbook. No external recruitment — per client feedback, all evaluation stays within the team. Internal rostering for the main evaluation starts now. In parallel, confirm the build is demo-ready on Richard's machine (Ollama and the pinned models are already running there from Week 4-6) and schedule a live screen-share call with Tianyi by **2026-09-25** (2 weeks from her request) — not deployed or hosted anywhere, consistent with the local-only claim.

**Client feedback incorporated this week:** per subsequent client (Tianyi Zhang) feedback, (1) the human-evaluation workload for Weeks 7-10 can be reduced — one to two weeks of sessions, not a requirement to complete every planned session, with representative examples/case studies/patterns an acceptable substitute for full completion; (2) fine-tuning is now confirmed declined (GPU access unavailable — see `build-reference.md` Section 10, this settles what was previously a conditional stretch goal); and (3) the client asked the team to explore RAG and/or agentic architectures instead, comparing up to four variants (Base LLM with a fixed data summary, RAG-enhanced, agentic, RAG+agent combined) ahead of the evaluation procedure. This comparison direction is adopted as the confirmed Week 7+ architectural direction, per client mandate and group-lead decision (see `build-reference.md` Section 6 for the variant list and what remains an open technical decision).

| Person | Task | Status (16 Oct 2026) |
|---|---|---|
| **Honghao Li** | No new features (frozen). Fix only critical/blocking bugs on a separate branch. Begin scoping any data-store/retrieval-source work the RAG/agentic comparison will need (see `build-reference.md` Section 6) — a new, separate exploration thread, not a reopening of the Tier 1 freeze. | Done: [rag_agent_storage_scope.md](docs/data-pipeline/rag_agent_storage_scope.md), [pilot issue log](docs/data-pipeline/week8_pilot_issue_log.md) (no critical pipeline bug in the pilot) |
| **Moe Tanaka** | Support the pilot; log calibration concerns for Week 8, no live changes. | Done: [week7-calibration-concerns.md](docs/statistics/week7-calibration-concerns.md) |
| **Richard Zhao** | Re-test guardrails (scripted run) against the frozen build; held-out set stays reserved. Continue fallback refinement. Preload and boot-test the local SLM (Ollama, phi4-mini:3.8b / qwen3:4b) on my own machine ahead of the Tianyi demo call — this machine hosts the live demo, since Ollama is already installed and running here. Begin the client-requested RAG/agentic variant comparison (see `build-reference.md` Section 6) as a new work thread, starting from the already-built Base LLM variant — specific technical choices (embedding model, retrieval method) are not yet decided and remain to be scoped. | Done: [week7-fallback-refinement.md](docs/slm/week7-fallback-refinement.md), [week7-variant-interface.md](docs/slm/week7-variant-interface.md), [demo-machine verification](docs/ui/demo-machine-verification-2026-09-21.md) |
| **Sheng Wang** | Support the pilot; log UI issues for Week 8. Support Richard in confirming the frontend runs cleanly end-to-end on his machine (the demo machine) ahead of the Tianyi screen-share call. | Done: [week7-pilot-ui-issues.md](docs/ui/week7-pilot-ui-issues.md), [demo-machine verification](docs/ui/demo-machine-verification-2026-09-21.md) |
| **Yuktha Naveen** | Run the full privacy check against the frozen build. | Done: [master-test-register.md](docs/privacy/master-test-register.md) |
| **Chonghao Shen** | Run the pilot using the session runbook and crisis-response script, with team members in rostered pairs (one operating the build, one facilitating/observing) standing in for external participants. Check protocol health after the first rostered pair. Begin scheduling the internal rostered-pair sessions for the main evaluation in parallel — no external recruitment. Per client feedback, the main evaluation does not need a fixed, complete schedule: one to two weeks of sessions, with representative examples/case studies/patterns standing in for full completion, is acceptable — schedule accordingly rather than over-committing session count. | Done: [rostered-pair pilot](docs/evaluation/week7-rostered-pair-pilot-main.md), [solo dry run](docs/evaluation/week7-solo-pilot-dry-run.md), [roster](docs/evaluation/week8-main-evaluation-roster.md) |
| **Honglin Lu** | Begin the Progress Report outline using real pilot findings. | Closed: course deliverable submitted outside this repository (Progress Report outline) |
| **Priyansh Khandelwal** | Pilot-fix intake with triage: critical/blocking issues get a full linked-issue process; minor polish items go into a simple batch checklist. Coordinate with Richard to confirm the frozen Tier 1 build runs end-to-end on his machine (where Ollama and the pinned models already run), rather than mine. Schedule and host the live screen-share call with Tianyi to demo Richard's running build by **2026-09-25** — no deployment or hosting. Coordinate the new RAG/agentic comparison thread (Richard: model/variant work; Honghao: data-store/retrieval-source work) as the confirmed Week 7+ direction, per client mandate and group-lead decision — an integration/coordination role only, no technical implementation choices dictated here. | Done: [pilot-triage-summary.md](docs/triage/pilot-triage-summary.md), [demo-machine verification](docs/ui/demo-machine-verification-2026-09-21.md), RAG/agentic coordination ([final-slm-methodology.md](docs/slm/final-slm-methodology.md) §3.1). Client live screen-share: Closed, the demo video was shared with the client in its place ([final-submission-checklist.md](docs/release/final-submission-checklist.md) §4) |

---

## Week 8 — Status Checking 2 Due (Oct 4)

Hardening from pilot feedback. Both fallback templates tested end-to-end, including a simulated crisis trigger.

| Person | Task | Status (16 Oct 2026) |
|---|---|---|
| **Honghao Li** | Fix pipeline issues found during the pilot. | Done: [week8_pilot_issue_log.md](docs/data-pipeline/week8_pilot_issue_log.md), [ces_local_provisioning.md](docs/data-pipeline/ces_local_provisioning.md) |
| **Moe Tanaka** | Fix statistical calibration issues found during the pilot. | Done: [week7-calibration-concerns.md](docs/statistics/week7-calibration-concerns.md), items 2-8 resolved or closed with evidence |
| **Richard Zhao** | Fix guardrail failures using the Week 4 pre-registered thresholds (not renegotiated after the fact). Confirm fail-safe defaults to the safe template on ambiguous cases. Draft the zero-shot-vs-few-shot and conversational-multi-turn-reasoning methodology plus empty results-table templates (documentation only — no build or prompt changes yet; see `build-reference.md`). | Done: [week8-safety-context-integration.md](docs/slm/week8-safety-context-integration.md), [week8-prompting-methodology.md](docs/slm/week8-prompting-methodology.md) |
| **Sheng Wang** | Fix UI issues found during the pilot. | Done: [week8-ui-hardening.md](docs/ui/week8-ui-hardening.md) |
| **Yuktha Naveen** | Run the final privacy verification. | **Open:** final privacy verification is the privacy sign-off on the final build, [release checklist §11](docs/release/release-candidate-checklist.md#11-remaining-before-freeze) |
| **Chonghao Shen** | Confirm the internal rostered-pair schedule remains workable under the now-reduced, client-approved evaluation scope; finalise 2-person rostered pairs (drawn from the 8 team members) for the main sessions, sized to a one-to-two week window rather than a fixed full schedule. Test both fallback templates end-to-end — simulate a generic SLM failure and a crisis-trigger case. | Done: [roster](docs/evaluation/week8-main-evaluation-roster.md), [week8-fallback-e2e.md](docs/evaluation/week8-fallback-e2e.md) |
| **Honglin Lu** | Prepare and submit Project Status Checking 2, with honest reporting of any deviation. | Done: [Status Checking 2](docs/status-checking/Status_Checking_Form_2_Filled_Updated.docx) |
| **Priyansh Khandelwal** | Review/merge PRs; confirm the release-candidate checklist is met. Lock the rule: all Week 9 sessions complete at least 2 working days before the Progress Report deadline. | Done: [release-candidate-checklist.md](docs/release/release-candidate-checklist.md) |

---

## Week 9 — Group Progress Report Due (Oct 11)

Main evaluation on a version-locked build, submitted after sessions are genuinely complete.

| Person | Task | Status (16 Oct 2026) |
|---|---|---|
| **Honghao Li** | Freeze the pipeline; record the feature-code version. Continue any data-store/retrieval-source work needed for the RAG-enhanced/agentic variants (see `build-reference.md` Section 6) on its own thread — the freeze applies to the Tier 1 pipeline only, not to this exploration. | Done: freeze record in [final-pipeline-methodology.md](docs/data-pipeline/final-pipeline-methodology.md) §5; retrieval source `backend/data_pipeline/retrieval_source.py` |
| **Moe Tanaka** | Support logistics; provide the quantitative angle to the master analysis (Chonghao owns it). | Done: [preregistration.md](docs/statistics/preregistration.md) §5.3 and §7 items 10-11 (reporting rules for the master analysis) |
| **Richard Zhao** | Ensure a fixed, reproducible SLM + prompt version runs throughout; confirm prompts are version-controlled files, not undocumented inline edits. Continue the RAG/agentic variant comparison begun in Week 7 (Section 6); keep each variant's build reproducible and version-controlled, same as the base SLM. | Done: [model_manifest.yaml](backend/slm/model_manifest.yaml), versioned prompts in `backend/slm/prompts/`, [week9-variant-quality-comparison.md](docs/slm/week9-variant-quality-comparison.md) |
| **Sheng Wang** | Support sessions; log issues without live-patching. | Done: [week9-evaluation-ui-issues.md](docs/ui/week9-evaluation-ui-issues.md) |
| **Yuktha Naveen** | Confirm and record exactly what was checked for the no-data-leaves-local claim, including any dependencies added since Week 4. | Done: Week 9 re-check in [master-test-register.md](docs/privacy/master-test-register.md); the final-build sign-off is open, [release checklist §11](docs/release/release-candidate-checklist.md#11-remaining-before-freeze) |
| **Chonghao Shen** | Run the main evaluation over a one-to-two week window using rostered-pair sessions with the 8 team members (rotating pair combinations; no external participants) — per client feedback, completing every planned session is not required; representative examples, case studies, and patterns are an acceptable substitute for full completion. Own the master analysis, honestly scoped to what was actually run; record the full version manifest, including which of the four architecture variants (Base LLM, RAG, agentic, RAG+agent — see `build-reference.md` Section 6) each session's build corresponds to. | Done: [session-responses.csv](docs/evaluation/results/main-evaluation/session-responses.csv) (variant and build per row), [pass-threshold-summary.md](docs/evaluation/results/main-evaluation/pass-threshold-summary.md) |
| **Honglin Lu** | Write the Progress Report using genuinely-run session data — per client feedback this no longer requires a fixed, fully-completed schedule; report honestly what was actually run, including partial coverage, rather than overclaiming completeness. | Closed: course deliverable submitted outside this repository (Progress Report) |
| **Priyansh Khandelwal** | Review/merge PRs; submit the Progress Report. Coordinate the RAG/agentic comparison thread's integration points across Richard's and Honghao's work, per the confirmed Week 7+ direction. | Done: PRs reviewed and merged; RAG/agentic coordination ([final-slm-methodology.md](docs/slm/final-slm-methodology.md)). Progress Report submission: Closed: course deliverable submitted outside this repository |

---

## Week 10 — Targeted Fixes + Smoke-Test

Targeted fixes and an honestly-framed smoke-test round. First of two cross-training sessions.

| Person | Task | Status (16 Oct 2026) |
|---|---|---|
| **Honghao Li** | Fix pipeline issues found during the main evaluation. Continue data-store/retrieval-source work for the RAG/agentic comparison in parallel (`build-reference.md` Section 6). | Done: the main evaluation found no pipeline issue (12 of 12 passes, [pass-threshold-summary.md](docs/evaluation/results/main-evaluation/pass-threshold-summary.md)) |
| **Moe Tanaka** | Complete the statistical write-up of the main evaluation results. | Done: [main-evaluation-statistical-writeup.md](docs/statistics/main-evaluation-statistical-writeup.md) |
| **Richard Zhao** | Fix guardrail/response-quality issues — most important category. If ahead of schedule, try few-shot examples in the prompt as a first, cheap improvement, and run the zero-shot-vs-few-shot comparison harness, filling in the Week 8 results table. Build and test the conversational multi-turn "memory" feature only inside a separate, standalone benchmark/test script — do NOT wire it into the real app used for the Tianyi demo (Week 7), so the demo build stays untouched and stable. Jointly with Yuktha Naveen, review this multi-turn work specifically for cross-message data leakage before it goes any further. Continue the RAG/agentic variant comparison (Section 6) in parallel, on its own branch — same non-interference rule as the multi-turn memory work: it does not touch the Tianyi demo build unless/until explicitly promoted. | Done: guardrail fixes (policy 0.3.2/0.3.3, `tests/slm/test_dev_50q.py`); Z/F comparison and multi-turn script ([final-slm-methodology.md](docs/slm/final-slm-methodology.md) §3.2-3.3); cross-message leakage checked by `tests/api/test_cross_message_isolation.py` and the multi-turn run (0 leaked numbers) |
| **Sheng Wang** | Fix UI issues found during the main evaluation. | Done: PR #78 (model selector), PR #80 (whole numbers), [final-build-screenshots.md](docs/ui/final-build-screenshots.md) |
| **Yuktha Naveen** | Write up the privacy-perception findings. Jointly with Richard, review the standalone multi-turn conversational-memory test script for cross-message/participant data leakage — this stays out of the demo build. | Closed: privacy is assured through technical verification ([pass-threshold-summary.md](docs/evaluation/results/main-evaluation/pass-threshold-summary.md#privacy-perceptions)); no questionnaire scores were collected. Multi-turn leakage: see SLM row; the offline test is in the sign-off, [release checklist §11](docs/release/release-candidate-checklist.md#11-remaining-before-freeze) |
| **Chonghao Shen** | Run a small second round (5-8 rostered team sessions, same 8 team members rotating pairs) re-testing the exact failed scenarios — framed as a directional smoke-test, not proof. Consistent with the client's reduced-workload allowance, this stays a small, honestly-framed round, not expanded back into a fixed full schedule. | Closed: waived, no failed scenario left to re-test ([pass-threshold-summary.md](docs/evaluation/results/main-evaluation/pass-threshold-summary.md#second-smoke-test-round-weekly-plan-week-10)) |
| **Honglin Lu** | Begin drafting the Final Report's core sections. Organise cross-training session 1 of 2 (45-60 minutes). | Final Report draft: Closed: course deliverable submitted outside this repository. Cross-training session 1: Closed, internal team activity, not tracked in the repository |
| **Priyansh Khandelwal** | Review/merge PRs; run full regression tests. | Done: CI run `38833421820` (all 4 stages), boot test in [release checklist §11](docs/release/release-candidate-checklist.md#11-remaining-before-freeze) |

---

## Week 11 — Finalise

Run the LAST guardrail check early, against the previously-untouched held-out prompt set for the first time. Rehearse the actual demo hardware.

| Person | Task | Status (16 Oct 2026) |
|---|---|---|
| **Honghao Li** | Final pipeline pass and methodology documentation. | Done: [final-pipeline-methodology.md](docs/data-pipeline/final-pipeline-methodology.md) |
| **Moe Tanaka** | Final statistical methodology write-up. | Done: [final-statistical-methodology.md](docs/statistics/final-statistical-methodology.md) |
| **Richard Zhao** | Run the final guardrail check early this week using the held-out prompt set for the first time. Fix and re-verify with time to spare. Fold the Week 10 zero-shot-vs-few-shot, standalone conversational-multi-turn-reasoning, and Base-LLM/RAG/agentic variant-comparison results into the final methodology write-up. Fine-tuning: now settled as declined per client confirmation (GPU access unavailable — see `build-reference.md` Section 10); not a conditional stretch goal to revisit this week. | **Open:** held-out safety check on the final build, [release checklist §11](docs/release/release-candidate-checklist.md#11-remaining-before-freeze). Done: results folded into [final-slm-methodology.md](docs/slm/final-slm-methodology.md) |
| **Sheng Wang** | Final UI polish and consistency pass. | Done: final-build UI ([final-build-screenshots.md](docs/ui/final-build-screenshots.md)) |
| **Yuktha Naveen** | Write the Final Report's privacy, limitations, and risks discussion. | Closed: course deliverable submitted outside this repository (Final Report section) |
| **Chonghao Shen** | Finalise the evaluation results section, including the Base-LLM/RAG/agentic variant comparison honestly scoped to what was actually run under the client-approved reduced evaluation workload; cross-check consistency across all documents. | Done: [pass-threshold-summary.md](docs/evaluation/results/main-evaluation/pass-threshold-summary.md) with the variant comparison; documentation consistency pass recorded in [final-submission-checklist.md](docs/release/final-submission-checklist.md) |
| **Honglin Lu** | Draft the bulk of the Final Report; script and record the demo video. Draft the Presentation slides now. Organise cross-training session 2 of 2. | Closed: course deliverable submitted outside this repository (Final Report, demo video, slides). Cross-training session 2: Closed, internal team activity, not tracked in the repository |
| **Priyansh Khandelwal** | Review/merge PRs; run a full end-to-end regression test. Preload and boot-test the model on the actual demo machine. | Done: regression and boot test on the group lead's machine, [release checklist §11](docs/release/release-candidate-checklist.md#11-remaining-before-freeze) |

---

## Week 12 — Buffer, Polish, Rehearsal Only

The model/prompt version is locked from Week 11 — no exceptions.

| Person | Task | Status (16 Oct 2026) |
|---|---|---|
| **Honghao Li** | Final documentation pass on the pipeline; no functional changes. | Done: [final-pipeline-methodology.md](docs/data-pipeline/final-pipeline-methodology.md) |
| **Moe Tanaka** | Final documentation pass on the statistical methodology; no functional changes. | Done: [final-statistical-methodology.md](docs/statistics/final-statistical-methodology.md), [week7-calibration-concerns.md](docs/statistics/week7-calibration-concerns.md) |
| **Richard Zhao** | Final documentation pass on SLM/guardrail behaviour; no new testing or model changes this week. | Done: [final-slm-methodology.md](docs/slm/final-slm-methodology.md) |
| **Sheng Wang** | Final UI/UX documentation and screenshots. | Done: [final-build-screenshots.md](docs/ui/final-build-screenshots.md) |
| **Yuktha Naveen** | Final privacy/security summary; no new checks. | **Open:** final privacy summary is part of the privacy sign-off, [release checklist §11](docs/release/release-candidate-checklist.md#11-remaining-before-freeze) |
| **Chonghao Shen** | Finalise all evaluation writeups; ensure consistency across every document. | Done: [pass-threshold-summary.md](docs/evaluation/results/main-evaluation/pass-threshold-summary.md), [statistical write-up](docs/statistics/main-evaluation-statistical-writeup.md) |
| **Honglin Lu** | Finalise the Final Report, Presentation (drafted in Week 11), and demo video (editing/polish only). Confirm the AI Acknowledgement statement is present everywhere required. | Closed: course deliverable submitted outside this repository (Final Report, Presentation, demo video); repository AI acknowledgement: [ai-acknowledgement.md](docs/proposal/ai-acknowledgement.md) |
| **Priyansh Khandelwal** | Coordinate the final submission checklist; run the full team rehearsal for the Presentation and Oral Defence. | Done: [final-submission-checklist.md](docs/release/final-submission-checklist.md). Presentation rehearsal: Closed: course deliverable submitted outside this repository |

---

## Canvas Checkpoints This Plan Is Built Around

- Week 5 (Sep 6): Group Proposal Report due
- Week 8 (Oct 4): Project Status Checking 2 due
- Week 9 (Oct 11): Group Progress Report due
- Week 12+ (per the shared tracker's confirmed dates): Final Report, Artifacts, Demo Video, Presentation, Oral Defence
