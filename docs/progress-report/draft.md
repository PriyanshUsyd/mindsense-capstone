# MindSense Progress Report — Working Draft

**Coordinator:** Honglin Lu  
**Status:** Working draft — update only with verified evidence  
**Submission format:** Transfer the reviewed content into the official Word template

> Writing rule: distinguish clearly between completed, in-progress, planned and pending work. Do not include participant names, individual questionnaire responses, raw screenshots or raw `/respond` JSON.

## 1. Progress and Achievements

### 1.1 Progress Against the Project Proposal

MindSense aims to develop a privacy-preserving conversational assistant that helps users understand relationships between their smartphone behaviour and wellbeing. The system is designed to operate locally, compare each person against their own historical baseline, and avoid unsupported causal, diagnostic or treatment-related claims.

The original proposal defined six main objectives: developing a behavioural data pipeline, implementing within-person statistical modelling, integrating a locally deployed small language model, enforcing evidence and safety controls, building a conversational interface, and conducting a staged evaluation. Substantial progress has been made across all technical components. The data pipeline, two-feature Tier-1 specification, statistical eligibility rules, local model pathway, response guardrails and user interface have been implemented and tested. The remaining work is primarily final evaluation, quantitative comparison of response variants, final privacy sign-off and consolidation of results into the report.

The current system remains within the agreed proof-of-concept scope. It is not intended to diagnose mental illness, recommend treatment or replace professional care. Its purpose is limited to describing supported patterns in a user’s own behavioural history and explicitly communicating when insufficient evidence is available.

### 1.2 Data Pipeline and Behavioural Features

The team completed an end-to-end pipeline for converting CES smartphone sensing records into behavioural features aligned with repeated PHQ-4 assessments. The dataset contains 216,065 participant-day records from 220 participants and 35,348 valid PHQ-4 observations from 218 participants.

Two cross-platform behavioural features were selected for the locked Tier-1 feature set:

1. daily distance travelled, derived from GPS records; and  
2. daily phone-unlock count.

GPS records are subject to a minimum location-quality requirement of 12 observed hours per day. Implausible distances above 500,000 metres per day are treated as missing, while participant-specific first and ninety-ninth percentiles are used for winsorisation. Negative unlock counts are treated as missing, whereas genuine zero-unlock days are retained.

Features are aggregated using a 14-day trailing window ending one day before each PHQ-4 assessment. The assessment day is excluded to avoid temporal leakage, and at least seven valid sensing days are required. Under the final 500-kilometre GPS cutoff, the pipeline produced 28,337 valid GPS windows across 214 participants. The unlock pipeline produced 34,235 valid windows. Sensitivity checks using 250-, 500- and 1,000-kilometre GPS thresholds produced similar participant coverage and did not reverse the direction of the observed association.

A home-duration feature was also implemented and tested as a candidate feature. However, it was not included in the locked Tier-1 set and should not be described as a final system feature.

### 1.3 Personal Baseline and Statistical Modelling

The statistical component uses within-person comparison rather than population-level norms. A 14-day feature window was selected to correspond to the PHQ-4 recall period. The modelling specification uses mixed-effects models with participant-level random intercepts and random slopes, together with a Mundlak within/between decomposition. This structure separates temporary deviations from an individual’s usual behaviour from stable differences between people.

Eligibility rules prevent the system from presenting comparisons before sufficient personal history is available. Comparative baseline statements require at least 28 calendar days, at least 20 valid sensor days and at least three completed assessments. Stronger historical-relationship claims require at least 56 days, at least 40 valid sensor days and eight assessments spanning at least 28 days.

The system distinguishes three cold-start states. State A provides only a general templated response when there is too little sensing or wellbeing data. State B can describe recent observations but must state that it is too early to make a baseline comparison. State C permits personal-baseline comparisons, while historical relationship claims remain conditional on the stronger evidence gate.

Bootstrap standard-error caching has been implemented in the statistical runner and is stored locally outside Git. However, the completed cache is not yet connected to the live `/respond` pathway. Therefore, bootstrap-based `evidence_available` responses should not yet be described as part of the evaluated live system. A fresh full B=500 rebuild and final integration remain pending.

### 1.4 Local Language Model and Safety Controls

The local language-model component communicates validated evidence through a structured EvidencePacket rather than receiving raw sensing or PHQ-4 records. The current implementation supports four response variants: Base, RAG, Agent and combined RAG-Agent. RAG is the default for the Ollama-backed pathway.

Retrieval is restricted to the supplied evidence packet. It does not use an external corpus, independent history store or cloud-based data source. Agent behaviour is similarly bounded and deterministic rather than operating as an autonomous planner.

The safety layer checks the user’s question, available evidence and generated response. Requests involving diagnosis, unsupported causation, crisis language, unavailable evidence or unsupported time windows are redirected to controlled responses. If approved context is unavailable, the system fails safely without invoking the language model.

Focused verification reported 459 tests passing with two deprecation warnings. Synthetic packet smoke tests achieved 8/8 successful cases for both Phi and Qwen after the question-policy correction. These results demonstrate functional integration and guardrail behaviour only; they do not establish model superiority or human-rated response quality.

The planned zero-shot and few-shot comparison has not yet been run. Its result tables must remain marked as pending until genuine experimental evidence becomes available.

### 1.5 User Interface and End-to-End Integration

A conversational web interface has been connected to the backend and local Ollama model. Demo-machine verification confirmed that the frontend loaded successfully and handled GPS uncertainty, phone-unlock uncertainty, diagnosis refusal and multi-turn presentation.

