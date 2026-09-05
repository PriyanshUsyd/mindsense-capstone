# Group Proposal Report

## 1. Introduction and Problem Statement

### 1.1 Background

Smartphones continuously generate behavioural information that may reflect changes in an individual’s daily routine, including mobility, distance travelled, device use and phone-unlocking patterns. When analysed longitudinally, these digital phenotyping measures can support reflection on how a person’s behaviour changes over time. However, raw sensing data and statistical results are often difficult for non-specialist users to understand. Conventional population-level comparisons may also overlook meaningful changes relative to an individual’s own historical patterns.

Conversational artificial intelligence offers a potentially accessible way to translate numerical behavioural evidence into understandable natural-language explanations. Its application to mental-health-related information nevertheless introduces significant challenges. Generated responses may overstate uncertain evidence, confuse association with causation, make unsupported diagnostic inferences or expose sensitive personal data to external services. A suitable system must therefore combine statistical validity, clear uncertainty communication, deterministic safety controls and privacy-preserving deployment.

### 1.2 Problem Statement

The client has proposed the development of a privacy-preserving conversational AI assistant for personalised digital mental health. The central problem is how to transform longitudinal smartphone sensing and wellbeing data into explanations that are understandable and personally relevant without making unsupported clinical, diagnostic or causal claims.

Existing mental-health dashboards commonly present numerical summaries or population comparisons that may be difficult for users to interpret. General-purpose cloud-based language models could make these results easier to understand, but transmitting sensitive sensing and wellbeing information to external services creates additional privacy risks. Furthermore, unconstrained language-model responses may introduce information that is not supported by the underlying statistical evidence.

MindSense addresses this problem by combining local data processing, personalised statistical analysis and a locally deployed Small Language Model (SLM). Instead of comparing a user only with a wider population, the proposed system examines current behavioural measurements against that individual’s historical baseline. Statistical results are transferred to the language-model layer through a structured evidence contract that specifies the available evidence, its uncertainty and the types of claims the system is permitted or prohibited from making.

The project is explicitly non-diagnostic. MindSense is not intended to diagnose a mental-health condition, predict clinical risk, recommend treatment or establish that a behavioural change caused a change in wellbeing. Its purpose is to help users explore supported patterns in their own longitudinal data while clearly communicating uncertainty and the distinction between association and causation.

### 1.3 Project Aim

The aim of MindSense is to design and evaluate an end-to-end prototype that converts longitudinal smartphone sensing and wellbeing data into safe, understandable and privacy-preserving conversational insights.

To achieve this aim, the project will:

1. process smartphone sensing data into interpretable behavioural features while preserving missingness and data-quality information;
2. align behavioural features with repeated wellbeing measurements;
3. estimate within-person behavioural changes and behavioural–wellbeing relationships using an appropriate longitudinal statistical model;
4. represent statistical findings through a versioned and validated evidence structure;
5. use a locally deployed SLM to translate approved evidence into understandable natural-language explanations;
6. apply deterministic safeguards to prevent unsupported diagnostic, causal, treatment and risk-prediction claims;
7. provide a conversational interface for exploring personal behavioural and wellbeing patterns; and
8. evaluate the prototype’s accuracy, comprehensibility, usefulness, trustworthiness, usability, uncertainty communication and perceived privacy.

### 1.4 Proposed Approach and Scope

The proposed system follows an end-to-end flow from sensing data to conversational output. Smartphone-derived measurements are first cleaned and converted into behavioural features. These features are aligned with longitudinal wellbeing measurements and analysed relative to each participant’s personal baseline. The resulting statistical evidence is packaged in a strictly validated EvidencePacket containing the current feature value, baseline information, uncertainty, evidence strength and permitted claim types.

Eligible questions and evidence are then passed to a locally deployed SLM. Requests involving insufficient data, diagnosis, causal conclusions, treatment advice, risk prediction or crisis-related language are handled through deterministic routing and fixed safety responses rather than unrestricted model generation. Generated responses are checked against the original evidence before being displayed to the user.

The prototype is designed to operate locally so that sensitive sensing and wellbeing information does not need to be sent to an external language-model service. Human evaluation is planned to assess whether the resulting explanations are faithful to the supplied evidence, understandable, useful and appropriately cautious. The project will also examine limitations and risks, including incomplete sensing coverage, uncertainty in personalised statistical estimates, language-model reliability, privacy assurance and the boundary between reflective information and clinical interpretation.

## 2. Dataset and Data Preparation

### 2.1 Dataset Selection

MindSense will use the College Experience Study (CES) dataset, a longitudinal mobile-sensing dataset containing smartphone-derived behavioural information and repeated self-reported mental-health measures from university students. The dataset includes 220 participants and covers an extended observation period from September 2017 to June 2022. Its longitudinal structure makes it suitable for examining changes within the same individual over time rather than relying only on comparisons between different individuals (Nepal et al., 2024).

CES was selected because it provides repeated behavioural and wellbeing measurements at the frequency required to establish personal baselines. The dataset contains pre-computed daily and hourly sensing features rather than raw GPS coordinates or complete raw sensor streams. This supports the development of the proposed prototype while reducing the need to process directly identifiable location trajectories.

The client specification uses the World Health Organization Five Well-Being Index (WHO-5) as an illustrative wellbeing measure. However, WHO-5 is not available in CES at the longitudinal density required by this project. MindSense will therefore use the Patient Health Questionnaire-4 (PHQ-4), which is repeatedly administered in CES and provides a brief screening measure of anxiety and depressive symptoms (Kroenke et al., 2009). This is a deliberate dataset-driven substitution and does not change the project’s non-diagnostic scope. PHQ-4 scores will be treated as longitudinal self-reported wellbeing-related outcomes rather than clinical diagnoses.

### 2.2 Dataset Verification

The team re-verified the current CES dataset using scripted checks rather than relying only on its published description. The verification confirmed 220 participants with sensing records and 218 participants with at least one valid PHQ-4 measurement. Among participants with valid PHQ-4 records, the median number of measurements was 169.5. A total of 217 participants had at least five PHQ-4 measurements, while 215 had at least ten, demonstrating that the outcome is repeatedly observed for almost the entire cohort.

Eligibility was evaluated using a predefined sufficiency rule requiring at least 20 valid sensor-days for both selected Tier 1 behavioural features and at least one valid PHQ-4 record. Under this rule, 214 of the 220 participants were eligible, corresponding to 97.3% of the cohort. CES therefore satisfies the project’s minimum data requirements, and the proposed fallback dataset is not currently required.

### 2.3 Behavioural Feature Selection

The CES sensing table contains a large number of derived variables, but feature availability differs between mobile platforms. The dataset contains records associated with 188 iOS and 32 Android participants, and some sensing streams are unavailable or represented differently across the two platforms. For example, physical-activity measurements are not consistently supported on Android, while call and SMS information is not available on iOS. Treating unsupported measurements as genuine zero behaviour would produce misleading comparisons.

To maintain cross-platform consistency, the initial Tier 1 feature set is restricted to two behavioural concepts:

1. GPS-derived distance travelled, representing mobility; and
2. phone-unlock count or duration, representing device engagement.

These features were selected because they are available across both principal platform groups and correspond directly to the mobility and device-use examples identified in the client specification. Additional features will remain outside the initial scope unless they meet the same availability, completeness and interpretability requirements.

### 2.4 Data Preparation and Missingness

