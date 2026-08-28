# MindSense — Week 4 Deliverable: Statistical Analysis Lead

**Owner:** Moe Tanaka (Statistical Analysis Lead)
**Week 4 scope (per Weekly Build Plan v5):** Name the actual statistical model, the
multiple-comparison control approach, and the comparison window. Define the minimum
baseline window as a specific number of days. Draft the three-state cold-start policy.
**Status:** Decisions locked for the Week 5 Wednesday Tier-1 meeting. Numbers below are
fixed commitments, not placeholders.
**Dataset referenced:** *College Experience Dataset* (Nepal et al. 2024), the copy in
`DATA5702/` — `Sensing/sensing.csv` (daily), `Sensing/steps.csv` (daily),
`EMA/general_ema.csv` (repeated self-report), `Demographics/demographics.csv`.

**Revision note (v2).** Updated after the GPS vertical-slice real-data audit
(`loc_dist_ep_0`). Changes from v1: (i) the predictor→outcome alignment window is now
**14 days for the PHQ-4 outcomes** (was a single 7-day figure), matching the PHQ-4
"last 2 weeks" recall period; the 7-day window is retained only for user-facing
deviation statements and as a pre-registered sensitivity analysis. (ii) Added an
explicit **feature-cleaning / GPS sanity-bound rule** (§1.4). (iii) Added an
**occasion-validity gate** on the alignment window. Section numbering shifted; §1 gained
subsections 1.3–1.4.

---

## 0. One-page summary (the locked decisions)

| Item | Decision |
|---|---|
| **Statistical model** | Linear **mixed-effects model** (LMM), Gaussian, with **person-level random intercepts** + random slope on the primary within-person predictor. Time-varying predictors are **person-mean-centred** (within-person centring) with the person mean re-entered as a between-person term (within–between / Mundlak specification). |
| **Primary outcome** | **PHQ-4 total score (0–12)** from `general_ema.csv`, measured repeatedly per person (~weekly). Secondary: PHQ-4 anxiety (items 1–2) and depression (items 3–4) subscales; PAM (1–16); single-item `stress`; state self-esteem (`sse3`). |
| **Predictor → outcome alignment window** | **14 days** ending on the EMA date (inclusive) for **PHQ-4 total / anxiety / depression** — matches the instrument's "over the last 2 weeks" recall period. **Same day (1 day)** for the momentary outcomes (PAM, `stress`, `sse3`). Alignment window requires **≥ 7 valid sensor-days** (14-day windows) or a valid EMA-day (momentary). A **7-day** version of the PHQ-4 alignment is run as a **pre-registered sensitivity analysis**. |
| **Feature cleaning (GPS / `loc_dist`)** | Per participant-day: drop to `NA` if `quality_loc < 8` h; drop to `NA` (not cap) if daily distance `> 500,000 m`; then **per-person winsorise** to the participant's [1st, 99th] percentile; model on **`log(distance + 1000)`**. Genuine zero-travel days (with `quality_loc ≥ 8` h) are kept. Sensitivity: re-run cap at 250 km and 1,000 km. |
| **Per-person statements** | Driven by **empirical-Bayes (BLUP) person-specific estimates** from the single population model — not separate per-person regressions. Shrinkage is what makes cold-start behaviour safe. |
| **Multiple-comparison control** | **Confirmatory family** (≤ 3 Tier-1 features × 1 primary outcome × lag 0): **Holm–Bonferroni**, FWER = 0.05, pre-registered. **Exploratory tests and per-person multi-statement reports:** **Benjamini–Hochberg FDR, q = 0.05**. Unadjusted p-values are never surfaced. |
| **Comparison (recency) window — user-facing** | **7 days**, aligned to the weekly EMA cadence; recomputed weekly; excluded from the baseline window to avoid overlap. This governs the *wording shown to the user* ("your recent week"), not the model fit. |
| **Minimum baseline window** | **28 days** of the participant's own history — the threshold that unlocks comparative ("relative to your baseline") statements. **Target baseline = 56 days** (used whenever available; **required** before any historical-relationship statement). |
| **Baseline sufficiency gates** | Within the baseline window: **≥ 20 valid sensor-days** for the feature in question **and ≥ 3 completed EMAs**. Historical-relationship claims additionally require **≥ 8 EMA occasions** spanning **≥ 28 days**. |
| **No-data threshold** | **< 7 days of history OR 0 completed EMAs** → templated message only. |
| **Window-vs-data rule** | The Kaggle data comfortably supports 28 and 56 days (see §8). If a *participant* or a *future dataset* cannot reach a window, the system **narrows the claim** (drops to a lower cold-start state); the window definition does **not** shrink to fit. |

