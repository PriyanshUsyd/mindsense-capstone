# MindSense — Statistical Analysis Pre-registration

**Status: DRAFT**, drafted pre-sign-off per the Week 4 deliverable (open item 6)
for the team to review alongside the Tier-1 feature proposal.

**Brought into this repository 2026-09-13.** This document previously existed
only as an uncommitted local file — it was not on `main`, not on any branch,
and not findable anywhere in this repository's history (see `CLAUDE.md`'s
"Unreflected changes" log, which records that gap). Per section 10 below, any
further change after this point needs its own dated addendum, not a silent
edit — the two corrections below are exactly that.

**[MIGRATION NOTE, 2026-09-13]** Two corrections applied at check-in time,
neither a retroactive rewrite of what was actually decided back in Week 5:

1. **Tier-1 feature list corrected to the two features actually signed off.**
   Section 1's feature-list bullet originally read "max 3 ... proposed —
   `loc_dist_ep_0`, plus 1-2 of: `loc_home_dur`, `unlock_num_ep_0` /
   `sleep_duration`" — this is what this draft said *before* the Wednesday
   sign-off meeting it was written for, and the draft was never updated
   afterward even though it sat on a local machine for over two weeks past
   that meeting. The actual outcome: all 8 team members agreed on
   **2026-08-26** to **`loc_dist_ep_0` + `unlock_num_ep_0`** (2 features, not
   3) — see `feature-list-signoff.md` (Integration/QA sign-off) and
   `freeze-decision.md` (the underlying team agreement, recorded
   2026-09-05). The hard cap was **2** cross-platform features per
   `Weekly_Plan.md` Week 4 ("maximum 2 ... unless a third genuinely meets the
   same standard"), not 3 — this draft's own "max 3" was already not what the
   team had actually committed to even at the time it was written. The
   pre-sign-off proposal text is left in place below, relabelled as such,
   since the real decision superseded it rather than amended it, and section
   7 (`loc_home_dur` construct-overlap check) is kept as-is for the same
   reason — see `Week5_Statistical_Analysis_Deliverable.md` §7 for the fuller
   correction note on that analysis.
2. **Path references to the retired `analysis/` pipeline updated** to where
   that logic actually lives now. `analysis/cleaning.py`, `analysis/baseline.py`
   and `analysis/evidence_model.py` are archived at `analysis/archive/` (not
   deleted); their logic is reconciled into `backend/statistics/` and
   `backend/data_pipeline/` — see `analysis/archive/README.md`'s
   module-by-module mapping table, which this file's updated references
   follow. The `predictors.py` module this draft originally cited was itself
   **never committed to any repository** (confirmed in that same README) —
   its 14-day trailing-window logic is `backend/statistics/mixed_effects_model.py`
   now. `analysis/output/` (run artifacts, one level up from `archive/`) was
   **not** archived and its paths below are unchanged and still resolve.

**This document is a specification, not a results report.** It carries no fitted
values (beta1, occasion counts, label breakdowns); those live in
`analysis/output/latest/week5_run_report.md`. Two data-dependent numbers appear
below out of necessity — the cohort family size (section 2.2) and the effect-size
band cited as the rationale for the user-facing collapse (section 5) — and are
flagged where they occur.

Decisions made **after** the Week 4 lock are marked `[POST-HOC]` inline and
collected in section 7. Everything else restates a Week 4 locked decision.

## 1. Confirmatory family (locked, per Week 4 doc)

- **Tier-1 feature list: confirmed, 2 features** — `loc_dist_ep_0` (implemented,
  see section 1.5) + `unlock_num_ep_0` (implemented, see section 1.6). *(This
  bullet originally read "max 3 ... proposed — `loc_dist_ep_0`, plus 1-2 of:
  `loc_home_dur`, `unlock_num_ep_0` / `sleep_duration`," reflecting this
  draft's pre-sign-off state; see the 2026-09-13 migration note above for why
  that text is now corrected rather than kept as the record of what was
  proposed.)*
- **Primary outcome:** PHQ-4 total (0-12), `general_ema.csv`.
- **Direction hypothesis for `loc_dist_ep_0`:** beta1 < 0 is not pre-specified by
  literature consensus in either direction strongly enough to commit to a
  one-sided test; two-sided test used (matches the Week 4 doc, which does not
  commit to a direction).

### 1.1 Comparison (alignment) window

- **Comparison window = `[-14, -1]`** — the 14 calendar days ending the day
  **before** the evaluation (EMA) date. The evaluation day itself is **excluded**.
- **Rationale:** `loc_dist_ep_0` is a whole-day 00:00-23:59 aggregate. Including
  the evaluation day would put behaviour recorded *after* the PHQ-4 response into
  the predictor for that response — a reversal of temporal order.
- **Occasion-validity gate:** the occasion is **dropped, not imputed**, if fewer
  than 7 valid sensor-days fall in `[-14, -1]`.
- The window is adjacent to, and does not overlap, the baseline window (section
  3), which ends at `-15`.
- Implemented as `backend.statistics.mixed_effects_model.ALIGNMENT_WINDOW_DAYS
  = 14`, `TRAILING_WINDOW_LAG_DAYS = 1`, `OCCASION_MIN_VALID_SENSOR_DAYS = 7`
  *(updated 2026-09-13 migration note: originally cited as
  `predictors.ALIGN_WINDOW_DAYS` / `ALIGN_WINDOW_LAG_DAYS` /
  `OCCASION_MIN_VALID_DAYS` — that module was never committed to any
  repository; these are the equivalent constants in the module this logic was
  actually reconciled into, same values, same semantics)*.

### 1.2 Predictor transform order (Week 4 decision — the order is part of the spec)

    daily cleaning
      -> arithmetic mean of the CLEAN (non-log) daily values within the 14-day window
      -> log(mean + 1000)

**The log is applied once, after averaging.** `mean(log(x))` is a different
quantity from `log(mean(x))` (Jensen's inequality) and must **not** be used. Any
per-day log column (e.g. `loc_dist_ep_0_log` in `backend/data_pipeline/cleaning.py`
*(updated 2026-09-13 — same column name, reconciled module)*) exists for
diagnostics only and must never be averaged over the window.

This was decided in Week 4, but the implementation did not follow it until Week 5;
the wording here is deliberately strong so the requirement cannot be read as a
preference. The (now-archived) `analysis/` pipeline recorded which order produced
each run in that run's `run_manifest.json` (`predictors.transform_order`,
expected value `log_of_mean`) — `backend/statistics/mixed_effects_model.py`'s
2026-09-12 fix applies the same locked order but does not currently write an
equivalent per-run manifest file; the order itself is enforced in code
(`build_trailing_predictor`), not just documented.

### 1.3 Lag

Lag 0 is primary. Lag 1 (the same 14-day construction ending at the person's
previous EMA date) is a pre-registered secondary/sensitivity term, not part of
the confirmatory claim.

**Implementation consequence, documented here for the first time:** the lag-1
term sits in the same model formula, so occasions whose lag-1 predictor is
missing (a person's first occasion, or a prior-EMA window that fails the
>=7-valid-day gate) are dropped listwise from the fit — the secondary term
therefore reduces the N of the primary estimate. Flagged for the Wednesday
meeting: either accept this explicitly, or fit lag 0 and lag 1 in separate
models.

### 1.4 Model

Linear mixed-effects, Gaussian, person-level random intercept + random slope on
the within-person predictor; person-mean-centred predictor with the person mean
re-entered as a between-person term (Mundlak).

Fixed-effects specification as implemented `[POST-HOC, 2026-09-27 —
corrected from the four-term formula this section stated until now]`:

    phq4_score ~ x_within_it + x_between_i
    + person-level random intercept and random slope on x_within
    + AR(1) residual structure (see section 1.4.1)

**Correction record.** Until this entry, this section read:

    phq4_score ~ x_within_it + x_within_lag1_it + x_between_i + week_in_study_it

"frozen exactly as fitted." That four-term formula is the retired `analysis/`
pipeline's model (27,530 occasions, 213 participants —
`Week5_Statistical_Analysis_Deliverable.md` sections 2.5, 3.2), not what
`backend/statistics/` fits or what produced the numbers this document and the
Week 5 deliverable report as primary:

