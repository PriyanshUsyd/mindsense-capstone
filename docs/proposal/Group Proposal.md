# MindSense: A Privacy-Preserving Conversational AI Assistant for Personalised Digital Mental Health

Project Proposal — Group Based 5703 Capstone Project, The University of Sydney

**Group Members**

1. Priyansh Khandelwal (541013279)
2. Honghao Li (550293370)
3. Moe Tanaka (550793630)
4. Richard Zhao (540556094)
5. Sheng Wang (540937835)
6. Yuktha Naveen (550302890)
7. Chonghao Shen (540365636)
8. Honglin Lu (550362539)

---

## Abstract

Smartphones passively collect large amounts of behavioural data through GPS location, screen activity and app usage. This data could help people understand how their day-to-day habits relate to their own mental wellbeing, but most existing digital mental health tools process this data in the cloud, compare users against population averages instead of their own history, and sometimes suggest cause-and-effect relationships the evidence does not support. MindSense is a conversational AI assistant that avoids all three problems. It runs entirely on the user's own device, compares a person's current behaviour only against their own past behaviour, and is restricted by an evidence contract that stops it from making diagnostic or causal claims.

The system has four parts: a data pipeline that turns raw smartphone sensor data into behavioural features; a statistical model that separates a person's normal behaviour from their temporary deviations from it; a small language model, run locally through Ollama, that turns the statistical output into plain language responses; and a chat interface where users can ask about their own data.

The project uses the College Experience Study dataset: 220 university students tracked for up to five years, with smartphone sensing data and weekly PHQ-4 depression and anxiety scores. After checking the data, the group confirmed two features that can be measured reliably across both iOS and Android: distance travelled and phone unlock frequency. Other features the client originally wanted, such as call and SMS activity, are only available on one operating system and were excluded for that reason.

The prototype will be tested with real participants in three stages: a small pilot, a larger main evaluation, and a final smoke test, checking accuracy, usefulness, trust and privacy perceptions. This project tests whether useful, personalised mental health insight can be delivered without sending sensitive data to the cloud. For the client, getting this right matters: failing to keep data on-device, or overstating what the evidence shows, would undermine the entire point of the project, which is why both constraints are enforced in code rather than only in writing.

---

## 1. Introduction

People carry their phones for most of the day, and phones passively record movement, screen use and communication patterns without any extra effort from the user. Researchers call this digital phenotyping: using ordinary smartphone data to learn something about a person's psychological state over time.

At the same time, mental health support is not always easy to access, and most people have no simple way to see how their daily habits connect to how they feel. Existing tools usually send data to a cloud server and compare a person to average users rather than their own history, making the insight feel generic rather than personal.

MindSense responds to this gap: a conversational assistant that helps a person see how their own behaviour changes over time and how that relates to their wellbeing, without any data leaving their device. It is built to describe patterns honestly, including when it lacks enough information to say anything useful, rather than guess or make a diagnosis, because an overconfident or wrong claim in a mental health context could genuinely harm someone already struggling.

The benefit is twofold: insight is possible without sending data to a third party, and because every comparison is against the person's own history, it is more likely to be relevant to that person's actual life. The statistical approach is set out in Section 4; the dataset is described in Section 3.3.

---

## 2. Related Literature

This project draws on five areas of existing research, alongside the practical precedent set by existing commercial tools in the same space.

### 2.1 Literature Review

The first is digital phenotyping: the idea that passively collected smartphone data can reveal a person's behaviour and mental state in real time, rather than relying on their memory of how they have been feeling (Insel, 2018). Smartphone ownership is now common enough to make this kind of moment-by-moment observation realistic at scale.

The second is research connecting specific sensed behaviours, such as movement and phone-unlock frequency, to validated depression and anxiety scores. Earlier studies have found modest but real within-person links between reduced mobility or changed phone use and self-reported symptoms, although results vary by population, tracking duration, and whether participants used iOS or Android (Wang et al., 2014; Saeb et al., 2015). The PHQ-4 itself is a validated short screening tool for depression and anxiety and is well suited to repeated weekly measurement (Kroenke et al., 2009). This inconsistency across studies is itself informative: it is why MindSense measures deviation from a person's own baseline rather than assuming a single behavioural signature that would replicate cleanly across different study populations.