---

## 1. Deliverable 1 — The named statistical model

### 1.1 Model family and why

We use a **linear mixed-effects model (LMM)** — equivalently a two-level hierarchical /
multilevel model — with **repeated EMA occasions (level 1) nested within persons
(level 2)**.

Rationale:

- The design is longitudinal and unbalanced: median ≈ 170 EMA occasions per person,
  range 1–441, spanning up to ~3.9 years (see §8). LMMs handle unbalanced panels and
  missing occasions under MAR without listwise deletion.
- **Person-level random intercepts** absorb stable between-person differences (trait
  negative affect, baseline mobility, device type, personality), so the fixed effect of
  interest is estimated *within person*.
- A **random slope** on the primary within-person predictor lets the behaviour–wellbeing
  association differ by person; the person-specific slope is exactly what the chatbot
  needs for "for you, lower mobility has tended to coincide with…" statements.
- It is the model the Project Spec's structured-evidence example implies ("*for this
  individual*") and the model named as the default in the Build Plan.

### 1.2 Formal specification

For person *i* at EMA occasion *t* (occasion date = EMA completion date):

**Model:**

```
PHQ4_it = β0
        + β1 · x_within_it                (within-person effect  ← primary estimand)
        + β2 · x_within_i(t−1)            (1-occasion lag, sensitivity / secondary)
        + β3 · x_between_i                (between-person effect, controls confounding)
        + β4 · week_in_study_it           (linear time / practice trend)
        + β5 · term_phase_it              (in-term vs break indicator; COVID-era flag)
        + u0_i + u1_i · x_within_it        (random intercept + random slope, person i)
        + e_it

  u_i = (u0_i, u1_i) ~ MVN(0, Σ)          Σ = 2×2 covariance (intercept/slope)
  e_it ~ N(0, σ²)                          AR(1) on e within person (see §1.3, overlap)
```

- **β1** is the reportable, causally-conservative quantity: how person-level wellbeing
  moves when this person's behaviour deviates from *their own* baseline.
- **β3** is kept in the model *specifically* so β1 is not contaminated by
  between-person differences (Mundlak / within–between formulation; Hoffman & Stawski
  2009; Curran & Bauer 2011). Reporting β1 without β3 is a known misspecification.
- The lag term (β2) supports "changes over time" framing and is a sensitivity check on
  direction; it is **not** promoted to a causal claim.

**Centring terms:**

- **Within-person (person-mean-centred):** `x_within_it = x_it − x̄_i`
- **Between-person:** `x_between_i = x̄_i − x̄..` (grand-mean-centred)
- `x̄_i` = person *i*'s mean of the cleaned feature across **all their valid occasion
  values** (full-history person mean) for the model fit. *At chatbot runtime* the
  personal baseline is operationalised as a trailing 56/28-day window (§4) so it adapts
  as data accrues — same concept ("this person's typical level"), different
  operationalisation (one-time full-history mean for the research fit; trailing window
  for progressive user-facing statements).

### 1.3 Predictor construction — trailing alignment window per outcome

`x_it` is built by aggregating the **cleaned** daily feature (see §1.4) over a trailing
window that ends on the EMA date and whose length **matches the recall period of the
outcome instrument**:

| Outcome | Instrument reference period | Trailing alignment window (ends on EMA date, inclusive) | Occasion-validity gate |
|---|---|---|---|
| **PHQ-4 total (0–12) — primary** | "over the last 2 weeks" | **14 days** | ≥ 7 valid sensor-days in the window (post-cleaning) |
| PHQ-4 anxiety (items 1–2) | last 2 weeks | 14 days | ≥ 7 valid sensor-days |
| PHQ-4 depression (items 3–4) | last 2 weeks | 14 days | ≥ 7 valid sensor-days |
| PAM (1–16) | "today" | same day (1 day); 3-day trailing as sensitivity | EMA day is a valid sensor-day |
| `stress` (single item) | "right now" | same day | EMA day is a valid sensor-day |
| `sse3` state self-esteem | "right now" | same day | EMA day is a valid sensor-day |

