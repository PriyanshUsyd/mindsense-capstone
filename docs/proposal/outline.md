# Group Proposal Report — Outline

> Starting content for whoever picks up the Group Proposal Report writing
> — a substantially fleshed-out outline, not finished prose, built during
> Week 4 to have something concrete to work from. Due Week 5 (Sep 6) per
> Weekly_Plan.md.

Sections map directly onto `Client_Specs.md`'s "Proposed System" (5
components) and "Expected Outcomes" (8 deliverables), with pointers to
what's actually real on `main` as of 2026-08-29 for each.

## 1. Introduction & Problem Statement

- Client: Tianyi Zhang. Coordinators: Sara Mumtaz, Dr Muhammad Farhan
  (`Client_Specs.md` header info via `build-reference.md` Section 1).
- Restate the client's framing directly: *"a privacy-preserving
  conversational AI assistant for personalised digital mental health"*
  (`Client_Specs.md` Introduction) — a chatbot that explains a person's own
  behavioural patterns against their own baseline, not a diagnostic tool.
- State plainly, early: this is explicitly **non-diagnostic** and
  **local-only** — both are constraints the client's spec sets up
  ("avoiding unsupported causal or diagnostic conclusions"), not choices
  the team added independently.

## 2. Dataset (Client_Specs.md doesn't name one — this is the team's choice, justify it)

- **College Experience Study (CES)**, chosen over the client's illustrative
  WHO-5 example because CES gives weekly, repeated-measures data at the
  density this project needs (`build-reference.md` Section 2) — the client's
  own spec explicitly allows this ("depending on data availability").
- PHQ-4 substituted for WHO-5 — flag this explicitly to the client/graders
  as a deliberate, documented substitution, not an oversight.
- The platform-split constraint (188 iOS / 32 Android) and why it locks the
  Tier 1 feature set to exactly two features (GPS distance, unlock
  count/duration) — both map directly onto `Client_Specs.md`'s "mobility and
  distance travelled" and "screen time and unlock frequency" examples under
  "Digital Phenotyping Pipeline."
- **Real artifact to cite:** `docs/data-pipeline/ces-reverification.md` and
  `backend/data_pipeline/ces_eligibility.py` — 97.3% of the 220-participant
  cohort is eligible under the real, locked sufficiency gate. This is now
  the shared, working eligibility script and figure (see that doc for the
  full derivation).

## 3. System Architecture — mapped to Client_Specs.md's 5 components

| Client_Specs.md component | This project's implementation | Real Week 4 artifact |
|---|---|---|
| 1. Digital Phenotyping Pipeline | Trailing-window feature aggregation, structural-missingness tracking (never zero-imputed) | `skills/data-pipeline-ces.md`; Honghao's pipeline code is Week 5 scope |
| 2. Mental Health & Wellbeing Integration | Mixed-effects model (LMM), person-mean-centring, within/between (Mundlak) specification | Moe's real, locked spec: `weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md` |
| 3. Local Small Language Model | Ollama + phi4-mini:3.8b, schema-constrained JSON, temperature=0, two fallback templates | `backend/slm/model_manifest.yaml`, `backend/slm/prompts/` |
| 4. Human evaluation | Rubric mapped to the client's 10 named criteria, adversarial suite, held-out set | Chonghao's real plan: `backend/evaluation/evaluation_plan_v0.1.md`, with the pass-threshold locked as the Week 4 default (100% high-severity / 90% standard, see `docs/evaluation/pass-threshold.md`) |
| 5. Conversational Interface | React + TypeScript (Vite), 7 mutually-exclusive chat states | `docs/ui/chat-states-design.md`, `frontend/` (scaffold builds clean) |

