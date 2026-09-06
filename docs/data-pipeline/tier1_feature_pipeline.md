# Tier-1 Feature Pipeline

## Overview

This document describes the final Tier-1 digital phenotyping pipeline implemented for the College Experience Study (CES) dataset.

The final Tier-1 features are:

1. GPS distance travelled (`loc_dist_ep_0`)
2. Home duration (`loc_home_dur`)
3. Phone unlock count (`unlock_num_ep_0`)

These features are aligned to repeated PHQ-4 assessments using a 14-day trailing comparison window.

---

## Data Sources

CES sensing data are loaded from:

`dataset/ces/Sensing/sensing.csv`

Repeated PHQ-4 outcomes are loaded from the CES EMA tables.

The sensing dataset contains 220 participants. Repeated PHQ-4 outcomes are available for 218 participants.

---

## GPS Distance Cleaning

Source column:

`loc_dist_ep_0`

Final cleaning policy:

- Require `quality_loc >= 12` hours/day.
- Negative values are treated as missing.
- Zero is retained as a valid value.
- Values strictly above 500,000 metres/day are set to missing.
- Values exactly equal to 500,000 metres/day are retained.
- Per-participant 1st–99th percentile winsorisation is applied after the hard cutoff.

The 500 km/day cutoff was selected after sensitivity analysis using 250 km, 500 km and 1,000 km thresholds.

Under the final preprocessing specification:

- 250 km: 28,270 valid PHQ-4 occasions, 214 participants
- 500 km: 28,337 valid PHQ-4 occasions, 214 participants
- 1,000 km: 28,372 valid PHQ-4 occasions, 214 participants

The estimated association remained negative and statistically significant under all three thresholds, with no sign flips.

---

## Home Duration Cleaning

Source column:

`loc_home_dur`

Final cleaning policy:

- Values below 0 hours/day are set to missing.
- Values above 24 hours/day are set to missing.
- Values from 0 through 24 hours/day are retained.

In the CES sensing data:

- 2,793 participant-days exceeded 24 hours/day.
- This represented approximately 1.29% of participant-days.
- 173 of 220 participants had at least one such value.

These values are treated as measurement or aggregation artefacts rather than capped at 24 hours.

---

## Unlock Count Cleaning

Source column:

`unlock_num_ep_0`

Final cleaning policy:

- Negative values are set to missing.
- Zero unlock counts are retained as valid observations.
- Positive values are winsorised using participant-specific 1st–99th percentiles.
- No unlock-specific quality gate is available in the aggregated CES schema.

The dataset contains 3,736 zero-unlock participant-days, representing approximately 1.73% of all participant-days.

Because zero unlocks can represent genuine behaviour and the aggregated dataset contains no screen-uptime quality variable, zero values are not recoded to missing.

---

## Feature Window Alignment

Tier-1 features are aligned to each PHQ-4 assessment using:

`[EMA date - 14 days, EMA date - 1 day]`

The PHQ-4 assessment day itself is excluded.

Each window records:

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

A feature window is considered valid when at least 7 of the 14 expected days contain valid observations.

---

## Platform Handling

The CES sensing table uses:

`is_ios`

Platform metadata are mapped as:

- `True` -> `iOS`
- `False` -> `Android`
- both values within a feature window -> `mixed`
- no platform information -> `unknown`

Mixed-platform windows are retained and explicitly marked rather than forcing each participant into a single platform category.

---

## Final Production Output

The production pipeline creates:

`outputs/data-pipeline/tier1_feature_windows.csv`

The final output contains:

- 106,044 FeatureWindow rows
- 35,348 rows for each of the three Tier-1 features

Valid windows:

- Home duration: 33,994
- GPS distance: 28,337
- Unlock frequency: 34,235

The GPS valid-window count matches the independently validated final 500 km preprocessing pipeline.

---

## Automated Tests

Automated tests are implemented in:

`tests/data_pipeline/test_tier1_features.py`

The tests verify:

- GPS quality gate behaviour
- 500 km hard-cutoff boundary
- GPS zero retention
- Home-duration boundary handling
- Unlock zero retention
- Unlock negative-value handling
- PHQ-4 day exclusion
- 14-day trailing window boundaries
- Minimum 7-day coverage rule
- Mixed-platform window handling

Current test result:

`6 passed`

---

## Status

The Tier-1 feature pipeline is implemented and tested end-to-end.

Locked Tier-1 features:

- GPS distance travelled
- Home duration
- Phone unlock count