The third is statistical method: mixed-effects models with a person-level random intercept and person-mean-centred predictors let researchers separate a stable baseline from a temporary deviation, exactly what MindSense needs to describe change relative to a person's own history rather than everyone else's (Curran & Bauer, 2011).

The fourth is on-device AI. Small language models that run locally, rather than on a cloud server, reduce the risk of exposing sensitive data, at some cost to capability compared with larger cloud-hosted models (Liu et al., 2024; Nakka et al., 2024). This is a genuine trade-off, not a free win: Liu et al. (2024) focus on how far a small model's capability can be pushed, while Nakka et al. (2024) separately raise trust and security concerns specific to on-device models, which is why MindSense treats the local model's restraint as insufficient and layers the schema-validation and evidence-grounding checks from Section 4.1 on top of it, rather than relying on model behaviour alone.

The fifth area is responsible AI communication in health settings: expressing uncertainty honestly, avoiding causal claims from correlation, and avoiding diagnostic or crisis advice without safeguards, which shapes MindSense's evidence contract (World Health Organization, 2024; Balcombe, 2023). Two findings sharpen this: constraining output structure (Geng et al., 2023) does not by itself stop fluent but unsupported content slipping through (Maynez et al., 2020), which is why MindSense enforces both a structural schema check and a separate evidence-grounding check rather than relying on either alone; neither study constitutes clinical validation of the prototype.

Outside academic literature, commercial apps such as Wysa and Woebot show real demand for this kind of tool, though as products rather than published research their methods aren't open to direct comparison; publicly they focus on general wellbeing conversation rather than a person's own longitudinal sensor history, the specific gap MindSense closes.

Read together, these areas point the same way but also expose a gap: the sensing-and-symptom studies (Wang et al., 2014; Saeb et al., 2015) support within-person comparison as a statistical choice, but neither evaluates a system that surfaces such comparisons back to a user in language, and the on-device AI literature is split between raw capability (Liu et al., 2024) and trust and security concerns (Nakka et al., 2024) without testing either against real behavioural evidence. MindSense borrows the measurement logic from one literature and the safety caution from another, but no existing study has evaluated that combination directly, which is why Section 4.5's evaluation, not the literature alone, is what will show whether it holds up.

---

## 3. Project Problems

Building on Section 1's motivation, this project addresses a specific gap: the group did not identify an existing tool combining on-device processing, within-person comparison and an explicit non-diagnostic claim boundary.

### 3.1 Project Aims & Objectives

The project has six aims:

- To develop a data pipeline that turns raw or simulated smartphone sensing data into behavioural features, measured against each person's own history.
- To develop a statistical model, using mixed-effects modelling, that describes the within-person relationship between behaviour and repeated wellbeing scores.
- To integrate a locally deployed small language model that turns statistical evidence into plain, natural responses.
- To ensure the system expresses uncertainty honestly and never makes an unsupported causal or diagnostic claim, enforced through code rather than guidelines alone.
- To build a conversational interface for users to explore their own behavioural and wellbeing history.
- To run a staged human evaluation covering accuracy, usefulness, trust, interpretability and privacy, plus any other criteria the client specifies.

The project's completion will be judged against the following measurable criteria, fixed in advance rather than assessed after the fact:

- **Feature validity**: at least two behavioural features measurable across both iOS and Android, from a dataset where 97.3% of participants meet the group's data-quality threshold (Section 4.2).
- **Safety**: the adversarial suite passes 100% of high-severity/crisis test cases and 90% of standard cases against pre-registered thresholds (Section 4.5), reconfirmed in Week 11 on the untouched held-out set.
- **Statistical validity**: the model's within-person comparison is only surfaced when a user's data meets the minimum coverage and eligible-window thresholds (Section 4.3); otherwise the system returns an explicit "not enough data" response.
- **Build milestones**: the Tier 1 feature set and both safety fallback states fully built and frozen by end of Week 6, with no further functional changes once Week 12 rehearsal begins (Section 7).
- **Human evaluation completion**: a pilot (4-5 participants), a main evaluation (10-15 participants), and a smaller follow-up check (5-8 participants) are each completed and reported against the criteria named above.

### 3.2 Project Questions

