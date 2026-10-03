# Preregistration — MindSense Statistical Analysis

**Status:** Compiled by session tooling from Moe Tanaka's existing, already-locked
decisions (not authored from scratch). This document did not exist anywhere in the
repository or on any branch before this compilation — confirmed via `git ls-tree`
across every local and remote branch. **Please review and fill any section marked
"pending Moe's input" below.**

**Sources compiled from** (every substantive claim below traces to one of these; see
inline citations):
- `weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md` (Moe Tanaka, Statistical
  Analysis Lead — locked Week 4 decisions)
- `Week5_Statistical_Analysis_Deliverable.md`
- `analysis/archive/baseline.py` (retired, logic reconciled into `backend/statistics/`;
  see `analysis/archive/README.md`)
- `backend/statistics/eligibility.py`
- `backend/statistics/mixed_effects_model.py`
- `backend/data_pipeline/cleaning.py`
- `CLAUDE.md`'s "Finalised decisions" section (supersedes earlier drafts where the two
  disagree — noted below wherever that applies)

Nothing in this document was invented for the occasion. Where a preregistration
normally needs a decision that isn't actually made anywhere in the repo, that gap is
left explicit rather than filled in.

---

## 1. Hypotheses

**Pending Moe's input.** The repository's locked material specifies the *model*, the
*primary estimand* (β1, the within-person effect of the Tier-1 predictor on PHQ-4), and
the *primary outcome/predictor pairing* (GPS distance → PHQ-4 total, Week 4 deliverable
§0/§1.1), but does not state a directional hypothesis in preregistration language (e.g.
"we predict lower GPS distance is associated with higher PHQ-4 scores"). Before this
document can serve as an actual preregistration, Moe needs to either supply that
directional statement or confirm that the analysis is intentionally non-directional /
exploratory for this predictor.

What *is* locked:
- **Primary outcome:** PHQ-4 total score (0–12), `general_ema.csv`, repeated per person
  (~weekly). Secondary outcomes: PHQ-4 anxiety (items 1–2) and depression (items 3–4)
  subscales; PAM (1–16); single-item `stress`; state self-esteem (`sse3`). (Week 4 §0)
- **Primary Tier-1 predictor (vertical slice):** GPS daily distance (`loc_dist_ep_0`).
  (Week 4 §0, revision note)
- **Primary estimand:** β1, the person-mean-centred within-person effect — "how person-
  level wellbeing moves when this person's behaviour deviates from their own baseline."
  β3 (between-person) is retained specifically so β1 isn't confounded by it (Mundlak /
  within-between specification; Hoffman & Stawski 2009; Curran & Bauer 2011). (Week 4
  §1.2)
- **Lag term (β2):** a 1-occasion-lag sensitivity/secondary term supporting "changes
  over time" framing — explicitly **not** promoted to a causal claim. (Week 4 §1.2)

## 2. Study design and data

- **Dataset:** College Experience Dataset (Nepal et al. 2024) — `Sensing/sensing.csv`
  (daily), `Sensing/steps.csv` (daily), `EMA/general_ema.csv` (repeated self-report),
  `Demographics/demographics.csv`. (Week 4 header)
- **Design:** longitudinal, unbalanced panel — repeated EMA occasions (level 1) nested
  within persons (level 2); median ≈170 EMA occasions/person, range 1–441, spanning up
  to ~3.9 years. (Week 4 §1.1, §8)

## 3. Statistical model

**Model family:** linear mixed-effects model (LMM), Gaussian, person-level random
intercept + random slope on the primary within-person predictor, time-varying
predictors person-mean-centred with the person mean re-entered as a between-person term
(within–between / Mundlak specification). (Week 4 §0, §1.1)

**Formal specification** (Week 4 §1.2):

```
PHQ4_it = β0
        + β1 · x_within_it                (within-person effect  ← primary estimand)
        + β2 · x_within_i(t−1)            (1-occasion lag, sensitivity / secondary)
        + β3 · x_between_i                (between-person effect, controls confounding)
        + β4 · week_in_study_it           (linear time / practice trend)
        + β5 · term_phase_it              (in-term vs break indicator; COVID-era flag)
        + u0_i + u1_i · x_within_it        (random intercept + random slope, person i)
        + e_it

  u_i = (u0_i, u1_i) ~ MVN(0, Σ)
  e_it ~ N(0, σ²)                          AR(1) on e within person
```

- `x_within_it = x_it − x̄_i` (person-mean-centred); `x_between_i = x̄_i − x̄..`
  (grand-mean-centred). `x̄_i` is person *i*'s mean over all their valid occasion-level
  `x_it` values used in the model fit. (Week 4 §1.2; implemented in
  `backend/statistics/mixed_effects_model.py::build_model_frame`)
- **Predictor construction (`x_it`):** clean each day → average the *raw* (untransformed)
  cleaned values over the trailing window → `log(mean + 1000)` once, after averaging —
  **log-of-mean, not mean-of-log** (`CLAUDE.md` "Finalised decisions"; implemented in
  `backend/statistics/mixed_effects_model.py::build_trailing_predictor`, fixed
  2026-09-12).
