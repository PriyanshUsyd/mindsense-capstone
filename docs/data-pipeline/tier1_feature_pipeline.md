# Tier-1 Feature Pipeline

## Overview

This document describes the final Tier-1 digital phenotyping pipeline implemented for the College Experience Study (CES) dataset.

**The locked, signed-off Tier-1 feature set is 2 features** (`feature-list-signoff.md`,
confirmed by Priyansh Khandelwal on 26 August 2026, per the hard cap in
`Weekly_Plan.md` Week 4 / `freeze-decision.md`):

1. GPS distance travelled (`loc_dist_ep_0`)
2. Phone unlock count (`unlock_num_ep_0`)

Both are aligned to repeated PHQ-4 assessments using a 14-day trailing comparison window.

**Home duration (`loc_home_dur`) is documented separately below as an implemented-but-not-locked candidate feature** (see "Home Duration Cleaning" and "Status" sections) — `scripts/build_gps_feature.py` builds and tests it alongside the two locked features because they share the same cleaning/alignment machinery, but it was never part of the 26 August sign-off and must not be treated as final or "locked" pending a fresh team decision to add a third feature under the same standard the other two met.

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

## Home Duration Cleaning (candidate feature, not part of the locked Tier-1 set)

**Not locked.** `feature-list-signoff.md` and `freeze-decision.md` cap the
signed-off Tier-1 set at 2 features (GPS distance, unlock count). Home
duration is implemented and tested in the same pipeline script because it
shares the same cleaning/alignment code, and is kept here for reference in
case the team later agrees a third feature meets the same cross-platform +
completeness standard — but it has no such agreement today and must not be
described as final, locked, or part of the production Tier-1 output.

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

The script generates 35,348 FeatureWindow rows per feature it processes,
106,044 in total across all three features it currently computes (GPS
distance, unlock count, and the not-locked home-duration candidate above).
**Of this, the locked Tier-1 output is 2 features / 70,696 rows** (GPS
distance + unlock count); the home-duration rows are additional candidate
output, not part of the signed-off set.

Valid windows:

- GPS distance: 28,337 (locked)
- Unlock frequency: 34,235 (locked)
- Home duration: 33,994 (candidate, not locked)

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

**Locked Tier-1 features (2, per `feature-list-signoff.md`):**

- GPS distance travelled
- Phone unlock count

**Implemented but not locked (candidate only):**

- Home duration — built and tested here for convenience; requires a fresh
  team decision before it can be described as locked or final.