- **The lag-1 term (`x_within_lag1_it`) was never ported.**
  `backend/statistics/mixed_effects_model.py`'s module docstring lists β2
  (the 1-occasion lag) under "NOT IMPLEMENTED ... out of scope for this
  task" — a scope limitation on the port, not a statistical decision to
  drop the term. It is also why `classify_evidence_strength`'s `strong`
  tier is structurally unreachable without a caller-supplied lag
  comparison (section 4 above).
- **`week_in_study` became optional (`extra_fixed_effects`) and is not used
  in the primary fit.** `fit_mixed_effects_model`'s `extra_fixed_effects`
  parameter can add `week_in_study` to the formula, but no caller supplies
  it for the primary/reported fit. There is no record of a reason it is
  excluded from primary beyond the fact that it isn't used — this document
  does not invent one.

Only the text above was stale; the analysis was not affected by it. The
primary β_W = −0.184, the B=500 bootstrap (section 4.1), and every number
`Week5_Statistical_Analysis_Deliverable.md` section 3.3 reports as primary
were all obtained from the two-term formula now stated above, not the
four-term one this section used to state. This correction brings the text in
line with what was actually run; it changes no analysis, re-fits nothing,
and moves no reported number.

**Alternative considered and rejected: add the two missing terms to the
implementation instead of correcting this section.** Rejected because the
lag-1 term is an implementation scope gap, not a statistical choice reached
for a reason — adding it now to match a document would be changing the
statistics to fit the paperwork, backwards from why a term belongs in a
model. Doing so would also move the primary point estimate and require
re-running the B=500 bootstrap (section 4.1), a materially larger change
than correcting a stale document.

- **Minimum occasions to enter the fit at all: 3** per person
  (`evidence_model.MIN_OCCASIONS_PER_PERSON` in the archived `analysis/`
  pipeline) *(2026-09-13 migration note, flagged rather than silently carried
  forward: no equivalent explicit gate was found in `backend/statistics/` at
  the time this file was checked in — a person's occasions there simply
  either pass or fail the per-occasion validity gate in section 1.1, and
  whoever has >=1 surviving occasion enters the model frame. Whether this
  3-occasion floor needs porting separately is unresolved, not confirmed
  equivalent.)*. This is separate from, and much weaker than, the 8/12-occasion
  evidence-strength gates in section 4.
- **Convergence policy:** if the random-slope model fails to converge, fall back
  to random-intercept-only (Week 4 doc 1.5). **Consequence:** in the fallback
  there is no per-person slope variance, so `slope_se` / `slope_p` are undefined
  and every participant classifies as `insufficient` — i.e. no per-person
  historical-relationship statement is emitted at all. The (now-archived)
  `analysis/` pipeline recorded this in that run's `run_manifest.json`
  (`model.fallback_to_intercept_only`); `backend.statistics.mixed_effects_model
  .MixedEffectsFitResult`/`Ar1EffectResult` carry the equivalent
  `used_random_slope` / `fallback_reason` fields on every fit.

#### 1.4.1 AR(1) is primary, not a robustness check *(confirmed 2026-09-15)*