- **Trailing alignment window:** 14 days, ending the day **before** the EMA date (not
  inclusive of it — avoids same-day information leakage). Gate: ≥7 valid sensor-days in
  the window; occasions failing the gate are **excluded, not imputed**.
  (`TRAILING_WINDOW_LAG_DAYS = 1`, `OCCASION_MIN_VALID_SENSOR_DAYS = 7`,
  `backend/statistics/mixed_effects_model.py`; `CLAUDE.md` comparison window
  `[-14, -1]`.) Week 4's original text describes a 14-day window "ending on the EMA date
  inclusive" — that has since been corrected to end the day before, per the fix above;
  treat the corrected (lag = 1) version as authoritative.
- **Estimation:** REML on both engines. Primary engine: R `lme4::lmer` + `lmerTest`
  (Satterthwaite or Kenward–Roger denominator df) and `nlme::lme(correlation =
  corAR1())` for the AR(1)-corrected fit with real per-person BLUPs. Python fallback
  (statsmodels `MixedLM` with a between-within denominator-df approximation; GEE
  Autoregressive robustness check) when R/rpy2 isn't usable — never silently, `engine`
  on every result says which path ran. (`backend/statistics/mixed_effects_model.py`;
  Week 4 §1.5)
- **Convergence policy:** if the random-slope model fails to converge or yields a
  degenerate random-effects covariance, fall back to random-intercept-only and record
  the fallback reason. (Week 4 §1.5; `backend/statistics/mixed_effects_model.py`)
- **`week_in_study` (β4):** exact — weeks elapsed since the person's first occasion in
  the model frame. **`term_phase` (β5):** an **approximation** — the dataset has no
  explicit academic-calendar field, so a generic US-academic-year heuristic is used
  (winter break ~Dec 15–Jan 15, spring break ~Mar 8–16, summer break ~May 15–Aug 25),
  not the real calendar for the study years. (`backend/statistics/mixed_effects_model.py`
  module docstring)
- **Per-person statements:** driven by empirical-Bayes (BLUP) person-specific estimates
  from the single population model, not separate per-person regressions — shrinkage is
  what makes cold-start behaviour safe. (Week 4 §0, §1.6)
  - **Flagged gap:** per-person standard errors are not yet extractable from the R
    `nlme` wrapper this codebase uses, so per-person statistical *significance*
    currently fails safe to "insufficient" for everyone rather than guessing — see
    `backend/statistics/evidence.py`'s module docstring. Moe Tanaka has offered to
    review/complete this specific piece; her numbers should not be treated as final
    until she has.

## 4. Feature cleaning / exclusion criteria (GPS distance, `loc_dist_ep_0`)

