# Final Data-Pipeline Methodology (Tier 1)

- **Area owner:** Data Pipeline Lead. Prepared by the Integration & QA Lead (group lead) from the code
- **Written:** 16 October 2026, from the code on `main` at `95e3171`
- **Scope:** the two frozen Tier-1 features, `loc_dist_ep_0` (GPS distance) and
  `unlock_num_ep_0` (phone unlocks), from the local CES files to the cleaned
  per-day columns the statistics layer reads.

Every rule below is quoted from the code it names. The run outputs in sections 5
and 6 are real runs on the group lead's machine against the local CES copy;
they are aggregate counts only.

## 1. Source data

| Item | Value | Code |
|---|---|---|
| Dataset | College Experience Study (CES), local copy under the git-ignored `dataset/` | [`ces_local_provisioning.md`](ces_local_provisioning.md) |
| Sensing file | `dataset/Sensing/sensing.csv`, one row per participant-day (`uid`, `day` as `YYYYMMDD`) | `gps_distance_feature.load_sensing_days` |
| EMA file | `dataset/EMA/general_ema.csv` (PHQ-4 responses) | `ces_eligibility.load_eligibility_inputs` |
| Demographics | `dataset/Demographics/demographics.csv` | `verify_ces.py` |
| Features | `loc_dist_ep_0` (metres/day), `unlock_num_ep_0` (count/day) | [`feature-list-signoff.md`](../../feature-list-signoff.md) |

Timestamp alignment is a sort by `(uid, day)`: the sensing file already holds one
row per participant and calendar day, which
`tests/data_pipeline/test_gps_distance_feature.py::test_no_duplicate_participant_days_in_the_real_dataset`
checks on the real data.

## 2. GPS distance (`loc_dist_ep_0`)

`backend/data_pipeline/cleaning.py::clean_gps_distance`, called by
`gps_distance_feature.build_gps_distance_feature`.

| Step | Rule | Constant |
|---|---|---|
| 1. Quality gate | day set to NA unless `quality_loc >= 12` hours | `QUALITY_LOC_MIN_HOURS = 12` |
| 2. Implausibility | day set to NA when distance `> 500,000 m` (not capped) | `GPS_IMPLAUSIBILITY_THRESHOLD_M` |
| 3. Winsorisation | clamp to each participant's own 1st–99th percentile of surviving days | `GPS_WINSORIZE_*_QUANTILE` |
| 4. Transform (modelling) | `log(x + 1000)` | `GPS_LOG_OFFSET_M = 1000` |
| Zero days | kept when the quality gate passes (a genuine stay-at-home day) | — |

Row count and order are preserved: a dropped day is NA, never a removed row.
Output columns: `loc_dist_ep_0_clean` (metres) and `loc_dist_ep_0_log`.

## 3. Phone unlocks (`unlock_num_ep_0`)

`backend/data_pipeline/cleaning.py::clean_unlock_frequency`, called by
`unlock_frequency_feature.build_unlock_frequency_feature`.

| Step | Rule |
|---|---|
| Quality gate | none: CES has no screen or unlock quality column |
| Implausibility | negative counts set to NA; no upper cutoff |
| Winsorisation | per-participant 1st–99th percentile of **positive** values; zeros are never clipped |
| Transform | none (identity), per `docs/statistics/preregistration.md` §1.6.2 |
| Zero days | kept as real values |

Output column: `unlock_num_ep_0_clean`.

## 4. Hand-off to statistics and to `/respond`

- `backend/statistics/feature_specs.py` declares each feature once
  (`GPS_DISTANCE_SPEC`, `UNLOCK_FREQUENCY_SPEC`): raw column, cleaning entry
  point and transform. The cleaned column name is derived as `<name>_clean`.
- `backend/statistics/participant_evidence.py` reads the cleaned columns to
  build the evidence packet: the reported value is the mean of the comparison
  window `[-14, -1]`, the personal baseline is the mean of `[-42, -15]`, and
  both are rounded to whole units for display (`_round_user_facing`).
- `backend/data_pipeline/retrieval_source.py` (RAG thread) reads only the
  current evidence packet's canonical summaries. It reads no sensing rows and
  computes no statistics.
- Eligibility counts (`ces_eligibility.py`) use at least
  `MIN_VALID_SENSOR_DAYS = 20` valid sensor-days; participant identifiers are
  pseudonymised before any output (`make_pseudonymizer`,
  [`privacy/ces-uid-fix.md`](../../privacy/ces-uid-fix.md)).

## 5. Feature-code freeze record

The Tier-1 pipeline is frozen at the following versions, read from git at
`95e3171`:

