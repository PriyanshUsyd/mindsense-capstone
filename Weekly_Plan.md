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

---

## Week 4 — Scope & Risk Lock

Every foundational decision that gates later work gets made concretely this week, not just researched.

| Person | Task |
|---|---|
| **Honghao Li** (Data) | Re-verify CES against the real, current copy of the data (participant count, PHQ-4 repeat density, feature completeness). Confirm the fallback dataset (Corona Health) by Wednesday if CES fails any check. |
| **Moe Tanaka** (Stats) | Name the exact statistical model now: mixed-effects with person-level random intercepts, person-mean-centred predictors. Define the minimum baseline window as a specific number of days. Draft the three-state cold-start policy: below-window = templated "not enough data" only; partial history = descriptive summary with explicit "too early to compare" language; full history = comparative statements allowed. |
| **Richard Zhao** (SLM) | Confirm Ollama + phi4-mini:3.8b as the local model. Design TWO fallback templates: a generic refusal, and a separate crisis-aware template with real helpline/support-resource content, drafted now. |
| **Sheng Wang** (UI) | Design (not build yet) the 7 required chat states: normal, insufficient-data/cold-start, uncertainty, refusal, generic fallback, crisis-aware fallback. Set up the Vite + React + TypeScript scaffold. |
| **Yuktha Naveen** (Privacy) | Draft privacy/architecture principles (network calls, telemetry, logs, dependencies). Run the real-machine SLM latency benchmark. Establish the ongoing rule: any PR adding a new dependency includes a 10-minute privacy spot-check in its description. |
| **Chonghao Shen** (Evaluation) | Freeze the adversarial taxonomy and expected response class per case. Pre-register the pass-threshold rule now (e.g. high-severity categories 100%; softer categories a fixed percentage). Set aside 20-30 prompts as a held-out set, never touched until Week 11. Draft a one-page participant information sheet and a facilitator crisis-response script. |
| **Honglin Lu** (Docs) | Set up the GitHub repo, branch protection, and skeleton per the repository structure in `build-reference.md`. Begin the Proposal outline. |
| **Priyansh Khandelwal** (Integration/QA) | Facilitate the evidence contract freeze meeting — tag `contract-v1.0.0` by Wednesday. Schedule the Tier 1 feature-list confirmation for Wednesday of Week 5. Hard cap confirmed: maximum 2 cross-platform features (GPS distance, unlock events) unless a third genuinely meets the same standard. |

**SLM decision update (2026-08-30):** the row above records the original Week 4 plan. The role owner has not approved Phi-4 Mini as the final model. Ollama is confirmed as the local runtime; `phi4-mini:3.8b` remains the pinned baseline and `qwen3:4b` the pinned challenger until a larger fixed evaluation supports a final choice.

---

## Week 5 — Group Proposal Report Due (Sep 6)

Narrow vertical slice: happy path + missing-data case only. Safety logic for prohibited requests is tested now, at the model/template layer, independent of the UI.

| Person | Task |
|---|---|
| **Honghao Li** | Build ONE feature end-to-end (GPS distance), including real cleaning (timestamp alignment, missing-sensor handling, outlier filtering). Confirm the final 2-feature Tier 1 list against the real schema by Wednesday. |
| **Moe Tanaka** | Implement baseline/evidence logic for that one feature using the named statistical model. |
| **Richard Zhao** | Build the SLM stub and both fallback templates as a shadow build. Run the prohibited-request portion of the adversarial suite against the model/template layer this week. |
| **Sheng Wang** | Integrate the UI against the real SLM stub; build the "normal response" state fully. Rough sketches of other states are fine but not required to work yet. |
| **Yuktha Naveen** | Document the privacy architecture; confirm Week 4's latency and dependency-audit results. |
| **Chonghao Shen** | Finalise the suite (held-out set stays untouched) and run it internally for a baseline reading. Jointly with Richard, judge baseline responses together and document 2-3 cases where judgment differed. |
| **Honglin Lu** | Compile the Group Proposal Report — primary focus this week. Include the AI Acknowledgement statement. |
| **Priyansh Khandelwal** | Confirm the vertical slice works for the happy path and a missing-data case. Confirm Week 5 prohibited-request tests pass even without full UI. Sign off the final 2-feature list. Review/merge PRs; submit the Proposal. |

---