**This is a confirmation of what Week 4 §1.2 already specified, not a new
decision.** Week 4 §1.2's own model specification (`e_it ~ N(0, σ²), AR(1)
on e within person`) writes an AR(1) residual structure directly into the
confirmatory model — this is what section 1.4's "AR(1) residual structure"
line above stands for. Week 4 does not offer it as an optional check the
way it explicitly labels Kenward-Roger (vs. Satterthwaite), the 7-day
alignment window, and the lag-1 term as such. Week 4 §1.2 calls the β
resulting from *this* model "the reportable, causally-conservative
quantity."

**Software constraint (not addressed by Week 4's idealised spec):** R
`lme4`/`lmerTest` gives Satterthwaite/Kenward-Roger denominator df but has
no `corAR1`-equivalent residual-correlation structure; R `nlme` gives the
AR(1) residual structure but not those denominator-df methods. No single
fit available to this codebase satisfies both halves of Week 4's model at
once, so one engine's β has to be designated the reportable one:

- **Primary: `nlme::lme` + `corAR1`** (`backend.statistics.r_bridge
  .fit_lme_ar1`, wired in as `fit_ar1_effect`'s primary path).
- **Sensitivity: `lme4::lmer` + `lmerTest`** (Satterthwaite denominator df,
  no AR(1) correction) — kept as the sensitivity figure precisely because
  it supplies the denominator-df rigor section 1.5 below still wants, on a
  model that is otherwise the closer-to-`lme4`-but-not-AR(1)-corrected
  specification.

**On the real dataset (`loc_dist_ep_0`), the two disagree by 34%**
(primary β_W = −0.184 vs. sensitivity β_W = −0.277) — **not because the
methods disagree about the data, but because of what the primary fit's own
`phi = 0.606` says is real:** substantial genuine occasion-to-occasion
serial correlation in the residual, exactly what section 1.1's window
overlap (median EMA gap ~5 days against a 14-day trailing window) predicts.
The sensitivity fit has no way to separate that serial correlation from
signal in the fixed effect, so some of it inflates β_W there. Full numbers
and the equivalent unlock comparison: `Week5_Statistical_Analysis_
Deliverable.md` sections 2.5, 3.3, 3.4, 3.9.

### 1.5 Cleaning thresholds (`loc_dist_ep_0`)

| Rule | Threshold | Action |
|---|---|---|
| GPS uptime | `quality_loc < 12h` | -> NA |
| GPS uptime missing | `quality_loc` is null | -> NA (GPS uptime cannot be verified) |
| Implausible high | `> 500,000 m/day` | -> NA (not capped) |
| Implausible low | `< 0 m/day` | -> NA `[POST-HOC]` |
| Outliers | per-person winsorise to [1st, 99th] pct | clip |
| Transform | `log(mean + 1000)` | see section 1.2 for the order |

- The 12h uptime threshold supersedes the 8h figure in the Week 4 one-page
  summary; the cost of 8h -> 12h is 1.63% of otherwise-valid days.
- Genuine zero-travel days with `quality_loc >= 12h` are real signal and are
  kept: the phone was tracking and recorded no movement.
- **`IMPLAUSIBLE_MIN_M = 0` is a new rule, outside the Week 4 lock** `[POST-HOC]`.
  A negative distance is physically impossible, so a negative value indicates a
  sensor or pipeline fault rather than behaviour. It is stated as a guard for
  future features and future data: **no rows in the current dataset are affected
  (0 occurrences).** It therefore changes no current result.
- Participants with fewer than 5 valid days are left un-winsorised (too few
  points for a stable percentile).
- **Sensitivity (pre-registered, not yet run):** re-run the implausibility filter
  at 250 km and 1,000 km. *(2026-09-13 migration note: the comparison output
  this draft originally pointed to, `analysis/output/sensitivity/transform_order/`,
  is not present in this repository checkout — flagged as a possibly
  local-only artefact rather than silently re-pointed to a guessed path. If
  this sensitivity run is still wanted, it has not yet been produced anywhere
  this checkout can see.)*

### 1.6 `unlock_num_ep_0` specification *(added 2026-09-13, see migration note)*

Mirrors sections 1.1-1.5's structure for the second confirmed Tier-1 feature.
`unlock_num_ep_0` (daily phone-unlock count) is, like `loc_dist_ep_0`, a
whole-day aggregate in `Sensing/sensing.csv`.

#### 1.6.1 Window

Reuses section 1.1's comparison window unchanged: `[-14, -1]`, occasion-validity
gate of >=7 valid days. **"Valid day" is defined differently for this feature**
(see 1.6.5): since there is no quality threshold to gate on, a day counts as
valid here if `unlock_num_ep_0` is non-null that day. *(Not separately
confirmed by the team as a distinct decision — stated here as the natural
reading of "valid sensor day" once the GPS-specific quality gate doesn't apply,
flagged rather than presented as an independent sign-off.)*

#### 1.6.2 Transform order: **no transform**

    daily cleaning
      -> arithmetic mean of the CLEAN daily values within the 14-day window
      -> used as-is (no log)

Unlike `loc_dist_ep_0` (raw skew 160.5, kurtosis 35,552, max 1.2e9 — a
genuinely extreme-tailed quantity that `log(mean + 1000)` exists to tame), raw
`unlock_num_ep_0` is only mildly skewed: **skew 1.73, kurtosis 6.32, max 754** —
nowhere near the same order of magnitude, so the same transform is not
automatically warranted by the same rationale.

Two log variants were checked and both make things **worse**, not better:

- **`log(unlock + 1)`: skew −2.38.** Not just a smaller skew — the sign flips
  and the distribution becomes **bimodal**, because the 3,736 genuine
  zero-unlock days (section 1.6.6) all collapse onto the single point
  `log(1) = 0`, a spike at one end of an otherwise roughly-continuous
  distribution.
- **`log(unlock + 1000)`** (copying `loc_dist_ep_0`'s 1 km / 1000 m offset
  structurally): **SD 0.0509, range [6.91, 7.47]**. A 1000-unit offset is two
  to three orders of magnitude larger than unlock's own 0-754 range, so adding
  it before logging compresses almost all of the real variation in the
  predictor into numerical noise — the offset that rescues `loc_dist_ep_0`'s
  transform actively breaks this one.

**No log transform is applied to `unlock_num_ep_0`.** `x_it` is the
trailing-window mean of the cleaned (winsorised) raw daily unlock count, used
directly.

#### 1.6.3 Lag

Same structure as section 1.3: lag 0 primary, lag 1 a pre-registered
secondary/sensitivity term, with the same listwise-deletion consequence for
occasions missing a lag-1 value.

#### 1.6.4 Model

Same specification as section 1.4 `[POST-HOC, 2026-09-27 — corrected
alongside section 1.4]`:

    phq4_score ~ x_within_it + x_between_i
    + person-level random intercept and random slope on x_within
    + AR(1) residual structure (see section 1.4.1)

with `x_it` built from `unlock_num_ep_0` per 1.6.1-1.6.2 instead of
`loc_dist_ep_0`. Fit as its own separate model (one Tier-1 feature per
confirmatory test, per section 1), not jointly with `loc_dist_ep_0` in a single
formula.

#### 1.6.5 Cleaning thresholds (`unlock_num_ep_0`)

| Rule | Threshold | Action |
|---|---|---|
| Quality gate | **none** — CES has no screen/device-uptime quality column (quality fields exist only for activity, audio, light, location) | n/a |
| Zero values | kept as real values | keep (see 1.6.6) |
| Implausible low | `< 0` unlocks/day | -> NA |
| Implausible high | **none** — no upper cutoff | n/a |
| Outliers | per-person winsorise to [1st, 99th] pct, **positive values only** | clip |
| Transform | none (see 1.6.2) | n/a |

- Winsorisation excludes zeros from the percentile calculation (a 1st
  percentile computed over a series padded with thousands of structural zeros
  would not describe the positive-value tail at all) and therefore never clips
  a zero — zeros pass through unchanged, positive values are clipped to that
  person's own [1st, 99th] pct among their positive days.
- No implausible-high rule exists because, unlike GPS distance, there is no
  physically-impossible upper bound on a daily unlock count to gate on.

#### 1.6.6 Zero-value policy

**Zero-unlock days are retained as values, not recoded to NA.** CES exposes
quality fields for activity, audio, light and location only; there is no screen
or phone uptime field, so a genuine zero cannot be distinguished from a day on
which screen sensing was not running. Unlike an impossible value such as a
45-hour day, a true zero cannot be ruled out, and discarding it would delete
real low-engagement behaviour.

Zero days number 3,736 of 216,065 participant-days (1.73%), affecting 215 of
220 participants, with a median of 12 zero days among affected participants
against a maximum of 231. (Figures supplied by the Data Pipeline Lead.)

This policy contrasts with the GPS rules above, where a missing `quality_loc`
*is* gated to NA precisely because the uptime field exists to check it.

**Limitation.** The zero-day distribution is skewed (median 12 vs. maximum
231): participants at the high end may carry a downward-biased personal mean
for device engagement, since a large share of their `x_bar_i` is built from
structural zeros rather than measured engagement. Whether these participants
need a covariate or an exclusion rule is deferred to Week 6 and is **not
pre-registered here.**

## 2. Multiple-comparison control

### 2.1 Confirmatory family

Holm-Bonferroni, FWER 0.05, across the confirmatory family
(2 Tier-1 features x 1 primary outcome x lag 0 — see the 2026-09-13 migration
note in section 1 for why this is 2, not the "<=3" this draft originally said).

### 2.2 Cohort-level per-person family `[POST-HOC]`

Week 4 defined a **user-facing** family (one person x up to 3 features, <=6
statements). It did **not** define a **cohort-level** family (one feature x all
participants). As a result, each per-person test was corrected as a family of 1,
where Holm and BH are both mathematically identical to the raw p-value — i.e. no
correction was in effect.

**The cohort-level family is defined as the participants who have a per-person
slope for this feature.** The size is data-dependent, not a fixed constant: it
is **214** for `loc_dist_ep_0` as of 2026-09-27. (The retired `analysis/`
pipeline's figure was 213; its origin is suspected, not verified, to be its
lag-1 term pushing one participant below the 3-occasion floor — see
`docs/statistics/week7-calibration-concerns.md` item 8. The current primary
has no lag-1 term and gives 214.) This definition is post-hoc.
`unlock_num_ep_0` is 216 as of 2026-10-06; `evidence.EXPECTED_FAMILY_SIZE` is
a per-feature dict of such current observed values (a visibility check that
warns on change, not a constraint). Both entry points pass the statistics-side
name (`FeatureSpec.name`) as `feature_id` so the check runs:
`participant_evidence` and, since 2026-10-09, the cached aggregation
(`bootstrap_cache.aggregate_checkpoint`, which previously passed none and so
skipped the check silently).

- **Reported values use BH-FDR across that family (n = 214 currently).**
- **Holm-Bonferroni across the same family is reported alongside as a
  sensitivity analysis.**
- Raw per-person p-values are never surfaced. A family-of-1 column is retained in
  `evidence_per_person.csv` (`label_family1`) as a legacy reference only.

**Note: this family size is specific to this one feature.** Now that a second
Tier-1 feature (`unlock_num_ep_0`, section 1.6) is confirmed and in production,
the family must be redefined per Week 4 doc section 2 — the correct family is
each person's per-feature statements batched together, not a per-feature sweep
across participants repeated independently for each of the 2 features.

**The two features do not share the same participant set.** Confirmed on the
real dataset (`backend.statistics.tier1_runner`, 2026-09-14): `loc_dist_ep_0`'s
model frame has **214** participants, `unlock_num_ep_0`'s has **216** — a
strict subset, not an overlapping-but-different pair (`only_in_loc_dist_ep_0`
is empty; `only_in_unlock_num_ep_0` has exactly 2 people). Traced to source:
both of those 2 participants fail GPS's `quality_loc >= 12h` gate almost
completely (0/356 and 3/1141 valid-quality days respectively — one of them has
literally zero non-null raw `loc_dist_ep_0` values at all) while their raw
`unlock_num_ep_0` coverage is complete (356/356, 1141/1141), since unlock has
no comparable quality field to lose them on. This is a **limitation**, not
just a bookkeeping note: it means there exist real participants for whom the
system can defensibly say "for you, X has tended to coincide with Y" using
`unlock_num_ep_0` but **cannot** say anything analogous using `loc_dist_ep_0`
— their GPS history is too sparse to ever enter that feature's model frame,
regardless of how much unlock or EMA history they accumulate. A chatbot
surfacing per-person relationship statements across both Tier-1 features must
treat "does this feature have anything to say about this person at all" as a
per-feature question, not assume that clearing one feature's cold-start gates
implies the other's model frame includes them too.

## 3. Baseline window and cold-start state

- **Baseline window = `[-42, -15]`** (28-day minimum) / **`[-70, -15]`**
  (56-day target).
- It ends immediately before the comparison window `[-14, -1]` (section 1.1), so
  the two are adjacent and never overlap.
- **Sufficiency gates** (all conditions must hold; per feature, not global):

| To unlock | Calendar history | Valid sensor-days in window | Completed EMAs in window |
|---|---|---|---|
| Descriptive (State B) | >= 7 days | >= 5 | >= 1 |
| Comparative (State C) | >= 28 days | >= 20 | >= 3 |
| Historical-relationship | >= 56 days | >= 40 | >= 8 |

- **Baselines are evaluated on a rolling basis, not from a participant's first 28
  days.** The window always trails the evaluation date, so the personal baseline
  moves forward as history accrues.
- **State A/B/C is a property of an evaluation occasion, not of a participant.**
  The same person can be State C at one occasion and State B at a later one (a
  bad two weeks of GPS data), so "N participants are in State C" is not a
  well-formed summary. Per-occasion evaluation was implemented in the
  (now-archived) `analysis/` pipeline's `run_week5_pipeline.run_cold_start_snapshot`
  *(2026-09-13 migration note: that script was never committed to any
  repository — see `analysis/archive/README.md`. The equivalent, independently
  implemented and confirmed-matching logic is
  `backend.statistics.eligibility.classify_state` / `ColdStartState`, in
  production since 2026-08-29.)*.
- Cold-start state and the occasion-validity gate (section 1.1) are independent
  questions about the same occasion: whether the feature has enough history to
  say anything (A/B/C) versus whether this occasion's 14-day window can enter the
  LMM. An occasion can pass one and fail the other in either direction.
- **"Meaningful change" threshold:** `|z| >= 1.0`, where
  `z = (recency_mean - baseline_mean) / baseline_SD`.

### 3.1 Requested time windows outside the pre-registered window `[POST-HOC, 2026-09-27]`

**Decision.** When a participant's question names an explicit time window
other than the pre-registered one ("the last 3 days", "last week", "this
month", a specific date/date range, etc.), the system refuses explicitly
rather than answering. **The fixed-window result is never presented as the
answer to the requested window.**

**Rationale.** Section 1.1's comparison window (`[-14, -1]`) and section 3's
baseline windows (`[-42, -15]` / `[-70, -15]`) are the only windows this
pre-registration defines a statistic for. No other window — a 3-day mean, a
calendar month, a named date range — has a pre-registered baseline,
evidence-strength classification, or "meaningful change" threshold. Comparing
an arbitrary 3-day mean against the 28-day baseline above would not be a
pre-registered quantity; nothing in this document licenses that comparison.
Presenting the pre-registered 14-day window's result as if it answered a
different, requested window is not merely non-responsive — it misrepresents
what was measured, and risks the participant believing their specific
question was answered when it was not.

**Implementation (verified against `main`; no statistics code required for
this decision).** `backend/slm/request_policy.py`'s
`_EXPLICIT_WINDOW_PATTERNS` detects an explicit period expression in the
question text; `request_scope_rejection` returns `"unsupported_time_window"`
when one is found; `backend/slm/prompts/unsupported_window.yaml` supplies the
refusal wording ("I can't provide the specific time range requested. This
version can explain only the observed window supplied with the evidence.").
This was already implemented on `main` before this entry; this entry is the
missing pre-registration sign-off for that behaviour, not a request to build
it.

**Amendment — the 14-day window itself `[POST-HOC, 2026-10-10]`.** Requests
that name the pre-registered 14-day window itself ("past two weeks", "fourteen
days", "fortnight", "past couple of weeks") are answered on that window rather
than refused, as of request policy 0.3.2 (fde16f0, 2026-10-10, following the
ME-P01 session). This is consistent with the rationale above: the refusal
exists because no statistic is defined for other windows, and the 14-day
statistic is the one that is. Other windows — three days, last month,
yesterday, past week — are still refused.

Note that the comparison window is [-14, -1], ending the day before the
assessment. A participant asking about "the past two weeks" on a given day is
answered on the fourteen days ending the day before. This is close enough to be
a fair answer but is not identical to the calendar fortnight they may have in
mind.

**History.** The 2026-09-20 rostered-pair pilot's Q2 ("What's changed in my
behavior over the last 3 days?") found the opposite of this decision: the
system silently returned the fixed 14-day window's result without confirming
it represented the requested three days —
`docs/evaluation/week7-rostered-pair-pilot-main.md`, "Fail — time-window
routing is not implemented." The refusal behaviour above was added on `main`
afterward, but without a statistics sign-off that it was the intended
resolution (as opposed to, for example, computing a genuine 3-day statistic).
This entry supplies that sign-off: explicit refusal, not silent substitution,
is correct per the rationale above.

**Detector coverage (verified empirically against `_EXPLICIT_WINDOW_PATTERNS`
on the current `main`).** Caught: numeric windows (`"last 3 days"`, `"past 2
weeks"`), the ten spelled-out numbers one–ten plus `fourteen`/`thirty`,
`last`/`past`/`previous`/`next`/`this` + an hours/days/weeks/months/
years/fortnights unit (`"this month"`, `"next week"`), `today`/`yesterday`/
`tomorrow`/`tonight`/`weekend(s)`, ISO and slash dates, and
`since`/`from`/`between`/`until`/`through`/`on`/`in` + a weekday or full
month name (`"since Monday"`, `"since January"`).

