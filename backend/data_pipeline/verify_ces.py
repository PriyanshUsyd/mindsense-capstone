"""
CES dataset re-verification — Week 4 task (Honghao Li, Data Pipeline Lead),
per Weekly_Plan.md: "Re-verify CES against the real, current copy of the
data (participant count, PHQ-4 repeat density, feature completeness)."

STATUS: Honghao reported this check complete (97.3% eligible) in chat, but
as of 2026-08-29 no artifact existed anywhere in the repo recording it — see
docs/data-pipeline/ces-reverification.md for the writeup. This script was
built by Priyansh (Integration/QA) as an independent cross-check against the
same locked feature columns named in skills/data-pipeline-ces.md, run
against the actual local dataset/ copy, NOT to replace Honghao's own
pipeline code (which still needs to be built/committed by him for Week 5's
"Build ONE feature end-to-end" task).

Run: python backend/data_pipeline/verify_ces.py
(requires the CES dataset downloaded locally per Readme.md — gitignored)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"

# Locked Tier 1 feature columns, per skills/data-pipeline-ces.md.
GPS_COL = "loc_dist_ep_0"
UNLOCK_COL = "unlock_num_ep_0"


def verify() -> dict:
    sensing = pd.read_csv(DATASET_DIR / "Sensing" / "sensing.csv")
    ema = pd.read_csv(DATASET_DIR / "EMA" / "general_ema.csv")
    demographics = pd.read_csv(DATASET_DIR / "Demographics" / "demographics.csv")

    n_sensing_participants = sensing["uid"].nunique()
    n_demographics_participants = demographics["uid"].nunique() if "uid" in demographics.columns else None

    # PHQ-4 repeat density — participants with a non-null phq4_score.
    phq4 = ema.dropna(subset=["phq4_score"])
    n_phq4_participants = phq4["uid"].nunique()
    phq4_counts = phq4.groupby("uid").size()
    median_phq4_entries = float(phq4_counts.median())

    # Platform split.
    platform_counts = sensing.drop_duplicates("uid")["is_ios"].value_counts().to_dict()

    # Feature completeness on the two locked columns.
    has_gps = sensing[GPS_COL].notna()
    has_unlock = sensing[UNLOCK_COL].notna()
    per_participant = sensing.groupby("uid").agg(
        gps_observed_days=(GPS_COL, lambda s: s.notna().sum()),
        unlock_observed_days=(UNLOCK_COL, lambda s: s.notna().sum()),
        total_days=(GPS_COL, "size"),
    )
    per_participant["gps_coverage"] = per_participant["gps_observed_days"] / per_participant["total_days"]
    per_participant["unlock_coverage"] = per_participant["unlock_observed_days"] / per_participant["total_days"]

    # "Eligible" here = has at least one PHQ-4 entry AND non-trivial coverage
    # (>0) on both locked features at some point. This is a coarse
    # cross-check, not Honghao's actual eligibility pipeline logic (which
    # should use the trailing-window rule in
    # docs/statistics/model-and-coldstart-spec.md, not this whole-history
    # check).
    eligible_uids = set(per_participant[
        (per_participant["gps_observed_days"] > 0) & (per_participant["unlock_observed_days"] > 0)
    ].index) & set(phq4["uid"].unique())

    n_total_uids = set(sensing["uid"].unique()) | set(ema["uid"].unique())
    if n_demographics_participants:
        n_total_uids |= set(demographics["uid"].unique()) if "uid" in demographics.columns else set()

    eligible_pct = 100.0 * len(eligible_uids) / n_sensing_participants

    # 14 uids reported in skills/data-pipeline-ces.md as appearing under both
    # platforms — cross-check that claim too.
    platform_by_uid = sensing.groupby("uid")["is_ios"].nunique()
    dual_platform_uids = int((platform_by_uid > 1).sum())

    # GPS outlier check (skills/data-pipeline-ces.md notes ~1.21e9 outlier).
    gps_max = float(sensing[GPS_COL].max())

    result = {
        "n_sensing_participants": int(n_sensing_participants),
        "n_demographics_participants": int(n_demographics_participants) if n_demographics_participants else None,
        "n_phq4_participants": int(n_phq4_participants),
        "median_phq4_entries_per_participant": median_phq4_entries,
        "platform_counts_raw_is_ios_flag": {str(k): int(v) for k, v in platform_counts.items()},
        "dual_platform_uid_count": dual_platform_uids,
        "gps_distance_max_value_observed": gps_max,
        "n_eligible_participants_coarse_check": len(eligible_uids),
        "eligible_pct_coarse_check": round(eligible_pct, 1),
    }
    return result


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
