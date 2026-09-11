# MindSense — Personal Build Reference

### Full Technical Specification

This document is the working technical reference for building MindSense. It exists to be consulted whenever a decision, tool choice, or implementation approach needs to be recalled during development. Every AI tool used by any team member should be pointed at this document — it is the single source of truth for how this project is built, so all 8 parts stay consistent with each other.

---

## 1. Project Summary

MindSense is a privacy-preserving conversational AI assistant for personalised digital mental health. It processes smartphone sensing data into interpretable behavioural features, combines these with a person's own repeated wellbeing outcomes over time, and lets a locally-deployed Small Language Model (SLM) explain personal patterns conversationally — while explicitly avoiding causal or diagnostic claims. The system runs entirely locally: no cloud dependency, no external API calls, nothing leaves the device.

**Client:** Tianyi Zhang. **Coordinators:** Sara Mumtaz, Dr Muhammad Farhan.

---

## 2. Dataset

**College Experience Study (CES)** — confirmed and locked.

- Kaggle: `subigyanepal/college-experience-dataset`
- License: CC BY-NC-SA 4.0 (verify the exact license tag directly on the Kaggle page before final submission — non-commercial academic use is permitted)
- 220 participants, tracked up to ~5 years (Sept 2017 – June 2022)
- Weekly PHQ-4 (depression + anxiety screening), real repeated measures — median ~170 entries per participant
- Data format: pre-computed daily/hourly features, not raw sensor streams

**Note on the client's spec vs. our actual outcome measure:** the client's spec example (`Client_Specs.md`, Section 2) illustrates the wellbeing outcome using WHO-5. No freely-accessible, zero-barrier dataset repeats WHO-5 with the density this project needs, so we use **PHQ-4** instead — a validated depression/anxiety screening instrument, administered weekly and repeated ~170 times per participant. This is a deliberate substitution, consistent with the client's own "depending on data availability" framing (Section 3.1 of her spec). Raise this explicitly with Tianyi if not already confirmed.

### The platform split — the single most important data caveat

188 iOS / 32 Android participants. Feature availability differs sharply by platform:

| Feature | iOS | Android |
|---|---|---|
| GPS distance travelled | Available | Available |
| Phone unlock count/duration | Available | Available |
| Physical activity | Available | Reads as zero (not missing — unsupported) |
| Call/SMS logs | Not available | Available |

**Locked MVP feature set — cross-platform only:** GPS distance travelled and phone unlock count/duration. These are the only two features confirmed reliable across the full 220-person cohort. Any third feature proposed in Week 5 must meet the same cross-platform + completeness standard, or it stays at two features rather than lowering the bar.

Missing platform-specific features (e.g. activity data on Android) must be stored as structural missingness (a `platform`, `expected_days`, `observed_days`, `coverage_ratio` set of fields) — never imputed as zero behaviour. A zero in an unsupported stream means "could not be measured," not "did not happen."

### Time alignment — hourly/daily sensing vs. weekly PHQ-4

CES sensing data is hourly/daily; PHQ-4 is weekly. These must not be joined naively (raw hourly rows directly against a weekly score). Build one row per participant × PHQ-4 outcome window, using a trailing aggregate of the sensing feature ending immediately before each PHQ-4 timestamp — never use a sensing value that occurred after the outcome it's meant to explain. This alignment step happens in the Data Pipeline, before the data ever reaches the Statistics lead's model.

---

## 3. Locked Technology Stack

| Category | Tool + Version | Why |
|---|---|---|
| Backend framework | FastAPI (latest stable) | Native Pydantic v2 integration auto-generates the OpenAPI contract every role builds against independently |
| ASGI server | Uvicorn | Standard FastAPI companion |
| Data validation / contract | Pydantic v2 (strict mode: extra="forbid", frozen=True) | Single source of truth for the Stats-to-SLM evidence contract, API schemas, and validated SLM output |
| Data handling | pandas + NumPy | CES's wide daily/hourly CSVs; direct, transparent aggregation, no ML pipeline needed |
| Statistical engine | statsmodels (MixedLM) | Fixed random-intercept mixed-effects model, see Section 4 |
| scikit-learn | Explicitly excluded | No model training, no train/test split, no cross-validation happens anywhere in this pipeline. Do not add it to the production environment. |
| Local SLM | Ollama + pinned Phi-4 Mini / Qwen3 candidates; final selection pending | Both `phi4-mini:3.8b` and `qwen3:4b` run locally and support the comparison workflow. The final model must be chosen from expanded, fixed safety and quality evaluation rather than treated as decided by the earlier Phi default. |
| Frontend | React + TypeScript (Vite) | One UI lead works against generated types from the OpenAPI contract while 6 others build backend in parallel; keeps all 7 chat screen-states visually consistent as reusable components |
| Charts | Apache ECharts | Native calendar-heatmap coordinate system, exact fit for daily/weekly personal trend visualisation. Chart.js was rejected: no native calendar heatmap, would need an unmaintained plugin. |
| Local storage | Python standard library sqlite3 (raw, not an ORM) | Schema is small (3-4 tables); a single guarded db.py wrapper module owns all SQL; Pydantic already handles type safety at the API boundary |
| Testing | pytest + pytest-asyncio | Fast local subset runs in under 10 seconds before every Friday push |
| Linting/formatting | Ruff | One tool replaces Black + isort + flake8; enforced via pre-commit |
| Prompt versioning | YAML files in git, validated through a strict Pydantic model | Human-reviewable, versioned, no external prompt-management service needed |

