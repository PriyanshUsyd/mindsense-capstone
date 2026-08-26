# Project Spec

## Title

Conversational AI for Personalised Digital Mental Health

## Introduction

This project aims to develop a **privacy-preserving conversational AI assistant for personalised digital mental health**. The system will process smartphone sensing data, such as mobility, location patterns, screen use, and device activity, into interpretable behavioural features and combine these with longitudinal mental health or wellbeing outcomes. Personal behavioural changes and statistically derived relationships between digital phenotyping features and wellbeing will be provided to a locally deployed Small Language Model (SLM), allowing users to explore their own behavioural and wellbeing patterns through natural-language conversation.

The project will investigate whether conversational AI can help users better understand **how their behaviours change over time and how these patterns relate to their mental health or wellbeing**, while appropriately communicating uncertainty and avoiding unsupported causal or diagnostic conclusions. The final system will include a working chatbot prototype and a human evaluation assessing the accuracy, usefulness, interpretability, trustworthiness, and privacy of the generated insights.

## GPU requirements (if fine-tuning)

 e.g. Kaggle account - 30 hours per week using GPU

Google Colab

## Expected Outcomes

By the end of the project, the team is expected to deliver:

1. A working prototype of a conversational digital mental-health assistant.
2. A pipeline for transforming raw sensing data into meaningful behavioural features.
3. A method for integrating longitudinal mental-health or wellbeing outcomes with behavioural data.
4. A backend analysis framework for identifying personalised behavioural–wellbeing relationships.
5. Integration with one or more locally deployed SLMs.
6. A conversational interface for querying and exploring personal behavioural and wellbeing information.
7. A human evaluation examining the accuracy, usefulness, trustworthiness, and interpretability of the generated insights.
8. An analysis of the opportunities, limitations, privacy considerations, and risks associated with conversational AI for digital mental health.

## Proposed System

The project will develop an end-to-end prototype containing four main components.

### 1. Digital Phenotyping Pipeline

Raw or simulated smartphone sensing data will be processed into interpretable secondary behavioural features. Depending on data availability, these may include:

- mobility and distance travelled;
- location diversity and entropy;
- time spent at home;
- screen time and unlock frequency;
- night-time device engagement;
- physical activity;
- social or communication-related features; and
- behavioural regularity and variability.

The system should also calculate changes relative to each individual’s historical baseline rather than relying solely on population-level comparisons.

### 2. Mental Health and Wellbeing Integration

Longitudinal self-reported outcomes will be aligned with the digital phenotyping data.

The backend will perform appropriate statistical analyses to characterise relationships between behaviour and wellbeing. These analyses may include within-person correlations, trends, regression models, lagged relationships, or other suitable longitudinal approaches.

The resulting evidence can be represented in a structured form (depending on the datasets) such as:

**Current behaviour:** Mobility 28% below personal baseline

**Current wellbeing:** WHO-5 decreased from the previous assessment

**Historical relationship:** Lower mobility has tended to coincide with lower WHO-5 scores for this individual

**Evidence strength:** Moderate

**Interpretation:** Association only; no causal relationship established

### 3. Local Small Language Model

One or more locally deployed SLMs will receive the structured behavioural and wellbeing information and generate conversational responses.

Keeping the language model local provides an opportunity to investigate **privacy-preserving AI for sensitive personal and mental-health-related data** while avoiding the need to send personal sensing information to external language-model services.

The SLM will primarily be responsible for:

- translating numerical information into understandable language;
- answering natural-language questions about behavioural history;
- explaining changes relative to personal baselines;
- communicating behavioural–wellbeing relationships;
- communicating uncertainty and limitations; and
- distinguishing association from causation.

### 4. Human evaluation

A human evaluation will assess whether the developed system communicates digital phenotyping and mental-health information accurately and usefully.

The models could be evaluated generated responses in terms of:

- accuracy and faithfulness;
- comprehensibility;
- usefulness;
- perceived personal relevance;
- trust;
- appropriate communication of uncertainty;
- ability to distinguish correlation from causation;
- inappropriate mental-health inference;
- usability; and
- privacy perceptions.

### 5. Conversational Interface

A user-facing chatbot will allow individuals to interact naturally with their longitudinal behavioural and wellbeing data.

The overall architecture will therefore be:

**Raw sensing data → Behavioural features → Personal baseline and longitudinal analysis → Mental-health/wellbeing outcomes [→ Statistical evidence/Secondary Analysis] → Local SLM → Conversational insights + Human analysis**
