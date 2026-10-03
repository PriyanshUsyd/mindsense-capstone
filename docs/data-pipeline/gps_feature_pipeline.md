# CES GPS Distance Feature Pipeline

## 1. Overview

This document describes the final implementation and validation of the GPS distance feature pipeline for the College Experience Study (CES) dataset.

The purpose of the pipeline is to construct a reproducible mobility feature from CES sensing data, align it with repeated PHQ-4 outcomes, and provide a validated Tier-1 feature for downstream longitudinal statistical analysis and the conversational system.

The primary GPS feature is:

- `loc_dist_ep_0`: daily distance travelled, measured in metres.

The pipeline performs:

1. CES sensing data loading and date standardisation.
2. GPS data-quality auditing.
3. Location sensing quality filtering.
4. GPS extreme-value diagnostics.
5. Hard-cutoff sensitivity analysis.
6. Participant-level winsorisation.
7. Construction of trailing GPS windows aligned with PHQ-4 observations.
8. Minimum-coverage validation.
9. Window-level GPS aggregation.
10. Statistical preprocessing for longitudinal modelling.
11. Rolling baseline sufficiency diagnostics.
12. Integration into the final Tier-1 FeatureWindow pipeline.

The GPS preprocessing specification is now locked following diagnostic checks, sensitivity analysis, and coordination with the Statistical Analysis Lead.

---

## 2. Data Sources

### 2.1 Sensing Data

The GPS pipeline uses the CES daily sensing dataset:

`dataset/ces/Sensing/sensing.csv`

The sensing data contain:

- 216,065 participant-day rows.
- 220 sensing participants.

The primary GPS variable is:

`loc_dist_ep_0`

which represents daily distance travelled.

The CES sensing table contains precomputed daily sensing features rather than the raw GPS trajectory used to derive them.

### 2.2 Mental-Health Outcome

Repeated PHQ-4 measurements are loaded from the CES EMA data.

The current data contain:

- 35,348 valid PHQ-4 observations.
- 218 participants with at least one valid PHQ-4 measurement.

PHQ-4 is treated as a repeated wellbeing/mental-health screening outcome rather than as a diagnostic measure.

---

## 3. Raw GPS Data Quality Audit

An initial audit was performed before applying GPS cleaning rules.

Across 216,065 participant-days:

| Metric | Result |
|---|---:|
| Total rows | 216,065 |
| Missing GPS values | 43,500 |
| Non-null GPS values | 172,565 |
| Negative GPS values | 0 |
| Zero GPS values | 15,616 |

Zero-distance days are retained as potentially valid observations rather than automatically treated as missing.

The raw GPS distance distribution is highly right-skewed:

| Statistic | Distance (m/day) |
|---|---:|
| Minimum | 0.00 |
| Median | 5,847.75 |
| Mean | 144,220.78 |
| 95th percentile | 255,662.36 |
| 99th percentile | 2,051,551.76 |
| 99.9th percentile | 9,540,429.20 |
| 99.99th percentile | 153,635,132.26 |
| Maximum | 1,211,515,851.22 |

The extreme upper-tail values show that raw `loc_dist_ep_0` cannot be used without explicit quality control.

Because the current CES sensing table provides precomputed daily GPS features rather than the underlying raw GPS trajectories, extreme values cannot be traced back to individual coordinates or trajectory points. The pipeline therefore handles these values using explicit and reproducible preprocessing rules rather than assuming a specific underlying error mechanism.

---

## 4. Location Quality Gate

The CES variable `quality_loc` is used as the daily location-data quality indicator.

Two candidate thresholds were evaluated:

- `quality_loc >= 8` hours/day
- `quality_loc >= 12` hours/day

Results:

| Quality threshold | Usable GPS days | Participants |
|---|---:|---:|
| >= 8 h | 168,304 | 217 |
| >= 12 h | 165,567 | 217 |

Increasing the threshold from 8 to 12 hours removed an additional 2,737 participant-days, corresponding to a relative loss of approximately 1.63%.

The final locked location-quality gate is:

`quality_loc >= 12 hours/day`

Participant-days below this threshold are treated as insufficiently observed and their GPS distance is set to missing (`NA`) rather than zero.

---

## 5. GPS Hard-Cutoff Diagnostics

After applying the 12-hour location-quality gate, 165,567 GPS participant-days entered the extreme-value cutoff analysis.

Three candidate hard cutoffs were evaluated:

| Cutoff | Days set to NA | Participants affected | Remaining valid days |
|---|---:|---:|---:|
| 250 km/day | 8,480 | 213 | 157,087 |
| 500 km/day | 4,284 | 209 | 161,283 |
| 1,000 km/day | 2,790 | 201 | 162,777 |