Rules:

- **Aggregation** is the mean of valid daily values in the window (robust `median` kept
  as a sensitivity variant for skewed features).
- **Occasion drop:** if the validity gate is not met, that EMA occasion is excluded from
  the model for that feature (it is *not* imputed).
- **7-day PHQ-4 sensitivity:** a parallel PHQ-4 alignment at 7 days is **pre-registered**
  as a robustness check; the primary result stands on 14 days, and β1 must be
  materially unchanged between the two for the finding to be reported.
- **Lag term (β2):** `x_within_i(t−1)` uses the same construction over the 14-day window
  ending at the **previous** EMA date.
- **Window overlap:** EMA occasions here are ~5 days apart (median; §8), so consecutive
  14-day windows overlap heavily and the derived predictor is autocorrelated across
  occasions. This is handled by the **AR(1) residual structure** in §1.2 and noted as a
  limitation. The alternative — one PHQ-4 per non-overlapping 14-day block — discards
  roughly half the EMA data and is **not** adopted.
- The **user-facing 7-day "recent week" window (§3)** is a communication choice for the
  deviation statement shown in the chatbot and is deliberately distinct from this
  14-day model alignment window. If the team finds the two-number split confusing, the
  fallback is to align both to 14 (open item, §9).

### 1.4 Feature cleaning and sanity bounds

A common cleaning pipeline is applied to every Tier-1 feature, with feature-specific
thresholds. The **GPS / location-distance rule is locked from the Week 4 vertical-slice
audit** and is the first concrete instance.

**General pipeline (per participant-day, in this order):**

1. **Quality gate → `NA`.** Drop the day's value for a feature if its source stream
   quality is below threshold. For location features: `quality_loc < 8` h → `NA`.
   *(Pending: Data Pipeline Lead to report the day-count cost of an 8 h vs 12 h
   threshold; we take the stricter option if the cost is small.)*
2. **Physical-implausibility filter → `NA` (not capped).** Values that cannot reflect
   real routine behaviour are set missing, because they are sensor error and, even when
   they reflect a genuine rare event (e.g. a cross-country flight), they are not
   informative about routine mobility baseline.
3. **Per-person winsorisation → clamp.** On the values surviving steps 1–2, clamp to the
   participant's [1st, 99th] percentile (or `median ± 5 · MAD`, whichever is more
   stable in the run). This tames the legitimate heavy right tail without deleting it.
4. **Transform for modelling.** Apply the feature's variance-stabilising transform;
   report effects on that scale and back-transform for user-facing statements.

**`loc_dist_ep_0` (daily distance travelled, metres) — locked thresholds:**

| Step | Rule |
|---|---|
| Quality gate | `quality_loc ≥ 8` h required, else `NA` |
| Implausibility filter | daily distance `> 500,000 m` (500 km) → `NA` |
| Winsorisation | per-person [1st, 99th] percentile |
| Transform | `log(loc_dist_ep_0 + 1000)` (log1p with a 1 km offset); `sqrt` as an alternative |
| Zeros | `loc_dist_ep_0 == 0` with `quality_loc ≥ 8` h is a genuine stay-home day — **kept** |

**Sensitivity analyses (pre-registered):** re-run the implausibility filter at 250 km
and 1,000 km and confirm the primary within-person slope (β1) does not move materially.

**Diagnostics required from the Data Pipeline Lead before the rule is finalised:**

1. Are the implausible values **concentrated in a few participant-devices** (→ exclude
   that participant × feature: broken sensor) or **spread across the cohort** (→ the
   day-level filter above is sufficient)?
2. Do the worst offenders correspond to **trajectories touching lat/lon ≈ (0, 0)**
   ("null island")? If so it is a pipeline artefact to fix upstream, not merely filter.

Audit numbers that motivated the rule are in §8.

### 1.5 Estimation and software

- **Estimator:** REML.
- **Denominator df / inference:** Satterthwaite (primary) with Kenward–Roger as a
  robustness check; profile-likelihood or parametric-bootstrap CIs for the variance
  components.
