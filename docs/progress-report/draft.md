# MindSense Progress Report — Working Draft

**Coordinator:** Honglin Lu  
**Status:** Working draft — update only with verified evidence  
**Submission format:** Transfer the reviewed content into the official Word template

> Writing rule: distinguish clearly between completed, in-progress, planned and pending work. Do not include participant names, individual questionnaire responses, raw screenshots or raw `/respond` JSON.

## 1. Progress and Achievements

### 1.1 Progress Against the Project Proposal

[Draft the original project aim and objectives, then state which objectives are completed, in progress or planned. Link each completed claim to repository evidence.]

### 1.2 Data Pipeline and Final Features

[Summarise the GPS/travel-distance and phone-unlock features, timestamp correction, missing-data handling, outlier filtering and dataset provisioning.]

**Evidence status:** Partially available; confirm the latest data-pipeline PR/commit before finalising.

### 1.3 Personal Baseline and Statistical Modelling

[Explain the within-person baseline approach, statistical model, cold-start handling, calibration work and bootstrap caching.]

**Current limitation:** Bootstrap-based standard-error wiring into `/respond` was deferred until after the evaluation lock to preserve the fixed model and prompt configuration. Consequently, the four fixed evaluation questions do not exercise a bootstrap-based `evidence_available` response, and the live evaluation path returns `no_claim`.

### 1.4 Local Language Model, RAG and Safety Controls

[Describe local model integration, RAG as the evaluation default, grounding, fallback responses, crisis handling and guardrail testing. Avoid diagnostic or causal claims.]

**Pending evidence:** Real 24-prompt Base/RAG/Agentic/RAG+Agent comparison results and the final model recommendation.

### 1.5 User Interface and End-to-End Integration

[Describe frontend/backend/model integration, normal and missing-data workflows, demo-machine preparation and verified UI fixes.]

**Pending evidence:** Any new UI issues found during ME-P01–P04 sessions.

### 1.6 Privacy and Security

[Describe the local-first design, network-egress controls, logging restrictions and dependency review.]

**Privacy rule for evaluation evidence:** Commit only aggregated results. Keep individual ratings, participant-identifying session details, raw screenshots and raw response JSON out of the repository.

**Pending evidence:** Final privacy sign-off on the release-candidate build.

### 1.7 Evaluation and Pilot Testing

[Describe the runbook, pairing process, fixed questions, response-quality rubric and pass thresholds.]

**Pending evidence:**

- ME-P01–P04 session completion and dates;
- median, range and valid response count for each questionnaire category, excluding N/A;
- critical safety failures;
- repeated usability, trust, calibration or accuracy patterns.

### 1.8 Summary of Achievements

[Summarise only achievements supported by merged code, committed documentation or verified test results.]

## 2. Obstacles

### 2.1 Data and Technical Obstacles

[Cover timestamp alignment, missing sensing data, outliers, cold-start behaviour, local-model constraints and integration issues.]

### 2.2 Statistical and Evaluation Obstacles

[Cover limited participant-level data, calibration uncertainty, small team-only evaluation and held-out-test restrictions.]

### 2.3 Privacy and Safety Risks

[Cover unintended network communication, telemetry/dependency risks, unsupported claims and crisis-response risks.]

### 2.4 Mitigation and Contingency Plans

For every material obstacle, record the evidence, impact, mitigation, owner, current status and contingency.

## 3. Deviation to Timeline

[Compare the current schedule with the Group Proposal. Explain the evaluation lock, deferred `/respond` SE wiring, added four-variant comparison and dependencies between team components.]

## 4. Milestones

| Milestone | Task | Evidence | Status |
|---|---|---|---|
| Week 7 | Pilot preparation and report outline | Repository documentation | Completed |
| Week 8 | Pilot fixes and evaluation preparation | PRs, issue logs and test evidence | In progress — verify merged state |
| Week 9 | Evaluation lock and Progress Report drafting | RC build, report draft and evidence register | In progress |
| Week 10 | Evaluation completion and method comparison | Aggregated results and comparison tables | Pending |
| Week 11 | Final validation and documentation | Validation evidence | Planned |
| Week 12 | Final demonstration and reporting | Final report and presentation | Planned |

## 5. Pending Evidence Before Finalisation

- Evaluation-session results and aggregated questionnaire statistics;
- real four-variant comparison results;
- final RC-build privacy sign-off;
- final UI issue status;
- merged PR links and commit SHAs for each technical claim;
- confirmed timeline dates and changes.

## AI Acknowledgement

[Complete this section according to the unit’s required AI acknowledgement wording and accurately describe any permitted AI assistance.]