Locked pipeline, in order (`backend/data_pipeline/cleaning.py`; `CLAUDE.md` "Finalised
decisions"):

1. **Quality gate:** `quality_loc >= 12` h required, else → NA. (**12h is the current,
   finalised threshold** — Week 4's original draft said 8h; this was updated 2026-09-12
   after a day-count-cost check came back at 1.63% of valid days, judged small enough to
   take the stricter option per the spec's own tie-breaking rule. Treat 12h as
   authoritative; the 8h figure in the Week 4 document text itself is superseded.)
2. **Physical-implausibility filter:** daily distance `> 500,000 m` (500 km) → NA, not
   capped. Sensitivity re-runs at 250 km and 1,000 km cutoffs.
3. **Per-person winsorisation:** clamp to the participant's own [1st, 99th] percentile,
   computed over their surviving (non-NA) values only.
4. **Transform:** `log(distance + 1000)` — see §3 above on log-of-mean ordering.
5. **Zeros:** genuine zero-travel days are kept if `quality_loc >= 12` h (not treated as
   missing).

## 5. Windows (comparison, baseline)

- **Comparison (recency) window — user-facing:** unified to **14 days** (`CLAUDE.md`;
  `RECENCY_WINDOW_DAYS` is deprecated — the earlier separate 7-day user-facing window
  was a valid Week 4 choice, since superseded by a deliberate decision to unify with the
  14-day model window, `analysis/archive/baseline.py` module docstring).
- **Baseline window:** `[-42, -15]` (28-day baseline) / `[-70, -15]` (56-day target
  baseline), relative to the assessment date (`CLAUDE.md`; `analysis/archive/baseline.py`
  `BASELINE_MIN_DAYS = 28`, `BASELINE_TARGET_DAYS = 56`). The 28-day window is the
  minimum that unlocks comparative ("relative to your baseline") statements; the 56-day
  target is required before any historical-relationship statement. (Week 4 §0, §4)
- **Baseline sufficiency gates** (must all hold, not just calendar days):
  - Descriptive: ≥7 calendar days, ≥5 valid sensor-days, ≥1 completed EMA.
  - Comparative (28-day baseline): ≥28 calendar days, ≥20 valid sensor-days, ≥3
    completed EMAs.
  - Historical (56-day baseline): ≥56 calendar days, ≥40 valid sensor-days, ≥8 completed
    EMAs spanning ≥28 days.
  (`analysis/archive/baseline.py` `GATE_DESCRIPTIVE` / `GATE_COMPARATIVE` /
  `GATE_HISTORICAL`; `backend/statistics/eligibility.py`
  `STATE_B_MIN_*` / `STATE_C_MIN_*` / `HISTORICAL_MIN_*` — confirmed identical gates
  across both modules, 2026-09-12.)

## 6. Cold-start policy (three-state)

Per-feature, per-EMA-occasion evaluation (the lowest qualifying state across a turn's
features governs that turn's framing):

- **State A — insufficient data:** below the descriptive sufficiency gate (< 7 calendar
  days, or 0 completed EMAs, or < 5 valid sensor-days) → templated message only.
- **State B — partial history:** meets the descriptive gate but not the 28-day
  comparative gate → descriptive summary + "too early to compare."
- **State C — full history:** meets the 28-day comparative gate → comparative
  statements allowed; historical-relationship statements additionally require the
  stricter 56-day gate.
(Week 4 §5; `backend/statistics/eligibility.py::classify_state`,
`is_historical_relationship_eligible`)

**Cold-start applies per evaluation opportunity; State C does not persist** across
occasions — each occasion is re-evaluated independently. (`CLAUDE.md` "Finalised
decisions"; consistent with `evaluate_person_feature` being called once per EMA
occasion, not once per participant, in `analysis/archive/baseline.py`.)

## 7. Multiple-comparison control

- **Confirmatory family** (≤3 Tier-1 features × 1 primary outcome × lag 0):
  Holm–Bonferroni, FWER = 0.05, pre-registered as the sensitivity analysis.
- **Exploratory tests and per-person multi-statement reports:** Benjamini–Hochberg FDR,
  q = 0.05. Unadjusted p-values are never surfaced.
- **Cohort-level family = 213; BH-FDR is the reported value, Holm is the sensitivity
  analysis** (`CLAUDE.md` "Finalised decisions" — this is the point on which the Week 4
  draft's "Holm as primary" framing has been superseded; treat `CLAUDE.md` as
  authoritative here).
(Week 4 §0, §2; `backend/statistics/mixed_effects_model.py::adjust_confirmatory_family`,
`adjust_exploratory_family`)

## 8. Evidence-strength classification

Applied to a candidate historical-relationship statement for one person/feature, using
the BLUP `slope_i` as the standardized effect (Week 4 §7):

| Label | q | \|effect\| | occasions | consistency |
|---|---|---|---|---|
| strong | < 0.01 | ≥ 0.20 | ≥ 12 | same sign at lag 0 AND lag 1 |
| moderate | < 0.05 | ≥ 0.10 | ≥ 8 | same sign at lag 0 |
| weak | < 0.10 | ≥ 0.10 | ≥ 8 | (none required) |
| insufficient | otherwise | | | |

(`backend/statistics/mixed_effects_model.py::classify_evidence_strength`)

**User-facing collapse:** binary (`evidence_available` / `no_claim`) — the four internal
tiers above are not shown to the user directly. (`CLAUDE.md` "Finalised decisions")

**Flagged gap:** "strong" requires a same-sign check at lag 0 *and* lag 1; the lag-1
term (β2) is out of the current implementation's scope, so this comparison is `None`
unless a caller supplies it — meaning "strong" is currently unreachable in practice, not
silently misclassified. (`backend/statistics/mixed_effects_model.py` module docstring)

## 9. Robustness / sensitivity analyses (pre-registered alongside the primary fit)

- 7-day PHQ-4 alignment window as a parallel robustness check against the primary
  14-day window; β1 must be materially unchanged between the two for the finding to be
  reported. (Week 4 §1.3)
- GPS hard-cutoff sensitivity at 250 km / 500 km / 1000 km against the locked 500 km
  reference. (Week 4 §1.4; `backend/data_pipeline/cleaning.py`)
- AR(1) residual structure as a check on the consequence of overlapping 14-day trailing
  windows (median ~5-day EMA gap). Primary: R `nlme::lme` + `corAR1` (real joint fit,
  real BLUPs). Fallback: population-averaged GEE Autoregressive check (Rosner & Munoz
  1988) — a genuinely different, less complete estimand, not a substitute for the
  primary fit. (Week 4 §1.2/§1.7; `backend/statistics/mixed_effects_model.py`)

## 10. Open items — pending Moe's input

- **§1 (Hypotheses):** explicit directional hypothesis statement, or confirmation this
  predictor is analyzed non-directionally.
- **Per-person standard errors** for BLUP-based per-person significance (flagged gap,
  `backend/statistics/evidence.py`) — Moe has offered to complete this port herself.
- **Whether this document is meant to stand alone**, or whether the Group Proposal
  (`docs/proposal/`) and/or `Week5_Statistical_Analysis_Deliverable.md` are intended to
  serve as its replacement/supplement — flagged as an open question in `CLAUDE.md`'s
  "Unreflected changes" section; still needs a decision from the Statistical Analysis
  Lead.
- **`term_phase` (β5):** whether the generic US-academic-year heuristic should be
  replaced with the actual Dartmouth academic calendar for the study years, or is
  accepted as a documented approximation.