---

## 4. The Statistical Model — Exact Specification

Confirmed approach: a linear mixed-effects model with a participant random intercept, using person-mean-centred predictors to explicitly isolate the within-person effect (not just between-person variation).

For a selected feature x:

```
PHQ4_it = B0 + Bw(x_it - x_mean_i) + Bb * x_mean_i + Bt * time_it + b0_i + e_it
```

- Bw (within-person deviation coefficient) is the only coefficient the app is permitted to use for a "your behaviour vs. your own baseline" statement
- b0_i (the random intercept) captures stable baseline differences between people. It does not by itself separate someone's temporary deviation from their between-person difference; that's what the centring does
- The model uses the locked 2-feature set, a predeclared coverage rule, and a versioned model_spec_id. It must never search across the dataset's columns after seeing results

**Minimum eligibility rule (a product safety decision, not just statistical):** no "ready" evidence is shown unless the observation window meets the agreed coverage threshold AND the participant has enough prior eligible windows to compute a real baseline. Otherwise, return insufficient_data — this is the "not enough data yet" state, not a guess dressed up as an answer.

---

## 5. The Evidence Contract (Stats to SLM)

This is the single most important shared file in the whole project — both the Statistical Analysis Lead and the SLM Integration Lead build against it independently from Week 4, without waiting on each other's implementation.

**Approach:** Strict Pydantic v2 models, extra="forbid", strict=True, frozen=True. FastAPI turns these same models into OpenAPI documentation and validated API inputs/outputs automatically — the UI lead can read /docs from Day 1 to see the exact JSON shape, even before the backend logic is finished.

**Required field groups:**
- Identity/version: contract_version, packet_id, model_spec_id, generated_at, opaque participant_ref (never the raw CES ID)
- Feature window: feature_id, unit, trailing-window dates, value, observed_days, expected_days, coverage_ratio, platform, quality flags
- Personal baseline: method, value, number of baseline observations, eligibility status, ineligible reason if applicable
- Statistical evidence: within-person deviation estimate, confidence interval, direction, evidence strength label
- Uncertainty: item-level and packet-level uncertainty reasons
- Claim policy: approved claim IDs, prohibited claim IDs, permitted response modes

**Permitted claim IDs (the only things the SLM is allowed to say):**
- observation_of_deviation
- within_person_association
- trend_description
- uncertainty_disclosure
- not_enough_data
- non_diagnostic_boundary

**Prohibited claim IDs (must never appear):**
- diagnosis
- causal_explanation
- treatment_or_crisis_advice
- risk_prediction

Example of a permitted statement: "Your unlock count was above your own recent baseline in the observed window, and there's a limited within-person association in this dataset."
Example of a prohibited statement: "Your phone use caused your anxiety." / "You are depressed." / "You should seek treatment."

**Contract freeze:** tag contract-v1.0.0 by Wednesday of Week 4. Any change after that requires sign-off from the Data, Statistics, SLM, UI, and Integration/QA leads together, plus a valid fixture, an invalid fixture, and a regenerated OpenAPI export.

---

## 6. Local SLM — Deployment Details