The client's original question was broad: can a conversational AI help people understand how their behaviour relates to their mental health, while communicating uncertainty honestly? After early discussions with the client and reviewing the available data, the group narrowed this to four specific, answerable questions:

- Which behavioural features can be measured reliably across the whole study population, regardless of phone operating system, and are therefore usable in a personal baseline model?
- Can a mixed-effects model meaningfully separate a person's temporary behavioural change from their stable baseline, using real longitudinal data?
- Can a small, locally deployed language model communicate this evidence in natural language while staying within a fixed, non-diagnostic set of permitted claims?
- Do users find the resulting insights accurate, useful, trustworthy and appropriately cautious, and do they feel their data is handled privately?

### 3.3 Project Scope

The group tested several candidate datasets against the requirement for real, repeated wellbeing measurements, and settled on the College Experience Study (CES) dataset: 220 participants, tracked for up to five years, with weekly PHQ-4 scores.

Within this dataset, phone operating system matters more than expected: of the 220 participants, 188 use iOS and 32 use Android, and several features the client originally wanted, such as call and SMS metadata, are only available on one platform.

The confirmed feature set is therefore limited to two cross-platform behaviours: distance travelled from GPS, and phone unlock activity. A third feature will only be added if it independently meets the same standard.

Out of scope: any feature that cannot be measured reliably across the full study population; any form of clinical diagnosis, treatment advice or crisis intervention, which the system is not designed to give under any circumstance; and cloud-based model fine-tuning, which conflicts with the project's local-only privacy commitment unless done on entirely synthetic data, and so remains a conditional stretch goal rather than a core deliverable.

### 3.4 Risks & Contingency

The group has identified four risks most likely to affect delivery, each with a contingency that keeps the evaluation and safety guarantees intact if the risk occurs:

- **Participant recruitment**: the staged evaluation needs 19-28 participants across three rounds (Section 4.5). If recruitment falls short, the group will combine the pilot and main rounds at minimum viable sample size and use the freed week for extra safety hardening.
- **Local model performance**: final selection between Phi-4 Mini and Qwen3 depends on Week 5 safety testing (Section 4.5). If neither model reliably clears the fixed pass thresholds, the group will extend the comparison into Week 6 and, if needed, select whichever model meets the non-negotiable 100% crisis-case threshold.
- **Ethics approval**: this has not yet been obtained. The evaluation cannot begin until it is granted for participant sessions, which the group is pursuing as part of the current project stage. If it is delayed, the group will bring forward safety-suite hardening and documentation work (Weeks 6-8) so the evaluation weeks slip later rather than shrinking.
- **Hardware and dataset access**: the system needs only a standard consumer laptop (Section 5.1), and the CES dataset is already secured and validated (Section 3.3). The main residual risk is a team member's development environment becoming unavailable; the documented local build process already used for deployment (Section 4.4) lets any member continue on their own machine.

> **Reconciliation note (2026-09-12):** ethics approval for external participant recruitment was subsequently confirmed *not* available (client, Tianyi Zhang) — see `Weekly_Plan.md`'s superseded note on the Week 6 Evaluation Design row. From Week 7 onward, evaluation runs team-only using rostered pairs drawn from the 8 team members rather than the 19-28 external participants this risk assumed. The contingency mechanism described above (combine pilot/main rounds, use the freed time for hardening) is the same shape of response the team actually took, just triggered by a scope change rather than a recruitment shortfall.

---

## 4. Methodologies

MindSense combines statistical modelling with software development in a weekly, contract-first cycle: technical decisions and shared interfaces are locked early, so the eight team members can build their own part in parallel against one shared, version-controlled specification, with integration and testing each week.

### 4.1 Methods

The semester splits into three phases. Weeks 4-6 lock foundational decisions, build the first feature end-to-end, and freeze the system's core functionality. Weeks 7-9 run a staged human evaluation: a small pilot, refinement, then a larger evaluation on a version-locked build. Weeks 10-12 cover targeted refinement, final safety checks, and final documentation.

This phased approach exists because the project's core requirement, avoiding unsupported diagnostic or causal claims, depends on pre-registered safety thresholds and held-out validation (Section 4.5), both fixed before any results are seen. A less structured process could not demonstrate this rigorously; it could only assert it.