Observations strictly above each candidate threshold were set to missing rather than capped at the threshold.

For the 500 km/day threshold:

- 4,284 participant-days exceeded the threshold.
- 209 participants had at least one such observation.
- The five participants with the most extreme days accounted for approximately 6.9% of all observations above 500 km/day.

This indicates that the extreme-distance problem is distributed across many participants rather than being driven by a small number of individuals.

The final locked hard cutoff is:

`loc_dist_ep_0 > 500,000 metres/day -> NA`

A value exactly equal to 500,000 metres/day is retained.

---

## 6. Participant-Level Winsorisation

Two participant-level winsorisation approaches were evaluated under the 500 km/day hard cutoff:

1. Participant-specific 1st–99th percentile winsorisation.
2. Participant-specific median ±5 MAD winsorisation.

A no-winsorisation model was also retained as a diagnostic reference.

Initial model comparison:

| Method | Beta | 95% CI |
|---|---:|---:|
| No winsorisation | -0.270236 | [-0.328617, -0.211856] |
| 1st–99th percentile | -0.277023 | [-0.336634, -0.217412] |
| Median ±5 MAD | -0.521729 | [-0.634117, -0.409341] |

The relative difference between the two winsorised estimates was approximately 88.33%.

The percentile-winsorised estimate remained close to the no-winsorisation estimate, while the MAD approach produced a substantially larger coefficient magnitude.

A direct audit of changed daily values showed:

| Method | Values changed | Percentage changed |
|---|---:|---:|
| 1st–99th percentile | 1,920 | 1.19% |
| Median ±5 MAD | 32,348 | 20.06% |

After the 12-hour quality gate and 500 km cutoff:

- 161,283 valid GPS participant-days remained.
- The median participant-specific P99 was approximately 358,003 metres/day.
- The median MAD-based upper cap was approximately 26,539 metres/day.

The MAD approach therefore substantially compressed the highly skewed GPS distribution.

The final locked winsorisation method is:

`participant-specific 1st–99th percentile winsorisation`

This method was retained because it performs relatively light tail cleanup while remaining close to the no-winsorisation result.

---

## 7. PHQ-4 Aligned Comparison Windows

GPS observations are aligned with repeated PHQ-4 assessments using the 14 calendar days immediately preceding each assessment.

The final comparison window is:

`[EMA date - 14 days, EMA date - 1 day]`

The PHQ-4 assessment day itself is excluded.

This prevents full-day sensing information collected after the assessment from entering the predictor window.

A GPS comparison window is considered valid when it contains at least:

`7 valid GPS days`

after the final daily cleaning rules have been applied.

Under the three candidate GPS cutoffs:

| Cutoff | Valid EMA occasions | Invalid occasions | Participants surviving gate | Median GPS days/window |
|---|---:|---:|---:|---:|
| 250 km | 28,270 | 7,078 | 214 | 13 |
| 500 km | 28,337 | 7,011 | 214 | 14 |
| 1,000 km | 28,372 | 6,976 | 214 | 14 |

All three thresholds retained the same 214 participants after the minimum-valid-day requirement.

The usable occasion counts differed by only 102 across the full fourfold change
in cutoff, from 250 km/day to 1,000 km/day:

- 250 km/day: 28,270 occasions
- 500 km/day: 28,337 occasions
- 1,000 km/day: 28,372 occasions

This shows that changing the hard cutoff over a wide range removed relatively
few additional PHQ-4-aligned windows. Participant inclusion was identical
across all three specifications, and occasion-level inclusion changed only
slightly. This provides a direct explanation for why the subsequent cutoff
sensitivity estimates remained stable.

---

## 8. Final Cutoff Sensitivity Analysis

The final hard-cutoff sensitivity analysis was rerun using the complete locked preprocessing order:

1. Require `quality_loc >= 12` hours/day.
2. Apply candidate hard cutoff.
3. Set values above the cutoff to missing.
4. Apply participant-specific 1st–99th percentile winsorisation.
5. Construct `[EMA date - 14, EMA date - 1]` windows.
6. Require at least 7 valid GPS days.
7. Calculate mean daily GPS distance across valid days.
8. Apply `log(mean_distance + 1000)`.
9. Person-mean centre the transformed predictor.
10. Fit the same sensitivity mixed-effects model.

Results:

| Cutoff | Valid occasions | Participants | Beta | 95% CI |
|---|---:|---:|---:|---:|
| 250 km/day | 28,270 | 214 | -0.308049 | [-0.376084, -0.240015] |
| 500 km/day | 28,337 | 214 | -0.277023 | [-0.336634, -0.217412] |
| 1,000 km/day | 28,372 | 214 | -0.256201 | [-0.311695, -0.200707] |

