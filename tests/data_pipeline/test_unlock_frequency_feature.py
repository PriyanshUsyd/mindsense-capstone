"""
Tests for backend/data_pipeline/unlock_frequency_feature.py.

Same pattern as test_gps_distance_feature.py: unit tests use a small
synthetic frame (no dataset dependency); the end-to-end test runs the real
builder against the real local CES dataset and is skipped automatically
when that dataset isn't present (gitignored per Readme.md).

FLAGGED FOR MOE TANAKA'S REVIEW — see clean_unlock_frequency's docstring:
the thresholds this module exercises (no quality gate, log(mean + 1))
are a methodology port, not a locked spec like GPS's.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.data_pipeline.unlock_frequency_feature import build_unlock_frequency_feature, summarize

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


def test_summarize_on_synthetic_data_has_expected_shape():
    df = pd.DataFrame(
        [
            {"uid": "a", "day": 1, "unlock_num_ep_0": -1},  # dropped: impossible
            {"uid": "a", "day": 2, "unlock_num_ep_0": 0},  # genuine zero, kept
            {"uid": "a", "day": 3, "unlock_num_ep_0": 50},
            {"uid": "a", "day": 4, "unlock_num_ep_0": 60},
            {"uid": "b", "day": 1, "unlock_num_ep_0": 30},
        ]
    )
    cleaned = build_unlock_frequency_feature(df)
    result = summarize(cleaned)

    assert result["feature"] == "unlock_num_ep_0"
    assert result["n_participants"] == 2
    assert result["n_participant_days_total"] == 5
    assert result["n_participant_days_raw_present"] == 5
    assert result["n_participant_days_after_cleaning"] == 4  # a/day2,3,4 + b/day1
    assert result["dropped_breakdown"]["negative_count_impossible"] == 1
    assert result["genuine_zero_unlock_days_kept"] == 1


def test_negative_counts_are_impossible_and_zero_is_not_winsorised():
    """Zero-unlock days must never be clipped even when every other value
    in that person's history is winsorised — mirrors
    scripts/build_gps_feature.py::clean_unlock's semantics for this."""
    from backend.data_pipeline.cleaning import clean_unlock_frequency

    df = pd.DataFrame(
        {
            "uid": ["u1"] * 6,
            "unlock_num_ep_0": [0, 10, 20, 30, 40, 10_000],  # 10000 is an extreme outlier
        }
    )
    out = clean_unlock_frequency(df)

    assert out.loc[0, "unlock_num_ep_0_clean"] == 0  # zero untouched
    assert out.loc[5, "unlock_num_ep_0_clean"] < 10_000  # extreme value winsorised down


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_end_to_end_against_the_real_dataset():
    """Real dataset, real cleaning, real numbers — not fixtures."""
    from backend.data_pipeline.unlock_frequency_feature import load_sensing_days

    sensing_days = load_sensing_days()
    cleaned = build_unlock_frequency_feature(sensing_days)
    result = summarize(cleaned)

    assert result["n_participants"] == 220
    assert result["n_participant_days_total"] > 200_000
    # Cross-check against Week5_Statistical_Analysis_Deliverable.md item 15's
    # independently-reported zero-unlock-day count (3,736 of 216,065, 1.73%)
    # -- if this drifts, either the dataset copy or the cleaning logic
    # has changed and both should be looked at before trusting new numbers.
    assert result["genuine_zero_unlock_days_kept"] == 3736
