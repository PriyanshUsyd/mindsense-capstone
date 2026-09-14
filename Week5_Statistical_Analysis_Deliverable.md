# MindSense — Week 5 Deliverable: Statistical Analysis Lead

**Owner:** Moe Tanaka (Statistical Analysis Lead)
**Week 5 scope (per Weekly Build Plan v5):** Implement baseline/evidence logic for
one feature using the named statistical model. Join the Tier-1 feature-list
proposal (jointly with Data Pipeline Lead).
**Status:** Baseline/evidence logic implemented and run end-to-end on the real
dataset for `loc_dist_ep_0` (the feature vertical-slice audited in Week 4),
**using Moe Tanaka's local pipeline described in Section 1 — not the version
currently committed to this repository.** Three specification deviations
found and corrected during the week; occasion counts independently
reconciled with the Data Pipeline Lead. The results in Section 3 are real
and stand as reported. **What is committed and runnable today differs from
what this document originally described as built — see the correction note
at the top of Section 1 before relying on any file path below.** A
preregistration document now exists at `analysis/preregistration.md`, but it
is a 2026-09-12 compilation of Moe's already-locked decisions by another
contributor, not the file this section originally referred to — still
pending her review (see Section 1's note).

---

## 1. What was built

**Correction (added after this document was first written; see
`CLAUDE.md`'s "Unreflected changes" and `analysis/archive/README.md`):**
the table below describes the pipeline as it was originally built and run,
on Moe Tanaka's own machine, to produce the results in Section 3. It does
**not** describe what is committed to this repository today. As committed:

- `cleaning.py`, `evidence_model.py`, and `baseline.py` were moved to
  `analysis/archive/` on 2026-09-12 (retired, not deleted) and are **not
  runnable as checked in** — `baseline.py` imports `from predictors import
  ALIGN_WINDOW_DAYS, ALIGN_WINDOW_LAG_DAYS, OCCASION_MIN_VALID_DAYS`, and
  `predictors.py` has never existed anywhere in this repository's history,
  on any branch. The `analysis/output/` artefacts already in this repo
  (including the numbers reported in Section 3) were produced from Moe's
  local, uncommitted copy of these modules, not from what is checked in.
- `run_week5_pipeline.py` and `tools/reconcile_occasions.py` were never
  committed to this repository at all.
- The **real, currently runnable, canonical implementation** of this
  logic now lives in `backend/statistics/` (`mixed_effects_model.py`,
  `eligibility.py`, `evidence.py`) and `backend/data_pipeline/cleaning.py`
  — ported from Moe's specification and archived code, authored primarily
  by Priyansh Khandelwal (Integration/QA), and still flagged in
  `backend/statistics/evidence.py`'s module docstring as pending Moe's own
  review before being treated as final (see that module's docstring for
  the specific open gap: per-person standard errors).
- `preregistration.md` exists at `analysis/preregistration.md`, but as a
  2026-09-12 compilation of Moe's already-locked decisions by another
  contributor — not the file originally referred to in this row, and not
  yet reviewed by her.

Original table, describing the local pipeline that produced Section 3's
results (run with `python analysis/run_week5_pipeline.py` **on that local
copy** — this exact invocation is not reproducible from this repository as
committed):

| File | Implements (Week 4 doc section) |
|---|---|
| `cleaning.py` | Feature cleaning / GPS sanity bound (1.4) |
| `predictors.py` | 14-day trailing alignment window, within/between-person centring (1.3) |
| `evidence_model.py` | Population LMM fit, BLUP extraction, evidence-strength classification (1.2, 1.5, 1.6, 7), Holm/BH correction (2) |
| `baseline.py` | Baseline windows, sufficiency gates, three-state cold-start policy (4, 5) |
| `run_week5_pipeline.py` | Orchestrates all of the above end-to-end |
| `tools/reconcile_occasions.py` | Independent re-implementation of the occasion-validity gate, used to reconcile counts against the Data Pipeline Lead |
| `preregistration.md` | Pre-registration artefact (Week 4 open item 6) |

Outputs are written per run to `analysis/output/runs/<timestamp>_<config>/`,
with `analysis/output/latest/` holding a copy of the most recent run. Each run
directory carries a `run_manifest.json` recording every threshold, window
definition, correction method and the fitted model formula, read at runtime
from the named constants rather than duplicated.

**Privacy handling:** participant-level `cold_start_states.csv`,
`evidence_per_person.csv`, `occasion_gate_keys.csv`, and reconciliation key
CSVs contain longitudinal identifiers or dates. They are retained locally for
authorised verification and excluded from Git. Shared repository evidence is
limited to aggregate diagnostics, model summaries, manifests, reports, and
`analysis/output/reconciliation/aggregate_summary.json`.

---

## 2. Correction log

Three deviations between the Week 4 locked specification and the implemented
pipeline were identified and corrected before the results in section 3 were
finalised. All reported figures reflect the corrected pipeline.

### 2.1 How they were found

The Data Pipeline Lead and the Statistical Analysis Lead were working with
different occasion counts (35,348 vs 28,337). Rather than accepting the gap or
assuming a cause, both sides produced a filter-by-filter cascade of surviving
occasions using identical step definitions, and exchanged the surviving
(participant, date) key sets for a set-difference comparison.

The first comparison showed the two counts were taken at different stages of
the cascade, not from different filtering. Closing the remaining 1.1% gap
required auditing each configuration value against the executed code rather
than against the specification document, and that audit is what surfaced all
three deviations below.

Only one of the three — the comparison window (2.3) — was discoverable by
reading the Week 4 deliverable against the source. The other two were not: the
quality gate because the deliverable and the code carried the same superseded
value, so a document-to-source comparison showed agreement (2.2); and the order
of operations because it is not a configuration constant, so a value-by-value
audit did not reach it (2.4). Both emerged only from pursuing the count
reconciliation to completion.

### 2.2 Location quality gate

| | |
|---|---|
| Week 4 deliverable | `quality_loc >= 8 h` |
| Decided in discussion | `quality_loc >= 12 h` |
| Implemented | `quality_loc >= 8 h` |
| Status | Corrected to 12 h |

Week 4 deliverable states 8 h; the 12 h threshold was decided in discussion
after establishing that the 8 h → 12 h change costs 1.63% of valid sensor-days,
but that decision was never written back into either the deliverable or
`cleaning.py`.

This is the one deviation that could not have been caught by comparing the
specification document against the source, because both carried the superseded
value. It surfaced only through the occasion-count reconciliation.

A related defect was found and corrected at the same time: days with a missing
`quality_loc` were passing the gate, because `NaN < threshold` evaluates to
False in pandas. GPS uptime cannot be verified for those days, so they are now
gated to NA explicitly and counted separately in the cleaning diagnostics. A
lower bound on distance (negative values → NA) was added at the same time as a
new rule not present in the Week 4 lock. Neither occurs in the current dataset
(0 rows each), so neither changed any reported figure; both are retained for
the fallback dataset.

### 2.3 Comparison window alignment

| | |
|---|---|
| Specified (Week 4) | `[-14, -1]`, ending the day before the assessment |
| Implemented | `[-13, 0]`, including the assessment day |
| Status | Corrected |

`loc_dist_ep_0` is a full-day (00:00–23:59) aggregate. Including the
assessment day places behaviour recorded *after* the PHQ-4 response into the
predictor, reversing the temporal ordering the design depends on. The
specification was set in Week 4 in direct response to this question from the
Data Pipeline Lead; the implementation did not match the answer given.

The lag is now a named constant (`ALIGN_WINDOW_LAG_DAYS = 1`), so the
pre-correction specification can be reproduced by setting it to 0.

### 2.4 Order of operations in the predictor transform

| | |
|---|---|
| Specified (Week 4) | `log(mean(clean daily values) + 1000)` |
| Implemented | `mean(log(clean daily value + 1000))` |
| Status | Corrected |

This is the deviation that materially changed the estimate.

`mean(log(x))` and `log(mean(x))` are different quantities for any
non-degenerate distribution (Jensen's inequality), and the gap is large for a
right-skewed variable such as daily GPS displacement. The implemented form is
a geometric-mean-based measure: log-compressing each day before averaging
suppresses the contribution of high-mobility days, so a week containing a long
trip moves the predictor far less than the arithmetic mean would. The reduced
predictor spread inflated the fitted slope.

The order of operations had been specified explicitly in Week 4 precisely
because the two forms diverge. The valid-day count was correctly derived from
the cleaned (non-log) column, so the filtering behaved as specified while the
values did not — which is why the deviation was not visible from occasion
counts alone.

The `<value_col>_log` column is retained for diagnostics but the module
docstring now states that it must not be aggregated over a window. Both the
within-person and between-person (Mundlak) terms derive from the same
corrected predictor, so the decomposition remains internally consistent.

### 2.5 Cumulative effect on the within-person estimate

| Configuration | β₁ | Change |
|---|---|---|
| 8 h gate, lag 0, mean(log) | −0.365 | — |
| 12 h gate, lag 0, mean(log) | −0.383 | +4.9% |
| 12 h gate, lag 1, mean(log) | −0.374 | −2.3% |
| 12 h gate, lag 1, log(mean) | **−0.248** | **−33.7%** |

Corrections 2.2 and 2.3 changed the estimate very little. They were made
because the implementation did not match a locked decision, and because the
temporal ordering was invalid — not because of their numerical effect.
Correction 2.4 accounts for essentially all of the movement.

The direction of the relationship and its significance are unchanged
throughout. The corrected effect is smaller, and is the better-specified
estimate: the earlier figures were inflated by the compressed predictor.

The three intermediate configurations predate the per-run output directory
scheme, so only the final row is reproducible from a retained run directory.
Re-running the cascade requires setting `QUALITY_THRESHOLD_HOURS`,
`ALIGN_WINDOW_LAG_DAYS` and the transform order back to the earlier values.

### 2.6 A fourth defect, in the verification tool

The independent re-implementation used for reconciliation
(`tools/reconcile_occasions.py`) initially returned 28,326 occasions against
the pipeline's 28,337. All 11 differing occasions were traced to a boundary
condition in the tool, not the pipeline: it rebuilt each participant's daily
index over their sensing range only, so EMA responses falling 2–8 days after a
participant's final sensing day had no corresponding row and were scored as
zero valid days, despite having 7–13 valid days inside their window. The
symmetric defect at the start of the observation period was corrected at the
same time although it does not occur in this dataset.

After correction, the two implementations agree on all 28,337 occasions with
zero differences in either direction.

This is recorded because it demonstrates the reconciliation method working: an
aggregate comparison would have treated a 0.04% gap as noise, while the
key-level comparison isolated eleven occasions sharing one specific structural
cause.

---

## 3. Results on the real dataset (`DATA5702/` copy)

### 3.1 Cleaning

216,065 daily observations; **74.65%** valid after the 12 h quality gate,
missing-quality gate, implausibility filter (`> 500 km/day`), and per-person
1st–99th percentile winsorisation.

### 3.2 Participant and occasion denominators

The three participant counts below are successive stages of one filter chain,
not inconsistent figures.

| Stage | N |
|---|---|
| Participants in the dataset | 220 |
| With at least one EMA occasion (cold-start evaluation set) | 218 |
| Passing the occasion-validity gate | 214 |
| Passing `MIN_OCCASIONS_PER_PERSON >= 3` (model frame) | 213 |

The Data Pipeline Lead's figures stop at 214; the minimum-occasions filter is
specific to the model frame.

The same chain at the occasion level accounts for the 807-occasion gap between
the gate-passing count and the model frame:

| Stage | Occasions | Lost |
|---|---|---|
| Passing the occasion-validity gate | 28,337 | — |
| With a lag-1 predictor available | 27,532 | 805 |
| Entering the model frame (`>= 3` occasions per person) | 27,530 | 2 |

The 805 is structural rather than a data-quality loss: every participant's
first EMA occasion has no preceding occasion to supply a lag-1 predictor, and
the lag-1 term sits in the same model formula, so those occasions are dropped
listwise. The remaining 2 occasions belong to the single participant who falls
below the three-occasion model-entry minimum.

### 3.3 Model fit

213 participants, **28,337** occasions passing the occasion-validity gate,
**27,530** entering the model frame. Random-intercept + random-slope model
converged (no fallback needed).

- Within-person effect (`log distance` → PHQ-4 total):
  **β₁ = −0.248, 95% CI [−0.315, −0.182], p < 0.001**
- Lag-1 term: **β = −0.040, 95% CI [−0.075, −0.004]** — same direction, roughly
  one sixth the magnitude. Secondary/sensitivity only, not part of the
  confirmatory claim.
- Time in study: **β = 0.007 PHQ-4 points per week, p < 0.001** — a small
  upward drift over a participant's time in the study, carried as a covariate
  so it is not absorbed into the mobility effect.
- Direction: within-person periods of *higher* mobility are associated with
  *lower* PHQ-4 (less distress) for the average person — consistent with prior
  mobility/wellbeing literature. This is an association, not a causal claim.
- Magnitude: on the `log(mean + 1000)` scale, roughly a 2.7× increase in mean
  daily distance corresponds to a 0.25-point decrease on the 0–12 PHQ-4 scale.
  The relationship is statistically clear and practically small. Conversational
  output must be worded accordingly.

### 3.4 Agreement with an independently computed estimate

After correction, the pipeline reproduces the Data Pipeline Lead's occasion
count exactly, and the two independent estimates agree.

| Source | Occasions | β₁ | 95% CI |
|---|---|---|---|
| Data Pipeline Lead, 1st–99th winsorisation | 28,337 | −0.277 | [−0.337, −0.217] |
| This pipeline, corrected | 28,337 | −0.248 | [−0.315, −0.182] |

The intervals overlap substantially and the difference in point estimates is
approximately one quarter of the confidence interval width. The residual
difference is attributable to model specification: the confirmatory model
carries person-level random slopes and Mundlak decomposition, while the
comparison figure comes from a simpler sensitivity specification. No attempt
was made to reconcile the two estimates further, as the specifications are
intentionally different.

### 3.5 Multiple-comparison family definition

Week 4 defined a family for the user-facing weekly report (one person × up to
three features). It did not define a family for the cohort-level per-person
analysis (one feature × 213 people). Because that second family was
undefined, each participant's test was being treated as its own family of one,
which makes both Holm and BH correction mathematically identical to the raw
p-value — the correction was not doing anything.

The cohort-level family is now defined as the 213 participants holding a
per-person slope for this feature. This is a post-hoc decision, made after
seeing the family-of-1 results, and is recorded as such.

**Benjamini–Hochberg FDR across 213 is adopted for the reported
classification.** The question being answered is what proportion of the
participants labelled as having evidence are false positives, which is exactly
the quantity FDR controls. Holm–Bonferroni is retained as a sensitivity
analysis: it is a family-wise error rate method, appropriate where a single
false positive is unacceptable, and at this family size it is too severe to be
informative (median adjusted p = 1.0, with 161 of 213 clipped to 1.0).

| Label | BH × 213 (reported) | Holm × 213 (sensitivity) | Family-of-1 (superseded) |
|---|---|---|---|
| strong | **28** | 24 | 34 |
| moderate | **36** | 5 | 45 |
| weak | **10** | 3 | 9 |
| insufficient | **139** | 181 | 125 |

No participant was promoted from `insufficient` under either correction, which
is the expected one-directional behaviour. That 30 of 45 `moderate`
classifications survive BH correction indicates the signal is not an artefact
of the uncorrected threshold. The most conservative correction still retains
24 `strong` classifications.

### 3.6 Evidence-strength decision rule (as implemented)

Recorded here as a table because the rule has been restated informally more
than once during the week and the restatements have not always matched the
code. The implementation is authoritative.

Conditions are evaluated top-down; the first tier whose conditions are all met
is assigned.

| Tier | q | Standardised effect | Min occasions | Lag consistency |
|---|---|---|---|---|
| strong | < 0.01 | ≥ 0.20 | ≥ 12 | lag-0 and lag-1 signs agree |
| moderate | < 0.05 | ≥ 0.10 | ≥ 8 | — |
| weak | < 0.10 | ≥ 0.10 | ≥ 8 | — |
| insufficient | otherwise | | | |

Standardised effect is `|slope_i| × predictor_sd / outcome_sd`, computed from
the fitted model, so it rescales automatically when the predictor
transformation changes.

A consequence worth stating explicitly: a participant whose q-value clears the
`strong` threshold but whose standardised effect is below 0.10 falls through
all three tiers to `insufficient`. There is no intermediate label for
"significant but too small to matter", which is deliberate.

### 3.7 User-facing collapse to two values

For the evidence contract passed to the SLM, the four internal tiers collapse
to two:

| Internal | User-facing | N |
|---|---|---|
| strong, moderate | `evidence_available` (hedged statement permitted) | **64** |
| weak, insufficient | `no_claim` (no relationship statement) | **149** |

This is a post-hoc decision. The four-tier scheme remains in place for
reporting and analysis; only the user-facing output is collapsed.

The rationale is the instability documented in section 5.3: 26 participants sit
in the `[0.15, 0.20)` standardised-effect band, directly below the
strong/moderate boundary, and correcting the predictor transformation alone
moved **68 of 213** classifications, of which **34 crossed the moderate/strong
boundary in a single cohort-wide switch**. If the same person can be `strong`
or `moderate` depending on a defensible alternative specification, there is no
basis for the chatbot to distinguish the two in what it says. The thresholds
themselves are unchanged, so this is not a departure from pre-registration.

The collapse absorbs the instability it was intended to absorb. Under the
transformation-order correction, 68 of 213 four-tier labels changed, but only
26 crossed the two-value boundary. The 34-participant cohort-wide switch
between `strong` and `moderate` is entirely absorbed, because both map to
`evidence_available`.

Measured comparison, per-person tables and a re-run script:
`analysis/output/sensitivity/transform_order/`.

Note that `weak` was already defined as exploratory-record-only and never
surfaced to users, so it groups with `insufficient` here without any change in
behaviour.

### 3.7.1 Evidence contract: permitted output by state × evidence

Cold-start state (§3.8) and evidence strength (§3.6) answer two independent
questions about the same occasion. What may be said is the grid, not either
axis alone.

Within State C there is a third axis: whether this occasion has a
recent-vs-baseline deviation to quote at all. State C unlocks the comparison
*framing*; it does not guarantee there is a *number*.

| Cold-start state | Evidence | Deviation | Permitted output | Occasions | % of all |
|---|---|---|---|---|---|
| A | any | — | templated message only; **no numbers** | 480 | 1.4% |
| B | any | — | descriptive only; **no comparison, no relationship claim** | 11,309 | 32.0% |
| C | `no_claim` | yes | comparison permitted; **relationship claim forbidden** | **14,588** | **41.3%** |
| C | `no_claim` | **no** | comparison framing permitted, **but no deviation value this occasion**; relationship claim forbidden | 517 | 1.5% |
| C | `evidence_available` | yes | comparison permitted; **hedged relationship claim permitted** | 8,209 | 23.2% |
| C | `evidence_available` | **no** | comparison framing permitted, **but no deviation value this occasion**; hedged relationship claim permitted | 245 | 0.7% |

**762 State C occasions (3.2% of State C, 170 participants) have no computable
deviation**: 741 because the recency window holds fewer than 7 valid days, 22
because the baseline SD is zero (a participant whose entire baseline window is
identical, in practice all zero-travel days); one occasion is both. The
relationship claim is unaffected — it rests on the person's fitted slope, not
on this occasion's deviation — so the `evidence_available` row keeps its hedged
claim even with no number to attach it to.

"Comparison is available in principle, but not this time" is a real state
affecting most participants at some point, not a sensor-failure edge case. What
the chatbot should say in it is Richard's call; the point here is that the
templates need a branch for it.

State A and State B are unconditional on evidence strength. A participant can
hold a strong per-person slope and still be in State A at an early occasion —
105 occasions are exactly that — and the claim is still not permitted, because
it would be about a period the system cannot describe.

**`A + evidence_available` (105 occasions, 59 participants) is an artefact of
retrospective analysis.** Evidence strength is estimated from each
participant's full record, while cold-start state is judged from the data
available up to the occasion being evaluated. The same participant's earliest
occasions can therefore be State A while an evidence label estimated from their
whole history reads `evidence_available`.

In live operation the combination does not arise: a new user has no history, so
the per-person slope cannot be estimated either and the evidence label is
unavailable rather than `evidence_available`. The contract still specifies it,
because the ordering must be unambiguous — **State A takes precedence, and the
output is the templated response regardless of evidence strength.**

**`C + no_claim` is the largest single cell at 42.7% of all occasions, and
64.1% of State C occasions.** "You may compare, but you may not say why" is the
normal operating state, not a degraded fallback. The pipeline now writes the
full per-occasion grid to `state_evidence_combinations.csv` and
`state_evidence_combinations_4tier.csv` on every run; previously the two axes
were written to separate files with nothing reconciling them.

### 3.8 Cold-start state

State is now evaluated per EMA occasion rather than once per participant. A
participant moves between states as history accrues and as data quality
varies, so a per-participant summary is not well-formed.

**Primary figure — all EMA occasions (35,348 occasions, 218 participants):**

| State | Occasions | Share |
|---|---|---|
| A (templated response only) | 480 | 1.4% |
| B (descriptive only, no comparison) | 11,309 | 32.0% |
| C (comparative statements permitted) | 23,559 | 66.7% |

**Secondary — occasions passing the occasion-validity gate (28,337, 214
participants):** State A 0, State B 5,519, State C 22,818.

The secondary figure is included only for consistency checking against the
model frame. It should not be read as a cold-start policy result: passing the
occasion-validity gate requires at least 7 valid days inside the 14-day
window, which is nearly mutually exclusive with the State A condition, so
State A is structurally absent from it. Reporting on that basis would exclude
precisely the situation the cold-start policy exists to handle.

**Three further measures:**

- Participants reaching State C at least once: **212 / 218 (97.2%)**
- Of participants who ever reach State C, the mean share of their subsequent
  occasions that remained in State C: **69.3%**
- Of the 22,797 occasions where a recent-vs-baseline deviation is computable,
  **3,569 (15.7%)** show a meaningful deviation (`|z| >= 1.0`).

The second figure is the operationally important one. Almost every
participant eventually qualifies for comparative statements, but having
qualified once, roughly **30% of their later occasions fall back out of State
C**. Under the previous "qualify once, keep it permanently" implementation,
those occasions would have received comparative statements against a stale
baseline. This is the empirical justification for the rolling evaluation.

The third figure bounds how often the system has anything to compare *about*.
Reaching State C establishes that a comparison is statistically permitted, not
that there is a change worth reporting: on roughly five occasions in six the
participant is within their usual range, and the correct output is "in line
with your usual range" rather than a deviation statement. A conversational
design that treats State C as a cue to report a change will manufacture one
five times out of six.

**Relation to the Data Pipeline Lead's baseline figures.** The Data Pipeline
Lead reports **213 of 218 participants (97.7%)** with at least one occasion
meeting the `[-42, -15]` baseline sufficiency rule. This reconciles exactly with
the figures above: 213 participants have at least one occasion clearing this
pipeline's baseline gate, and 212 of them (97.2%) go on to reach State C.

State C is strictly the narrower set on occasions too, because `comparative_ok`
demands **≥ 28 calendar days of history since the participant's first sensing
day** in addition to baseline sufficiency, which the baseline-window rule alone
does not test. Applying this pipeline's own gate (≥ 20 valid baseline days
**and** ≥ 3 EMAs in the window) gives 23,801 occasions, of which 242 are held
at State B by exactly that calendar-span requirement, leaving 23,559.

The two sides' **occasion** counts are not quoted here, because the definitional
difference between them has not been identified and quoting a number whose rule
is unknown would be misleading. *(For a later check: this pipeline's closest
analogues are 25,200 occasions under a valid-days-only rule and 23,801 under
valid days plus EMA count. Resolving this needs the key-level reconciliation
used for the occasion gate in §5, not a comparison of totals.)*

*(Note: State C does **not** require the recency window to clear its ≥ 7
valid-day gate — 741 State C occasions have fewer than 7 valid recency days.
That gate governs only whether a deviation z-score is computed, not the state
itself.)*

The 66.7% State C share should not be read as a forecast of live behaviour.
This dataset carries several hundred to over a thousand days of history per
participant, so State A and State B concentrate in each participant's earliest
weeks and are diluted across a long tail of later occasions. A deployed system
with continuing new-user intake would show a substantially higher State B
share.

Full numbers: `analysis/output/latest/week5_run_report.md`.

---

## 4. Decisions closed this week

**Week 4 open item #4 (7-day user-facing recency window vs 14-day model
alignment window) — resolved in favour of a single 14-day window.**

The two windows were separate concepts: the chatbot would describe a 7-day
deviation while the evidence strength attached to that statement was estimated
on 14-day means. Presenting a quantity computed over one period alongside a
relationship estimated over another is not a claim the analysis supports.
Standardising on 14 days removes the mismatch, aligns the behavioural period
with the PHQ-4 instrument's own two-week reference period, and yields a more
stable mean. `RECENCY_WINDOW_DAYS` is withdrawn.

**Winsorisation method — per-person 1st–99th percentile confirmed.**

The Data Pipeline Lead's comparison showed 1st–99th moving β₁ by 2.5% from the
no-winsorisation baseline, against 93% for median ± 5 MAD. Daily GPS
displacement is heavily right-skewed with most days clustered at a few
kilometres, so the MAD is very small and the resulting ceiling is low;
compressing the predictor's range while outcome variation is unchanged
inflates the slope mechanically.

The cause is visible on the input side, not only in the fitted slope:

| Rule | Day-values modified | Median participant cap |
|---|---|---|
| Per-person 1st–99th | 1,920 of 161,283 (**1.19%**) | ≈ 358 km/day |
| Median ± 5 MAD | 32,348 of 161,283 (**20.06%**) | **26.5 km/day** |

A rule that rewrites one day in five, capping at a distance routinely exceeded
by ordinary commuting, is reshaping the variable rather than trimming its tail.
This is the mechanism behind the 93% shift in β₁: the inflated slope is a
signature of over-truncation, not of a stronger relationship.

*(Figures supplied by the Data Pipeline Lead.)*

**Cohort-level multiple-comparison family — defined as 213 (section 3.5).**

**User-facing evidence output — collapsed to two values (section 3.7).**

---

## 5. Known limitations and open items

### 5.1 Carried from Week 4, unchanged

1. Per-person significance approximates `Var(slope_i)` as
   `Var(beta1_hat) + Var(u1_i)`, treating the fixed-effect estimator and the
   BLUP as independent (their true covariance isn't directly exposed by
   `statsmodels MixedLM`). Should be cross-checked against R `lme4`/`lmerTest`
   (the doc's primary estimator, section 1.5) before being reported as final.
2. **Lag-1 sign consistency is evaluated cohort-wide, and the `strong` tier
   turns on it.** The `strong` threshold requires the lag-0 and lag-1 signs to
   agree, but the comparison uses the population-level fixed effects, not
   per-person lag-1 BLUPs. One coefficient therefore opens or closes the tier
   for every participant simultaneously.

   Section 5.3 makes the consequence concrete. Correcting the transform order
   alone moved the lag-1 fixed effect from **+0.0098, 95% CI [−0.0421,
   +0.0618]** (p = 0.711) to **−0.0397, 95% CI [−0.0754, −0.0040]** (p =
   0.029). The sign flipped, the consistency check went from failing to
   passing, and the number of `strong` participants went from **0 to 34**.
   No individual participant's data changed.

   The lag-1 coefficient is small in absolute terms and its sign cannot be
   treated as settled: under the pre-correction specification the interval
   straddles zero comfortably, and under the current one it clears zero only
   marginally. So the `strong` label does not rest on per-person evidence
   alone — it rests additionally on a single sign shared across the whole
   cohort, estimated from a term that is barely distinguishable from zero.

   Moving to per-person lag-1 BLUPs (a 3-random-effect model: intercept,
   slope_lag0, slope_lag1) is therefore **not a precision improvement but a
   classification-stability issue**, and should be prioritised as such.
3. AR(1) residual structure is not fit (statsmodels limitation, already flagged
   in the Week 4 doc, section 1.7); an independence working correlation is
   used instead.
4. COVID-era / term-phase fixed effect not yet included (Week 4 doc open item
   5, still pending a team decision).

### 5.2 Identified during this week's review

5. **Winsorisation look-ahead.** Per-person 1st–99th percentile bounds are
   computed from each participant's full history, so a given day's cleaned
   value depends in part on data recorded after it. This is standard for
   retrospective analysis but has no deployment equivalent; a live system
   would require an expanding-window formulation.
6. **Winsorisation minimum.** Participants with fewer than 5 valid days are
   left un-winsorised, as a percentile estimated from fewer points is not
   stable.
7. **Pre-computed source feature.** `loc_dist_ep_0` is supplied already
   aggregated, so the (0,0) "null island" hypothesis for extreme daily values
   cannot be checked against raw coordinates.
8. **Family size is feature-specific.** The 213-participant family is defined
   for this single feature. Once additional Tier-1 features are modelled, the
   family must be redefined across person × feature rather than person alone.
   **[Confirmed 2026-09-14, now that `unlock_num_ep_0` is actually modelled]**
   The two Tier-1 features do not share a participant set:
   `loc_dist_ep_0`'s model frame has 214 participants, `unlock_num_ep_0`'s has
   216, and the former is a strict subset of the latter (`only_in_loc_dist_ep_0`
   is empty; exactly 2 participants are `unlock_num_ep_0`-only). Traced to
   source: both of those 2 participants fail GPS's `quality_loc >= 12h` gate
   almost completely (0/356 and 3/1141 valid-quality days; one has zero
   non-null raw `loc_dist_ep_0` values at all), while their unlock coverage is
   complete, since unlock has no comparable quality field to lose them on.
   **This is a limitation in its own right, not only a family-size mechanic:**
   there exist real participants for whom a defensible "for you, X has tended
   to coincide with Y" statement is possible via `unlock_num_ep_0` but not via
   `loc_dist_ep_0` — their GPS history is too sparse to ever enter that
   feature's model frame, independent of how much unlock or EMA history they
   accumulate. Any per-person relationship statement must be evaluated as a
   per-feature question ("does *this* feature have anything to say about
   *this* person"), not inferred from one feature's cold-start state to the
   other's.
9. **Code is not under version control** *(as of when this was written — see
   the Section 1 correction note for what changed since).* At the time this
   analysis was run, Moe's `analysis/` directory was not a git repository, so
   `run_manifest.json` recorded a null commit hash and the per-PR review and
   automated gates defined in the Build Plan did not apply to it. This
   repository's own `analysis/` folder is now under version control (the
   original modules are archived at `analysis/archive/`), but the specific
   run that produced Section 3's numbers still is not reproducible from a
   committed commit hash — it predates that archiving and was never itself
   committed.
10. **Two model-entry rules existed only in code.** The `week_in_study_it`
    time-trend covariate is part of the fitted confirmatory formula, and
    `MIN_OCCASIONS_PER_PERSON = 3` governs model entry (distinct from the
    8/12-occasion evidence-strength gates). Neither appeared in the Week 4
    deliverable or in the pre-registration. Both are now written into
    `preregistration.md`, but they need explicit sign-off rather than
    documentation alone — the confirmatory model formula is part of what is
    being frozen.
11. **Convergence fallback removes all per-person statements.** If the
    random-slope model fails to converge, the fallback to random-intercept-only
    leaves no per-person slope variance, so `slope_se` and `slope_p` are
    undefined, every participant classifies as `insufficient`, and the system
    emits no historical-relationship statements at all. The model converged on
    this dataset so the path was never taken, but it is reachable on the
    fallback dataset. The behaviour needs documenting as a defined degradation
    mode rather than left as an implicit consequence. **[Updated 2026-09-13]**
    This item is about the convergence-fallback edge case specifically — the
    broader fact that the `backend/statistics/evidence.py` port left
    `slope_se`/`slope_p` `None` in *every* case (not just this fallback) is
    covered separately, and now resolved via bootstrap, in section 5.4.
12. **Implausibility-cutoff sensitivity not run.** The 250 km and 1,000 km
    re-runs are pre-registered in the Week 4 lock but have not been executed.
13. **The Mundlak person-mean is computed over a wider set than the model
    fits.** `x_bar_i` comes from the occasion-validity-gate-passing set (214
    participants, 28,337 occasions), not the model frame (213 / 27,530).
    `add_within_between()` runs before `build_model_frame()`, so it does not
    see the lag-1 listwise deletion or the `MIN_OCCASIONS_PER_PERSON` filter.
    The one excluded participant therefore contributes to the grand mean that
    every other participant's between-person term is measured against.

    Re-running with `x_bar_i` computed from the model frame instead: β₁ is
    −0.248 either way, the 95% CI differs in the third decimal place
    ([−0.3146, −0.1816] vs [−0.3145, −0.1815]), and **0 of 213 per-person
    labels change**. More observations give a more stable person-mean estimate,
    so the current behaviour is kept.
14. **`baseline_sd` carries a selection effect, so deviation flagging is not
    uniform across participants.** Participants with complete baseline windows
    have systematically smaller baseline standard deviations — mean 39,396 at
    28 valid days, against 52,000–57,600 across the 20–27 day bands. This is
    not an estimation artefact: the ratio-based noise indicator (each
    occasion's SD over that participant's own mean SD) is flat across bands,
    0.760 at 20–21 days against 0.693 at 28. It appears instead to reflect a
    real association between data completeness and behavioural regularity.

    Because the deviation z-score divides by this standard deviation,
    participants with complete data clear `|z| >= 1.0` more often — 18.6% of
    occasions in the 28-day band against 10.3% at 20–21 days. Whether a
    participant is told "this is unusual for you" therefore depends in part on
    how complete their sensing record is, not only on their behaviour.
15. **Zero-unlock days cannot be distinguished from screen-sensing outages.**
    They are retained as values rather than recoded to NA. CES exposes quality
    fields for activity, audio, light and location only; there is no screen or
    phone uptime field, so there is no way to tell a genuine zero from a day on
    which screen sensing was not running. Unlike an impossible value such as a
    45-hour day, a true zero cannot be ruled out.

    Zero days number 3,736 of 216,065 participant-days (1.73%), affecting 215
    of 220 participants. The distribution is skewed: a median of 12 zero days
    among affected participants against a maximum of 231. Participants with
    many zero days may therefore carry a downward-biased personal mean for
    device engagement. Whether high-zero participants need a covariate or an
    exclusion rule is a Week 6 decision.

    *(Figures supplied by the Data Pipeline Lead.)*

### 5.3 Classification stability

Per-person classifications are sensitive to specification choices at a level
that should be stated explicitly rather than discovered later.

- 29 of 213 participants have p-values in `[0.05, 0.20)` — just outside the
  `moderate` and `weak` boundaries.
- 59 of 213 have standardised effects in `[0.10, 0.20)` — above the `weak`
  floor but below the `strong` threshold.
- Correcting the predictor transformation alone, with no change to the sample,
  the occasion set or the model formula, moved **68 of 213 classifications
  (31.9%)** — 43 toward a stronger label, 25 toward a weaker one.

Measured by re-running both transform orders against the current production
configuration; per-person tables, transition matrices and a re-run script are
in `analysis/output/sensitivity/transform_order/`. The harness reproduces the
retained family-of-1 run exactly (0 label mismatches, 0.0 maximum slope
difference), which is what validates the comparison.

**One qualification on that 68.** It is not 68 independent boundary crossings.
Under the pre-correction transform the lag-1 population fixed effect is
**+0.0098** against a lag-0 effect of −0.3742; the signs disagree, and because
lag consistency is currently evaluated at the population level (limitation 2),
the `strong` tier is closed to the entire cohort at once — no participant is
`strong` under that configuration. Correcting the transform flips the lag-1
effect to −0.0397, the signs agree, and the tier opens. 34 of the 68 changes
are that single switch; the other 34 are genuine per-person movements across
the q and effect-size thresholds.

That makes the `strong` label doubly fragile: it depends on a cohort-wide
lag-sign term that is itself sensitive to specification, and on a per-person
threshold with 26 participants sitting just below it. Both point the same way —
`strong` and `moderate` should not be distinguished in what the system says.

Roughly a quarter to a third of the cohort sits near one boundary or another.
Individual labels should therefore be treated as indicative rather than
determinate, which is the direct motivation for the two-value user-facing
collapse in section 3.7.

### 5.4 Per-person SE via bootstrap and cross-method intersection (backend port, added 2026-09-13)

**[POST-HOC.]** `backend/statistics/evidence.py`'s per-person significance test
had been left with `slope_se`/`slope_p` always `None` — the R `nlme` engine that
module's AR(1) fit runs on (see section 4/section 3.4 of the correction log for
that port) has no `lme4::condVar`-equivalent way to extract a per-person BLUP
variance, and a direct check confirmed `nlme::simulate.lme` refuses models with
a `corStruct` outright, so a delta-method or `nlme`-native fix was not
available. Two bootstrap SE estimators were implemented instead
(`backend/statistics/bootstrap.py`), compared against each other on the real
dataset (B=500 each), and found to disagree badly enough that **neither is used
alone** — only their intersection is.

**The two designs:**

- **Parametric.** Resimulate `y` from the real fit's own generative parameters
  (fixed effects, the random-effects covariance `D`, the AR(1) coefficient,
  residual `sigma`) — a fresh random-effect draw and a fresh AR(1) residual
  series for every person, every replicate — then refit and collect the
  resimulated per-person slope.
- **Cluster (case resampling).** Resample participants with replacement,
  keeping each resampled copy's real observed data unchanged, then refit and
  collect the per-person slope. A participant drawn more than once is
  relabelled per copy so the model treats repeats as distinct clusters.

**They are not simply differently scaled — they are sensitive to opposite
things.** On the real dataset:

- Parametric SE correlates **positively** with a person's occasion count
  (Spearman ρ ≈ **+0.81**): more occasions means less BLUP shrinkage toward the
  population mean, so more of the true random-slope variance passes through
  into how much the resimulated `slope_i` varies from replicate to replicate.
- Cluster SE correlates **negatively** with occasion count (ρ ≈ **−0.33**):
  more of a participant's own real, unchanging data makes their contribution
  more stable regardless of who else gets resampled alongside them — the
  ordinary "more data, smaller SE" pattern.
- Because the two are driven by the same variable in opposite directions,
  their **per-person SE rankings are themselves negatively correlated**
  (Spearman ρ ≈ **−0.397**, p ≈ 1.7×10⁻⁹) — not a constant rescaling. The SE
  ratio (parametric ÷ cluster) ranges **1.05× to 29.5×** across participants
  (mean **7.85×**), not one fixed factor.

**Why neither survives alone.** Cluster's SE is small specifically because it
never re-draws a selected participant's own observed trajectory — only who
else is resampled alongside them — so it does not encode the uncertainty from
that participant's data having come out differently, which is exactly what a
person-level SE needs to capture; it understates the quantity the evidence-
strength test actually needs. Parametric's SE reflects genuine generative
uncertainty but is dominated by an occasion-count/shrinkage effect, a
different quantity from "how uncertain is this person's estimated slope."

**Decision: `label_intersection` — `evidence_available` only where both
methods independently agree** (`backend.statistics.evidence
.intersect_bootstrap_evidence`). Confirmed on the real dataset (B=500 both
methods):

| | cluster: `evidence_available` | cluster: `no_claim` |
|---|---|---|
| **parametric: `evidence_available`** | 23 | 0 |
| **parametric: `no_claim`** | 28 | 163 |

Agreement rate **86.9%** (186/214). The disagreement is **one-directional**:
every participant parametric calls `evidence_available` is also called
`evidence_available` by cluster (zero counter-examples); cluster additionally
calls **28 more** participants `evidence_available` that parametric does not —
consistent with cluster's smaller, less trustworthy-alone SE being the more
permissive side. Intersection yields **23 of 214** participants as
`evidence_available` — numerically equal to parametric's own set here, though
the *rule* is "both agree," not "defer to parametric": a dataset where
cluster's set were instead a strict subset of parametric's would produce a
different intersection than either parent set alone.

**Stability check (requested before considering B=1000):** the 500 iterations
were split by `iteration_index` into two halves (0–249, 250–499) and the
intersection recomputed independently on each. Half A and half B each yield
**24** participants (not 23) — each half agrees with the full-B=500 23-person
set entirely, plus **one additional, different borderline participant per
half** (Jaccard(half A, full) = Jaccard(half B, full) = 0.958; Jaccard(half A,
half B) = 0.92). The full B=500 set is a strict subset of both halves — more
replicates resolved two borderline cases toward `no_claim` that a smaller,
noisier B had let through. This is a reasonably stable result and does not, on
its own, argue for B=1000: the picture that would change with more replicates
(further tightening around 1-2 more borderline participants) is a small,
diminishing-returns correction, not evidence that 23 is unreliable.

**This is a post-hoc decision, not a pre-registered one** — Week 4's
pre-registration specified BH-FDR correction over a single per-person test; it
did not anticipate reconciling two different bootstrap SE estimators, because
the SE gap itself was not foreseen as needing a bootstrap solution. Recorded in
the same register as the cohort-level family size (213, section 3.5) and the
binary user-facing collapse (section 3.7) — see also
`docs/statistics/preregistration.md` section 7's post-hoc log.

**`strong` remains unreachable** under either method or the intersection, for
the same reason already noted in section 3.6/5.1: `classify_evidence_strength`
requires an explicit lag-0/lag-1 sign-consistency flag that no caller
currently supplies (the lag-1 term is out of this module's scope). All 23
intersection-positive participants are therefore `moderate`, not `strong`, by
construction — this is the existing, already-documented scope gap, not a new
one introduced by bootstrapping.

Parametric-only and cluster-only classifications remain available as
standalone sensitivity views (`reclassify_family213`'s own `label_bh`/
`label_holm` per method) — the intersection is an addition to the per-person
table, not a replacement of either single-method view.

---

## 6. Handover to other workstreams

Four items require action from other leads.

| To | Item |
|---|---|
| SLM Integration (Richard), Conversational Interface (Sheng) | **State C is not permanent.** Under rolling evaluation a participant moves C → B → C. Empirically, 30.7% of occasions after a participant's first State C fall back out of it. Templates and UI states must handle a state that changes, not a one-time unlock. |
| SLM Integration (Richard), Conversational Interface (Sheng) | **State C does not mean there is a change to report.** Only 15.7% of occasions with a computable deviation show one meaningful enough to state (`\|z\| >= 1.0`). On roughly five occasions in six the correct output is "in line with your usual range". Templates must make the no-change case a first-class response, not a fallback. |
| SLM Integration (Richard), Conversational Interface (Sheng) | **State C does not mean a relationship may be stated.** `C + no_claim` is the largest cell in the evidence contract (§3.7.1): 42.7% of all occasions, and **64.1% of State C occasions**. The normal state is "comparison permitted, relationship claim forbidden" — a template set that pairs every comparison with an explanation will be out of contract on roughly two thirds of State C occasions. |
| SLM Integration (Richard), Conversational Interface (Sheng) | **State C does not guarantee a deviation number either.** 762 State C occasions (3.2%, 170 participants) have no computable deviation — the comparison framing is unlocked but there is nothing to quote (§3.7.1). Templates need a distinct branch for "comparison is available in principle, but not this time"; falling back to State B wording would be wrong, since the participant does have a usable baseline. |
| SLM Integration (Richard), Conversational Interface (Sheng) | **User-facing wording changes from "this week" to "the past two weeks"** following the 14-day unification (section 4). |
| SLM Integration (Richard) | **Evidence strength is surfaced as two values, not four** (section 3.7). Templates distinguishing `strong` from `moderate` are not required. |
| Documentation & Report (Honglin), Integration & QA (Priyansh) | **The analysis code is not in the GitHub repository** and is not under version control (limitation 9). |

---

## 7. Tier-1 feature list (confirmed)

**[CORRECTED 2026-09-13]** This section previously described a 3-feature list
(`loc_dist_ep_0` + `loc_home_dur` + `unlock_num_ep_0`) as "proposed, pending
team sign-off." That was already stale when written: the team's actual hard
cap, set in `Weekly_Plan.md` Week 4, is **maximum 2 cross-platform features
unless a third genuinely meets the same standard** — not 3 — and the team had
already converged on a 2-feature list before this section's "pending" language
was drafted. Corrected below rather than silently rewritten; the original
construct-overlap analysis is kept, relabelled, since it answers a real
question even though it turned out not to be the one the sign-off needed.

- **Tier 1 is confirmed as two features: `loc_dist_ep_0` + `unlock_num_ep_0`.**
  All 8 team members agreed on this 2026-08-26 (verbal record over the team
  WhatsApp group) — see `feature-list-signoff.md` (Integration/QA sign-off)
  and `freeze-decision.md` (the underlying team agreement this sign-off is
  based on, recorded 2026-09-05). Consistent with the feature set already
  described as locked in CS-62 Project Status Checking 1 (client Tianyi
  Zhang, 30 Aug 2026 meeting).
- `loc_dist_ep_0` is a working reference implementation: real data, converged
  model, significant effect in the direction prior literature predicts,
  independently reconciled against a second implementation.
- The same pipeline generalises to `unlock_num_ep_0` (and to any future
  Tier-1 candidate) by swapping the value/quality columns and cleaning
  thresholds — no architecture change needed. `tools/reconcile_occasions.py`
  is retained so the same count reconciliation can be run on each.
- **Construct-overlap analysis below was run against the wrong candidate for
  what was actually decided, and does not bear on the confirmed Tier-1
  list.** It was checking whether `loc_dist_ep_0` and `loc_home_dur` measure
  the same underlying behaviour — `loc_home_dur` was never the feature the
  team actually added; `unlock_num_ep_0` was. The analysis was run without
  knowing the 2-feature cap (and the specific 2-feature choice) had already
  been agreed on 2026-08-26. Kept here as material for if/when a third
  feature is revisited, not as a finding about the current list: the
  within-person correlation between person-mean-centred `log(loc_dist)` and
  person-mean-centred `loc_home_dur` is **r = −0.2425** across 157,725 paired
  participant-days and 217 participants, well below the 0.6 threshold set for
  considering a substitution — i.e. if a third feature is ever added,
  `loc_home_dur` would not be disqualified by construct overlap with
  `loc_dist_ep_0` on this basis alone. Time spent away from home is not the
  same quantity as distance covered: a participant can spend a full day at a
  single non-home location while travelling almost nothing.

  *(Correlation supplied by the Data Pipeline Lead.)*
- Location entropy is **Tier 2**, not Tier 1, independent of the above: CES
  has no pre-computed entropy variable, and deriving it (Shannon entropy over
  per-cluster time shares) would need its own cleaning rules, sanity bounds
  and validation, none of which exist.
- **Two preregistration documents currently exist, not yet reconciled.**
  `docs/statistics/preregistration.md` (brought into this repository
  2026-09-13 — Moe Tanaka's actual original local 354-line file, with real
  provenance; it previously existed only as an uncommitted local copy — see
  its own migration note) now covers both confirmed features: `loc_dist_ep_0`
  (section 1.5) and `unlock_num_ep_0` (section 1.6, added at the same
  check-in — no quality gate, zeros retained, no log transform; see that
  section for the skew/kurtosis figures ruling the log transform out).
  Separately, `analysis/preregistration.md` (249 lines) was independently
  compiled by another contributor's session (Priyansh Khandelwal, 2026-09-12)
  from Moe's already-locked decisions, inside the now-archived `analysis/`
  directory — not a document she drafted herself, and not yet reconciled
  against the file above (see `CLAUDE.md`'s "Unreflected changes" for this
  flagged, unresolved duplication).
- Remaining open items: PHQ-4 total as sole primary outcome vs. co-primary
  subscales; COVID-era handling; sign-off on the two previously-undocumented
  model-entry rules (limitation 10).

---

*See `Week4_Statistical_Analysis_Deliverable.md` for the full locked-decision
rationale this builds on.*
