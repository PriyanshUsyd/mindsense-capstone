# MindSense Project Progress Report Outline

**Template:** COMP5703 Group-Based Capstone Project Progress Report  
**Coordinator:** Honglin Lu  
**Status:** Week 7 initial outline  
**Reporting basis:** Group Proposal, frozen build evidence and verified pilot-testing results

## 1. Progress and Achievements

> The final Word version of this section must be at least three pages and must explain progress against the aims, objectives, scope and expected outcomes stated in the Group Proposal.

### 1.1 Progress Against the Project Proposal

- Restate the original project aim and objectives briefly.
- Identify which proposal objectives have been completed, are in progress or remain planned.
- Explain whether the current frozen build remains within the agreed project scope.

### 1.2 Data Pipeline and Behavioural Features

- Travel-distance feature implementation.
- Phone-unlock feature implementation.
- Timestamp correction, missing-data handling and outlier filtering.
- Evidence supporting the selection of the final two features.
- Current limitations of the data pipeline.

### 1.3 Personal Baseline and Statistical Modelling

- Within-person comparison approach.
- Personal historical baseline logic.
- Mixed-effects modelling progress.
- Missing-data and cold-start handling.
- Calibration or accuracy concerns identified during pilot testing.

### 1.4 Local Language Model and Safety Controls

- Local model integration status.
- Evidence-grounded response generation.
- General fallback response.
- Crisis-related fallback response.
- Guardrail and prohibited-question testing.
- Known limitations and remaining validation work.

### 1.5 User Interface and End-to-End Integration

- Chat interface implementation.
- Connection between frontend, backend and local model.
- Normal-case and missing-data workflows.
- Demo-machine preparation.
- Interface issues identified during the pilot.

### 1.6 Privacy and Security

- Local-first architecture.
- Network-egress controls.
- Logging and telemetry restrictions.
- Dependency review.
- Results of the Week 7 frozen-build privacy and security check.

### 1.7 Evaluation and Week 7 Pilot Testing

- Pilot objectives.
- Pairing and observation process.
- Runbook and crisis-response procedure.
- Scenarios tested.
- Verified preliminary results.
- Safety, usability, trust, calibration and accuracy observations.
- Issues assigned for Week 8.

### 1.8 RAG and Agent Comparison Work

- Base answering method.
- Retrieval-enhanced method.
- Agent-directed method.
- Combined retrieval and agent method.
- Data-storage and retrieval scoping.
- Planned comparison criteria and current implementation status.

### 1.9 Summary of Achievements

Summarise the main verified achievements without presenting planned or incomplete work as completed.

## 2. Obstacles

> Explain the significant obstacles encountered, their impact, supporting evidence, mitigation and contingency plan.

### 2.1 Data and Technical Obstacles

- Dataset alignment and timestamp problems.
- Missing or inconsistent sensing data.
- Outlier handling.
- Local model and hardware limitations.
- Frontend and backend integration issues.

### 2.2 Statistical and Evaluation Obstacles

- Limited participant-level data.
- Cold-start limitations.
- Calibration and uncertainty.
- Small pilot sample.
- Held-out test restrictions.

### 2.3 Privacy, Safety and Dependency Risks

- Risk of unintended network communication.
- Dependency and telemetry risks.
- Unsupported, causal or diagnostic model outputs.
- Crisis-response risks.

### 2.4 Client, Scheduling and External Dependencies

- Client feedback affecting project direction.
- Unavailable GPU resources and the decision not to fine-tune.
- Dependencies between team components.
- Availability of team members for pilot sessions.

### 2.5 Mitigation and Contingency Plans

For every major obstacle, record:

- evidence;
- impact;
- mitigation already attempted;
- current status;
- responsible team member;
- contingency if the mitigation fails.

## 3. Deviation to Timeline

> Compare current progress with the timeline in the Group Proposal. Explain why each meaningful change occurred and how it affects delivery.

### 3.1 Comparison With the Original Timeline

Identify activities that were completed on time, moved, reduced, extended or added.

### 3.2 Reasons for Deviations

Possible reasons include:

- build-freeze requirements;
- client feedback;
- technical integration dependencies;
- data-quality problems;
- model or hardware constraints;
- pilot scheduling;
- the addition of the RAG and agent comparison.

### 3.3 Impact on the Project

Explain the impact on:

- scope;
- deliverables;
- evaluation;
- team workload;
- final demonstration;
- final report.

### 3.4 Recovery Actions

Document revised priorities and the actions planned to prevent further delay.

## 4. Milestones and Reporting

> Replace the sample table in the Word template with the team’s real milestone plan. Changes from the original proposal should be clearly identified in the final Word version.

| Milestone | Tasks | Reporting or Evidence | Date | Status or Change |
|---|---|---|---|---|
| Week 4 | Initial component design and documentation | Repository documentation and client update |  | Completed |
| Week 5 | Group Proposal preparation | Proposal draft and component review |  | Completed |
| Week 6 | Integration and Group Proposal submission | Frozen-build evidence and submitted proposal |  | Completed |
| Week 7 | Pilot testing and Progress Report outline | Pilot log, safety and privacy checks, report outline |  | In progress |
| Week 8 | Address verified pilot issues | Updated tests and implementation evidence |  | Planned |
| Week 9 | Progress Report completion | Final Progress Report |  | Planned |
| Week 10 | Extended evaluation and method comparison | Comparison results |  | Planned |
| Week 11 | Final validation and documentation | Validation evidence and demonstration material |  | Planned |
| Week 12 | Final demonstration and reporting | Final presentation, report and demonstration |  | Planned |

## Evidence Still Required

- Frozen-build commit or tag.
- Pilot session dates and participant pairs.
- Test scenarios and pass or fail results.
- Screenshots, logs or pull-request links.
- Privacy and security verification results.
- Guardrail re-test results.
- Calibration and accuracy observations.
- User-interface observations.
- RAG and agent comparison progress.
- Confirmed timeline changes and their reasons.

## Writing Rules

- Report only verified results.
- Clearly distinguish completed, in-progress and planned work.
- Do not use held-out test questions before the scheduled evaluation.
- Do not make clinical-validity claims.
- Link technical claims to repository evidence where possible.
- Transfer the final content into the official Word template without changing its required formatting.