- **Software:** R `lme4::lmer` + `lmerTest` (primary); cross-checked in Python with
  `statsmodels.regression.mixed_linear_model.MixedLM`. Both are local, open-source,
  no network calls — consistent with the privacy constraint.
- **Convergence policy:** if a random-slope model fails to converge or yields a
  degenerate Σ, fall back to random-intercept-only for that feature and record the
  fallback in the evidence manifest.

### 1.6 Per-person estimates for the chatbot (this is the important part)

The chatbot must not fit a fresh regression per user — with a handful of EMA points that
is unstable and would produce confident nonsense at cold start. Instead:

- Fit **one population LMM per Tier-1 feature** on all participants.
- Extract **empirical-Bayes (BLUP) person-specific coefficients**:
  `slope_i = β1 + û1_i`, with its posterior SE.
- These are **shrunk toward the population mean** in proportion to how little data
  person *i* has. A user with 6 EMAs gets an estimate close to the population effect
  with a wide interval; a user with 150 EMAs gets a largely person-driven estimate.
- The chatbot only makes a historical-relationship statement when `slope_i` clears the
  evidence-strength gate in §7 (adjusted significance + effect size + minimum
  occasions). Otherwise it stays descriptive.

### 1.7 Assumptions, diagnostics, robustness

| Assumption | Check | If violated |
|---|---|---|
| Level-1 residual normality / homoscedasticity | Residual vs fitted, QQ, scale-location per person | Per-person winsorisation (§1.4); log/√ transform skewed features; report robust (sandwich) SEs |
| Random effects ~ MVN | QQ of BLUPs | Report; large N per person makes β1 robust to this |
| Outcome scale (PHQ-4 is 0–12, mildly bounded/count-like) | Compare Gaussian LMM vs mixed-effects Poisson / cumulative-link mixed model | If material divergence, switch primary to CLMM; keep Gaussian as the communicable effect size |
| Residual autocorrelation (worsened by 14-day window overlap, §1.3) | ACF of within-person residuals | AR(1) error structure (already specified) |
| Missingness mechanism | Compare completers vs sparse responders on demographics + baseline sensing | Document as MAR-plausible; note as a limitation; no imputation of the outcome |
| Device heterogeneity (iOS vs Android feature availability) | `is_ios` as covariate; fit within-platform sensitivity | Restrict a feature to the platform where it is well-measured |

---

## 2. Deliverable 2 — Multiple-comparison control approach

**Principle:** shrink the problem before correcting it. Pre-registration + a hard cap of
3 Tier-1 features + a single primary outcome + a single primary lag keeps the
confirmatory family at **≤ 3 tests**.

| Test family | What is in it | Correction | Level |
|---|---|---|---|
| **Confirmatory** | {Tier-1 feature} × {PHQ-4 total} × {lag 0}, on the **14-day** alignment window. ≤ 3 tests. Pre-registered before looking at fitted results. | **Holm–Bonferroni** (controls FWER — each is a headline claim) | 0.05 |
| **Secondary / exploratory** | Other outcomes (subscales, PAM, stress, self-esteem), lag 1, episode-of-day features, the 7-day-window variant, interaction terms | **Benjamini–Hochberg FDR** | q = 0.05 |
| **Per-person weekly report** | The ≤ ~6 statements a single user's report could contain (up to 3 features × {current-deviation, historical-relationship}) | **Benjamini–Hochberg FDR** across that report | q = 0.05 |

Additional rules:

- **Effect-size gate on top of significance.** A statement is only surfaced if it also
  clears a minimum standardised effect (§7). "Significant but trivial" is not reported.
- **No unadjusted p-values** ever reach the SLM or the UI. The evidence contract carries
  adjusted p / q-values and the evidence-strength label only.
- **We are not running 220 per-person tests.** One population model per feature; person
  differences come from BLUPs, not from 220 separate hypothesis tests, so the
  correction burden stays small.
- **Pre-registration artefact:** the confirmatory feature list, outcome, alignment
  window (14 days), lag, direction hypotheses, cleaning thresholds (§1.4), and
  evidence-strength thresholds (§7) are committed to `analysis/preregistration.md` at
  the Week 5 Tier-1 sign-off and not changed afterward.

---

## 3. Deliverable 3 — The comparison (recency) window (user-facing)

This window governs the **wording shown to the user**, not the model fit (the model uses
the 14-day alignment window in §1.3).