## Week 6 — Build Tier 1, Freeze

Implement the signed-off feature list. Hard freeze at week's end. Build both fallback UI states and the actual cold-start rules — not just placeholders.

| Person | Task |
|---|---|
| **Honghao Li** | Implement the signed-off 2-feature set fully. Hard freeze at week's end. Anything beyond it is Tier 2/stretch. |
| **Moe Tanaka** | Extend baseline/evidence logic to both features. Write the three-state cold-start policy into actual working logic. |
| **Richard Zhao** | Iterate prompts using the Week 5 baseline against the pre-registered thresholds. Both fallback templates become fully functional. Build the deterministic response health-check tied to explicit evidence-contract violations. |
| **Sheng Wang** | Build the cold-start, insufficient-data, refusal, and both fallback UI states — visually distinct from each other and from normal responses. |
| **Yuktha Naveen** | Jointly with Priyansh Khandelwal, build the automated privacy/regression check and a lightweight per-PR gate (build + integration test + guardrail subset). |
| **Chonghao Shen** | Draft and internally test the evaluation rubric, built directly around the client's 10 named criteria (see build-reference.md Section 9: accuracy/faithfulness, comprehensibility, usefulness, perceived personal relevance, trust, uncertainty communication, correlation-vs-causation distinction, inappropriate mental-health inference, usability, privacy perceptions) - not a rubric invented independently of the spec. Finalise the evaluation-data-source decision (synthetic vs. de-identified real extract). Draft the one-page session runbook. Increase planned pilot to 4-5 participants. |
| **Honglin Lu** | Update documentation to reflect the frozen Tier 1 architecture. |
| **Priyansh Khandelwal** | Review/merge PRs; run integration tests confirming the complete Tier 1 set and both fallback UI states work end-to-end. Confirm the adversarial suite runs as a scripted/batch process. |

---

## Week 7 — Pilot

Pilot (4-5 participants) against a frozen build, using the tested rubric and session runbook. Recruitment for the main evaluation starts now.

| Person | Task |
|---|---|
| **Honghao Li** | No new features (frozen). Fix only critical/blocking bugs on a separate branch. |
| **Moe Tanaka** | Support the pilot; log calibration concerns for Week 8, no live changes. |
| **Richard Zhao** | Re-test guardrails (scripted run) against the frozen build; held-out set stays reserved. Continue fallback refinement. |
| **Sheng Wang** | Support the pilot; log UI issues for Week 8. |
| **Yuktha Naveen** | Run the full privacy check against the frozen build. |
| **Chonghao Shen** | Run the pilot using the session runbook and crisis-response script. Check protocol health after the first participant. Start main-evaluation recruitment in parallel. |
| **Honglin Lu** | Begin the Progress Report outline using real pilot findings. |
| **Priyansh Khandelwal** | Pilot-fix intake with triage: critical/blocking issues get a full linked-issue process; minor polish items go into a simple batch checklist. |

---

## Week 8 — Status Checking 2 Due (Oct 4)

Hardening from pilot feedback. Both fallback templates tested end-to-end, including a simulated crisis trigger.

| Person | Task |
|---|---|
| **Honghao Li** | Fix pipeline issues found during the pilot. |
| **Moe Tanaka** | Fix statistical calibration issues found during the pilot. |
| **Richard Zhao** | Fix guardrail failures using the Week 4 pre-registered thresholds (not renegotiated after the fact). Confirm fail-safe defaults to the safe template on ambiguous cases. |
| **Sheng Wang** | Fix UI issues found during the pilot. |
| **Yuktha Naveen** | Run the final privacy verification. |
| **Chonghao Shen** | Confirm recruitment on track; roster 2-person facilitation teams for the 10-15 main sessions. Test both fallback templates end-to-end — simulate a generic SLM failure and a crisis-trigger case. |
| **Honglin Lu** | Prepare and submit Project Status Checking 2, with honest reporting of any deviation. |
| **Priyansh Khandelwal** | Review/merge PRs; confirm the release-candidate checklist is met. Lock the rule: all Week 9 sessions complete at least 2 working days before the Progress Report deadline. |

---

## Week 9 — Group Progress Report Due (Oct 11)

Main evaluation on a version-locked build, submitted after sessions are genuinely complete.

