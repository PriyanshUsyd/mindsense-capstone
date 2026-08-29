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

## On the 97.3% eligible figure specifically — RECONCILED 2026-08-29

**Resolved — see `docs/data-pipeline/eligibility-methodology-note.md` for
the full writeup.** Short version: the original coarse check above (98.2%)
counted "any data ever" as eligible. Re-running with the real ≥20-valid-
sensor-day threshold from Moe Tanaka's locked statistics spec
(`weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md` Section
4.3) gives **214/220 = 97.27% → 97.3%**, matching Honghao's reported number
exactly. **97.3% is now the official figure**, using this "gated"
definition (`backend/data_pipeline/verify_ces.py`'s `eligible_pct_OFFICIAL`).

**Still pending:** Honghao's own script/notebook that originally produced
97.3% still hasn't been committed anywhere — this reconstruction matches
his number exactly, but that's independent corroboration, not confirmation
of his exact method. Flagged to Priyansh: ask Honghao to commit his real
script or confirm this matches his intent.

## Fallback dataset (Corona Health) check

Weekly_Plan.md also asked Honghao to "confirm the fallback dataset (Corona
Health) by Wednesday if CES fails any check." Since CES passes every check
above, this doesn't apply — noted for the record so it isn't mistaken for an
unaddressed task.