- Model call pattern: schema-constrained output using the response model's JSON schema, temperature=0 — deterministic output, not free-form generation
- Pin every evaluated model tag in the documented model manifest. The current baseline is `phi4-mini:3.8b` and the current challenger is `qwen3:4b`; the final selection is still pending. Do not use a floating `latest` tag in any release script
- Two fallback templates, not one: a generic refusal, and a separate crisis-aware template with real, reviewed helpline/support-resource content — drafted in Week 4, not improvised later
- Deterministic safety gate: every draft response is validated a second time before becoming a response. It is rejected/rewritten to the safe fallback unless every evidence ID in the draft exists in the input packet, every claim ID is approved by its referenced evidence item, no prohibited claim or phrase is present, and every "ready" explanation includes an uncertainty statement
- Crisis wording is never a model inference. A rule-based detector triggers the pre-approved deterministic crisis-support message — this is safer and auditable, consistent with the project's non-diagnostic scope

**Week 6 branch status (pending review/merge):** `Rz-week6` addresses the
off-topic limitation documented on `main`. Request policy `0.2.0` adds an
explicit `off_topic` category and routes unmatched or ambiguous requests to
the versioned generic refusal before model generation. Crisis and existing
prohibited-request rules keep priority. Prompt `0.4.10` adds a second fail-closed
instruction if an unrelated request unexpectedly reaches the model. The five
fixed public development questions were run against the real local
`phi4-mini:3.8b`: Prompt `0.4.8` produced 0/5 correct refusals by substituting a
grounded evidence answer, while the updated service produced 5/5 deterministic
pre-model refusals. This is development evidence, not held-out or joint
acceptance; see `docs/slm/week6-integration-report.md`.

---

## 7. Privacy Architecture

"No data leaves the local environment" is defined precisely, not left implicit:

- No runtime network requests except the local Ollama daemon (bound to loopback only)
- No telemetry, no analytics, no crash-reporting services
- No CDN-hosted fonts/scripts in the frontend — package everything locally
- Every new dependency added via a PR gets a 10-minute privacy spot-check (does it phone home?) documented in the PR description — this is a standing rule, not a one-off Week 4 task
- Tests should fail the build if any unexpected external socket connection is attempted during testing

---

## 8. Repository Structure

```
mindsense-capstone/
  docs/                      Documentation Lead
  backend/
    contracts/               Shared evidence contract - changes need full sign-off
    data_pipeline/            Data Pipeline Lead
    statistics/                Statistical Analysis Lead
    slm/                       SLM Integration Lead
      prompts/                  YAML prompt templates, versioned in git
    privacy/                   Privacy & Security Lead
    evaluation/                 Evaluation Design Lead
    db.py                       The ONLY file that imports sqlite3
    api/                        Integration & QA Lead - the merge boundary
  frontend/                   Conversational Interface Lead
    src/
      api/                      generated types from OpenAPI + fetch wrapper
      components/
      features/chat/
  tests/                     Mirrors backend/ structure
  dataset/                   CES CSVs - gitignored, never committed
  .pre-commit-config.yaml
```

**Rule:** if a file in data_pipeline/ needs to talk to statistics/, it imports from contracts/ — never directly from another role's folder. No role edits another role's internal code just to make their own pass; cross-role communication happens only through the shared contract.

---

## 9. Evaluation Criteria (Client-Specified)

The client's spec (Section 4) names 10 exact dimensions the human evaluation must assess. The evaluation rubric built in Week 6 must map directly to these — not a rubric invented independently:

1. Accuracy and faithfulness
2. Comprehensibility
3. Usefulness
4. Perceived personal relevance
5. Trust
6. Appropriate communication of uncertainty
7. Ability to distinguish correlation from causation
8. Inappropriate mental-health inference (i.e. the rubric must actively check for this failure mode, not just measure positive qualities)
9. Usability
10. Privacy perceptions

### 9.1 Metric justification (added 2026-09-11)

