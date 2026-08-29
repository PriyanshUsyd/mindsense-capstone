# CES Re-verification — Week 4 (Honghao Li's task)

**Status: Honghao reported this task complete in chat (97.3% eligible), but
as of 2026-08-29 there was no artifact anywhere in the repo recording it —
that was the actual Week 4 gap.** This file plus
`backend/data_pipeline/verify_ces.py` were built by Priyansh (Integration/QA)
as an **independent cross-check**, run for real against the local
`dataset/` copy — not as a replacement for Honghao's own pipeline work,
which is still his to build/commit for Week 5.

## Independent cross-check results (run 2026-08-29, real local dataset)

```json
{
  "n_sensing_participants": 220,
  "n_demographics_participants": 216,
  "n_phq4_participants": 218,
  "median_phq4_entries_per_participant": 169.5,
  "platform_counts_raw_is_ios_flag": {"1": 188, "0": 32},
  "dual_platform_uid_count": 14,
  "gps_distance_max_value_observed": 1211515851.22,
  "n_eligible_participants_coarse_check": 216,
  "eligible_pct_coarse_check": 98.2
}
```

**This corroborates every count already documented in
`skills/data-pipeline-ces.md`:** 220 sensing / 216 demographics / 218 PHQ-4
participants, median ~170 PHQ-4 entries, 188 iOS / 32 Android, 14
dual-platform uids, and the ~1.21e9 GPS outlier are all confirmed present in
the actual current copy of the data — the skill file's documented quirks are
real, not stale.

## On the 97.3% eligible figure specifically

The coarse check above returns **98.2% eligible**, not Honghao's reported
**97.3%** — these are not the same calculation, so this is not a
discrepancy to resolve, just a difference in method to be transparent about:

- This script's "eligible" = has ≥1 PHQ-4 entry AND ≥1 day of non-null
  coverage ever on both locked features, across a participant's entire
  history.
- Honghao's actual eligibility number almost certainly uses the real
  trailing-window + coverage-ratio rule (the kind defined in
  `docs/statistics/model-and-coldstart-spec.md`), applied per PHQ-4 window,
  not a whole-history yes/no check.

**Action needed (flagged to Priyansh for direct follow-up with Honghao):**
ask Honghao to commit the actual script/notebook that produced 97.3%, so the
number is reproducible by anyone on the team, not just reported verbally.
This doc and `verify_ces.py` should not be treated as "the" CES verification
— they're a corroborating sanity check that happens to confirm the same
underlying dataset facts.

## Fallback dataset (Corona Health) check

Weekly_Plan.md also asked Honghao to "confirm the fallback dataset (Corona
Health) by Wednesday if CES fails any check." Since CES passes every check
above, this doesn't apply — noted for the record so it isn't mistaken for an
unaddressed task.