- **Current / recency window = 7 days.** "Your recent [feature]" = the mean of the
  cleaned daily feature over the last 7 calendar days ending at the report date,
  requiring **≥ 4 valid days**; otherwise the feature is reported as "not enough recent
  data".
- **Cadence:** recomputed **weekly**, aligned to the EMA schedule (median gap between
  EMA completions ≈ 5 days; p75 ≈ 8 days — §8).
- **Non-overlap:** the current 7-day window is **excluded** from the baseline window, so
  "recent vs baseline" compares disjoint periods.
- **Deviation metrics:**
  - Standardised: `z = (current_7d_mean − baseline_mean) / baseline_SD`
  - Percentage (only when `baseline_mean` is meaningfully non-zero):
    `pct = 100 · (current_7d_mean − baseline_mean) / baseline_mean`
  - For log-transformed features (§1.4), compute the deviation on the log scale and
    present the back-transformed percentage.
- **"Meaningful change" threshold:** report a change only when `|z| ≥ 1.0`. Below that:
  "in line with your usual range".

---

## 4. Deliverable 4 — Minimum baseline window (specific number of days)

### 4.1 The number

> **Minimum baseline window = 28 days** of the participant's own history — the threshold
> that unlocks **comparative** statements ("X% below your personal baseline").
>
> **Target baseline window = 56 days.** Used whenever the participant has it; produces a
> stabler personal mean/SD and is **required** before any *historical-relationship*
> statement ("lower mobility has tended to coincide with…").

28 days = the standard 4-week rolling baseline used across digital-phenotyping /
deviation work; long enough to average out weekday/weekend structure and a single
atypical week, short enough that a new user reaches it in a month.

### 4.2 Baseline computation

- `baseline_mean`, `baseline_SD` (and robust `median`, `MAD`) of the **cleaned** daily
  feature over the trailing baseline window ending at (report date − 7 days).
- Cleaning per §1.4 (quality gate, implausibility filter, per-person winsorisation).
- Baseline window slides forward with time (always "trailing N days"), so the personal
  baseline adapts as the person accrues history.

### 4.3 Sufficiency gates (all must hold, not just calendar days)

| To unlock… | Calendar history | Valid sensor-days for that feature *in the baseline window* | Completed EMAs *in the baseline window* |
|---|---|---|---|
| Descriptive summaries (State B) | ≥ 7 days | ≥ 5 | ≥ 1 |
| **Comparative statements (State C)** | **≥ 28 days** | **≥ 20** | **≥ 3** |
| Historical-relationship statements | ≥ 56 days | ≥ 40 | ≥ 8, spanning ≥ 28 days |

If calendar days are met but a data gate is not, the participant stays in the lower
state for that feature (per-feature, not global).

---

## 5. Deliverable 5 — Three-state cold-start policy

State is evaluated **per feature, per report**, using §4.3. The lowest qualifying state
across the features in a given user turn governs the framing of that turn.

### State A — No / insufficient data → **templated message only**

**Trigger:** < 7 days of history since enrolment, **OR** 0 completed EMAs, **OR** fewer
than 5 valid sensor-days for every Tier-1 feature.

**Allowed:** a fixed template explaining that the assistant is still collecting data.
No numbers. No feature values. No "your baseline". No comparisons. No trends.

**Drafted copy (hand to SLM Integration Lead as a locked template):**

> "I don't have enough of your data yet to say anything specific about your patterns.
> I need about **4 weeks** of app use before I can compare your recent behaviour to your
> own typical range, and a bit longer before I can talk about how your behaviour and
> wellbeing relate for you. For now, everything is still being collected in the
> background on your device. You can check back in a week or two."

Follow-up question in State A → same template, optionally plus one neutral definitional
answer (e.g. "PHQ-4 measures…") with **no personalised content**.

### State B — Partial history → **descriptive summary + "too early to compare"**

**Trigger:** ≥ 7 days of history and ≥ 1 EMA, but the feature has **not** met the 28-day
comparative gate (§4.3).

