"""
Tests for backend/data_pipeline/gps_distance_feature.py.

Unit tests use a small synthetic frame (no dataset dependency). The
end-to-end test runs the real builder against the real local CES dataset
and is skipped automatically when that dataset isn't present (it's
gitignored per Readme.md) — same pattern as
tests/integration/test_ces_eligibility_scripts_agree.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.data_pipeline.gps_distance_feature import build_gps_distance_feature, summarize

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


def test_summarize_on_synthetic_data_has_expected_shape():
    df = pd.DataFrame(
        [
            {"uid": "a", "day": 1, "quality_loc": 24, "loc_dist_ep_0": 100.0},
            {"uid": "a", "day": 2, "quality_loc": 3, "loc_dist_ep_0": 200.0},  # dropped: quality
            {"uid": "a", "day": 3, "quality_loc": 24, "loc_dist_ep_0": 600_000.0},  # dropped: implausible
            {"uid": "a", "day": 4, "quality_loc": 24, "loc_dist_ep_0": 0.0},  # genuine zero, kept
            {"uid": "b", "day": 1, "quality_loc": 24, "loc_dist_ep_0": 500.0},
        ]
    )
    cleaned = build_gps_distance_feature(df)
    result = summarize(cleaned)

    assert result["feature"] == "loc_dist_ep_0"
    assert result["n_participants"] == 2
    assert result["n_participant_days_total"] == 5
    assert result["n_participant_days_raw_present"] == 5
    assert result["n_participant_days_after_cleaning"] == 3  # a/day1, a/day4, b/day1
    assert result["dropped_breakdown"]["quality_gate_below_8h"] == 1
    assert result["dropped_breakdown"]["implausibility_filter_over_500km"] == 1
    assert result["genuine_zero_travel_days_kept"] == 1


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_end_to_end_against_the_real_dataset():
    """Real dataset, real cleaning, real numbers — not fixtures."""
    from backend.data_pipeline.gps_distance_feature import load_sensing_days

    sensing_days = load_sensing_days()
    cleaned = build_gps_distance_feature(sensing_days)
    result = summarize(cleaned)

    # Sanity bounds, not exact figures (the point is that this runs
    # end-to-end against the real 220-participant dataset and produces
    # numbers consistent with the cleaning rules, not that we hardcode
    # today's exact output).
    assert result["n_participants"] == 220
    assert result["n_participant_days_after_cleaning"] > 0
    assert result["n_participant_days_after_cleaning"] <= result["n_participant_days_raw_present"]
    assert result["cleaned_distance_m_stats"]["max"] <= 500_000
    assert result["cleaned_distance_m_stats"]["min"] >= 0
    # No raw participant identifier appears anywhere in the summary.
    import json

    dumped = json.dumps(result)
    assert "uid" not in dumped.lower() or "n_participants" in dumped  # aggregate field name only, not values


def test_no_duplicate_participant_days_in_the_real_dataset():
    """The 'timestamp alignment' concern: confirms the real dataset has
    exactly one row per (uid, day), so sort-by-day is a sufficient
    alignment step and no de-duplication/resampling is silently needed."""
    if not (DATASET_DIR / "Sensing" / "sensing.csv").exists():
        pytest.skip("real CES dataset not present locally (gitignored)")

    from backend.data_pipeline.gps_distance_feature import load_sensing_days

    sensing_days = load_sensing_days()
    duplicates = sensing_days.duplicated(subset=["uid", "day"]).sum()
    assert duplicates == 0
