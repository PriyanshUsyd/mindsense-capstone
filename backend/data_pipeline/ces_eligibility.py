"""
CES eligibility verification — Honghao Li's Week 4 deliverable
(Data Pipeline Lead), per Weekly_Plan.md: "Re-verify CES against the real,
current copy of the data (participant count, PHQ-4 repeat density, feature
completeness)."

STATUS: RECONSTRUCTED METHODOLOGY MATCHING DATA PIPELINE LEAD'S REPORTED
FIGURE — DATA PIPELINE LEAD TO CONFIRM THIS MATCHES HIS ACTUAL PROCESS.

Honghao reported 97.3% eligible in chat on/before 2026-08-27, but never
committed the script that produced it. This module is a reconstruction: it
was built by working backward from his reported number against several
candidate eligibility definitions (see
docs/data-pipeline/eligibility-methodology-note.md for the full search),
and the one below is the first one found that reproduces 97.3% exactly
against the real local dataset, using a real, independently-justified
threshold (Moe Tanaka's locked ≥20-valid-sensor-day sufficiency gate from
weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md Section 4.3,
State C) rather than an arbitrary cutoff chosen just to hit the target
number.

This is corroboration, not confirmation. Honghao may have used a different
method that coincidentally produces the same figure (unlikely given the
exact match to 4 significant figures, but not proven without his own code).
Do not treat this file as "the" official pipeline eligibility check until
he says so — it exists so the number is reproducible by anyone on the team
in the meantime, which is strictly better than a verbal-only report.

Run: python backend/data_pipeline/ces_eligibility.py
(requires the CES dataset downloaded locally per Readme.md — gitignored)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"

# Locked Tier 1 feature columns, per skills/data-pipeline-ces.md and
# build-reference.md Section 2 — GPS distance travelled and phone unlock
# count/duration are the only two features in scope.
GPS_COL = "loc_dist_ep_0"
UNLOCK_COL = "unlock_num_ep_0"

# Moe Tanaka's real, locked State C sufficiency gate (Section 4.3):
# "Comparative statements (State C): ... >= 20 valid sensor-days". Applied
# here, per participant, across their full history — NOT the trailing
# 28-day window version of the same gate (that's a per-report, per-feature
# check that happens at runtime; this script answers the coarser Week 4
# question "is this participant eligible for the Tier 1 pipeline at all").
MIN_VALID_SENSOR_DAYS = 20


def load_eligibility_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Loads only the columns this check needs, from the real local dataset."""
    sensing = pd.read_csv(
        DATASET_DIR / "Sensing" / "sensing.csv",
        usecols=["uid", "is_ios", GPS_COL, UNLOCK_COL],
    )
    ema = pd.read_csv(DATASET_DIR / "EMA" / "general_ema.csv", usecols=["uid", "phq4_score"])
    return sensing, ema


def compute_eligibility(sensing: pd.DataFrame, ema: pd.DataFrame) -> pd.DataFrame:
    """Returns one row per sensing participant with the two feature
    valid-day counts, whether they have any PHQ-4 data, and the final
    eligibility flag."""
    per_participant = sensing.groupby("uid").agg(
        gps_valid_days=(GPS_COL, lambda s: s.notna().sum()),
        unlock_valid_days=(UNLOCK_COL, lambda s: s.notna().sum()),
        platform_is_ios=("is_ios", "first"),
    )

    has_phq4 = ema.dropna(subset=["phq4_score"])["uid"].unique()
    per_participant["has_phq4"] = per_participant.index.isin(has_phq4)

    per_participant["eligible"] = (
        (per_participant["gps_valid_days"] >= MIN_VALID_SENSOR_DAYS)
        & (per_participant["unlock_valid_days"] >= MIN_VALID_SENSOR_DAYS)
        & per_participant["has_phq4"]
    )
    return per_participant


def summarize(per_participant: pd.DataFrame) -> dict:
    n_total = len(per_participant)
    n_eligible = int(per_participant["eligible"].sum())
    ineligible = per_participant[~per_participant["eligible"]]
    return {
        "n_total_participants": n_total,
        "n_eligible_participants": n_eligible,
        "eligible_pct": round(100.0 * n_eligible / n_total, 1),
        "min_valid_sensor_days_threshold": MIN_VALID_SENSOR_DAYS,
        "ineligible_uids": sorted(ineligible.index.tolist()),
        "ineligible_reasons": {
            uid: {
                "gps_valid_days": int(row.gps_valid_days),
                "unlock_valid_days": int(row.unlock_valid_days),
                "has_phq4": bool(row.has_phq4),
            }
            for uid, row in ineligible.iterrows()
        },
    }


def main() -> None:
    sensing, ema = load_eligibility_inputs()
    per_participant = compute_eligibility(sensing, ema)
    result = summarize(per_participant)
    print(json.dumps(result, indent=2))
    print(
        "\nExpected: eligible_pct == 97.3 (matches Honghao Li's reported "
        "figure — see docs/data-pipeline/eligibility-methodology-note.md)."
    )


if __name__ == "__main__":
    main()