This subsection is the standing methodological reference for how each client
metric is evaluated and, where one exists, which citation from our own
literature review (the submitted Proposal's References section) backs it.
It reflects the Task 1 team-only evaluation structure (Weeks 7-10: rostered
pairs from the 8 team members, no external participants) — the rubric,
criteria, and pass thresholds themselves are unchanged from the client-spec
mapping above.

**What we've done so far (factual, repo-grounded):**

Evaluation today is a synthetic, development-stage Pass/Fail regime, not yet
a human-participant study:

- **Source plan**: `backend/evaluation/evaluation_plan_v0.1.md` — 5
  categories (data faithfulness, personal-baseline interpretation, wellbeing
  interpretation, association-vs-causation, uncertainty/insufficient-evidence),
  8-10 synthetic dev questions, provisional ≥90% pass rate / 0 causal claims /
  0 diagnoses.
- **Guardrail suite**: `benchmarks/` — 14 high-severity + 2 privacy-extension
  guardrail cases passing (`docs/evaluation/week5-proposal-contribution.md`);
  deterministic safety-gate checks in `backend/slm/safety_gate.py` and
  `backend/slm/output_grounding.py`.
- **Rubric mapped to the client's 10 criteria**: `docs/evaluation/response-quality-rubric-v0.1.md`,
  tied to Section 9 above — drafted and internally tested, not yet run with
  human (or team-only) participants.
- **Held-out set**: 20-30 prompts frozen, untouched until Week 11.
- **Not yet covered**: longitudinal PHQ-4 change and behavioural-PHQ-4
  association interpretation (the evidence contract can't represent those
  inputs yet); joint inter-rater comparison between Chonghao and Richard is
  still outstanding; no pilot or main evaluation session has run yet.

**How we'll do it from today to the end — metric by metric:**

| Client metric | Approach today → end | Existing citation used | Gap |
|---|---|---|---|
| Accuracy / faithfulness | Deterministic evidence-grounding checks (`output_grounding.py`) verify every claim traces to an approved evidence ID in the packet; extended through team rostered-pair sessions Weeks 7-10, held-out set Week 11 | Maynez et al. (2020) — fluent generated text can still be unfaithful to its source, motivating a grounding check separate from fluency | — |
| Usefulness | Rated by rostered-pair team members using the rubric's usefulness dimension | **None exists in our literature review.** Balcombe (2023) ("AI chatbots in digital mental health") is in the Proposal's references but is cited there only for responsible-AI-communication framing, not usefulness — worth checking directly before citing it this way | State this gap explicitly in the report rather than inventing a source |
| Trust | Same rubric, trust dimension, rostered-pair sessions | **None exists.** Same Balcombe (2023) caveat as above | State explicitly, as above |
| Interpretability / uncertainty communication | Enforced structurally — every normal/uncertainty-mode response must contain an explicit uncertainty sentence (`backend/slm/prompts/evidence_explainer.yaml`), checked deterministically, then rated by rostered-pair sessions | World Health Organization (2024) — general AI-health risk-management rationale for bounded, uncertainty-qualified explanations; Balcombe (2023) — AI chatbots in digital mental health, cited alongside WHO for this same responsible-communication framing | Neither source validates a specific interpretability *measurement*, only the rationale for requiring it |
| Correlation vs. causation | Deterministic claim-policy enforcement (prohibited `causal_explanation` claim ID) plus rubric rating | Curran & Bauer (2011) — within/between-person disaggregation is exactly why a within-person deviation is not itself a causal claim | Supports the statistical design choice, not a measurement of whether users correctly read association-not-causation |
| Privacy | Deterministic no-network-egress tests (`tests/privacy/test_no_network_egress.py`), dependency spot-checks, loopback-only Ollama client, rubric's privacy-perceptions dimension rated by rostered-pair sessions | None from the academic literature review; the OWASP Logging Cheat Sheet (informal engineering reference, not an academic source) informs what to redact/not log | Treat as engineering best practice, not a research citation, in the write-up |

**Structural point to carry into the Progress Report:** two of the client's
10 criteria — usefulness and trust — currently have no supporting citation
anywhere in our own literature review. Comprehensibility, usability, and
inappropriate-inference likewise aren't citation-backed; they're addressed
through the deterministic evidence contract and rubric design, not through
literature. State this plainly rather than manufacturing a citation to fill
the gap.

---

## 10. Key Decisions Log

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Statistical library | statsmodels only | scikit-learn | No trainable ML pipeline exists in this project - a fixed mixed-effects model needs no estimator selection, splitting, or cross-validation |
| Database | Raw sqlite3 + one wrapper module | SQLAlchemy ORM | Small, stable 3-4 table schema; Pydantic already validates at the API boundary; ORM overhead isn't worth it for a time-boxed student team |
| Frontend | React + TypeScript | Vanilla HTML/JS | 7 mutually-exclusive chat states benefit from reusable typed components staying visually consistent over a 9-week build with constant backend changes |
| Charts | Apache ECharts | Chart.js | Native calendar-heatmap support, exact fit for daily/weekly personal trend data |
| Fine-tuning | Conditional stretch goal only, mid-Week 11 at the earliest | Default cloud fine-tuning | Real, unresolved privacy conflict - the client's spec (GPU requirements section) names Kaggle (30 free GPU-hours/week) and Google Colab as the intended fine-tuning platforms, but training on cloud GPU contradicts the "nothing leaves local" claim unless training data is purely synthetic. Raised with Tianyi; default is prompt-only + few-shot until resolved. |