For the SLM component, validated statistical evidence is provided through a versioned `EvidencePacket` rather than raw sensing or PHQ-4 records. The packet and user question pass to a versioned prompt, and the structured draft is checked against permitted claims, evidence identifiers, feature names, units, numerical roles and uncertainty requirements. Requests involving insufficient data, prohibited claims or crisis language route instead to a deterministic fallback response.

```
Runs entirely on the user's device, with no data sent to the cloud
┌─────────────────┐   ┌───────────────┐   ┌───────────────────┐
│ Smartphone       │──▶│ Data pipeline │──▶│ Statistical model  │
│ sensors          │   │               │   │ (mixed-effects)    │
│ (GPS, unlocks)   │   └───────────────┘   └─────────┬──────────┘
└─────────────────┘                                  ▼
                                              ┌───────────────┐
                                              │ Evidence       │
                                              │ Packet         │
                                              └───────┬────────┘
                                                       ▼
┌───────────────────┐   ┌────────────────────┐   ┌───────────────┐
│ Conversational      │◀─│ Safety / evidence   │◀──│ Local SLM      │
│ interface (chat)    │  │ check               │   │ (Ollama)       │
└───────────────────┘   └─────────┬──────────┘   └───────────────┘
        ▲                          │ fallback response when data is
        └──────────────────────────┘ insufficient or a request violates
                                     the evidence contract
```

*Figure 1. MindSense system architecture: sensing data is converted into a versioned `EvidencePacket`, which is either narrated by the local SLM (subject to a deterministic safety and evidence check) or, when checks fail, routed straight to a fixed fallback response.*

### 4.2 Data Collection

The project uses the College Experience Study (CES) dataset (Nepal et al., 2024), available on Kaggle under a CC BY-NC-SA 4.0 licence that permits non-commercial academic use with attribution. It covers 220 university students tracked from September 2017 to June 2022, combining daily and hourly smartphone sensing data with weekly PHQ-4 depression and anxiety scores.

Before committing to this dataset, the group validated it directly and confirmed that 97.3% of participants meet the group's data-quality threshold, defined as at least 80% sensor-data coverage across the tracking period with no gap longer than seven consecutive days. The group also confirmed a real constraint: of the 220 participants, 188 use iOS and 32 use Android, and some features are only reliably available on one platform because of how each operating system restricts background data access, not because participants behave differently. This is what shaped the scope decision in Section 3.3.

### 4.3 Data Analysis

The statistical approach is a linear mixed-effects model with a person-level random intercept and person-mean-centred predictors, separating stable differences between people from a person's own temporary deviation from their usual behaviour. Only the second is used to compare someone's current behaviour with their own baseline, so the system never confuses a between-person comparison with a within-person one.

The group also built an eligibility rule to stop the system generating a comparison when there is not enough personal history: a comparison only appears once a participant's data meets a minimum coverage threshold (at least 14 days of valid sensing data in the preceding 30-day window) and has at least four such eligible windows recorded. Otherwise the system returns an explicit "not enough data" response instead of guessing.

> **Reconciliation note (2026-09-12):** these coverage/window figures reflect the Week 5 proposal-stage design. Several statistical parameters were subsequently finalised more precisely and, in one case, changed — see `CLAUDE.md`'s "Finalised decisions": the quality gate is locked at 12h (not stated numerically here), the comparison window is `[-14, -1]` (ending the day *before* assessment, not the assessment day itself — a fix applied 2026-09-12 to `backend/statistics/mixed_effects_model.py`), and the transform order is locked as `log(mean)`, not `mean(log)`. This proposal is left as the Week 5 record of the plan; it is not restated here as if the Week 5 text already reflected the later corrections.

### 4.4 Deployment

MindSense runs locally without external cloud inference. Its FastAPI backend uses Ollama over loopback (Ollama, n.d.). Phi-4 Mini is the baseline, Qwen3 the challenger; final selection remains pending, verified in Week 5. Updates are versioned in GitHub and delivered through a documented local process agreed with the client.

### 4.5 Testing

Because this project handles sensitive mental health data, testing goes beyond standard practice: safety testing is treated as seriously as correctness testing.

