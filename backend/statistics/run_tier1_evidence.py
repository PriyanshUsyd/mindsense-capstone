"""
Runs the full baseline/evidence pipeline for BOTH signed-off Tier-1
features (`feature-list-signoff.md`: `loc_dist_ep_0` + `unlock_num_ep_0`)
against the real local CES dataset, and reports real output for each —
not synthetic numbers.

This is the "extend baseline/evidence logic to both features" Week 6 task
(Weekly_Plan.md, Statistical Analysis Lead) actually wired end to end:
cleaning -> `build_model_frame` -> `fit_mixed_effects_model` /
`fit_ar1_effect` -> `evidence.extract_person_slopes` /
`evidence.reclassify_family213`, run once per feature, same architecture
GPS distance already used on its own (each Tier-1 feature gets its own
confirmatory model and its own family-213 correction — that per-feature
family design is unchanged here, not redesigned).

**FLAGGED FOR MOE TANAKA'S REVIEW, same as the unlock cleaning module:**
this is the first time unlock frequency has been run through this
pipeline at all. Nothing here is a finalised statistical result — see
`backend/data_pipeline/cleaning.py::clean_unlock_frequency`'s docstring
for the specific methodology calls (no quality gate available for
unlock; `log(mean + 1)` transform) that still need her sign-off.

Run: python -m backend.statistics.run_tier1_evidence
(needs the real CES dataset downloaded locally per Readme.md — gitignored.)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from backend.data_pipeline.cleaning import UNLOCK_LOG_OFFSET, GPS_LOG_OFFSET_M
from backend.data_pipeline.gps_distance_feature import build_gps_distance_feature
from backend.data_pipeline.unlock_frequency_feature import build_unlock_frequency_feature
from backend.statistics import evidence
from backend.statistics.mixed_effects_model import build_model_frame, fit_ar1_effect, fit_mixed_effects_model

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"

FEATURES = {
    "gps_distance": {
        "raw_col": "loc_dist_ep_0",
        "clean_col": "loc_dist_ep_0_clean",
        "log_offset": GPS_LOG_OFFSET_M,
        "clean_fn": build_gps_distance_feature,
    },
    "unlock_frequency": {
        "raw_col": "unlock_num_ep_0",
        "clean_col": "unlock_num_ep_0_clean",
        "log_offset": UNLOCK_LOG_OFFSET,
        "clean_fn": build_unlock_frequency_feature,
    },
}


def load_sensing_and_ema() -> tuple[pd.DataFrame, pd.DataFrame]:
    sensing = pd.read_csv(
        DATASET_DIR / "Sensing" / "sensing.csv",
        usecols=["uid", "day", "quality_loc", "loc_dist_ep_0", "unlock_num_ep_0"],
    ).sort_values(["uid", "day"]).reset_index(drop=True)
    ema = pd.read_csv(DATASET_DIR / "EMA" / "general_ema.csv", usecols=["uid", "day", "phq4_score"])
    return sensing, ema


def run_one_feature(feature_name: str, sensing: pd.DataFrame, ema: pd.DataFrame) -> dict:
    spec = FEATURES[feature_name]
    cleaned = spec["clean_fn"](sensing)

    frame = build_model_frame(cleaned, ema, value_col=spec["clean_col"], log_offset=spec["log_offset"])

    fit = fit_mixed_effects_model(frame)
    ar1 = fit_ar1_effect(frame)

    result: dict = {
        "feature": feature_name,
        "n_occasions": len(frame),
        "n_participants": int(frame["uid"].nunique()),
        "primary_fit": {
            "engine": fit.engine,
            "converged": fit.converged,
            "used_random_slope": fit.used_random_slope,
            "x_within_beta": fit.params.get("x_within"),
            "x_within_p": fit.pvalues.get("x_within"),
            "denom_df_method": fit.denom_df_method,
        },
        "ar1_fit": {
            "engine": ar1.engine,
            "ar1_coefficient": ar1.ar1_coefficient,
            "x_within_beta": ar1.params.get("x_within"),
            "fallback_reason": ar1.fallback_reason,
        },
    }

    # Per-person evidence (Section 7) -- only reachable with real BLUPs,
    # i.e. only when the R engine actually ran. Report this honestly
    # rather than fabricate blups on the GEE fallback path.
    if ar1.blups is not None:
        person_slopes = evidence.extract_person_slopes(ar1, frame)
        outcome_sd = float(frame["phq4_score"].std())
        predictor_sd = float(frame["x_within"].std())
        evidence_table = evidence.reclassify_family213(person_slopes, outcome_sd, predictor_sd)
        result["evidence"] = {
            "family_size": len(evidence_table),
            "label_bh_counts": evidence_table["label_bh"].value_counts().to_dict(),
            "label_holm_counts": evidence_table["label_holm"].value_counts().to_dict(),
        }
    else:
        result["evidence"] = {
            "skipped_reason": (
                f"ar1_result has no BLUPs (engine={ar1.engine!r}) -- "
                "extract_person_slopes requires the R engine; see "
                "docs/statistics/r-bridge-setup.md. R is not usable in this "
                "environment (r_bridge.r_bridge_available() is False here), "
                "so per-person evidence classification cannot run for "
                "real in this sandbox for EITHER feature -- this is not "
                "specific to unlock."
            )
        }

    return result


def main() -> None:
    sensing, ema = load_sensing_and_ema()

    results = {name: run_one_feature(name, sensing, ema) for name in FEATURES}

    print(json.dumps(results, indent=2, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else o))


if __name__ == "__main__":
    main()