- The shared evidence contract (`backend/contracts/evidence.py`) is the
  load-bearing interface between components 2 and 3 — describe it as the
  mechanism that lets 6 of the 8 roles build independently in parallel
  (`build-reference.md` Section 8's "no role edits another role's internal
  code" rule).
- Locked technology stack table — `build-reference.md` Section 3 — explain
  the scikit-learn exclusion and the raw-sqlite3-over-ORM choice; both read
  as deliberate, reasoned decisions in the report, not omissions.

## 4. Statistical Approach

- Present Moe's real model as locked: LMM with person-level random
  intercept **and** random slope, Mundlak within/between centring,
  Holm-Bonferroni (confirmatory) + Benjamini-Hochberg FDR (exploratory)
  multiple-comparison control.
- The three-state cold-start policy (State A: no data / State B: partial,
  descriptive-only / State C: full, comparative) — this is what keeps the
  system from asserting a baseline comparison it can't actually support,
  directly serving `Client_Specs.md`'s requirement to "calculate changes
  relative to each individual's historical baseline."
- Evidence-strength banding (weak/moderate/strong) — ties the system's
  confidence language to real statistical output rather than a
  hand-waved label.

## 5. SLM Integration & Safety

- Ollama + phi4-mini:3.8b, why local (`Client_Specs.md` Local SLM section:
  *"avoiding the need to send personal sensing information to external
  language-model services"*).
- The permitted/prohibited claim system — walk through the exact structured
  example from `Client_Specs.md` ("Current behaviour... Current
  wellbeing... Historical relationship... Evidence strength...
  Interpretation") and show how the evidence contract implements that shape.
- Two fallback templates, the deterministic safety gate, and why crisis
  wording is rule-based rather than model-generated — this is a direct
  answer to the client's "avoiding unsupported causal or diagnostic
  conclusions" requirement, made concrete.
- **Flag in the report itself:** the crisis-aware template's helpline
  content is still a reviewed-pending placeholder as of Week 4 — state this
  honestly rather than implying it's finished.

## 6. Privacy Architecture

- What "nothing leaves the device" means precisely (network calls,
  telemetry, logs, dependencies) — Yuktha's real work:
  `privacy/privacy_architecture_principles.md`,
  `privacy/dependency_privacy_checklist.md`.
- Note honestly: the real-machine SLM latency benchmark has been attempted
  twice (once by Yuktha, once independently) and both times found no Ollama
  installed on the machine being used — flag this as a genuine open risk
  for the report's Timeline & Risk section, not something to gloss over.

## 7. Evaluation Plan

- The client's 10 named criteria (`Client_Specs.md` "Human evaluation"
  section, reproduced in `build-reference.md` Section 9) — the rubric must
  map directly to these.
- Chonghao's real evaluation plan (5 categories, 8-10 dev questions) with
  the pass-threshold locked as the Week 4 default (100% high-severity /
  90% standard) — Evaluation Design Lead may still propose a revision via
  normal PR review, but this isn't a blocker for the report.
- The held-out set discipline (20-30 prompts, untouched until Week 11) —
  explain *why* this matters for the report's credibility, not just that
  it exists.

## 8. Timeline & Risk

- Weekly plan summary, Week 4 → Week 12.
- Name the real risks already surfaced, honestly:
  1. PHQ-4/WHO-5 substitution (needs client confirmation).
  2. Fine-tuning vs. cloud-GPU conflict (`build-reference.md` decisions log)
     — the client's spec names Kaggle/Colab GPU hours, which conflicts with
     the local-only privacy claim unless training data is purely synthetic.
  3. SLM latency is still unverified on any real machine as of Week 4.
  4. Crisis-line resource content is still a reviewed-pending placeholder
     — needs real review before Week 7's pilot at the latest.

## 9. AI Acknowledgement Statement

- Required per Weekly_Plan.md Week 5.
- Describe honestly where AI tools were used, including this Week 4
  gap-fill/reconciliation pass — the real teammate branches that were
  merged in, the AI-drafted placeholders that were built and later
  superseded, and the shared CES eligibility script built to match
  Honghao's reported figure. This kind of transparency is exactly what an
  AI Acknowledgement statement is for.