Sensing information and PHQ-4 measurements are recorded at different frequencies. Behavioural sensing features may be available daily or hourly, whereas PHQ-4 is collected at repeated assessment points. The data therefore cannot be joined by simply matching every sensor record to a wellbeing score. For each PHQ-4 assessment, the proposed pipeline will construct a trailing behavioural window ending at or before the assessment date. This prevents future behavioural observations from being used to explain an earlier wellbeing measurement.

The implemented GPS-distance prototype loads one record per participant per observation day, orders records chronologically and applies a transparent cleaning process. Records that fail the required sensing-quality threshold are excluded, implausibly large distance values are filtered, extreme remaining values are limited within each participant’s distribution, and the positively skewed distance measure is log-transformed for statistical analysis. Genuine zero-travel days are preserved where the measurement is supported and passes the relevant quality checks.

Missing and unsupported sensing values will not be automatically replaced with zero. The pipeline instead records data availability through fields such as the number of observed days, expected days, coverage ratio, platform and quality flags. This distinction is important because an unavailable sensor stream means that the behaviour could not be measured, not that the behaviour did not occur. Participants or observation windows that do not meet the predefined coverage requirements will be routed to an insufficient-data or cold-start response instead of receiving an unsupported personal comparison.

### 2.5 Current Status and Remaining Work

CES suitability, participant coverage, PHQ-4 repeat density and cohort eligibility have been verified. A working GPS-distance feature prototype is also present in the current system, including missingness handling, quality filtering, outlier treatment and transformation for statistical modelling. The remaining data-pipeline work includes completing and validating the second Tier 1 feature, confirming consistent processing across the full pipeline and documenting the final frozen feature set before participant-facing evaluation.

## 2. Dataset and Data Preparation

### 2.1 Dataset Selection

MindSense will use the College Experience Study (CES) dataset, a longitudinal mobile-sensing dataset containing smartphone-derived behavioural information and repeated self-reported mental-health measures from university students. The dataset includes 220 participants and covers an extended observation period from September 2017 to June 2022. Its longitudinal structure makes it suitable for examining changes within the same individual over time rather than relying only on comparisons between different individuals (Nepal et al., 2024).

CES was selected because it provides repeated behavioural and wellbeing measurements at the frequency required to establish personal baselines. The dataset contains pre-computed daily and hourly sensing features rather than raw GPS coordinates or complete raw sensor streams. This supports the development of the proposed prototype while reducing the need to process directly identifiable location trajectories.

The client specification uses the World Health Organization Five Well-Being Index (WHO-5) as an illustrative wellbeing measure. However, WHO-5 is not available in CES at the longitudinal density required by this project. MindSense will therefore use the Patient Health Questionnaire-4 (PHQ-4), which is repeatedly administered in CES and provides a brief screening measure of anxiety and depressive symptoms (Kroenke et al., 2009). This is a deliberate dataset-driven substitution and does not change the project’s non-diagnostic scope. PHQ-4 scores will be treated as longitudinal self-reported wellbeing-related outcomes rather than clinical diagnoses.

### 2.2 Dataset Verification

The team re-verified the current CES dataset using scripted checks rather than relying only on its published description. The verification confirmed 220 participants with sensing records and 218 participants with at least one valid PHQ-4 measurement. Among participants with valid PHQ-4 records, the median number of measurements was 169.5. A total of 217 participants had at least five PHQ-4 measurements, while 215 had at least ten, demonstrating that the outcome is repeatedly observed for almost the entire cohort.

Eligibility was evaluated using a predefined sufficiency rule requiring at least 20 valid sensor-days for both selected Tier 1 behavioural features and at least one valid PHQ-4 record. Under this rule, 214 of the 220 participants were eligible, corresponding to 97.3% of the cohort. CES therefore satisfies the project’s minimum data requirements, and the proposed fallback dataset is not currently required.

### 2.3 Behavioural Feature Selection

The CES sensing table contains a large number of derived variables, but feature availability differs between mobile platforms. The dataset contains records associated with 188 iOS and 32 Android participants, and some sensing streams are unavailable or represented differently across the two platforms. For example, physical-activity measurements are not consistently supported on Android, while call and SMS information is not available on iOS. Treating unsupported measurements as genuine zero behaviour would produce misleading comparisons.

To maintain cross-platform consistency, the initial Tier 1 feature set is restricted to two behavioural concepts:

1. GPS-derived distance travelled, representing mobility; and
2. phone-unlock count or duration, representing device engagement.

These features were selected because they are available across both principal platform groups and correspond directly to the mobility and device-use examples identified in the client specification. Additional features will remain outside the initial scope unless they meet the same availability, completeness and interpretability requirements.

### 2.4 Data Preparation and Missingness

Sensing information and PHQ-4 measurements are recorded at different frequencies. Behavioural sensing features may be available daily or hourly, whereas PHQ-4 is collected at repeated assessment points. The data therefore cannot be joined by simply matching every sensor record to a wellbeing score. For each PHQ-4 assessment, the proposed pipeline will construct a trailing behavioural window ending at or before the assessment date. This prevents future behavioural observations from being used to explain an earlier wellbeing measurement.

The implemented GPS-distance prototype loads one record per participant per observation day, orders records chronologically and applies a transparent cleaning process. Records that fail the required sensing-quality threshold are excluded, implausibly large distance values are filtered, extreme remaining values are limited within each participant’s distribution, and the positively skewed distance measure is log-transformed for statistical analysis. Genuine zero-travel days are preserved where the measurement is supported and passes the relevant quality checks.

Missing and unsupported sensing values will not be automatically replaced with zero. The pipeline instead records data availability through fields such as the number of observed days, expected days, coverage ratio, platform and quality flags. This distinction is important because an unavailable sensor stream means that the behaviour could not be measured, not that the behaviour did not occur. Participants or observation windows that do not meet the predefined coverage requirements will be routed to an insufficient-data or cold-start response instead of receiving an unsupported personal comparison.

### 2.5 Current Status and Remaining Work

CES suitability, participant coverage, PHQ-4 repeat density and cohort eligibility have been verified. A working GPS-distance feature prototype is also present in the current system, including missingness handling, quality filtering, outlier treatment and transformation for statistical modelling. The remaining data-pipeline work includes completing and validating the second Tier 1 feature, confirming consistent processing across the full pipeline and documenting the final frozen feature set before participant-facing evaluation.

## 3. Proposed System Architecture

### 3.1 Architecture Overview

MindSense is designed as a modular, end-to-end system that converts longitudinal smartphone-sensing and wellbeing data into evidence-grounded conversational explanations. The architecture separates data preparation, statistical analysis, language generation, safety validation and presentation into distinct components. This separation enables each component to be developed and tested independently while ensuring that sensitive information and unsupported claims do not pass unchecked through the system.

The overall information flow is:

**CES sensing and PHQ-4 data → Data validation and behavioural feature extraction → Personal baseline and longitudinal statistical analysis → Validated EvidencePacket → Deterministic request routing → Local SLM generation → Output grounding and safety validation → Conversational interface → Human evaluation**

The system contains five principal components aligned with the client specification:

1. a digital phenotyping and data-preparation pipeline;
2. a statistical and wellbeing-integration layer;
3. a locally deployed Small Language Model with deterministic safety controls;
4. a conversational user interface; and
5. an evaluation framework for response quality, safety, usability and privacy.

A shared evidence contract connects the statistical, SLM, API and interface layers. This contract is central to the architecture because it defines exactly which information may move between components and which claims may be presented to the user.

### 3.2 Digital Phenotyping and Data-Preparation Layer

The first component ingests the CES sensing and PHQ-4 datasets and verifies that their structure satisfies the project’s requirements. Smartphone-derived measurements are transformed into interpretable behavioural features, beginning with GPS-derived distance travelled and phone-unlock activity.