**Known limitation (recorded, not fixed here).** Two different kinds of
question currently reach the fixed 14-day window silently, and only one of
them is intended to:

- **Intended pass-through — vague recency with no competing window.**
  `"recently"`, `"lately"`, `"nowadays"`, `"these days"`, `"of late"`, `"just
  now"` name no specific alternative period, so answering from the observed
  window is not a misrepresentation. This is the documented purpose of
  leaving them unmatched (`request_policy.py`'s own comment: "Keep
  unspecified 'recent' / 'observed window' questions available").
- **Detector gap — these read as explicit requests but are not caught,**
  verified empirically: spelled-out numbers beyond the hardcoded list
  (`"over twelve days"`, `"eleven days"`, `"twenty days"` — only one–ten,
  `fourteen`, `thirty` are recognised); season/term references (`"last
  winter"`, `"this semester"`, `"last spring"` — not hours/days/weeks/
  months/years/fortnights); and abbreviated month names (`"since Sept 1"`,
  `"in Sept"` — only full month names are recognised). A question phrased
  this way is answered from the fixed window with no refusal and no
  disclosure that the requested period was substituted. This is a gap in the
  refusal detector's text patterns, not a statistics gap; closing it is an
  SLM/request-policy fix (widen `_EXPLICIT_WINDOW_PATTERNS`), not a
  pre-registration change, and is not done as part of this entry.

**What remains open.** Refusal is the correct behaviour for *this*
pre-registration, not necessarily forever. A future version could compute a
genuine statistic for a requested window, but that needs its own baseline
definition, evidence-strength classification, and gating for that window
size — none of which this document defines. Building that support requires a
pre-registration revision, not a request-policy change alone.

## 4. Evidence-strength classification (per person, on BLUP `slope_i`)

| Tier | q | Standardised effect | Min occasions | Lag consistency |
|---|---|---|---|---|
| strong | < 0.01 | >= 0.20 | >= 12 | lag0 / lag1 signs agree |
| moderate | < 0.05 | >= 0.10 | >= 8 | — |
| weak | < 0.10 | >= 0.10 | >= 8 | — |
| insufficient | none of the above | | | |

    standardised effect = |slope_i| * predictor_sd / outcome_sd

`q` is the BH-FDR-adjusted value over the family defined in section 2.2.

**The tiers are conjunctive and there is no partial credit.** A participant who
meets the strong q threshold but whose standardised effect is below 0.10 matches
none of the three tiers and is classified `insufficient`. No intermediate label
for the "significant but too small to matter" case exists; this is deliberate,
not an oversight in the table.

The minimum-occasion gates and the lag-consistency requirement are load-bearing
parts of the classification and are stated here as spec, not as implementation
detail.

### 4.1 Per-person SE via bootstrap, and cross-method intersection `[POST-HOC, 2026-09-13]`

Section 9 item 1 (below) flags that `Var(slope_i)`'s per-person standard error
was never available from the R `nlme` engine `backend.statistics
.mixed_effects_model`/`evidence.py` actually run on: `nlme::ranef()` has no
`lme4::condVar`-equivalent conditional-variance extraction, and a direct check
confirmed `nlme::simulate.lme` refuses any model with a `corStruct` (this one
has `corAR1`) outright — so neither a delta-method nor an `nlme`-native fix
existed. `backend/statistics/bootstrap.py` implements two bootstrap SE
estimators instead, and `backend.statistics.evidence.intersect_bootstrap_evidence`
combines them. This section records what was decided and measured; the
mechanism itself is documented in that module's docstrings.

**The two designs compared (B=500 replicates each, on the real dataset):**

- **Parametric.** Resimulate `y` from the real fit's own generative parameters
  (fixed effects, random-effects covariance `D`, AR(1) coefficient, residual
  `sigma`) — a fresh random-effect draw and AR(1) residual series per person,
  per replicate — then refit and collect the resimulated per-person slope.
- **Cluster (case resampling).** Resample participants with replacement,
  keeping each resampled copy's real observed data unchanged; refit and
  collect the per-person slope. A participant drawn more than once is
  relabelled per copy so repeats are treated as distinct clusters, not doubled
  occasions within one cluster.

**Finding: not a scaling difference — a different sensitivity.**

| Quantity | Value |
|---|---|
| Spearman ρ(parametric SE, occasion count) | **+0.81** |
| Spearman ρ(cluster SE, occasion count) | **−0.33** |
| Spearman ρ(parametric SE, cluster SE) | **−0.397** (p ≈ 1.7×10⁻⁹) |
| SE ratio (parametric ÷ cluster) | mean **7.85×**, range **1.05×–29.5×** |

Parametric SE rises with occasion count because more occasions means less BLUP
shrinkage toward the population mean, so more of the true random-slope
variance passes through into how much the resimulated slope varies across
replicates. Cluster SE falls with occasion count because more of a
participant's own real, unchanging data makes their contribution more stable
regardless of who else is resampled alongside them — the ordinary "more data,
smaller SE" pattern. Driven by the same variable in opposite directions, the
two methods' SE *rankings* end up negatively correlated with each other, not
merely differently scaled by a constant factor.

**Why neither is used alone.** Cluster's SE is small specifically because it
never re-draws a participant's own observed trajectory — it does not encode
the uncertainty from that participant's data having come out differently,
which is exactly what a person-level SE must capture, so it understates it.
Parametric's SE reflects genuine generative uncertainty but is dominated by an
occasion-count/shrinkage effect, a different quantity from "how uncertain is
this person's estimated slope."

**Decision: `label_intersection` — `evidence_available` only where both
methods independently agree.**

| | cluster: `evidence_available` | cluster: `no_claim` |
|---|---|---|
| **parametric: `evidence_available`** | 23 | 0 |
| **parametric: `no_claim`** | 28 | 163 |

Agreement rate **86.9%** (186/214 participants). The disagreement is
**one-directional**: every participant parametric calls `evidence_available`
is also `evidence_available` under cluster (zero counter-examples); cluster
additionally calls 28 more participants `evidence_available` that parametric
does not. Intersection yields **23 of 214** participants — this session's
`label_intersection`. Parametric-only and cluster-only labels
(`reclassify_cohort_family`'s own `label_bh`/`label_holm` per method) remain
available as standalone sensitivity views; the intersection does not replace
either.

**Replication on `unlock_num_ep_0` `[POST-HOC, 2026-10-10]`.** The same B=500 procedure (both methods, `master_seed=20260913`) was run on the second Tier-1 feature: 1000/1000 records usable, 0 fallbacks, family 216. Side by side with GPS:

| | `loc_dist_ep_0` (GPS) | `unlock_num_ep_0` |
|---|---|---|
| Family | 214 | 216 |
| Intersection `evidence_available` | 23 | fewer than 5 (see small-cell note) |
| Cluster-only / parametric-only | 28 / 0 | 36 / 0 |
| Agreement rate | 86.9% (186/214) | 83.3% (180/216) |
| SE ratio, parametric ÷ cluster (mean) | 7.85× | 10.14× |
| Spearman ρ(parametric SE, cluster SE) | −0.397 | −0.612 |
| Spearman ρ(parametric SE, occasion count) | +0.81 | +0.54 |
| Spearman ρ(cluster SE, occasion count) | −0.33 | −0.29 |

The pattern (one-directional disagreement, parametric SE larger, negatively correlated SE rankings, opposite-signed dependence on occasion count) appears in both features. This supports reading it as a property of the two bootstrap methods rather than of GPS, and strengthens the case for requiring both to agree (the intersection). Magnitudes are not identical (the cross-method correlation is stronger and the parametric/occasion-count correlation weaker for unlock). The figures here are from the unlock run's `aggregated_cache.json`; the per-feature cache is the reference.

**Small-cell note (section 5.3).** The unlock intersection count (3 of 216) is below 5. In any *published* aggregate it is written "fewer than 5", and the corresponding cell of the 2×2 agreement table (both `evidence_available`) is likewise suppressed or merged; the exact count appears only in repository-internal documents. The GPS counts (23, 28, 163) are all at least 5.

**Family-size warning.** The unlock run's log was not kept, so whether the `EXPECTED_FAMILY_SIZE` warning fired could not be checked from the outputs. The family is 216 throughout and equals the dict's expected value for `unlock_num_ep_0`, so no warning is expected.

**Stability check** (run before considering raising B beyond 500): splitting
the 500 replicates by `iteration_index` into two halves (0–249, 250–499) and
recomputing the intersection on each independently gives **24** participants
per half — the full-B=500 23 plus **one additional, different borderline
participant per half** (Jaccard(half, full) ≈ 0.958 both halves; Jaccard(half
A, half B) = 0.92). The full-B=500 set is a strict subset of both halves: more
replicates resolved two borderline cases toward `no_claim` that a smaller,
noisier B had let through. Reasonably stable; a further increase to B=1000 was
judged not to change this picture materially and was not run.

**`strong` remains unreachable** for the intersection set, same reason as
section 4's own note: `classify_evidence_strength` needs an explicit lag-0/
lag-1 sign-consistency flag that no caller currently supplies (the lag-1 term
is out of `backend.statistics.mixed_effects_model`'s scope). All 23
intersection-positive participants are `moderate`, not `strong`, by
construction.

**Why this is post-hoc, not a pre-registration violation.** Section 1 above
(written pre-sign-off) specifies BH-FDR correction over a single per-person
test; it did not anticipate reconciling two different bootstrap SE estimators,
because the SE gap itself was not foreseen as needing a bootstrap solution at
all. Recorded in the same register as the cohort-level family definition
(participants holding a per-person slope; 214 currently, section 2.2) and the binary user-facing collapse (section 5) — see section 7's
post-hoc log for the consolidated list.

**Cached bootstrap SE: when a cached result stops counting `[POST-HOC, 2026-10-07]`.**
The B=500 result is stored (`backend/statistics/bootstrap_cache.py`, under the
git-ignored `outputs/bootstrap_cache/<feature>/`) together with a fingerprint,
and is used only while the recomputed fingerprint is identical. The fingerprint
covers (A) a content hash of the exact model frame the fit consumes, so any
change to the data, cleaning, windows or transform invalidates it; (B) content
hashes of every source file on the estimation path (`bootstrap.py`,
`mixed_effects_model.py`, `r_bridge.py`, `feature_specs.py`, and the
`backend/data_pipeline` cleaning/feature modules); and (C) the Python/R/`nlme`/
numpy/scipy/pandas/rpy2 versions and the run configuration (feature, transform,
`master_seed`, B, engine). The aggregated per-person SE and intersection table
are additionally keyed on `evidence.py` and the evidence-classification
thresholds, so a classification-only change invalidates the aggregate without
invalidating the raw replicates. A missing cache leaves every label
`insufficient`; a mismatching one stops that feature with an error naming the
changed key; a cache is only ever written from a committed, unmodified tree, and
a partial run is only resumed under an identical fingerprint. None of this
changes what is estimated or any threshold in this document.

**Cache and per-person output permissions: fail-closed `[POST-HOC, 2026-10-09]`.**
The cache and `tier1_runner`'s per-person outputs contain participant uids. Every
such directory and file is restricted to the owner (POSIX mode 700/600; Windows
`icacls`, inheritance removed, current user only) and the result is **verified by
reading the permissions back**, not by the exit status of the command. Earlier
this was best-effort (a failure warned and the run continued); it is now
fail-closed: if the restriction cannot be applied and verified, nothing is
written, and an existing cache folder that is not owner-only is restricted once
on load/resume or the run stops with an error. A permission failure is a
different class of error from a stale cache and aborts the whole Tier-1 run
rather than only the affected feature. This changes where and how files are
stored, not what is estimated or any threshold in this document.

## 5. User-facing collapse to two values `[POST-HOC]`

The evidence contract handed to the SLM collapses the four tiers to two:

| Internal tier | Evidence contract |
|---|---|
| strong, moderate | `evidence_available` (may be surfaced, with the required hedge) |
| weak, insufficient | `no_claim` (say nothing about the relationship) |

The internal 4-tier classification is unchanged and is still used for reports and
analysis.

### 5.1 Permitted output by (cold-start state x evidence strength)

Cold-start state (section 3) and evidence strength (section 4) answer two
independent questions about the same occasion — *is there enough history for
this feature* and *is there a defensible relationship claim*. What may be said
is the grid, not either axis alone. This table is the contract; no output may
exceed its cell.

Within State C a third axis applies: whether the occasion has a computable
recent-vs-baseline deviation. State C unlocks the comparison *framing*; it does
not guarantee a *number*. The deviation is undefined when the recency window
holds fewer than 7 valid days, or when the baseline SD is zero.

| Cold-start state | Evidence | Deviation | Permitted output |
|---|---|---|---|
| A | any | — | templated message only; **no numbers** |
| B | any | — | descriptive only; **no comparison, no relationship claim** |
| C | `no_claim` | yes | comparison permitted; **relationship claim forbidden** |
| C | `no_claim` | no | comparison framing permitted, **no deviation value this occasion**; relationship claim forbidden |
| C | `evidence_available` | yes | comparison permitted; **hedged relationship claim permitted** |
| C | `evidence_available` | no | comparison framing permitted, **no deviation value this occasion**; hedged relationship claim permitted |

The relationship claim does not depend on the deviation axis: it rests on the
participant's fitted slope over their whole record, not on this occasion's
deviation, so it remains permitted when no deviation can be quoted.

State A and State B are unconditional on evidence strength: a participant may
hold a strong per-person slope and still be in State A at an early occasion,
and the claim is still not permitted, because the statement would be about a
period the system cannot describe. **State A takes precedence over evidence
strength**, and the ordering is not negotiable at output time.

`A + evidence_available` occurs in this dataset only as an artefact of
retrospective analysis: evidence strength is estimated from each participant's
full record, whereas cold-start state is judged from the data available up to
the occasion being evaluated, so a participant's earliest occasions can be
State A while their whole-history evidence label is `evidence_available`. In
live operation a new user has no history, the per-person slope cannot be
estimated, and the combination does not arise.

**`C + no_claim` is the modal cell, not an edge case** — on the current dataset
it is the single largest combination by occasion count. "You can compare, but
you may not say why" is the normal operating state, and templates must treat it
as such rather than as a degraded fallback. Per-occasion frequencies for every
cell are written to `state_evidence_combinations.csv` on each run.

**Rationale (post-hoc).** 26 participants sit in the standardised-effect band
[0.15, 0.20), immediately below the strong/moderate boundary. (A data-dependent
number, stated because it is the rationale.) Correcting the predictor transform
order alone moved the labels of 68 of 213 participants, 34 of them across the
moderate/strong boundary in a single cohort-wide switch driven by the
population-level lag-sign check. Under the two-value mapping the same change
moves only 26 of 213. If the same person can land on either side of that
boundary under two defensible specifications, there is no basis for saying
different things about them. **The thresholds themselves are unchanged, so this
is not a pre-registration violation** — it is a decision about what the
strong/moderate distinction is allowed to be used for. Measured comparison:
`analysis/output/sensitivity/transform_order/` *(2026-09-13 migration note:
not present in this repository checkout — see the equivalent flag in section
1.5)*.

### 5.2 User-facing numeric precision (rounding rule) `[POST-HOC, 2026-09-27]`

**Decision.** Both Tier-1 features' user-facing values (`FeatureWindow.value`
and `PersonalBaseline.value` — the 14-day window average and the 28-day
baseline average) are rounded to the nearest whole unit before they reach the
`EvidencePacket`: whole km/day for `loc_dist_ep_0`, whole unlocks/day for
`unlock_num_ep_0`. Rounding uses ordinary "round half up"
(`Decimal`/`ROUND_HALF_UP`), not Python's built-in `round` (round-half-to-even
— it would silently send a `0.5` tie to `0`, not the ordinary half-up rule a
participant-facing "nearest whole number" is understood to mean).

This responds to three independent records of the same excessive-precision
problem, all citing the same concrete case
(`120.71428571428571` unlocks/day):
`docs/ui/demo-machine-verification-2026-09-21.md` (lines 66-70),
`docs/evaluation/week8-fallback-e2e.md` (line 110), and
`docs/slm/week8-safety-context-integration.md` (line 43).

**Basis: the digit shown must not exceed the day-to-day measurement
precision.** For each participant, the standard deviation and coefficient of
variation (SD / |mean|) of the daily feature values inside their own 14-day
comparison window were computed on the real dataset:

| Feature | Median within-person CV | Reading |
|---|---|---|
| `loc_dist_ep_0` | **1.28** | day-to-day SD *exceeds* the mean — the window average is already a rough summary of a highly variable quantity |
| `unlock_num_ep_0` | **0.30** | day-to-day SD is ~30% of the mean |

A coefficient of variation this large means any digit past the whole unit is
precision the measurement does not have. Displaying it is not displaying a
more accurate number — it is displaying a falsely precise one. This applies
to both features; `loc_dist_ep_0`'s case is the more extreme of the two.

**Alternative considered and rejected: express the uncertainty in the
granularity itself** (e.g. round GPS to the nearest 5 km, to make the
imprecision visible in the number's shape). Rejected because it reads worse
than a plain integer and duplicates a job this system already does elsewhere:
the response template's hedging/uncertainty sentence is the place uncertainty
is disclosed, not the number's step size.

**Implementation.** `backend/statistics/participant_evidence.py`'s
`_round_user_facing` helper, called from `build_evidence_packet` at the point
`feature_value` and `baseline_value` are computed — not in
`backend/slm/output_grounding.py` at render time. The `EvidencePacket` is the
canonical value; `output_grounding.validate_output_grounding` checks rendered
text against the packet's stored values under exact `Decimal` equality, so
the displayed value must already be what the packet stores, not rounded a
second time on the way out.

**Known limitation (recorded, not special-cased).** A participant whose
14-day GPS average is under 1 km/day is shown "0 km per day". They did move;
whole-number rounding removes it from view. Keeping one decimal place only
below that threshold was considered and rejected — a rule that changes shape
below a cutoff is a second rule, not the same rule applied more carefully.

**Out of scope for this decision.** Percentage/ratio framing ("X% less than
your baseline") is not implemented anywhere in the current system and is not
addressed here — `backend/slm/prompts/evidence_explainer.yaml` explicitly
forbids the model from computing a percentage. `current` and `baseline`
remain the only two values ever surfaced, shown side by side, each rounded
independently by the same rule.

### 5.3 Small-cell suppression in published aggregates `[POST-HOC, 2026-10-09]`

Any aggregate table that is published — in a report, in slides, or as a table
leaving the repository — must either suppress (hide) every cell with a count
below 5 or merge it into an adjacent category so that no published cell is
below 5. This was added at the Privacy & Security Lead's request. Analysis
outputs that stay inside the repository (`analysis/output/`, `outputs/`) are
exempt, but the rule applies as soon as a table is transcribed from them into
anything published.

**Evaluation questionnaire ratings: why the rule is not applied, and what is published instead.**
Evaluation questionnaire ratings come from team members acting
as evaluators — participants in the evaluation, though their
ratings are opinions of the system rather than health or
behavioural data. The under-5 cell rule is not applied to them,
since every cell is small by design (n ≈ 8) and suppression
would blank the table. Instead, only cross-evaluator aggregates
(per-item n, median, range) and critical failures by question
are published; per-evaluator rows and the mapping from
evaluator codes to people are not.

Confirmed with the Privacy & Security Lead on 2026-10-10:
ratings are published as per-item n, median and range across all
evaluators, with no per-score counts. Items with fewer than five
applicable ratings are marked as insufficient rather than summarised.
Critical failures are reported by question and count, not by session —
the evaluation roster links sessions to named evaluators, so a session
identifier would identify the rater. Session-level detail, individual
ratings and the evaluator-code mapping are kept only in restricted team
records.

## 6. Exploratory family (BH-FDR, q=0.05)

Other outcomes (PHQ-4 subscales, PAM, stress, sse3), lag 1 as a standalone
claim, episode-of-day features, the 7-day PHQ-4 **alignment**-window sensitivity
analysis, interaction terms, and any per-person multi-statement report.

The now-deleted analysis/preregistration.md described the 7-day
alignment-window check as a pre-registered robustness analysis
with a "β1 materially unchanged" acceptance criterion. Here it is
listed as exploratory. Which status it should carry is not
settled by this document; the compiled file's framing is not
authoritative (it was assembled by session tooling, not written
as a specification). Not to be confused with the 7-day recency
window retired in open item #4 below, which is a different
window.

## 7. Register of post-hoc decisions

Decisions taken after the Week 4 lock, listed so the freeze is auditable:

1. **`IMPLAUSIBLE_MIN_M = 0`** (section 1.5) — new rule outside the Week 4 lock;
   0 rows affected in the current dataset.
2. **Cohort-level family = participants holding a per-person slope for the
   feature (data-dependent; 214 for `loc_dist_ep_0`)** (section 2.2) — a family Week 4 never defined;
   BH-FDR reported, Holm as sensitivity.
3. **User-facing 2-value collapse** (section 5) — thresholds unchanged.

Resolved Week 4 open items (decisions, not post-hoc changes):

4. **Open item #4 — the 7-day user-facing recency window is retired; everything
   uses the 14-day window.** `RECENCY_WINDOW_DAYS = 7` no longer exists; the
   recency window reuses `ALIGN_WINDOW_DAYS` / `ALIGN_WINDOW_LAG_DAYS`
   (`backend.statistics.mixed_effects_model.ALIGNMENT_WINDOW_DAYS` /
   `TRAILING_WINDOW_LAG_DAYS` in the current, reconciled module).
   **Rationale:** if the quantity shown to the user differs from the quantity
   whose evidence strength was estimated, the claim being shown is not the claim
   the analysis supports. The 7-day window was a valid Week 4 choice, not a bug —
   just not the one the team settled on.
5. **Tier-1 feature list confirmed as 2 features, not <=3** (section 1,
   2026-09-13 migration note) — `loc_dist_ep_0` + `unlock_num_ep_0`, team
   agreement 2026-08-26, sign-off recorded 2026-09-05.
6. **Per-person SE via bootstrap, and cross-method intersection** (section
   4.1) — Week 4 pre-registered BH-FDR over a single per-person test, not
   reconciliation across two disagreeing bootstrap SE estimators; the SE gap
   itself was not foreseen as needing a bootstrap. `label_intersection`
   (parametric AND cluster both `evidence_available`) is now the reported
   value; 23 of 214 participants qualify.
7. **User-facing numeric precision: round to the nearest whole unit**
   (section 5.2) — km/day for `loc_dist_ep_0`, unlocks/day for
   `unlock_num_ep_0`, via `Decimal`/`ROUND_HALF_UP`. Not a Week 4 open item;
   raised by three independent Week 7/8 records of the same excessive-
   precision output.
8. **Requested time windows outside `[-14, -1]` / baseline are refused, not
   silently answered from the fixed window** (section 3.1). Not a Week 4
   open item; sign-off for behaviour already implemented on `main`
   following the 2026-09-20 pilot's Q2 finding.
9. **Section 1.4's fixed-effects formula corrected from four terms to two**
   (section 1.4, 1.6.4) — `x_within_it + x_between_i` (+ random intercept,
   random slope on `x_within`, AR(1) residual), not
   `x_within_it + x_within_lag1_it + x_between_i + week_in_study_it`. The
   lag-1 term was never ported to `backend/statistics/` (an implementation
   scope gap, per `mixed_effects_model.py`'s docstring); `week_in_study` is
   optional (`extra_fixed_effects`) and unused in the primary fit. A
   documentation correction to match what was actually run — the primary
   β_W = −0.184 and the B=500 bootstrap were already computed from the
   two-term formula; no analysis changed.
10. **Small-cell suppression in published aggregates** (section 5.3,
    2026-10-09) — cells below 5 are suppressed or merged into an adjacent
    category in anything published (report, slides, tables leaving the
    repository). Not a Week 4 open item; added at the Privacy & Security
    Lead's request. In-repository outputs are exempt, but the rule applies when
    a table is transcribed from them.
11. **Evaluation questionnaire ratings: no under-5 cell suppression; instead
    cross-evaluator aggregates only, "insufficient" below five applicable
    ratings, and critical failures by question, not by session** (section
    5.3). Added following the Privacy & Security Lead's review (confirmed
    2026-10-10) of `scripts/summarize_session_responses.py`: the roster
    links sessions to named evaluators, so session IDs are not published.
    Not a Week 4 open item; does not touch the Tier-1 analysis.
12. **Requests naming the 14-day window itself are answered, not refused**
    (section 3.1 amendment, 2026-10-10) — request policy 0.3.2 (fde16f0)
    stops refusing "past two weeks" / "fourteen days" / "fortnight" / "past
    couple of weeks". The answer is on `[-14, -1]`, which ends the day before
    the assessment and so is not identical to the calendar fortnight the
    participant may mean. Other windows (three days, last month, yesterday,
    past week) are still refused. Not a Week 4 open item; follows the ME-P01
    session.

## 8. Reference implementation

`loc_dist_ep_0` was first implemented end-to-end in a local, uncommitted copy
of `analysis/run_week5_pipeline.py` as the worked example — see
`analysis/output/latest/week5_run_report.md` for the real fitted result on the
DATA5702 copy of the dataset, and `run_manifest.json` in the same directory for
the config that produced it. *(2026-09-13 migration note: that script was
never committed to any repository — see `analysis/archive/README.md`. Both
Tier-1 features are now implemented in
`backend/statistics/mixed_effects_model.py` (model fit, AR(1), BLUPs) +
`backend/statistics/evidence.py` (per-person evidence-strength, BH-FDR/Holm) +
`backend/statistics/eligibility.py` (cold-start state) — this is now the
canonical engine each Tier-1 feature runs through, unchanged except for the
feature-specific cleaning thresholds in sections 1.5/1.6.5.)*

Code that needs "the current outputs" reads `analysis/output/latest/`, never
`analysis/output/` directly. *(Still accurate — `analysis/output/` was not
part of the 2026-09-12 archival; only the three pipeline modules under
`analysis/` itself moved to `analysis/archive/`.)*

## 9. Known simplifications to close out before this is finalized

1. Per-person significance uses `Var(slope_i) ~ Var(beta1_hat) + Var(u1_i)`,
   treating the fixed-effect estimator and the BLUP as independent — their true
   covariance is not directly exposed by `statsmodels` `MixedLM`. Needs either a
   derivation from the mixed-model equations or a cross-check against R
   `lme4`/`lmerTest` (the doc's primary estimator) before being reported as final.
   *(As of this 2026-09-13 check-in, `backend.statistics.mixed_effects_model`
   has since moved to R `lme4`/`lmerTest` + `nlme::lme(corAR1(...))` as its
   primary engine, with real per-person BLUPs — but `nlme::ranef()` has no
   equivalent to `lme4`'s `condVar`, so this specific approximation was
   deliberately **not** ported. **Resolved the same day, by a different route:
   bootstrap, not delta method** — see section 4.1 above for the full result
   (two disagreeing bootstrap SE estimators, used only via their
   intersection) and `backend.statistics.evidence`'s module docstring /
   `intersect_bootstrap_evidence`'s docstring for the mechanism.)*
2. Lag-1 sign consistency currently compares population-level fixed-effect
   signs, not per-person lag-0 vs lag-1 BLUPs (would need a 3-random-effect
   model).
3. AR(1) residual structure is not fit (independence working correlation used
   instead) — flagged as a limitation in the Week 4 doc itself (section 1.7).
   *(As of this 2026-09-13 check-in, superseded for `backend.statistics`: a
   real joint AR(1) fit via R `nlme::lme(correlation = corAR1(...))` is now the
   primary path there — see that module's docstring for what carries over and
   what doesn't. Left unchanged here as the historical record of what this
   draft knew at the time.)*
4. COVID-era / term-phase fixed effect not yet included (Week 4 doc open item 5).
5. The 250 km / 1,000 km implausibility sensitivity analysis (section 1.5) is
   pre-registered but has not been run.
6. **`term_phase` calendar `[open item, added 2026-10-06]`.** Item 4 above says
   the term-phase effect is "not yet included"; to be precise, it exists in
   `backend.statistics.mixed_effects_model` as an optional extra fixed effect
   (not used in the primary fit, section 1.4) built from a **generic
   US-academic-year heuristic** (winter break ~Dec 15-Jan 15, spring break
   ~Mar 8-16, summer break ~May 15-Aug 25), not the real Dartmouth academic
   calendar for the study years, because the CES dataset carries no
   academic-calendar field. **Open:** replace the heuristic with the actual
   Dartmouth calendar, or accept it as a documented approximation. Undecided;
   needs the Statistical Analysis Lead.

## 10. Not to be changed after Wednesday sign-off

Feature list, comparison window and its `[-14, -1]` definition, predictor
transform order, lag, direction hypotheses, cleaning thresholds, baseline windows
and sufficiency gates, evidence-strength thresholds, family definitions, and the
user-facing collapse. Changes after sign-off require a documented, dated
addendum, not a silent edit.
