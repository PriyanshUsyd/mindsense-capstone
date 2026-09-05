"""
GPS-distance feature builder, implementing the Week 5 Data Pipeline Lead
task from Weekly_Plan.md: "Build ONE feature end-to-end (GPS distance),
including real cleaning (timestamp alignment, missing-sensor handling,
outlier filtering)."

Builds the locked Tier-1 GPS feature (`loc_dist_ep_0`, per
skills/data-pipeline-ces.md and build-reference.md's 2-feature cap) from
the real local CES dataset, end to end:

  1. Load one row per participant-day from Sensing/sensing.csv (already
     one row per (uid, day) — see `test_no_duplicate_participant_days`
     for the timestamp-alignment check: no participant has two rows for
     the same calendar day, so no de-duplication/re-alignment step is
     needed beyond sorting by day, which this module also does).
  2. Apply Moe Tanaka's locked cleaning pipeline
     (backend.data_pipeline.cleaning.clean_gps_distance): quality gate,
     implausibility filter ("outlier filtering"), per-person
     winsorisation, log transform.
  3. Summarise real before/after row counts and feature statistics for
     the full 220-participant cohort.

STATUS: this is a real feature-builder run against the real dataset (the
same dataset/ copy verify_ces.py and ces_eligibility.py use, 97.3%
eligible) — not a hand-authored fixture. Output is aggregate-only
(no participant identifiers), per the privacy fix in
backend/data_pipeline/ces_eligibility.py / privacy/ces-uid-fix.md.

Run: python -m backend.data_pipeline.gps_distance_feature
(needs repo root on sys.path since it imports backend.data_pipeline.cleaning
— unlike verify_ces.py/ces_eligibility.py, which have no cross-module
imports and so can be run as a bare script. Requires the CES dataset
downloaded locally per Readme.md — gitignored.)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.data_pipeline.cleaning import clean_gps_distance

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
GPS_COL = "loc_dist_ep_0"
QUALITY_COL = "quality_loc"


def load_sensing_days() -> pd.DataFrame:
    """Loads one row per participant-day, sorted by participant then day
    (the "timestamp alignment" step — day is already a YYYYMMDD calendar
    date per row in this dataset, so alignment is sort-by-day, not a
    join/resample; see the module docstring)."""
    df = pd.read_csv(
        DATASET_DIR / "Sensing" / "sensing.csv",
        usecols=["uid", "day", QUALITY_COL, GPS_COL],
    )
    return df.sort_values(["uid", "day"]).reset_index(drop=True)


def build_gps_distance_feature(sensing_days: pd.DataFrame) -> pd.DataFrame:
    """Missing-sensor handling + outlier filtering, per Moe's locked
    Section 1.4 pipeline. Returns the input frame with
    `loc_dist_ep_0_clean` / `loc_dist_ep_0_log` columns added."""
    return clean_gps_distance(sensing_days, gps_col=GPS_COL, quality_col=QUALITY_COL)


def summarize(cleaned: pd.DataFrame) -> dict:
    clean_col = f"{GPS_COL}_clean"
    log_col = f"{GPS_COL}_log"

    n_rows_total = len(cleaned)
    n_rows_raw_present = int(cleaned[GPS_COL].notna().sum())
    n_rows_clean_present = int(cleaned[clean_col].notna().sum())
    n_rows_dropped_by_cleaning = n_rows_raw_present - n_rows_clean_present

    n_quality_gate_dropped = int(
        ((cleaned[QUALITY_COL] < 8) & cleaned[GPS_COL].notna()).sum()
    )
    n_implausibility_dropped = int(
        (
            (cleaned[QUALITY_COL] >= 8)
            & cleaned[GPS_COL].notna()
            & (cleaned[GPS_COL] > 500_000)
        ).sum()
    )
    n_genuine_zero_days_kept = int(
        ((cleaned[QUALITY_COL] >= 8) & (cleaned[GPS_COL] == 0)).sum()
    )

    clean_values = cleaned[clean_col].dropna()
    log_values = cleaned[log_col].dropna()

    per_participant_clean_days = (
        cleaned.dropna(subset=[clean_col]).groupby("uid").size()
    )

    return {
        "feature": GPS_COL,
        "n_participants": int(cleaned["uid"].nunique()),
        "n_participant_days_total": n_rows_total,
        "n_participant_days_raw_present": n_rows_raw_present,
        "n_participant_days_after_cleaning": n_rows_clean_present,
        "n_participant_days_dropped_by_cleaning": n_rows_dropped_by_cleaning,
        "dropped_breakdown": {
            "quality_gate_below_8h": n_quality_gate_dropped,
            "implausibility_filter_over_500km": n_implausibility_dropped,
        },
        "genuine_zero_travel_days_kept": n_genuine_zero_days_kept,
        "cleaned_distance_m_stats": {
            "count": int(clean_values.count()),
            "mean": round(float(clean_values.mean()), 2),
            "median": round(float(clean_values.median()), 2),
            "std": round(float(clean_values.std()), 2),
            "min": round(float(clean_values.min()), 2),
            "max": round(float(clean_values.max()), 2),
        },
        "log_transformed_stats": {
            "count": int(log_values.count()),
            "mean": round(float(log_values.mean()), 4),
            "median": round(float(log_values.median()), 4),
            "std": round(float(log_values.std()), 4),
        },
        "median_clean_days_per_participant": float(per_participant_clean_days.median()),
        "min_clean_days_per_participant": int(per_participant_clean_days.min()),
        "max_clean_days_per_participant": int(per_participant_clean_days.max()),
    }


def main() -> None:
    sensing_days = load_sensing_days()
    cleaned = build_gps_distance_feature(sensing_days)
    result = summarize(cleaned)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