The data-preparation layer is responsible for chronological alignment, missingness handling, coverage assessment, quality filtering and feature transformation. Behavioural records are aligned with the relevant PHQ-4 assessment windows so that observations occurring after a wellbeing assessment are not used to explain that earlier outcome. Unsupported or unavailable sensing streams are represented as missing rather than being treated as zero behaviour.

Each processed feature window includes information describing the measurement period, observed and expected days, coverage ratio, platform and relevant quality flags. Windows that do not satisfy the predefined data-sufficiency requirements are marked as ineligible for personalised comparison. This allows later components to provide an insufficient-data response instead of generating an unsupported interpretation.

### 3.3 Statistical and Wellbeing-Integration Layer

The statistical layer combines the processed behavioural features with repeated PHQ-4 measurements. Its primary purpose is to distinguish temporary within-person behavioural changes from stable differences between participants. This is necessary because the project aims to describe how a person’s current behaviour differs from their own historical pattern rather than relying only on population-level comparisons.

The proposed approach uses a linear mixed-effects model with person-level random effects and person-mean-centred predictors. The statistical layer estimates behavioural deviation from the personal baseline, associated uncertainty and the strength of the available evidence. It also applies the project’s cold-start policy to determine whether the available history supports no interpretation, a descriptive summary or a comparative statement.

The statistical component does not send unrestricted model output directly to the SLM. Instead, it converts approved results into a structured EvidencePacket. This prevents the language model from independently searching the dataset, selecting variables or deriving new statistical conclusions.

### 3.4 Shared Evidence Contract

The EvidencePacket is the controlled interface between the analytical backend and the conversational layer. The current contract is versioned as `contract-v1.0.0` and implemented through strict validation models. Unexpected fields are rejected, and validated packets are treated as immutable after creation.

Each EvidencePacket contains five principal groups of information:

- identity and version information, including the contract version, model specification and an opaque participant reference;
- the behavioural feature window, including the feature name, unit, dates, value and coverage information;
- personal-baseline information and the corresponding eligibility status;
- statistical evidence, including the estimated within-person deviation, confidence interval, direction and evidence strength; and
- uncertainty and claim-policy information defining what the conversational layer may and may not communicate.

Permitted claims include observations of behavioural deviation, supported within-person associations, trend descriptions, uncertainty disclosures, insufficient-data statements and reminders of the non-diagnostic boundary. Prohibited claims include diagnosis, unsupported causal explanations, treatment advice and mental-health risk prediction.

By representing these rules as validated data rather than relying only on prompt instructions, the contract reduces ambiguity between system components. It also enables the data, statistics, SLM, interface and integration work to be tested against the same expected structure.

### 3.5 Local SLM and Safety Layer

Eligible EvidencePackets and user questions are sent through the backend request-policy layer. Requests involving diagnosis, unsupported causal conclusions, treatment recommendations, risk prediction, privacy-sensitive disclosure or crisis-related language are intercepted before unrestricted language-model generation.

Questions that are within scope may be passed to a locally deployed SLM through Ollama. The current baseline model is `phi4-mini:3.8b`, while `qwen3:4b` remains a challenger for later comparison. The final model will be selected using fixed safety and response-quality criteria rather than assumed in advance.

The SLM receives structured evidence rather than raw participant records. It is responsible for translating approved numerical and statistical information into understandable language, not for calculating new evidence. After generation, an output-grounding layer checks whether the response refers only to supplied feature names, units, values, uncertainty and approved claim types. Responses that fail these checks are rejected or replaced by a deterministic fallback.

Missing-data, refusal and crisis-related requests use predefined response routes. In particular, crisis-support wording is not generated freely by the SLM. It is provided through a fixed, reviewable template so that critical information remains consistent and auditable.

### 3.6 Backend API and Component Integration

A local backend API provides the integration boundary between the analytical pipeline, SLM service and frontend. Requests are validated before entering the SLM service, and responses use a structured format that identifies the response mode, displayed text, fallback status, rejection reason, model version and whether the model was invoked.

This design supports several response modes, including normal explanation, uncertainty, insufficient data, refusal, generic fallback and crisis-aware fallback. The response mode enables the frontend to present each situation using an appropriately distinct visual state.

The current repository contains a narrow vertical slice demonstrating an eligible GPS-distance question and deterministic handling of missing-data and prohibited-request paths. This provides an integration foundation, but it does not yet constitute the complete participant-facing system. Completion of the second Tier 1 feature, the remaining interface states and participant-ready privacy checks is planned in subsequent stages.

### 3.7 Conversational Interface

The user-facing component is being developed using React and TypeScript. It communicates with the local backend rather than accessing the dataset or SLM directly. This keeps statistical processing, request routing and safety enforcement outside the browser interface.

The proposed interface contains visually distinct states for normal responses, insufficient data, uncertainty, refusal, generic fallback, crisis-aware fallback and loading. A limited normal-response prototype is currently available and communicates with the backend using a synthetic development EvidencePacket. The remaining states will be implemented and tested as the project progresses.

The interface will present supported behavioural insights without using diagnostic labels or clinical risk categories. Missing data will be shown as unavailable rather than as zero, and uncertainty will be displayed explicitly so that users can distinguish strong evidence from tentative or incomplete observations.

### 3.8 Evaluation Layer

The evaluation component examines whether responses remain faithful to the supplied evidence and whether they communicate personal patterns safely and understandably. Automated development tests cover evidence grounding, prohibited requests, deterministic response routing, privacy controls and integration behaviour.

Later human evaluation will assess the client-specified dimensions of accuracy, comprehensibility, usefulness, personal relevance, trust, uncertainty communication, association-versus-causation distinction, inappropriate mental-health inference, usability and privacy perception. Evaluation therefore operates as both a development control and a method for assessing the completed prototype.

### 3.9 Current Architecture Status

The versioned evidence contract, local SLM service, deterministic request routing, output-grounding controls, backend API and core automated tests are currently present. CES validation and a GPS-distance processing prototype are also available. These components support a limited end-to-end development path using synthetic evidence.

The complete architecture remains a proposed prototype rather than a finished production system. Outstanding work includes

## 4. Statistical Approach

### 4.1 Analytical Objective

The statistical component is designed to identify changes relative to an individual’s own behavioural history and to examine how longitudinal behavioural patterns are associated with repeated PHQ-4 outcomes. This requires separating within-person change from stable differences between participants.

A simple population-level correlation would not adequately support personalised interpretation. For example, participants who are generally more mobile may also differ from less-mobile participants in characteristics unrelated to short-term behavioural change. Such a population-level difference does not demonstrate that a temporary reduction in mobility is associated with a change in wellbeing for the same person. MindSense therefore uses a longitudinal mixed-effects approach with person-mean centring.

The statistical analysis is explicitly associational and non-diagnostic. Model estimates will not be interpreted as evidence that a behavioural change caused a change in wellbeing, nor will PHQ-4 scores be treated as clinical diagnoses.

### 4.2 Linear Mixed-Effects Model

The proposed primary analysis uses a linear mixed-effects model with participant-level random effects. For participant \(i\) at assessment occasion \(t\), the principal model can be expressed as:

\[
PHQ4_{it} = \beta_0 + \beta_W(x_{it}-\bar{x}_i) + \beta_B\bar{x}_i + \beta_T time_{it} + b_{0i} + b_{1i}(x_{it}-\bar{x}_i) + \epsilon_{it}
\]

where:

- \(PHQ4_{it}\) is the participant’s PHQ-4 score at occasion \(t\);
- \(x_{it}\) is the behavioural feature aggregated over the relevant trailing window;
- \(\bar{x}_i\) is the participant’s mean value for that behavioural feature;
- \(x_{it}-\bar{x}_i\) represents the within-person behavioural deviation;
- \(\beta_W\) estimates the average within-person association;
- \(\beta_B\) represents the between-person association;
- \(\beta_T\) accounts for change over time;
- \(b_{0i}\) is the participant-specific random intercept;
- \(b_{1i}\) is the participant-specific random slope; and
- \(\epsilon_{it}\) is the residual error.

The within-person term is the principal quantity relevant to personalised explanations. It measures whether a participant’s wellbeing-related outcome tends to differ when their behaviour is above or below their own typical level. The between-person term is retained to prevent stable differences between individuals from being incorrectly interpreted as within-person change.

Random intercepts account for differences in participants’ typical PHQ-4 levels. Random slopes allow the behavioural association to vary between participants, subject to model convergence and data sufficiency. If the random-slope model does not converge reliably, a predefined simpler model may be used and the change must be documented rather than concealed.

### 4.3 Temporal Alignment

The behavioural predictors and PHQ-4 outcomes are observed at different frequencies. For each PHQ-4 assessment, the pipeline constructs a trailing 14-day behavioural window ending on or before the assessment date. The 14-day interval corresponds to the recall period represented by PHQ-4 and prevents future sensing data from being used to explain an earlier outcome.

A behavioural window must contain at least seven valid sensor-days before it can contribute to the model. Windows that fail this requirement are excluded rather than imputed. Overlapping trailing windows may create serial correlation between repeated observations, so the analysis includes an autoregressive AR(1) assessment.

The current implementation supports an AR(1)-aware mixed-effects fit through R’s `nlme` framework when the required R environment is available. A Python fallback is retained for development and testing, but its result must be identified as an approximation rather than presented as equivalent to the primary R analysis.

### 4.4 Personal Baselines and Cold-Start Policy

Personalised comparison is permitted only when sufficient historical information exists. The statistical design therefore defines three cold-start states.

**State A — No or insufficient data:** This state applies when fewer than seven calendar days of history are available, no valid PHQ-4 assessment is available, or every Tier 1 feature has fewer than five valid sensor-days. The system may provide only a fixed insufficient-data response. It must not present numerical comparisons or behavioural–wellbeing interpretations.

**State B — Partial history:** This state applies when at least seven days of history and one PHQ-4 assessment are available but the feature has not reached the minimum comparative-baseline requirement. The system may describe recent observed behaviour while stating that it is too early to make a reliable historical comparison. Baseline percentages, standardised deviation scores and historical relationship claims are not permitted.

**State C — Sufficient history:** Comparative statements become available when a feature has at least 28 calendar days of history, at least 20 valid sensor-days and at least three completed PHQ-4 assessments. A stronger historical relationship claim additionally requires the target 56-day history, at least 40 valid sensor-days, at least eight PHQ-4 assessments spanning at least 28 days, and sufficient statistical evidence.

The lowest qualifying state among the features used in a response controls the framing of that response. This prevents a well-observed feature from concealing insufficient evidence for another feature.

### 4.5 Multiple Comparisons and Evidence Strength

The project distinguishes between confirmatory and exploratory statistical tests. The confirmatory analysis will use Holm–Bonferroni correction to control the family-wise error rate across the small predefined set of primary tests. Exploratory analyses will use the Benjamini–Hochberg procedure to control the false discovery rate.

Evidence strength will not be determined from a p-value alone. Classification also considers the adjusted significance level, standardised effect size, number of valid assessment occasions, data coverage and consistency of the estimated direction across relevant model specifications. Evidence may be classified as insufficient, weak, moderate or strong.

These classifications control the language available to the SLM. Weak or incomplete evidence requires cautious descriptive wording, while stronger evidence may support an associational statement. No evidence category permits diagnostic or causal language.

### 4.6 Estimation and Statistical Software

The primary statistical pathway uses R mixed-effects libraries for denominator degrees-of-freedom estimation and residual-correlation modelling. Satterthwaite or Kenward–Roger methods are used where applicable, while an AR(1) residual structure is fitted through `nlme`.

A Python implementation using `statsmodels` is maintained as a documented fallback when the R environment is unavailable. The output records which engine and estimation method produced each result. This avoids silently presenting an approximate fallback as the primary statistical analysis.

The implementation also provides Holm–Bonferroni and Benjamini–Hochberg correction utilities and evidence-strength classification logic. Statistical outputs are converted into validated evidence fields before they can be used by the conversational layer.

### 4.7 Current Implementation Status and Limitations

The current statistical prototype implements the main within-person and between-person predictors, participant-level random effects, optional time-related fixed effects, multiple-comparison correction, evidence-strength utilities and an R-based AR(1) pathway. It is connected to the implemented GPS-distance feature and can generate the principal statistical information required by the evidence contract.

The implementation nevertheless remains incomplete in several respects. The planned one-occasion lagged behavioural predictor has not yet been incorporated into the full model. Consequently, the strongest evidence category, which requires consistent directions across the contemporaneous and lagged terms, cannot yet be reached automatically without additional evidence supplied by the caller.

The R pathway can produce participant-level empirical Bayes estimates, but these estimates have not yet been connected to a dedicated participant-level reporting process. In addition, the current academic-term covariate uses an approximate general United States academic calendar because the CES data does not include a definitive term-phase field. This approximation must be refined or clearly retained as a limitation.

The present results should therefore be described as a working statistical prototype rather than a final confirmatory analysis. Subsequent work will add the lagged predictor, complete participant-level evidence generation, validate the final two-feature model and confirm that all outputs satisfy the agreed evidence-strength and cold-start rules.

## 5. SLM Integration and Safety

### 5.1 Role of the Small Language Model

The Small Language Model component translates validated statistical evidence into conversational explanations that are accessible to non-specialist users. Its role is limited to explaining evidence supplied by the analytical backend. It is not permitted to search the CES dataset, calculate new statistical relationships, infer missing values or independently decide whether a participant has a mental-health condition.

This separation is important because fluent language-model responses may sound credible even when they contain unsupported values or interpretations. MindSense therefore combines structured generation with deterministic validation. The language model produces a candidate explanation, but the surrounding safety system determines whether that explanation may be shown to the user.

Research on grammar-constrained generation and factual consistency supports the use of separate structural and evidence-validation controls around generated language (Geng et al., 2023; Maynez et al., 2020). These studies inform the technical approach but do not establish the clinical safety of the MindSense prototype.

### 5.2 Local Model Deployment

The SLM is deployed locally through Ollama to reduce the need to transmit sensitive behavioural and wellbeing evidence to an external language-model service. The current model manifest identifies `phi4-mini:3.8b` as the baseline and `qwen3:4b` as the challenger.

A final model has not yet been selected. Model selection will be based on an expanded and fixed comparison covering evidence faithfulness, response quality, latency and safety performance. This avoids treating an early development default as a final technical decision.

Eligible requests are submitted to the model through a loopback-only client. The client accepts local hosts such as `127.0.0.1` and `localhost`, disables environment-provided proxies and rejects redirects or non-local endpoints. Raw CES records are not sent to the SLM. Instead, the model receives a validated EvidencePacket containing only the minimum behavioural and statistical evidence required for the response.

### 5.3 Structured Prompting

MindSense uses version-controlled YAML prompt templates rather than undocumented prompts embedded directly in application code. Each prompt version defines the intended task, permitted evidence fields, output structure and safety requirements. Model tags and prompt versions are recorded so that an evaluated response can be reproduced against the same configuration.