At the unit and integration level, the group maintains a growing automated test suite covering the statistical logic, shared data contract, and local privacy guarantees, run on every change. Separately, an adversarial safety suite checks the system refuses unsupported diagnostic, causal, treatment and risk-prediction requests, and routes crisis or self-harm inputs to a deterministic Australia-specific support response, with pass thresholds fixed before any results were seen (100% crisis cases, 90% standard). A held-out prompt set is used once, near the project's end, to check this generalises.

Finally, the group runs a staged human evaluation: a pilot (4-5 participants), a main evaluation (10-15 participants) on a version-locked build, and a follow-up check (5-8 participants) to confirm earlier issues were fixed. Participation is voluntary: participants give informed consent before each session and may withdraw at any time, with their data discarded. A participant disclosing distress or risk triggers a standardised crisis-response script and escalation instead of continuing. Session data is de-identified, kept only on local systems, and assessed against five criteria from Section 3.1: accuracy (whether the assistant's stated evidence matches the participant's own logged behaviour), usefulness, trust, interpretability and privacy, using the rubric and runbook from Week 6.

> **Reconciliation note (2026-09-12):** as recorded in the Section 3.4 note above, the evaluation format changed after this proposal — team-only rostered pairs from Week 7 onward, not external participant recruitment. The pass-threshold figures and testing philosophy in this section are unchanged and still accurate.

---

## 5. Resources

### 5.1 Hardware & Software

The system runs on a standard consumer laptop with no special hardware. These technology choices were locked early so all eight team members could build against them in parallel:

- **FastAPI (Python) with Pydantic**: backend framework enforcing the shared data contract via built-in validation.
- **pandas and statsmodels**: data preparation and fitting the mixed-effects model.
- **Ollama, running Phi-4 Mini (baseline) and Qwen3 (challenger)**: local LLM runtime chosen for offline, schema-constrained operation.
- **React, TypeScript and Vite**: conversational interface, built independently of the backend against the same shared contract.
- **Apache ECharts**: visualises behavioural trends, including calendar-heatmap views of a person's patterns over time.
- **SQLite**: local, file-based storage with no separate server process, consistent with the local-only design.
- **pytest and Ruff**: automated testing and code-quality checks across the shared codebase.

### 5.2 Materials

The CES dataset, obtained from Kaggle under its Creative Commons licence; a shared GitHub repository for version control and documentation; Zoom for weekly meetings; and each member's own laptop, sufficient to run the project's local software stack.

### 5.3 Roles & Responsibilities

Each member holds one fixed role for the semester, with detailed responsibilities below:

| Role & Member | Detailed Responsibilities |
|---|---|
| **Integration & QA Lead**<br>Priyansh Khandelwal | Coordinates the shared technical contract, reviews and merges code contributions, runs the automated test suite, and facilitates client and group meetings. |
| **Data Pipeline Lead**<br>Honghao Li | Validates the CES dataset, builds the pipeline from raw sensing data to locked behavioural features, and manages data-quality/platform-availability issues. |
| **Statistical Analysis Lead**<br>Moe Tanaka | Designs and implements the mixed-effects model, defines personal-baseline eligibility rules, and produces the evidence consumed by the language model. |
| **SLM Integration Lead**<br>Richard Zhao | Integrates and configures the local SLM, designs conversational prompts and fallback templates, and implements the deterministic safety-checking layer. |
| **Conversational Interface Lead**<br>Sheng Wang | Designs and builds the user-facing conversational interface and behavioural trend visualisations. |
| **Privacy & Security Lead**<br>Yuktha Naveen | Defines the project's privacy and security architecture, keeping sensitive data on-device, and validates it through automated leak-detection tests and privacy/security reviews. |
| **Evaluation Design Lead**<br>Chonghao Shen | Designs the adversarial safety-testing taxonomy, defines evaluation pass thresholds, and designs and facilitates the staged human evaluation process. |
| **Documentation & Report Lead**<br>Honglin Lu | Coordinates the group's written deliverables, including this proposal, and manages meeting documentation and client-facing status reporting. |

---

## 6. Expected Outcomes

The deliverables below follow from the aims in Section 3.1 and the methods in Section 4: each is part of one integrated system, not a standalone piece of work.

### 6.1 Project Deliverables