Frontend testing, linting and the production build passed during Week 8 hardening. A later Mac verification confirmed that the local scientific Python environment imported correctly and that a development GPS fixture returned a normal response within the 180-second target without using fallback behaviour.

The Week 7 pilot identified an excessive-decimal-precision presentation issue and showed that explicit unsupported time windows were not initially routed correctly. Subsequent guardrail documentation and tests introduced clearer handling of unsupported time windows. Final confirmation on the release-candidate build remains part of the evaluation process.

Dataset provisioning across every evaluation machine remains a dependency. This must be completed before the remaining evaluation sessions begin.

### 1.6 Privacy and Security

MindSense follows a local-first architecture. During the tested demo workflow, Ollama, the backend and the frontend were restricted to loopback communication. Chat content remained in transient interface state, and the reviewed workflow did not write conversations into browser storage.

Raw sensing data, participant-level bootstrap records, screenshots and full `/respond` outputs are not intended for the public repository. Only de-identified aggregate results, such as medians, ranges, response counts and safety failures, should be committed. Existing privacy checks also confirmed that Week 9 workflow logs did not contain user questions, participant markers, evidence identifiers, credentials or tracebacks; the raw logs were subsequently deleted.

The privacy review applies to a trusted operator running the prototype locally on a single machine. It does not constitute approval for a public deployment, user accounts, external data sources or multi-user operation. A final privacy sign-off on the release-candidate build remains pending.

### 1.7 Evaluation and Pilot Testing

A rostered-pair pilot was conducted on 20 September 2026 using the local Phi model and de-identified CES data. The pilot examined routing, evidence use, refusal behaviour and the practical evaluation procedure.

The phone-unlock question passed and returned the correct evidence while explaining that insufficient history was available for a baseline comparison. The unsupported three-day question failed because the system initially substituted the default GPS window rather than explicitly refusing the unsupported time period. The diagnosis-seeking question produced an appropriate user-visible refusal, although its internal classification was recorded as off-topic rather than diagnosis-seeking.

The pilot also confirmed that the evaluation procedure was understandable and exposed concrete issues before the main sessions. However, it was a lightweight, screenshot-mediated pilot and did not include the final questionnaire. It should therefore not be presented as evidence of overall user satisfaction or system effectiveness.

The main ME-P01–ME-P04 sessions, aggregate questionnaire analysis and held-out guardrail evaluation are still pending. When completed, only aggregate results should be added to the repository and report.

### 1.8 RAG and Agent Comparison

The repository now contains implementations for four controlled variants: Base, RAG, Agent and RAG-Agent. These variants use the same local architecture and safety boundaries, allowing the contribution of retrieval and bounded tool use to be examined without changing the overall privacy model.

Synthetic smoke tests demonstrate that the variants can be invoked, but they do not provide sufficient evidence for a quality comparison. The planned 24-prompt held-out evaluation and human-rating analysis must be completed before recommending one variant over another or claiming that RAG or agent behaviour improves response quality.

### 1.9 Summary of Current Achievements

By Week 9, the project has delivered:

1. an end-to-end behavioural data pipeline;
2. a locked two-feature Tier-1 specification;
3. within-person statistical and cold-start eligibility rules;
4. a locally deployed conversational pathway;
5. evidence-bound retrieval and bounded agent variants;
6. deterministic safety and fallback controls;
7. an integrated chat interface;
8. local privacy and logging controls; and
9. a completed pilot that identified actionable integration issues.

The principal remaining activities are the main rostered-pair evaluation, questionnaire aggregation, held-out variant comparison, final release-candidate privacy verification and completion of the report’s result-dependent sections.

## 2. Obstacles

Several significant obstacles affected delivery.

First, missing and inconsistent sensing data required explicit quality gates, missing-value handling and participant-specific outlier treatment. This reduced the number of valid analysis windows but prevented low-quality data from being presented as meaningful personal evidence.

Second, platform differences limited the usable feature set. Some candidate features, including call and SMS information, were not consistently available across iOS and Android. The project therefore retained only GPS distance and phone-unlock frequency as the locked cross-platform features.

Third, personal-baseline inference is limited during cold start. The team addressed this through staged eligibility rules that prevent numerical or historical claims when the required amount of personal data is unavailable.

Fourth, local model execution created hardware and latency constraints. Testing showed that the system could operate on the demo machine, but model loading and cold-start performance required additional hardening and careful preparation of evaluation machines.

Fifth, the pilot exposed integration problems that unit tests alone had not detected, including unsupported time-window handling and presentation precision. These findings led to further response-policy and interface work before the main evaluation.

Finally, ethics approval for external participant recruitment was not available. The evaluation design was consequently changed to team-only rostered pairs. This reduced the generalisability of the human evaluation and means that the findings must be presented as internal proof-of-concept evidence rather than validation with an external user population.

## 3. Deviation to Timeline

The project’s foundational components were implemented broadly in line with the proposal, but the evaluation schedule and some integration work changed.

External participant evaluation was replaced with team-only rostered-pair sessions because external recruitment was not approved. The evaluation build was also locked to protect the validity of the sessions, which meant that some non-critical statistical wiring—particularly bootstrap standard errors in `/respond`—was deferred until after evaluation.

The RAG and agent comparison introduced additional implementation and documentation work. Although the four variants are available, their final quality comparison depends on the pending held-out evaluation. The main questionnaire analysis and final privacy sign-off were also moved later because they depend on completion of the rostered sessions and the release-candidate build.

These changes do not alter the project’s central scope: a local, non-diagnostic and evidence-constrained prototype. However, they reduce the strength of claims that can be made about external user acceptance and require the final report to distinguish clearly between implemented functionality, internal evaluation evidence and work that remains pending.

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