For an eligible question, the prompt instructs the SLM to:

- describe only behavioural features supplied in the EvidencePacket;
- use the supplied current and baseline values accurately;
- communicate the stated evidence strength and uncertainty;
- distinguish association from causation;
- preserve the non-diagnostic boundary; and
- return a structured response that can be validated before display.

The model is not allowed to introduce unsupported participant characteristics, population comparisons, diagnoses, causes, treatment recommendations or predictions of mental-health risk.

### 5.4 Deterministic Request Routing

Before a question reaches the SLM, a deterministic request-policy layer determines whether model generation is appropriate. Requests are classified according to their content and the available evidence.

Questions involving supported behavioural comparisons may proceed to the local model. Other requests are handled without unrestricted model generation:

- insufficient evidence is routed to a fixed insufficient-data response;
- diagnostic requests are routed to a refusal;
- requests for unsupported causal conclusions are refused;
- treatment and risk-prediction requests are refused;
- requests seeking raw identifiers or sensitive location information are refused;
- prompt-injection attempts are rejected; and
- crisis-related language is routed to a deterministic crisis-aware response.

This design reduces reliance on the SLM’s willingness to follow a safety instruction. High-risk requests are intercepted before model invocation instead of asking the model to generate a refusal itself.

### 5.5 Output Grounding and Validation

Responses generated for eligible questions pass through an output-grounding layer before being displayed. The validator compares the candidate response with the original EvidencePacket and checks whether the response uses only approved evidence.

The validation process checks:

- referenced feature names and units;
- current and baseline values;
- direction of behavioural change;
- uncertainty language;
- evidence-strength statements;
- approved and prohibited claim identifiers;
- unsupported diagnostic or causal wording; and
- compliance with the required response structure.

A response is rejected if it introduces a number, feature, relationship or claim that cannot be grounded in the supplied evidence. Rejected or malformed output is replaced by an appropriate deterministic fallback rather than being silently shown to the user.

The current grounding rules use a deliberately bounded response grammar. This improves auditability but may reject safe paraphrases that fall outside the recognised wording patterns. Future development must balance linguistic flexibility with reliable evidence validation.

### 5.6 Fallback and Crisis-Aware Responses

The SLM subsystem includes separate deterministic responses for ordinary system failure and crisis-related language. The generic fallback is used when model invocation fails, the returned structure is invalid or the response cannot be grounded in the supplied evidence.

The crisis-aware response follows a distinct route. Crisis wording is not generated or paraphrased freely by the language model. Instead, the system displays a fixed resource-oriented message containing Australian emergency and crisis-support information. This ensures that critical wording remains consistent, reviewable and auditable.

The crisis-aware response is not a diagnosis or a prediction that the user is at risk. It is a precautionary support route triggered by explicit language patterns. Its content must receive the required client and evaluation approval before participant-facing deployment.

### 5.7 Development Verification

Richard’s Week 5 SLM work includes the local service, request policy, output grounding, deterministic fallbacks, synthetic test fixtures and recorded shadow-build evidence. The development snapshot recorded 65 output-grounding regression cases passing. The corresponding repository test run recorded 265 passing checks and eight environment- or data-dependent skips at that stage of development.

A Phi-4 Mini shadow smoke test exercised four principal paths:

1. a model-generated GPS-distance explanation;
2. a deterministic insufficient-data response;
3. a deterministic refusal; and
4. a deterministic crisis-aware response.

The model-backed service also passed the six questions that were executable under the current evidence contract. Two planned evaluation questions were not executed because the contract could not yet represent longitudinal PHQ-4 change or a behavioural–PHQ-4 association. These cases were recorded as not covered rather than assigned fabricated responses.

Separately, all 14 registered high-severity guardrail cases and two privacy-extension cases passed in the recorded development review. These results apply only to the fixed synthetic cases and recorded model, prompt and policy versions.

### 5.8 Current Status and Limitations

The local SLM service, prompt templates, request routing, output grounding and deterministic fallback mechanisms are implemented and supported by automated development tests. This provides a working foundation for evidence-grounded local explanations.

However, the current results do not demonstrate clinical safety, general paraphrase coverage, multilingual performance, human usefulness or held-out evaluation performance. The tests use synthetic evidence and a limited collection of fixed prompts. The final model comparison remains incomplete, and Qwen3 has not been re-evaluated against all recent grounding changes.

Further work will extend the evidence contract to support the two uncovered evaluation questions, repeat the fixed comparison across the candidate models, complete joint evaluation review, test the full API-to-interface path and obtain approval for participant-facing crisis wording. The SLM component should therefore be described as a tested development implementation rather than a clinically validated conversational system.

### References

Geng, S., Josifoski, M., Peyrard, M., & West, R. (2023). Grammar-constrained decoding for structured NLP tasks without finetuning. *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing*, 10932–10952. https://doi.org/10.18653/v1/2023.emnlp-main.674

Maynez, J., Narayan, S., Bohnet, B., & McDonald, R. (2020). On faithfulness and factuality in abstractive summarization. *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics*, 1906–1919. https://doi.org/10.18653/v1/2020.acl-main.113

## 6. Privacy and Security Architecture

### 6.1 Privacy Risks

The Privacy and Security component addresses the risk that sensitive smartphone-sensing, behavioural and wellbeing information could leave the local environment through cloud APIs, telemetry, application logs, remote frontend assets or third-party dependencies. It also considers accidental disclosure through participant identifiers, model prompts, generated responses, terminal output and shared statistical evidence.

These risks are particularly important because behavioural sensing and mental-health-related data may reveal sensitive information even when individual fields appear harmless in isolation. Privacy must therefore be enforced across the complete processing chain rather than treated only as a data-storage concern. The project adopts privacy-risk management and safe-logging principles informed by the NIST Privacy Framework and the OWASP Logging Cheat Sheet (National Institute of Standards and Technology, 2020; OWASP Foundation, n.d.).

### 6.2 Local-First Architecture

MindSense adopts a local-first architecture in which dataset ingestion, behavioural feature extraction, statistical processing and SLM inference are designed to operate within the local environment. The SLM is accessed through Ollama using loopback addresses such as `127.0.0.1` or `localhost`. The application’s model client restricts connections to these local addresses, disables environment-provided proxies and prevents redirects to unintended external destinations.

Raw sensing records are not intended to be transferred directly to the language model. Instead, the data pipeline and statistical layer reduce the available information to a validated EvidencePacket containing only the structured evidence required to answer an eligible question. Participant references are represented using opaque identifiers rather than raw CES user identifiers. This data-minimisation approach reduces the amount of sensitive information exposed to the conversational layer.

Telemetry, analytics, crash-reporting uploads and remote model services are excluded from the proposed runtime architecture. Application logs should contain only the minimum non-identifying technical information required for debugging and verification, such as aggregate latency, model and prompt versions, response routes and error categories. Raw participant identifiers, sensing values, prompts and wellbeing-related outputs should not be written to routine logs.

### 6.3 Dependency and Network Controls

Every software dependency is treated as part of the project’s privacy boundary because a dependency may introduce network communication, telemetry, automatic downloads or access to sensitive runtime data. The project’s pull-request template therefore requires a privacy spot-check whenever a dependency is added or materially changed. This review examines the dependency’s purpose, network behaviour, telemetry and logging behaviour, installation scripts, data access, licence and available alternatives.

Automated network controls supplement this manual review. The Python test environment applies a socket restriction, and privacy regression tests check that reviewed runtime paths do not make unexpected public-network connections. The current SLM client allows communication with the local Ollama service while rejecting non-loopback hosts. Frontend assets are packaged locally to avoid automatic requests to external content-delivery networks.

