# Week 5 run report — loc_dist_ep_0 baseline/evidence vertical slice

Feature: `loc_dist_ep_0` | Outcome: PHQ-4 total | Alignment window: 14 days | Baseline: 28-day min / 56-day target.

## 1. Cleaning (section 1.4)
- 216,065 daily observations; 74.65% valid after quality-gate + implausibility-filter + winsorisation.

## 2. LMM fit (section 1.2)
- Participants in model frame: 213 | Occasions: 27,530
- Random-slope model converged
- beta1 (within-person x_within_it -> PHQ-4): -0.2481
- p (raw): 2.568e-13 | p (Holm, confirmatory family): 2.568e-13

## 3. Evidence-strength classification (section 7), per participant
Production (BH-FDR, exploratory family = all N participants):
- insufficient: 139
- moderate: 36
- strong: 28
- weak: 10


Sensitivity (Holm-Bonferroni, same family):
- insufficient: 181
- strong: 24
- moderate: 5
- weak: 3


Reference (legacy family-of-1, superseded by the BH version above):
- insufficient: 125
- moderate: 45
- strong: 34
- weak: 9


User-facing (2-value, evidence_model.to_user_facing_evidence() on the BH label; post-hoc collapse, see that function's docstring for the rationale):
- no_claim: 149
- evidence_available: 64


## 4. Cold-start state (sections 4-5), evaluated per EMA occasion
1. Occasion-level A/B/C breakdown (primary reported figure):
- State A: 480
- State B: 11309
- State C: 23559


2. Participants reaching State C at least once: 212/218 (97.2%)

3. Of participants who ever reach C, mean share of their occasions from the first C occasion onward that stayed C (didn't drop back to B): 69.3%

## 5. Known simplifications / open items for Wednesday Tier-1 meeting
- Lag-1 sign consistency (evidence-strength 'consistency' column) currently uses the population-level fixed-effect sign, not per-person lag-1 BLUPs — a 3-random-effect model (intercept, slope_lag0, slope_lag1) is the next extension.
- AR(1) residual structure (doc 1.2/1.3) is not available in statsmodels MixedLM; current fit uses an independence working correlation. R lme4/lmerTest remains the primary estimator per doc 1.5 and should be cross-checked before this is reported as final.
- COVID-era / term-phase fixed effects (beta5 in the full spec) are not yet included — open item #5 from the Week 4 doc, still pending a team decision.
- Feeds directly into the Wednesday Tier-1 proposal: this is the worked example for `loc_dist_ep_0`; the other 1-2 Tier-1 features reuse this same pipeline unchanged (only `VALUE_COL`/`QUALITY_COL` and any feature-specific cleaning thresholds differ).
- The per-person exploratory family (BH/Holm correction) is currently scoped to this one feature's N participants. Once multiple Tier-1 features exist, the family should batch each person's per-feature statements together (per doc section 2's "per-person weekly report" family), not just batch across participants for a single feature — this needs revisiting before a second feature is added.