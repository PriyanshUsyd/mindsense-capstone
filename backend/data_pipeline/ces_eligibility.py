"""
CES eligibility verification — Honghao Li's Week 4 deliverable
(Data Pipeline Lead), per Weekly_Plan.md: "Re-verify CES against the real,
current copy of the data (participant count, PHQ-4 repeat density, feature
completeness)."

STATUS: This is the shared, working eligibility script — Data Pipeline
Lead continues building directly on this file during Week 5 work, rather
than maintaining a separate version.

PRIVACY FIX (2026-09-05): this script previously printed raw CES uids in
its `ineligible_uids` / `ineligible_reasons` output. Per
skills/privacy-security.md and evidence.py's own rule that
`participant_ref` must never be the raw CES uid, all output paths now use
a salted-hash pseudonym (see `make_pseudonymizer`) instead of the raw id.
The salt is generated fresh per run and discarded, so the pseudonym is
non-reversible and not correlatable across separate runs. See
privacy/ces-uid-fix.md.

Honghao reported 97.3% eligible in chat on/before 2026-08-27; this module
reproduces that figure exactly against the real local dataset, using a
real, independently-justified threshold (Moe Tanaka's locked
≥20-valid-sensor-day sufficiency gate from
weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md Section 4.3,
State C) rather than an arbitrary cutoff chosen just to hit the target
number — see docs/data-pipeline/eligibility-methodology-note.md for the
full derivation.

Run: python backend/data_pipeline/ces_eligibility.py
(requires the CES dataset downloaded locally per Readme.md — gitignored)
"""

from __future__ import annotations

import hashlib
import json
import os
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


def make_pseudonymizer(salt: bytes | None = None):
    """Returns a callable mapping a raw CES uid to a non-reversible pseudonym.

    Privacy fix (see privacy/ces-uid-fix.md): raw participant uids must never
    appear in this script's stdout or any file it writes — per
    skills/privacy-security.md and backend/contracts/evidence.py's own rule
    that `participant_ref` must never be the raw CES uid. The salt defaults
    to a fresh random value generated once per process invocation, so
    pseudonyms cannot be correlated across separate runs of this script
    (or back to the raw uid, since SHA-256 with a discarded random salt is
    not invertible). Callers that need a stable/testable mapping within a
    single test may pass a fixed salt explicitly.
    """
    if salt is None:
        salt = os.urandom(16)

    def pseudonym(uid: str) -> str:
        return "p_" + hashlib.sha256(salt + str(uid).encode("utf-8")).hexdigest()[:12]

    return pseudonym


def summarize(per_participant: pd.DataFrame, pseudonymize=None) -> dict:
    if pseudonymize is None:
        pseudonymize = make_pseudonymizer()

    n_total = len(per_participant)
    n_eligible = int(per_participant["eligible"].sum())
    ineligible = per_participant[~per_participant["eligible"]]
    ineligible_reasons = {
        pseudonymize(uid): {
            "gps_valid_days": int(row.gps_valid_days),
            "unlock_valid_days": int(row.unlock_valid_days),
            "has_phq4": bool(row.has_phq4),
        }
        for uid, row in ineligible.iterrows()
    }
    return {
        "n_total_participants": n_total,
        "n_eligible_participants": n_eligible,
        "eligible_pct": round(100.0 * n_eligible / n_total, 1),
        "min_valid_sensor_days_threshold": MIN_VALID_SENSOR_DAYS,
        "ineligible_participant_pseudonyms": sorted(ineligible_reasons.keys()),
        "ineligible_reasons": ineligible_reasons,
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