The privacy review found no intended telemetry, analytics, cloud-language-model integration or automatic public frontend requests in the reviewed application paths. It also identified an earlier risk in which participant identifiers could appear in eligibility-script output. This issue has since been addressed by changing the output to aggregate-only reporting.

### 6.4 Verification and Performance Evidence

The Week 4 privacy review included automated no-egress testing, dependency inspection and a local benchmark of `phi4-mini:3.8b` using five synthetic prompts containing no participant data. The initial benchmark recorded a mean response latency of 2.22 seconds, with observed results ranging from 0.91 to 3.46 seconds.

A Week 5 repeat benchmark recorded a mean latency of 2.57 seconds and a sample 95th-percentile latency of 3.88 seconds. All five requests completed successfully. These results provide preliminary evidence that local inference is technically feasible on the tested machine. However, the sample is too small to support production-level performance claims, and latency measurements do not demonstrate clinical validity, response quality or safety.

Subsequent Week 5 verification also covered the merged SLM transport and privacy controls, including prohibited-request paths and checks that disallowed requests did not unexpectedly invoke the model. These tests strengthen the evidence for local synthetic development but do not yet demonstrate that the entire participant-facing application is safe for deployment.

### 6.5 Privacy Status and Remaining Work

The current privacy status is a conditional approval for local development using synthetic data. It is not approval for participant-facing use or the processing of identifiable participant data. Before such use, the complete integrated application must be tested with public-network access blocked, and the team must confirm that only aggregate or appropriately de-identified evidence reaches downstream components.

Additional work includes producing a resolved and reproducible Python dependency lockfile, extending redaction coverage, approving a formal logging and retention policy, and repeating the privacy review whenever dependencies or runtime paths change. Participant-facing evaluation will also require appropriate governance, approved study materials and confirmation that the deployed configuration matches the version that passed the privacy checks.

Accordingly, the project treats privacy as a continuing release condition rather than a one-time design decision. A build should proceed to participant-facing evaluation only when its data flow, dependencies, logging behaviour, local-model connection and network restrictions have all been reviewed and verified.

### 6.6 Privacy Evidence

The privacy design and current verification status are supported by the project’s privacy architecture principles, dependency privacy checklist, pull-request privacy rule, dependency audit, no-network-egress tests, SLM transport tests and recorded local latency benchmarks. The principal repository evidence includes:

- `privacy/privacy_architecture_principles.md`;
- `privacy/dependency_privacy_checklist.md`;
- `.github/pull_request_template.md`;
- `docs/privacy/week4-privacy-lead-report.pdf`;
- `docs/privacy/week5-privacy-security-report.pdf`;
- `docs/privacy/week5-proposal-contribution.md`;
- `tests/privacy/test_no_network_egress.py`;
- `tests/slm/test_transport_privacy.py`; and
- `benchmarks/slm_latency_results.json`.

### References

National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A Tool for Improving Privacy through Enterprise Risk Management, Version 1.0*. https://www.nist.gov/privacy-framework/privacy-framework

OWASP Foundation. (n.d.). *Logging Cheat Sheet*. https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

## 7. Evaluation Plan

### 7.1 Evaluation Objectives

The evaluation component will assess whether MindSense communicates behavioural and wellbeing evidence accurately, understandably and safely. The principal risk is not limited to reporting an incorrect number. A response may also overstate weak evidence, conceal uncertainty, confuse association with causation, make an inappropriate mental-health inference or disclose sensitive information.

Evaluation therefore covers both evidence faithfulness and the quality of the user-facing explanation. The automated development evaluation is intended to identify technical and safety failures before participant-facing use. A later human evaluation will examine whether the completed system is understandable, useful, trustworthy and usable.

The evaluation does not assess whether MindSense can diagnose a mental-health condition or provide clinical treatment. PHQ-4 is treated as a validated screening instrument and longitudinal outcome rather than a diagnostic result (Kroenke et al., 2009).

### 7.2 Evaluation Criteria

The participant-facing evaluation will map directly to the ten dimensions identified in the client specification:

1. accuracy and faithfulness;
2. comprehensibility;
3. usefulness;
4. perceived personal relevance;
5. trust;
6. appropriate communication of uncertainty;
7. distinction between association and causation;
8. avoidance of inappropriate mental-health inference;
9. usability; and
10. privacy perceptions.

These dimensions will be incorporated into a structured participant rubric. Accuracy and safety criteria will also be applied to synthetic development cases before the participant study.

A response should be considered faithful only when its behavioural feature, current value, baseline value, direction, uncertainty and evidence strength agree with the supplied EvidencePacket. A fluent or helpful-sounding response will not pass if it introduces unsupported evidence or exceeds the project’s non-diagnostic scope.

### 7.3 Adversarial Evaluation

The adversarial evaluation tests whether the system responds safely to requests that should not receive an unrestricted model-generated answer. The current taxonomy includes:

- crisis-related requests;
- requests for diagnosis;
- unsupported causal interpretations;
- treatment recommendations;
- mental-health risk prediction;
- prompt-injection attempts;
- disclosure of raw participant identifiers; and
- disclosure of sensitive location information.

Each case specifies the expected response class in advance. Depending on the request, the expected result may be a refusal, an insufficient-data response, a crisis-aware fallback or another deterministic safety route. This prevents the expected outcome from being changed after observing model performance.

The pre-registered development threshold requires all high-severity guardrail cases to pass. Standard response-quality cases use a 90% threshold. Any critical safety failure blocks progression to participant-facing evaluation until it has been corrected and re-tested.

### 7.4 Development and Held-Out Test Sets

Evaluation uses separate development and held-out materials. Public synthetic development cases may be used repeatedly during implementation to identify problems and improve prompts, routing and grounding controls.

A separate set of held-out prompts has been sealed and protected by a recorded checksum. This set will remain unused during routine prompt development and is scheduled for first use during Week 11. Keeping the held-out set untouched reduces the risk that the team will optimise the system specifically for known test questions and then overstate its ability to handle unfamiliar requests.

The held-out evaluation will be run against a fixed model, prompt, evidence-contract and application version. Results must be reported with the corresponding version information so that they can be reproduced and interpreted accurately.

### 7.5 Week 5 Development Review

The Week 5 development review assessed the fixed synthetic cases that were executable under the current evidence contract. Six executable questions from the source evaluation plan passed the independent review. These cases included supported personal-baseline explanations, insufficient-data handling and refusal of unsupported diagnostic and causal requests.

Two planned questions were recorded as not covered. The current EvidencePacket cannot yet represent longitudinal PHQ-4 change or a complete behavioural–PHQ-4 association. No responses were fabricated for these questions, and they were not counted as either passes or failures.

The recorded review also found:

- 14 of 14 registered high-severity guardrail cases passed;
- two of two privacy-extension cases passed; and
- no critical failure was observed in the reviewed response snapshot.

These results apply only to the exact synthetic cases and recorded model, prompt, request-policy and output-grounding versions. They do not establish clinical safety, general paraphrase coverage, multilingual performance, human usefulness or held-out performance.

### 7.6 Human Evaluation

Following completion of the required implementation and privacy checks, a pilot evaluation is planned with approximately four to five participants. The pilot will test the clarity of the study procedure, participant materials, interface behaviour, rubric and facilitator response process. Critical issues identified during the pilot will be resolved before the main evaluation.

The subsequent main evaluation is planned with approximately 10–15 participants using a version-locked build. Participants will interact with the conversational interface and rate the system against the client-specified dimensions. Facilitators will record both structured ratings and qualitative feedback concerning confusing explanations, trust, uncertainty, privacy and usability.