| Scope | Last commit | Date |
|---|---|---|
| Tier-1 feature code (`cleaning.py`, `gps_distance_feature.py`, `unlock_frequency_feature.py`) | `094736870e9026f728f15d7582d663cc4671720c` | 2026-09-14 17:08 +10:00 |
| Whole `backend/data_pipeline/` package (adds `retrieval_source.py`, RAG thread) | `171013aa02195766bc833ca1b42557a45d9a0165` | 2026-09-26 21:54 +10:00 |
| `backend/data_pipeline/` tree object at `95e3171` | `b0aec43248cf0d998b5e1f0e4c853980697f2fb6` | — |

Per file, at `95e3171`:

| File | Last commit | Date |
|---|---|---|
| `cleaning.py` | `0947368` | 2026-09-14 |
| `unlock_frequency_feature.py` | `0947368` | 2026-09-14 |
| `gps_distance_feature.py` | `0895180` | 2026-09-12 |
| `ces_eligibility.py` | `d751ec6` | 2026-09-05 |
| `verify_ces.py` | `8f17285` | 2026-08-29 |
| `retrieval_source.py` | `171013a` | 2026-09-26 |
| `__init__.py` | `d24c55e` | 2026-08-29 |

Reproduce with `git log -1 --format='%H %ad' 95e3171 -- backend/data_pipeline/<file>`.

## 6. Run record, 16 October 2026 (group lead's machine, Windows 11, Python 3.14.5, `95e3171`)

### 6.1 Dataset preflight ([`ces_local_provisioning.md`](ces_local_provisioning.md), "Preflight check")

```text
Test-Path .\dataset\Sensing\sensing.csv          True
Test-Path .\dataset\EMA\general_ema.csv          True
Test-Path .\dataset\Demographics\demographics.csv True

.venv\Scripts\python.exe .\backend\data_pipeline\verify_ces.py
{
  "n_sensing_participants": 220,
  "n_demographics_participants": 216,
  "n_phq4_participants": 218,
  "median_phq4_entries_per_participant": 169.5,
  "platform_counts_raw_is_ios_flag": {"1": 188, "0": 32},
  "dual_platform_uid_count": 14,
  "gps_distance_max_value_observed": 1211515851.22,
  "n_eligible_participants_coarse_check": 216,
  "eligible_pct_coarse_check": 98.2,
  "n_eligible_participants_gated_check": 214,
  "eligible_pct_gated_check": 97.3,
  "eligible_pct_OFFICIAL": 97.3
}
```

All three files are present and the gated eligibility is 214 of 220 (97.3%),
the value the provisioning procedure expects.

### 6.2 Feature builders

`python -m backend.data_pipeline.gps_distance_feature`:

| Measure | Value |
|---|---|
| Participants / participant-days | 220 / 216,065 |
| Days with a raw value | 172,565 |
| Days after cleaning | 161,283 |
| Dropped by the 12 h quality gate | 6,998 |
| Dropped by the 500 km/day filter | 4,284 |
| Zero-travel days kept | 14,354 |
| Cleaned distance, median (m/day) | 5,666.9 |
| `log(x + 1000)`, mean / SD | 9.1861 / 1.4958 |
| Clean days per participant, median (min–max) | 729 (2–1,302) |

`python -m backend.data_pipeline.unlock_frequency_feature`:

| Measure | Value |
|---|---|
| Participants / participant-days | 220 / 216,065 |
| Days with a raw value / after cleaning | 216,065 / 216,065 |
| Negative counts dropped | 0 |
| Zero-unlock days kept | 3,736 |
| Cleaned count, median / mean (per day) | 79.0 / 90.22 |
| Clean days per participant, median (min–max) | 1,143.5 (2–1,370) |

## 7. Tests

| Test file | Covers |
|---|---|
| `tests/data_pipeline/test_cleaning.py` | every cleaning step and constant above |
| `tests/data_pipeline/test_gps_distance_feature.py` | real-data GPS build (runs when `dataset/` is present) |
| `tests/data_pipeline/test_tier1_features.py` | GPS quality gate and cutoff, unlock cleaning |
| `tests/data_pipeline/test_ces_contract.py` | CES participant, PHQ-4 density and eligibility checks |
| `tests/data_pipeline/test_validate_ces_script.py` | `validate_ces.py` against the real dataset |
| `tests/data_pipeline/test_ces_eligibility_privacy.py` | pseudonymised eligibility output |
| `tests/integration/test_ces_eligibility_scripts_agree.py` | the two eligibility scripts agree |

With the dataset present these run in the full suite (1027 passed on
`95e3171`, 16 October 2026; the 19 skips need R).
