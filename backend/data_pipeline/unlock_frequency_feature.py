"""
Phone-unlock-frequency feature builder — the second signed-off Tier-1
feature (`feature-list-signoff.md`: `loc_dist_ep_0` + `unlock_num_ep_0`),
built the same way `gps_distance_feature.py` builds GPS distance: load one
row per participant-day, apply the locked cleaning pipeline
(`backend.data_pipeline.cleaning.clean_unlock_frequency`), summarise real
before/after counts.

**FLAGGED FOR MOE TANAKA'S REVIEW.** Unlike GPS distance, unlock's cleaning
thresholds are not locked anywhere in the Week 4/5 deliverables (those
documents only ever list `unlock_num_ep_0` as a *candidate* feature, never
lock concrete numbers for it the way §1.4 locks GPS's). This module ports
the existing standalone implementation
(`scripts/build_gps_feature.py::clean_unlock`) into `backend/` rather than
inventing new thresholds, but see
`backend.data_pipeline.cleaning.clean_unlock_frequency`'s docstring for the
specific methodology calls (no quality gate available; `log(mean + 1)`
transform) that still need her sign-off before being treated as final.

Run: python -m backend.data_pipeline.unlock_frequency_feature
(same requirements as gps_distance_feature.py: repo root on sys.path, real
CES dataset downloaded locally per Readme.md.)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.data_pipeline.cleaning import clean_unlock_frequency

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
UNLOCK_COL = "unlock_num_ep_0"


def load_sensing_days() -> pd.DataFrame:
    """Loads one row per participant-day, sorted by participant then day —
    same timestamp-alignment step as `gps_distance_feature.load_sensing_days`.
    No `quality_*` column is loaded here: CES has no unlock/screen quality
    field (see `clean_unlock_frequency`'s docstring)."""
    df = pd.read_csv(
        DATASET_DIR / "Sensing" / "sensing.csv",
        usecols=["uid", "day", UNLOCK_COL],
    )
    return df.sort_values(["uid", "day"]).reset_index(drop=True)


def build_unlock_frequency_feature(sensing_days: pd.DataFrame) -> pd.DataFrame:
    """Impossibility filtering + per-person winsorisation, per
    `clean_unlock_frequency`. Returns the input frame with
    `unlock_num_ep_0_clean` / `unlock_num_ep_0_log` columns added."""
    return clean_unlock_frequency(sensing_days, unlock_col=UNLOCK_COL)


def summarize(cleaned: pd.DataFrame) -> dict:
    clean_col = f"{UNLOCK_COL}_clean"
    log_col = f"{UNLOCK_COL}_log"

    n_rows_total = len(cleaned)
    n_rows_raw_present = int(cleaned[UNLOCK_COL].notna().sum())
    n_rows_clean_present = int(cleaned[clean_col].notna().sum())
    n_rows_dropped_by_cleaning = n_rows_raw_present - n_rows_clean_present

    n_negative_dropped = int((cleaned[UNLOCK_COL] < 0).sum())
    n_genuine_zero_days_kept = int((cleaned[clean_col] == 0).sum())

    clean_values = cleaned[clean_col].dropna()
    log_values = cleaned[log_col].dropna()

    per_participant_clean_days = cleaned.dropna(subset=[clean_col]).groupby("uid").size()

    return {
        "feature": UNLOCK_COL,
        "n_participants": int(cleaned["uid"].nunique()),
        "n_participant_days_total": n_rows_total,
        "n_participant_days_raw_present": n_rows_raw_present,
        "n_participant_days_after_cleaning": n_rows_clean_present,
        "n_participant_days_dropped_by_cleaning": n_rows_dropped_by_cleaning,
        "dropped_breakdown": {
            "negative_count_impossible": n_negative_dropped,
        },
        "genuine_zero_unlock_days_kept": n_genuine_zero_days_kept,
        "cleaned_count_stats": {
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
    cleaned = build_unlock_frequency_feature(sensing_days)
    result = summarize(cleaned)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