Participant sessions will use approved information materials and a predefined facilitator crisis-response procedure. The study will use synthetic or appropriately approved de-identified evidence according to the final evaluation-data decision. No identifiable participant data will be introduced without the required privacy, governance and study approval.

### 7.7 Analysis of Evaluation Results

Automated cases will be reported using pass/fail outcomes by category rather than only a pooled overall accuracy score. High-severity safety failures will be reported separately because averaging them with lower-severity cases could conceal an unacceptable result.

Participant ratings will be summarised descriptively for each of the ten evaluation dimensions. Qualitative feedback will be analysed to identify recurring strengths, misunderstandings and concerns. Particular attention will be given to whether participants:

- understand that the system is non-diagnostic;
- recognise uncertainty in the explanations;
- distinguish association from causation;
- find personal-baseline comparisons meaningful;
- trust the system for appropriate reasons; and
- understand how their information is processed locally.

Given the planned sample size, participant findings will be interpreted as formative evidence about the prototype rather than as proof of clinical effectiveness or broad population generalisability.

### 7.8 Current Status and Remaining Work

Evaluation Plan v0.1, the adversarial taxonomy, pass thresholds, response-quality rubric, synthetic development review and sealed held-out set are currently available. Participant information and crisis-response materials also exist as development artifacts.

Remaining work includes extending the evidence contract to support the two uncovered questions, completing joint review of model responses, finalising the participant rubric, confirming whether the evaluation will use synthetic or approved de-identified data, completing the session runbook and obtaining the required approval before participant recruitment.

The current evaluation status should therefore be described as a completed development framework with preliminary synthetic results, not as a completed human evaluation.

## 8. Conversational Interface

### 8.1 Interface Objectives

The conversational interface will allow users to ask natural-language questions about their longitudinal behavioural and wellbeing information. Its purpose is to make statistical evidence easier to understand without exposing users to implementation details or suggesting that the system provides a clinical assessment.

The interface will not access the CES dataset, statistical model or local SLM directly. Instead, it will communicate with the local backend API and display the validated response returned by the safety-controlled service. This separation prevents the browser interface from bypassing the evidence contract, request policy or output-grounding controls.

The interface is being developed using React, TypeScript and Vite. These technologies support reusable response components and typed communication with the backend.

### 8.2 Proposed Conversational States

The proposed design contains seven visually distinguishable states:

1. **Normal response:** presents a supported explanation of behavioural evidence relative to the user’s personal baseline.
2. **Insufficient-data response:** explains that there is not yet enough valid information to make a comparison.
3. **Uncertainty response:** presents available evidence while prominently communicating that the conclusion is tentative.
4. **Refusal response:** explains that a diagnostic, causal, treatment, risk-prediction or otherwise prohibited request is outside the system’s scope.
5. **Generic fallback:** indicates that the model or validation process could not produce a reliable response.
6. **Crisis-aware fallback:** displays fixed support information when relevant crisis-related language is detected.
7. **Loading or processing state:** indicates that a request is being processed without presenting unsupported interim content.

These states correspond to response modes produced by the backend. Safety-related wording will come from the validated backend response rather than being rewritten by the frontend. In particular, the crisis-aware message must be displayed exactly as approved and must not be paraphrased or regenerated in the browser.

### 8.3 Presentation of Evidence and Uncertainty

Normal responses will present concise conversational explanations supported by the EvidencePacket. Where appropriate, the interface may also display the behavioural feature, current value, personal baseline, direction of change, observation period and evidence strength.

Uncertainty must be visible rather than hidden in secondary information. A response based on weak or partial evidence should use a distinct uncertainty indicator and cautious language. Insufficient-data responses should not display empty charts as though they represented zero behaviour.

The interface will avoid clinical labels and alarm-oriented visualisations. Behavioural values will be described as above, below or similar to the user’s personal baseline rather than as “depressed,” “anxious” or “high risk.” Crisis-related information should be visually distinct and easy to locate without using unnecessarily alarming presentation.

### 8.4 Accessibility and Usability

The interface will use clear headings, readable text, descriptive controls and sufficient visual contrast. Response modes should be distinguishable through labels and layout rather than colour alone. Interactive elements must remain keyboard accessible, and error or status messages should be exposed appropriately to assistive technologies.

The interface should also explain why a request was refused or why insufficient data prevented a comparison. This helps users distinguish between a system failure, a safety boundary and a lack of evidence.

Human evaluation will assess whether participants understand the responses, recognise uncertainty, trust the system appropriately and understand its non-diagnostic scope.

### 8.5 Current Status and Remaining Work

The current repository contains a React and TypeScript scaffold and a limited normal-response development component. This component sends a fixed synthetic GPS EvidencePacket to the local backend API and can display a validated response or an API connection error. Frontend unit tests cover its idle, loading, success and error behaviour.

This implementation demonstrates the intended frontend-to-backend interaction but is not yet a complete conversational interface. It currently uses synthetic example evidence and does not establish that the full CES data pipeline is connected to a participant-facing application.

The remaining conversational states have not yet been fully implemented. Subsequent work will connect the interface to the completed Tier 1 evidence flow, build the insufficient-data, uncertainty, refusal and fallback components, apply a consistent accessible visual design and test the complete interface before participant-facing evaluation.

## 9. Project Timeline, Risks and Expected Outcomes

### 9.1 Project Timeline

The project is organised across Weeks 4–12. Development follows a staged process in which scope and safety decisions are established first, followed by implementation, pilot evaluation, refinement and final validation.

| Period | Main activities | Planned milestone or output |
|---|---|---|
| **Week 4: Scope and risk lock** | Verify CES suitability; define the statistical model and cold-start policy; establish the SLM approach, safety templates, privacy principles and evaluation taxonomy; create the repository structure and freeze the evidence contract. | CES verification, statistical specification, initial SLM and privacy architecture, Evaluation Plan v0.1 and `contract-v1.0.0`. |
| **Week 5: Proposal and vertical slice** | Implement the GPS-distance development path; build baseline statistical logic, the local SLM service and safety controls; review synthetic evaluation cases; document privacy evidence; prepare the Group Proposal Report. | Group Proposal submission and a limited vertical slice covering an eligible GPS question, missing-data handling and prohibited requests. |
| **Week 6: Tier 1 implementation and freeze** | Complete the signed-off Tier 1 behavioural features; extend statistical evidence generation; implement the remaining interface and fallback states; strengthen automated privacy and integration checks; finalise participant-evaluation materials. | Frozen Tier 1 architecture and an integrated build ready for internal pilot testing. |
| **Week 7: Pilot evaluation** | Run a pilot with approximately four to five participants; test the evaluation procedure, interface, rubric and facilitator response process; record technical and usability issues. | Pilot findings and prioritised corrective actions. |
| **Week 8: Hardening and Status Checking 2** | Address pilot issues; re-test safety and privacy controls; verify generic and crisis-aware fallback paths end to end; confirm readiness for the main evaluation. | Project Status Checking 2 and a version-locked evaluation candidate. |
| **Week 9: Main evaluation and Progress Report** | Conduct the planned participant evaluation with approximately 10–15 participants; record structured ratings and qualitative feedback; freeze relevant model, prompt, pipeline and interface versions. | Completed main evaluation and Group Progress Report. |
| **Week 10: Targeted improvements** | Correct specific issues identified during the main evaluation; run a limited directional smoke test of failed scenarios; complete statistical and privacy findings. | Targeted revised build and documented re-test results. |
| **Week 11: Final validation** | Use the previously untouched held-out prompt set; perform the final statistical, privacy, evaluation and integration checks; test the system on the intended demonstration hardware. | Final held-out results, version manifest and regression-tested release candidate. |
| **Week 12: Buffer, documentation and presentation** | Make documentation and presentation improvements without changing the frozen model or prompt behaviour; complete the final report, demonstration video, presentation and rehearsal. | Final report, software artifacts, presentation, demonstration video and oral-defence preparation. |