- A working prototype of a conversational digital mental health assistant.
- A data pipeline that turns raw or simulated smartphone sensing data into behavioural features.
- A statistical framework combining longitudinal wellbeing outcomes with behavioural data to identify personalised behaviour-wellbeing relationships.
- Integration with one or more locally deployed small language models.
- A conversational interface for exploring personal behavioural and wellbeing history.
- A staged human evaluation of accuracy, usefulness, trust and interpretability, plus the client's other specified criteria.
- An analysis of the opportunities, limitations, privacy considerations and risks of conversational AI in digital mental health.

### 6.2 Implications

For the individual user, this project tests whether passively collected phone data can become private insight into their own wellbeing without leaving their device, a principle future tools could prioritise over cloud convenience. For the wider field, it offers an evaluated proof-of-concept combining personal-baseline statistical modelling with a locally deployed conversational AI, constrained by an explicit, auditable claim boundary addressing concerns about AI systems overstating certainty.

Given the project's timeframe and prototype status, these implications are an initial proof-of-concept, not a clinically validated tool. The CES sample comes from a single university with an uneven iOS-to-Android split and self-reported PHQ-4 scores rather than a clinical diagnosis, so findings may not generalise further. On-device processing removes the risk of data leaving the phone, but does not itself guarantee safe outputs; that depends on the evidence contract and testing in Section 4.5. The system must never be presented as a diagnostic, treatment or crisis-intervention tool, a limitation discussed further in the group's Final Report; compromising privacy or overstating claims are risks this project's design is built to avoid.

---

## 7. Milestones / Schedule

This schedule reflects the group's locked plan for Weeks 4-12 (Section 4.1).

| Milestone | Tasks | Reporting | Date |
|---|---|---|---|
| Week 4 | Lock foundational decisions: dataset, model, SLM plan, evidence contract. | Client meeting; Status Checking 1 | Week 4 |
| Week 5 | Build one feature end-to-end; confirm feature set; run safety testing. | Group Proposal Report due | 6 Sep |
| Week 6 | Freeze the Tier 1 feature set and safety fallback states. | None | Week 6 |
| Week 7 | Pilot evaluation: 4-5 participants, frozen build. | None | Week 7 |
| Week 8 | Harden system from pilot findings; test safety fallback states. | Project Status Checking 2 | 4 Oct |
| Week 9 | Main evaluation: 10-15 participants, version-locked build. | Group Progress Report due | 11 Oct |
| Week 10 | Address findings; smoke-test; first cross-training. | None | Week 10 |
| Week 11 | Final safety validation on held-out set; finalise documentation and demo video. | None | Week 11 |
| Week 12 | Final polish and rehearsal only; no further changes. | Final Report, Presentation, Demo Video | Week 12 |

> **Reconciliation note (2026-09-12):** per the Section 3.4 note above, the Week 7-10 evaluation rows now run team-only (rostered pairs), not external participants; the reporting deadlines and milestone shape are otherwise unchanged from this proposal.

---

## References

Balcombe, L. (2023). AI chatbots in digital mental health. *Informatics, 10*(4), Article 82. https://doi.org/10.3390/informatics10040082

Curran, P. J., & Bauer, D. J. (2011). The disaggregation of within-person and between-person effects in longitudinal models of change. *Annual Review of Psychology, 62*, 583-619. https://doi.org/10.1146/annurev.psych.093008.100356

Geng, S., Josifoski, M., Peyrard, M., & West, R. (2023). Grammar-constrained decoding for structured NLP tasks without finetuning. In *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing* (pp. 10932-10952). Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.emnlp-main.674

Insel, T. R. (2018). Digital phenotyping: A global tool for psychiatry. *World Psychiatry, 17*(3), 276-277. https://doi.org/10.1002/wps.20550

Kroenke, K., Spitzer, R. L., Williams, J. B. W., & Löwe, B. (2009). An ultra-brief screening scale for anxiety and depression: The PHQ-4. *Psychosomatics, 50*(6), 613-621. https://doi.org/10.1176/appi.psy.50.6.613

Liu, Z., Zhao, C., Iandola, F., Lai, C., Tian, Y., Fedorov, I., Xiong, Y., Chang, E., Shi, Y., Krishnamoorthi, R., Lai, L., & Chandra, V. (2024). MobileLLM: Optimizing sub-billion parameter language models for on-device use cases. In *Proceedings of the 41st International Conference on Machine Learning* (PMLR 235, pp. 32431-32454). PMLR. https://proceedings.mlr.press/v235/liu24ce.html