All three estimates:

- had the same negative direction;
- were statistically significant;
- retained 214 participants;
- showed no sign flip.

The confidence intervals overlapped substantially across the three
specifications, and there were no sign flips.

Relative to the locked 500 km/day threshold:

- the 250 km estimate differed by approximately 11.20%;
- the 1,000 km estimate differed by approximately 7.52%.

The important sensitivity result is not that the numerical coefficient changed
only slightly, but that the substantive inference was the same under all three
cutoffs. Across the 250 km, 500 km and 1,000 km specifications, the estimated
within-person association remained negative and statistically significant.

This stability is also consistent with the window-retention results. The usable
occasion counts were 28,270, 28,337 and 28,372 respectively, a maximum
difference of only 102 occasions across a fourfold change in the hard cutoff.
All three specifications retained the same 214 participants.

Therefore, changing the cutoff over this range had very little effect on the
analytic sample, and the substantive inference did not depend on the selected
cutoff.

Following this sensitivity analysis and review with the Statistical Analysis
Lead, the 500 km/day threshold remains the locked final hard cutoff.

---

## 9. Final GPS Aggregation and Statistical Preprocessing

The final GPS processing order is important.

Daily GPS observations are cleaned first.

Within each valid 14-day comparison window:

1. retain cleaned daily GPS values;
2. require at least 7 valid days;
3. calculate the mean daily GPS distance;
4. apply the transformation once to the window mean:

`log(mean_daily_distance + 1000)`

5. person-mean centre the transformed window-level predictor for within-person longitudinal modelling.

The pipeline does not calculate the mean of individually log-transformed daily distances.

This distinction is intentional because:

`mean(log(daily distance + 1000))`

is not equivalent to:

`log(mean(daily distance) + 1000)`.

The latter is the locked specification.

---

## 10. Cold-Start and Rolling Baseline Sufficiency

### 10.1 Initial 28-Day Diagnostic

An early dataset-quality diagnostic examined the first 28 calendar days following each participant's first sensing date.

The diagnostic required:

- `quality_loc >= 12` hours/day;
- at least 20 valid GPS sensor-days.

Results:

| Metric | Result |
|---|---:|
| Participants evaluated | 220 |
| Sufficient participants | 200 |
| Insufficient participants | 20 |
| Sufficiency rate | 90.9% |
| Median valid days | 26 |

The first-28-day result is retained as a descriptive dataset-quality diagnostic only.

It is not the operational cold-start rule.

### 10.2 Final Rolling Baseline

The operational baseline is evaluated relative to each assessment date.

The 14-day comparison window is:

`[assessment - 14, assessment - 1]`

The immediately preceding 28-day baseline window is:

`[assessment - 42, assessment - 15]`

The baseline therefore does not overlap the comparison window.

A 28-day baseline is considered sufficient when it contains at least:

`20 valid sensor-days`

Results:

- 25,464 of 35,348 PHQ-4 occasions met the baseline-only requirement.
- Baseline-only sufficiency was approximately 72.0%.
- 213 of 218 participants had at least one baseline-sufficient occasion.
- Median valid baseline days was 28.

The 213/218 result should be interpreted as participant-level "ever sufficient" coverage rather than as the operational State-C rate.

The full conversational State-C rule additionally requires sufficient recent/comparison-window coverage, so its rate can be lower than the baseline-only rate.

A longer 56-day trend baseline may use:

`[assessment - 70, assessment - 15]`

with at least 40 valid sensor-days when required by downstream statistical logic.

Because sufficiency is evaluated using rolling windows, a participant may move between data-sufficiency states over time.

---

## 11. Additional Tier-1 Feature Validation

GPS distance is one of three locked Tier-1 sensing features.

The other two are:

- home duration: `loc_home_dur`
- phone unlock count: `unlock_num_ep_0`

### 11.1 Home Duration

`loc_home_dur` represents time spent at home and is measured in hours/day.

Raw audit:

| Metric | Result |
|---|---:|
| Total rows | 216,065 |
| Missing | 852 |
| Negative | 0 |
| Values >24 h | 2,793 |
| Median | 9.62 h |
| 99th percentile | 24.003 h |
| 99.9th percentile | 24.009 h |
| Maximum | 45.803 h |

Impossible values above 24 hours/day occurred on:

- 2,793 participant-days;
- approximately 1.29% of participant-days;
- across 173 of 220 participants.

The five participants with the most violations accounted for approximately 17.0% of these observations.

The final deterministic cleaning rule is:

`loc_home_dur < 0 or loc_home_dur > 24 -> NA`

Values are not capped at 24 hours.

No additional home-duration winsorisation is currently applied.

### 11.2 Phone Unlock Count

`unlock_num_ep_0` represents daily phone unlock frequency.

Raw audit:

| Metric | Result |
|---|---:|
| Total rows | 216,065 |
| Missing | 0 |
| Negative | 0 |
| Median | 79 |
| 90th percentile | 161 |
| 95th percentile | 197 |
| 99th percentile | 285 |
| 99.9th percentile | 449 |
| Maximum | 754 |

Zero-unlock audit:

- 3,736 zero-unlock participant-days;
- approximately 1.73% of participant-days;
- 215 of 220 participants had at least one zero-unlock day;
- median zero days among affected participants = 12;
- maximum = 231.

The aggregated CES schema contains location, activity, audio and light quality variables but does not expose an unlock-specific or screen-uptime quality variable that can reliably distinguish a genuine zero from failed unlock sensing.

The final unlock cleaning policy is therefore:

1. numeric coercion;
2. negative values -> `NA`;
3. retain zero as a genuine possible observation;
4. apply participant-specific 1st–99th percentile winsorisation to positive unlock values;
5. do not apply an arbitrary hard upper cutoff;
6. do not apply an unlock-specific quality gate.

Positive-only winsorisation ensures that genuine zero values remain exactly zero.

---

## 12. Tier-1 Redundancy Check

A within-person correlation diagnostic was performed between:

- fully cleaned GPS mobility; and
- cleaned home duration.

GPS used:

- `quality_loc >= 12`;
- 500 km hard cutoff;
- participant-specific P1–P99 winsorisation;
- `log(distance + 1000)`;
- person-mean centering.

Home duration used:

- theoretical `[0, 24]` validity filtering;
- person-mean centering.

Results:

- 157,725 paired participant-days;
- 217 participants;
- within-person correlation `r = -0.2425`.

The absolute correlation is well below the provisional redundancy threshold of 0.6.

GPS distance and home duration are therefore retained as distinct Tier-1 features rather than treating one as a substitute for the other.

---

## 13. Location Entropy

Standard Shannon location entropy requires participant-specific location shares:

`H = -sum(p_i * ln(p_i))`

where `p_i` represents the proportion of time associated with each participant-specific location cluster.

The aggregated CES sensing table exposes predefined semantic-location duration variables such as home, study, social and food locations, but these are not equivalent to participant-specific location clusters.

Therefore, standard location entropy cannot be reconstructed reliably from the current aggregated sensing table.

Location entropy remains a Tier-2 candidate unless raw location-level data are processed separately.

It is not part of the locked Tier-1 feature set.

---

## 14. Final Tier-1 FeatureWindow Contract

The production pipeline creates one FeatureWindow record for each:

- participant;
- PHQ-4 assessment;
- Tier-1 feature.

The output fields include:

- `uid`
- `ema_date`
- `phq4_score`
- `feature_id`
- `source_column`
- `unit`
- `window_start`
- `window_end`
- `value`
- `observed_days`
- `expected_days`
- `coverage_ratio`
- `platform`
- `occasion_valid`
- `quality_flags`

The three production feature identifiers are:

| Feature ID | Source column | Unit |
|---|---|---|
| `mobility_distance` | `loc_dist_ep_0` | metres/day |
| `home_duration` | `loc_home_dur` | hours/day |
| `unlock_frequency` | `unlock_num_ep_0` | count/day |

For the production FeatureWindow representation, `value` stores the cleaned window-level aggregate.

Model-specific transformations such as GPS `log(mean + 1000)` and person-mean centering are applied downstream in the statistical analysis layer rather than replacing the interpretable aggregate stored in the FeatureWindow.

---

## 15. Coverage Metadata

Every FeatureWindow carries explicit coverage metadata.

For the standard 14-day comparison window:

`expected_days = 14`

`observed_days` is the number of non-missing cleaned daily observations available for the specific feature.

Coverage is calculated as:

`coverage_ratio = observed_days / expected_days`

The minimum valid-day requirement is:

`observed_days >= 7`

If no valid observations are available:

`quality_flags = no_valid_days`

If observations are available but fewer than 7 valid days remain:

`quality_flags = insufficient_coverage`

Unsupported or unavailable sensing data are not imputed as zero.

---

## 16. Platform Handling

The CES sensing table exposes platform information through:

`is_ios`

The production pipeline maps this field as:

- `True` -> `iOS`
- `False` -> `Android`
- both values within the same feature window -> `mixed`
- no available platform information -> `unknown`