**Allowed:**
- Current 7-day values in plain language ("Over the last week your phone was unlocked
  about 60 times a day on average").
- Simple within-window direction *if* ≥ 10 valid days exist ("that's been fairly steady
  over the last two weeks") — described, not quantified against a baseline.
- Definitional / educational content.

**Prohibited:**
- Any "% above/below your baseline" or "your personal baseline is…" statement.
- Any z-score or deviation framing.
- Any historical behaviour–wellbeing relationship ("your mood tends to…").
- Any evidence-strength label above "insufficient".

**Required language (must appear whenever a value is given in State B):**

> "It's still **too early to compare this to your own baseline** — I need about
> **4 weeks** of your data before those comparisons are reliable. Right now I can only
> describe what your recent week looks like on its own."

### State C — Full history → **comparative statements allowed**

**Trigger:** the feature meets the 28-day comparative gate (§4.3). Historical-relationship
statements additionally require the 56-day gate **and** the evidence-strength gate (§7).

**Allowed:**
- Comparative deviation statements when `|z| ≥ 1.0`:
  "Your mobility over the last week is about **28% below** your personal baseline
  (roughly 1.3 standard deviations below your usual range)."
- Historical within-person relationships (56-day + evidence gate met):
  "For you, weeks with lower mobility have tended to coincide with lower PHQ-4 wellbeing
  scores. This is an **association**, not a cause, and the evidence is **moderate**."
- Structured-evidence block exactly as in the Project Spec (Current behaviour / Current
  wellbeing / Historical relationship / Evidence strength / Interpretation).

**Still prohibited in State C (standing constraints, not cold-start):**
- Causal language ("because", "caused", "led to", "will make you").
- Diagnostic or clinical inference ("you are depressed", "this is a symptom of…").
- Predictions about the future.
- Any claim on a feature that is only in State B this turn — mixed-state turns take the
  lower framing for the weaker feature.

### State transitions

- Re-evaluated every weekly report. A user moves A → B → C as history accrues.
- A user can drop back (B ← C) if a long data outage pushes valid sensor-days in the
  trailing window below the gate — intended; the UI shows "not enough recent data"
  rather than a stale baseline.

---

## 6. Handoffs

| Consumer | What they get from this document |
|---|---|
| **Integration & QA (evidence contract)** | State enum {A, B, C} per feature; `baseline_history_days`; `valid_sensor_days_in_window`; `ema_count_in_window`; `alignment_window_days` (14 for PHQ-4, 1 for momentary); `permitted_claims` / `prohibited_claims` derived from state; adjusted p / q and evidence-strength label fields. |
| **SLM Integration Lead** | The three locked templates in §5 (State A message, State B "too early" clause, State C structured block). These are the *content*; the generic-refusal and crisis-aware templates remain SLM-lead-owned. |
| **Conversational Interface Lead** | Required UI states map 1:1: cold-start (A), insufficient-data / "too early to compare" (B), normal + uncertainty (C). |
| **Data Pipeline Lead** | Implement the §1.4 cleaning pipeline; expose `valid_sensor_days` per feature per trailing window (7-day, 14-day, 28-day, 56-day); return the two GPS diagnostics in §1.4; report the 8 h vs 12 h `quality_loc` day-count cost. |
| **Evaluation Design Lead** | Evidence-strength thresholds (§7) feed the adversarial cases for "asserts baseline when none available" and "overstates evidence". |

---

## 7. Evidence-strength classification (bridge into Week 5)

Owned by this role; drafted here so the thresholds are pre-registered before results are
seen. Applied to each candidate historical-relationship statement, per person, per
feature, using the BLUP `slope_i` from §1.6.

| Label | Adjusted significance | Standardised effect `|slope_i|` (SD of outcome per SD of predictor) | Min EMA occasions | Consistency |
|---|---|---|---|---|
| **Strong** | q < 0.01 | ≥ 0.20 | ≥ 12 | same sign at lag 0 and lag 1 |
| **Moderate** | q < 0.05 | ≥ 0.10 | ≥ 8 | same sign at lag 0 |
| **Weak** | q < 0.10 | ≥ 0.10 | ≥ 8 | — (reported only as "weak / preliminary") |
| **Insufficient** | otherwise | — | — | → no relationship statement; State B/descriptive framing only |

"Weak" statements are permitted but must carry the explicit hedge and never appear in the
structured-evidence "Historical relationship" slot as anything above "weak".

---

## 8. Does the data support the windows? (Build Plan clause: narrow the claim, don't shrink the window)

Empirical check on the `DATA5702/` copy of the dataset (streamed, all participants).

**EMA outcome (`general_ema.csv`) — PHQ-4 / PAM / stress / self-esteem, identical cadence:**

| Quantity | Value |
|---|---|
| Participants with ≥ 1 EMA | 218 / 220 |
| Completed EMA occasions per person | min 1, p25 ≈ 97, **median ≈ 170**, p75 ≈ 205, max 441 |
| Per-person observation span | median ≈ 1259 days, p25 ≈ 889, max ≈ 1429 |
| Gap between consecutive EMAs | **median 5 days**, p75 8, p90 11 |

**Sensing (`sensing.csv`), daily:**

| Quantity | Value |
|---|---|
| Participants | 220 |
| Sensing-days per person | p10 ≈ 320, p25 ≈ 751, **median ≈ 1144**, p75 ≈ 1283 |
| Per-person span | median ≈ 1310 days |
| Coverage (sensing-days ÷ span) | **median 0.95**, p25 0.87, p10 0.72 |

**GPS vertical-slice audit (`loc_dist_ep_0`, pre-cleaning):**

| Quantity | Value |
|---|---|
| Non-null daily observations | 172,565 across 218 participants |
| Median daily distance | 5.85 km |
| 95th percentile | 255.66 km |
| 99th percentile | 2,051.55 km |
| Max | 1.21 × 10⁹ m (≈ 1.2 million km — physically impossible; sensor/pipeline error) |

This heavy implausible tail is why §1.4 filters `> 500 km/day` to `NA` (not a cap) and
then winsorises per person. ~2–3% of daily observations sit above the 500 km filter;
losing them is an accepted trade-off (they are error and/or non-routine travel days).

**Conclusions:**

- The dataset comfortably supports the **14-day alignment window** (once past study
  day 14, every occasion has a preceding 14 days; median sensing coverage 0.95 means a
  typical 14-day window has ~13 valid days, well past the ≥ 7 gate), the **28-day
  minimum** and the **56-day target** baseline. A typical participant reaches 56 days
  with ~10 EMAs and ~53 sensor-days — past every sufficiency gate in §4.3. The windows
  are **not** data-constrained here.
- **Narrow-don't-shrink still applies at two points:** (1) a new or sparse *participant*
  sits in State A/B until they accrue the window — the threshold is not lowered for
  them; (2) if the **fallback dataset** cannot support 56 days, historical-relationship
  statements are disabled system-wide and only current-vs-28-day-baseline comparisons
  remain — rather than redefining "full baseline" as a smaller number.

---

## 9. Open items for the Week 5 Wednesday Tier-1 meeting

1. **Final Tier-1 feature list (max 3)** — jointly with Data Pipeline Lead, against the
   locked schema. Current front-runners: (a) `loc_home_dur` (time at home, hrs/day),
   (b) `loc_dist_ep_0` (daily distance travelled, m — cleaning rule locked in §1.4) or a
   location-entropy feature, (c) `unlock_num_ep_0` (unlock frequency) or
   `sleep_duration`. Selection criteria: All-platform availability, ≥ 80% daily
   coverage, interpretable, prior literature support with PHQ-4.
2. **Confirm PHQ-4 total as sole primary outcome** vs splitting anxiety/depression
   subscales as co-primary (affects the confirmatory family size and Holm correction).
3. **Data Pipeline Lead to return, before implementation:** the two GPS diagnostics in
   §1.4 (device-concentration; null-island trajectories) and the `quality_loc` 8 h vs
   12 h day-count cost.
4. **Decide** whether to keep the user-facing recency window at 7 days or align it to
   the 14-day model window (§1.3) for consistency.
5. **COVID-era handling** — `covid_ema.csv` starts 2020-03; decide whether to add a
   pandemic-phase fixed effect or restrict the modelling window.
6. **Register** `analysis/preregistration.md` with the frozen feature list, 14-day
   alignment window (+ 7-day sensitivity), cleaning thresholds, lag, direction
   hypotheses, and evidence-strength thresholds.

---

*Prepared for MindSense / COMP5703. Cite: Nepal, S., Liu, W., Pillai, A., et al. (2024).
Capturing the College Experience. Proc. ACM IMWUT 8(1), Article 38. doi:10.1145/3643501.*