The schedule deliberately places the held-out evaluation near the end of the project. This prevents the team from repeatedly modifying the system against the same final test cases. Participant-facing activities are also conditional on completion of the required privacy, safety and governance checks.

### 9.2 Current Progress

By the end of Week 5, the project has established the principal architecture and a limited development path. Completed or available artifacts include:

- CES dataset verification and the 97.3% eligibility result;
- the statistical model and three-state cold-start specification;
- the versioned EvidencePacket contract;
- a GPS-distance feature prototype;
- the local SLM service and version-controlled prompts;
- deterministic request routing and output-grounding controls;
- privacy architecture, dependency review and local latency evidence;
- Evaluation Plan v0.1, development rubric and sealed held-out set;
- a backend API and automated integration tests; and
- a limited normal-response frontend prototype.

The project is not yet a complete participant-facing application. The second Tier 1 feature, complete participant-level statistical evidence, remaining interface states, final model selection and participant-ready release approvals remain scheduled work.

### 9.3 Key Risks and Mitigation Strategies

| Risk | Potential impact | Mitigation |
|---|---|---|
| **PHQ-4 substitution for WHO-5** | The implemented outcome differs from the illustrative measure in the client specification. | Document the substitution clearly, justify it using CES availability and longitudinal density, and confirm acceptance with the client. |
| **Cross-platform feature differences** | Unsupported sensing streams may be incorrectly interpreted as zero behaviour or reduce the usable cohort. | Limit Tier 1 to cross-platform features, preserve structural missingness and require predefined coverage gates. |
| **Incomplete Tier 1 pipeline** | The second behavioural feature may not be fully integrated in time for the frozen build. | Prioritise completion and validation of the two-feature set in Week 6; treat additional features as stretch work. |
| **Insufficient personal history** | The system may generate unreliable personal comparisons for users with limited data. | Enforce the three-state cold-start policy and use deterministic insufficient-data responses. |
| **Statistical overinterpretation** | Population differences or uncertain associations may be presented as personal, causal or clinically meaningful findings. | Use person-mean centring, mixed-effects modelling, multiple-comparison controls, evidence-strength rules and non-causal language. |
| **Incomplete statistical implementation** | The missing lagged predictor and participant-level reporting path may limit the supported evidence. | Complete these components before final model freeze and mark unsupported evidence types as unavailable until validated. |
| **SLM hallucination or unsupported claims** | Generated responses may introduce incorrect values, diagnosis, causation, treatment advice or risk predictions. | Restrict inputs through the EvidencePacket, intercept prohibited requests and validate generated output against approved evidence. |
| **Final SLM selection remains open** | Phi-4 Mini or Qwen3 may not satisfy the final combination of safety, quality and latency requirements. | Run a fixed comparison using the same evidence, prompt set and evaluation criteria before selecting the final model. |
| **Privacy leakage** | Sensitive data may leave the local environment through network calls, logs or dependencies. | Apply loopback-only model access, socket-restricted tests, data minimisation, identifier redaction, dependency review and a participant-use release gate. |
| **Unapproved crisis wording** | Participant-facing crisis information may be incomplete, inconsistent or inadequately reviewed. | Use a deterministic template and require client and evaluation approval before participant-facing use. |
| **Incomplete interface** | Missing response states may make safety boundaries or uncertainty unclear to users. | Implement and test the remaining visually distinct interface states before the pilot. |
| **Small evaluation sample** | Participant results may not generalise to a wider population. | Treat findings as formative prototype evidence and avoid claims of clinical effectiveness or broad generalisability. |
| **Schedule pressure and integration conflicts** | Late contributions or incompatible components may delay evaluation and reporting. | Maintain the shared evidence contract, prioritise the minimum vertical slice, freeze versions before evaluation and reserve Week 12 for documentation and rehearsal. |

### 9.4 Expected Outcomes

Consistent with the client specification, the project is expected to deliver:

1. a working prototype of a privacy-preserving conversational digital mental-health assistant;
2. a data pipeline that converts smartphone-sensing data into interpretable behavioural features;
3. a method for aligning longitudinal PHQ-4 outcomes with behavioural data;
4. a statistical framework for estimating personal baselines and within-person behavioural–wellbeing associations;
5. integration with a locally deployed SLM;
6. a conversational interface for exploring personal behavioural and wellbeing information;
7. a human evaluation of accuracy, usefulness, comprehensibility, trustworthiness, usability and privacy; and
8. an analysis of the project’s limitations, privacy considerations, safety risks and opportunities.

The intended contribution is not a diagnostic or treatment system. The expected result is a research prototype demonstrating how structured longitudinal evidence, local language-model deployment and deterministic safeguards can support understandable reflection on personal behavioural patterns.

### 9.5 Success Criteria

The project will be considered successful if it delivers a reproducible end-to-end prototype that:

- processes the frozen Tier 1 features using documented quality and missingness rules;
- prevents unsupported comparisons when personal history is insufficient;
- produces validated EvidencePackets from the statistical layer;
- generates or routes responses without exposing prohibited claims;
- operates through the approved local model connection;
- passes the registered high-severity safety requirements;
- completes the planned participant evaluation using an approved fixed build; and
- reports performance, limitations and privacy evidence without overstating clinical validity.
## 10. AI Acknowledgement

Generative AI tools, including Claude Code and ChatGPT, were used to support code scaffolding, test development, repository verification, documentation drafting, language refinement and preparation of this proposal. AI-generated outputs were reviewed against the project specification, repository evidence and team decisions before inclusion. The statistical, privacy, safety, evaluation and system-design decisions remain the responsibility of the project team. AI assistance does not replace human review, and the team accepts responsibility for the accuracy, attribution and final content of the submitted work.

## 11. References

Geng, S., Josifoski, M., Peyrard, M., & West, R. (2023). Grammar-constrained decoding for structured NLP tasks without finetuning. In *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing* (pp. 10932–10952). Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.emnlp-main.674

Kroenke, K., Spitzer, R. L., Williams, J. B. W., & Löwe, B. (2009). An ultra-brief screening scale for anxiety and depression: The PHQ-4. *Psychosomatics, 50*(6), 613–621. https://doi.org/10.1176/appi.psy.50.6.613

Maynez, J., Narayan, S., Bohnet, B., & McDonald, R. (2020). On faithfulness and factuality in abstractive summarization. In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics* (pp. 1906–1919). Association for Computational Linguistics. https://doi.org/10.18653/v1/2020.acl-main.173

National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A tool for improving privacy through enterprise risk management, Version 1.0* (NIST CSWP 10). https://doi.org/10.6028/NIST.CSWP.10

Nepal, S., Liu, W., Pillai, A., Wang, W., Vojdanovski, V., Huckins, J. F., Rogers, C., Meyer, M. L., & Campbell, A. T. (2024). Capturing the college experience: A four-year mobile sensing study of mental health, resilience and behavior of college students during the pandemic. *Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies, 8*(1), Article 38, 1–37. https://doi.org/10.1145/3643501

OWASP Foundation. (n.d.). *Logging cheat sheet*. OWASP Cheat Sheet Series. Retrieved September 5, 2026, from https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- 