| Person | Task |
|---|---|
| **Honghao Li** | Freeze the pipeline; record the feature-code version. |
| **Moe Tanaka** | Support logistics; provide the quantitative angle to the master analysis (Chonghao owns it). |
| **Richard Zhao** | Ensure a fixed, reproducible SLM + prompt version runs throughout; confirm prompts are version-controlled files, not undocumented inline edits. |
| **Sheng Wang** | Support sessions; log issues without live-patching. |
| **Yuktha Naveen** | Confirm and record exactly what was checked for the no-data-leaves-local claim, including any dependencies added since Week 4. |
| **Chonghao Shen** | Run the main evaluation (10-15 participants) with rostered 2-person facilitation. Own the master analysis; record the full version manifest. |
| **Honglin Lu** | Write the Progress Report using genuinely complete session data. |
| **Priyansh Khandelwal** | Review/merge PRs; submit the Progress Report. |

---

## Week 10 — Targeted Fixes + Smoke-Test

Targeted fixes and an honestly-framed smoke-test round. First of two cross-training sessions.

| Person | Task |
|---|---|
| **Honghao Li** | Fix pipeline issues found during the main evaluation. |
| **Moe Tanaka** | Complete the statistical write-up of the main evaluation results. |
| **Richard Zhao** | Fix guardrail/response-quality issues — most important category. If ahead of schedule, try few-shot examples in the prompt as a first, cheap improvement. |
| **Sheng Wang** | Fix UI issues found during the main evaluation. |
| **Yuktha Naveen** | Write up the privacy-perception findings. |
| **Chonghao Shen** | Run a small second round (5-8 participants) re-testing the exact failed scenarios — framed as a directional smoke-test, not proof. |
| **Honglin Lu** | Begin drafting the Final Report's core sections. Organise cross-training session 1 of 2 (45-60 minutes). |
| **Priyansh Khandelwal** | Review/merge PRs; run full regression tests. |

---

## Week 11 — Finalise

Run the LAST guardrail check early, against the previously-untouched held-out prompt set for the first time. Rehearse the actual demo hardware.

| Person | Task |
|---|---|
| **Honghao Li** | Final pipeline pass and methodology documentation. |
| **Moe Tanaka** | Final statistical methodology write-up. |
| **Richard Zhao** | Run the final guardrail check early this week using the held-out prompt set for the first time. Fix and re-verify with time to spare. See the fine-tuning note in `build-reference.md` for the conditional stretch goal. |
| **Sheng Wang** | Final UI polish and consistency pass. |
| **Yuktha Naveen** | Write the Final Report's privacy, limitations, and risks discussion. |
| **Chonghao Shen** | Finalise the evaluation results section; cross-check consistency across all documents. |
| **Honglin Lu** | Draft the bulk of the Final Report; script and record the demo video. Draft the Presentation slides now. Organise cross-training session 2 of 2. |
| **Priyansh Khandelwal** | Review/merge PRs; run a full end-to-end regression test. Preload and boot-test the model on the actual demo machine. |

---

## Week 12 — Buffer, Polish, Rehearsal Only

The model/prompt version is locked from Week 11 — no exceptions.

| Person | Task |
|---|---|
| **Honghao Li** | Final documentation pass on the pipeline; no functional changes. |
| **Moe Tanaka** | Final documentation pass on the statistical methodology; no functional changes. |
| **Richard Zhao** | Final documentation pass on SLM/guardrail behaviour; no new testing or model changes this week. |
| **Sheng Wang** | Final UI/UX documentation and screenshots. |
| **Yuktha Naveen** | Final privacy/security summary; no new checks. |
| **Chonghao Shen** | Finalise all evaluation writeups; ensure consistency across every document. |
| **Honglin Lu** | Finalise the Final Report, Presentation (drafted in Week 11), and demo video (editing/polish only). Confirm the AI Acknowledgement statement is present everywhere required. |
| **Priyansh Khandelwal** | Coordinate the final submission checklist; run the full team rehearsal for the Presentation and Oral Defence. |

---

## Canvas Checkpoints This Plan Is Built Around

- Week 5 (Sep 6): Group Proposal Report due
- Week 8 (Oct 4): Project Status Checking 2 due
- Week 9 (Oct 11): Group Progress Report due
- Week 12+ (per the shared tracker's confirmed dates): Final Report, Artifacts, Demo Video, Presentation, Oral Defence