Maynez, J., Narayan, S., Bohnet, B., & McDonald, R. (2020). On faithfulness and factuality in abstractive summarization. In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics* (pp. 1906-1919). Association for Computational Linguistics. https://doi.org/10.18653/v1/2020.acl-main.173

MindSense Group. (2026). *Client project specification: Conversational AI for personalised digital mental health.* Unpublished project brief provided by client Tianyi Zhang, University of Sydney.

Nakka, K., Dani, J., & Saxena, N. (2024). Is on-device AI broken and exploitable? Assessing the trust and ethics in small language models. *arXiv*. https://arxiv.org/abs/2406.05364

Nepal, S., Liu, W., Pillai, A., Wang, W., Vojdanovski, V., Huckins, J. F., Rogers, C., Meyer, M. L., & Campbell, A. T. (2024). College Experience Study dataset [Data set]. Kaggle. https://www.kaggle.com/datasets/subigyanepal/college-experience-dataset

Ollama. (n.d.). *Ollama documentation.* Retrieved September 6, 2026, from https://ollama.com/docs

Saeb, S., Zhang, M., Karr, C. J., Schueller, S. M., Corden, M. E., Kording, K. P., & Mohr, D. C. (2015). Mobile phone sensor correlates of depressive symptom severity in daily-life behavior: An exploratory study. *Journal of Medical Internet Research, 17*(7), Article e175. https://doi.org/10.2196/jmir.4273

Wang, R., Chen, F., Chen, Z., Li, T., Harari, G., Tignor, S., Zhou, X., Ben-Zeev, D., & Campbell, A. T. (2014). StudentLife: Assessing mental health, academic performance and behavioral trends of college students using smartphones. In *Proceedings of the 2014 ACM International Joint Conference on Pervasive and Ubiquitous Computing* (pp. 3-14). ACM. https://doi.org/10.1145/2632048.2632054

World Health Organization. (2024). *Ethics and governance of artificial intelligence for health: Guidance on large multi-modal models.* World Health Organization. https://www.who.int/publications/i/item/9789240084759

---

## 8. AI Acknowledgement

**Part A: Have you used AI tools in the completion of this assignment?**

Yes.

**Part B: What automated writing or generative AI tools have you used?**

Claude (Anthropic). https://claude.ai

**Part C: How have you used automated writing or generative AI tools in the assessment?**

We used Claude (Anthropic), accessed through claude.ai and through Claude Code with direct access to the group's GitHub repository, throughout Weeks 4 and 5 of this project. Claude was used in two distinct ways. First, as a coding and verification assistant: reviewing the repository against the team's Weekly Plan, running and interpreting the automated test suite, helping implement and debug the statistical model (including setting up an R-based statistical bridge for degrees-of-freedom and serial-correlation estimation not available in Python), and cross-checking status claims in the repository against actual code and test results. Second, as a writing and editing assistant for this proposal report: drafting section content from facts, data and decisions supplied by the group, restructuring and tightening the writing after supervisor feedback, and formatting the document to match the university's official template.

We did not ask Claude to generate the Related Literature section's citations from its own knowledge, because of the risk of it inventing sources that do not exist. The literature and references in Section 2.1 and the Reference list were sourced and verified separately, then formatted into the report with Claude's help.

We went through several drafts of this report with Claude across multiple sessions rather than accepting a single output. Every technical claim, dataset detail, test result and project decision in this report reflects the group's own work; Claude's role was to help express that work clearly, in the university's required format, and to check it against the actual project record rather than to invent content of its own.

> **Cross-reference note (2026-09-12):** this Part A/B/C statement is the University's official assessment-declaration format, present in the source PDF this section was reconciled from. A separate, much more detailed internal accounting — including specific commit hashes, per-person attribution gaps found and later resolved (Sheng Wang, Honghao Li), and an explicit list of what the AI did *not* do — is maintained at `docs/proposal/ai-acknowledgement.md`. That document is the fuller record for the team's own reconciliation purposes; this section is the one required in the submitted proposal format. The two are consistent with each other; neither replaces the other.