Mixed-platform windows are explicitly marked rather than forcing the participant into a single platform category.

This is important because the CES data contain participants whose sensing records are associated with more than one platform across the observation period.

---

## 17. Production Output

The final Tier-1 FeatureWindow pipeline generates:

`outputs/data-pipeline/tier1_feature_windows.csv`

The generated file is a reproducible derived output and is excluded from Git tracking.

The final production run generated:

`106,044 FeatureWindow rows`

Rows by feature:

| Feature | Rows |
|---|---:|
| Home duration | 35,348 |
| GPS mobility distance | 35,348 |
| Unlock frequency | 35,348 |

Valid windows:

| Feature | Valid windows | Approx. valid proportion |
|---|---:|---:|
| Home duration | 33,994 | 96.2% |
| GPS mobility distance | 28,337 | 80.2% |
| Unlock frequency | 34,235 | 96.9% |

The GPS production count of 28,337 valid windows exactly matches the final 500 km GPS sensitivity pipeline.

---

## 18. Automated Tests

Automated data-pipeline tests are located in:

`tests/data_pipeline/test_tier1_features.py`

The current test suite verifies:

1. GPS location-quality filtering.
2. GPS 500 km cutoff boundary behaviour.
3. Retention of valid zero-distance days.
4. Home-duration theoretical bounds.
5. Retention of zero unlock counts.
6. Rejection of negative unlock counts.
7. Exclusion of the PHQ-4 assessment day.
8. Correct 14-day trailing-window construction.
9. Minimum 7-valid-day coverage behaviour.
10. Mixed-platform FeatureWindow handling.

Current test result:

`6 passed`

The test suite completes successfully with exit code 0.

---

## 19. Reproducibility

The main implementation is contained in:

`scripts/build_gps_feature.py`

The CES dataset validation script is contained in:

`scripts/validate_ces.py`

Dataset validation documentation is contained in:

`docs/data-pipeline/dataset_validation_CES.md`

The final Tier-1 pipeline summary is contained in:

`docs/data-pipeline/tier1_feature_pipeline.md`

Automated Tier-1 tests are contained in:

`tests/data_pipeline/test_tier1_features.py`

Generated production outputs are written under:

`outputs/data-pipeline/`

and are excluded from Git tracking because they can be reproduced from the source data and pipeline code.

---

## 20. Final Locked GPS Specification

The final GPS preprocessing specification is:

1. Source feature: `loc_dist_ep_0`.
2. Require `quality_loc >= 12` hours/day.
3. Treat negative GPS distance as missing.
4. Retain zero GPS distance when the quality requirement is satisfied.
5. Set values strictly above 500,000 metres/day to missing.
6. Retain exactly 500,000 metres/day.
7. Apply participant-specific 1st–99th percentile winsorisation.
8. Use `[EMA date - 14, EMA date - 1]` as the comparison window.
9. Exclude the PHQ-4 assessment day.
10. Require at least 7 valid GPS days.
11. Calculate mean daily GPS distance over valid days.
12. For statistical modelling, apply `log(mean_distance + 1000)` after aggregation.
13. Person-mean centre the transformed predictor for within-person longitudinal analysis.

The substantive inference was the same under the 250 km, 500 km and 1,000 km
sensitivity specifications: all three estimates remained negative and
statistically significant, their confidence intervals overlapped substantially,
and there were no sign flips.

The usable occasion counts differed by only 102 across the full fourfold change
in cutoff, while all three specifications retained the same 214 participants.
This provides additional evidence that the conclusion does not depend on the
choice of hard cutoff.

The 500 km/day threshold and participant-specific P1–P99 winsorisation are
therefore retained as the final GPS extreme-value policy.


---

## 21. Final Tier-1 Status

The final locked Tier-1 features are:

1. GPS distance travelled (`loc_dist_ep_0`)
2. Home duration (`loc_home_dur`)
3. Phone unlock count (`unlock_num_ep_0`)

The Tier-1 pipeline is now implemented end-to-end from CES sensing data through cleaned PHQ-4-aligned FeatureWindow generation.

Current status:

- CES dataset contract validation: complete
- GPS raw-data audit: complete
- GPS quality gate: locked
- GPS hard cutoff: locked
- GPS winsorisation: locked
- GPS PHQ-4 alignment: locked
- GPS cutoff sensitivity: complete
- Home-duration cleaning: implemented
- Unlock cleaning: implemented
- Rolling baseline diagnostic: complete
- Platform metadata handling: implemented
- Tier-1 FeatureWindow generation: implemented
- Automated Tier-1 tests: 6/6 passing
- Production pipeline: runs successfully end-to-end