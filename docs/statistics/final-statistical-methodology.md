# Final Statistical Methodology

- **Area owner:** Statistical Analysis Lead. Prepared by the Integration & QA Lead (group lead) from the code and the preregistration
- **Written:** 16 October 2026, from the code on `main` at `95e3171` and the
  [preregistration](preregistration.md)
- **Status of the source documents:** the preregistration is the specification
  and the register of every post-hoc decision (§7, items 1–13). This page is
  the final summary of what the code runs; where the two meet, section numbers
  point to the preregistration.

## 1. Features and cleaning

Two Tier-1 features, each fitted as its own model: `loc_dist_ep_0` (GPS
distance) and `unlock_num_ep_0` (phone unlocks). Cleaning, quality gate (12 h
for GPS; none exists for unlocks) and transforms (`log(mean + 1000)` for GPS,
identity for unlocks, always `log(mean)` and never `mean(log)`) are in the
[final pipeline methodology](../data-pipeline/final-pipeline-methodology.md) and
preregistration §1.2, §1.5, §1.6.

## 2. Confirmatory model (preregistration §1.4, §1.4.1, §1.6.4)

    phq4_score ~ x_within_it + x_between_i
    + person-level random intercept and random slope on x_within
    + AR(1) residual structure

- `x_it` is the transformed mean of the feature over the comparison window
  `[-14, -1]`; an occasion with fewer than 7 valid sensor-days is dropped, not
  imputed (`mixed_effects_model.OCCASION_MIN_VALID_SENSOR_DAYS = 7`).
- Person-mean centring with the person mean re-entered (Mundlak).
- Engine: R `nlme::lme` with `corAR1` (`backend/statistics/r_bridge.py`,
  `mixed_effects_model.fit_ar1_effect`); the Python `statsmodels` fit is the
  fallback when R is unavailable.
- Primary GPS estimate: β_W = −0.184 (AR(1), 28,337 occasions;
  [`Week5_Statistical_Analysis_Deliverable.md`](../../Week5_Statistical_Analysis_Deliverable.md) §3.3).
- Test: two-sided. Confirmatory family: Holm-Bonferroni, FWER 0.05 (§2.1).

## 3. Per-person evidence (preregistration §2.2, §4, §4.1, §5)

1. **Per-person slope:** the AR(1) fixed effect plus each participant's BLUP.
2. **Per-person SE:** B = 500 bootstrap replicates by two designs, parametric
   and cluster (`backend/statistics/bootstrap.py`).
3. **Multiple comparisons:** BH-FDR across the cohort family, defined per
   feature as the participants holding a per-person slope
   (`evidence.EXPECTED_FAMILY_SIZE`: 214 for GPS, 216 for unlocks). Holm over
   the same family is the sensitivity analysis.
4. **Evidence tiers:** strong / moderate / weak / insufficient (§4), collapsed
   for users to `evidence_available` (strong, moderate) or `no_claim` (§5).
5. **Cross-method intersection:** `evidence_available` only where both
   bootstrap designs independently give `evidence_available`
   (`evidence.intersect_bootstrap_evidence`).
6. **Results (B = 500, real dataset):** GPS 23 of 214 `evidence_available`;
   unlocks fewer than 5 of 216 (small-cell rule, §5.3).
7. **Cache:** results are written once to a fingerprinted, owner-only,
   git-ignored cache (`backend/statistics/bootstrap_cache.py`); a request never
   runs the bootstrap.

## 4. Cold-start states (preregistration §3; `eligibility.classify_state`)

| State | Calendar days | Valid sensor-days | EMAs | What may be said |
|---|---|---|---|---|
| A | < 7, or < 5 valid days, or no EMA | | | templated "not enough data" only |
| B | ≥ 7 | ≥ 5 | ≥ 1 | the current value, "too early to compare" |
| C | ≥ 28 | ≥ 20 | ≥ 3 | comparison with the person's own baseline, gated by section 5 |

State is computed per feature and per evaluation occasion and does not persist.
Each request is answered from exactly one feature
(`request_policy.infer_feature_from_question`); a question naming both
features or neither is answered with a request to name one feature
(`ambiguous_feature_request`).

## 5. Baseline comparison on `/respond` (O2, PR #80; preregistration §4.1, §7 item 13)

`backend/statistics/participant_evidence.py::build_evidence_packet`:

- **Windows:** reported value = mean of `[-14, -1]`; personal baseline = mean
  of `[-42, -15]` (28 days). Both are rounded to whole units with
  `ROUND_HALF_UP` (§5.2): km/day for GPS, unlocks/day for unlocks.
- **Comparison shown** when the occasion is State C, the participant's cached
  intersection label is `evidence_available`, and the deviation is defined
  (at least 7 valid recent days and a non-zero baseline SD, §5.1). The packet
  is `ELIGIBLE` with `StatisticalEvidence`, and the answer gives both values and
  the uncertainty sentence.
- **Every other State C occasion** is sent as `PARTIAL_DESCRIPTIVE_ONLY` with a
  `comparison_reasons` value, and the answer says: "Your history is long enough
  to compare with your own baseline, but there is not enough statistical
  evidence to report a comparison" (or, with no defined deviation, that there
  are too few recorded days in the comparison periods).
- **Fail closed:** no R engine, or a missing, stale, unreadable, malformed or
  not owner-only cache, gives `no_claim` for that request. On a machine without
  the cache the comparison count is 0 by design.
- **State A/B** keep "too early to compare".

Observed on the final build (`95e3171`, 16 October 2026, Ollama,
`phi4-mini:3.8b`, a machine without the R cache): the evaluation questions Q1
and Q2 returned the State C sentence above with 121 unlocks/day and 29 km/day
([release checklist §11](../release/release-candidate-checklist.md#11-remaining-before-freeze)).

Tests: `tests/statistics/test_participant_evidence_bootstrap.py`,
`tests/statistics/test_participant_evidence.py`,
`tests/statistics/test_bootstrap_cache.py`, `tests/slm/test_output_grounding.py`.

## 6. Reporting rules (preregistration §5.3)

- Published aggregates suppress or merge cells below 5.
- Evaluation ratings: cross-evaluator aggregates only; critical failures by
  question and count, never by session.
- Raw per-person p-values are never shown to participants.

The main-evaluation results under these rules are in the
[statistical write-up](main-evaluation-statistical-writeup.md).
