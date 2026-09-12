"""
Tests for backend/statistics/run_tier1_evidence.py — confirms both
signed-off Tier-1 features (GPS distance, unlock frequency) actually run
through the full baseline/evidence pipeline, not just GPS alone.

FLAGGED FOR MOE TANAKA'S REVIEW, same as the unlock cleaning module and
the runner script itself: this is the first time unlock frequency has
been run through this pipeline, and its cleaning/transform choices are a
port, not a locked spec.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.statistics.run_tier1_evidence import FEATURES, load_sensing_and_ema, run_one_feature

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_both_features_registered():
    assert set(FEATURES) == {"gps_distance", "unlock_frequency"}


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_unlock_frequency_runs_end_to_end_against_the_real_dataset():
    """Real dataset, real cleaning, real model fit for the SECOND Tier-1
    feature -- this is the actual "extend to both features" check, not a
    synthetic-fixture stand-in."""
    sensing, ema = load_sensing_and_ema()

    result = run_one_feature("unlock_frequency", sensing, ema)

    assert result["n_occasions"] > 1000
    assert result["n_participants"] > 100
    assert result["primary_fit"]["converged"]
    assert result["primary_fit"]["x_within_beta"] is not None
    # This is a real fit result, not a hardcoded expectation on direction/
    # significance -- unlock frequency's association with PHQ-4 is an open
    # empirical question this run answers, not something to assert a
    # particular sign for.


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_gps_distance_still_runs_end_to_end_after_the_log_offset_fix():
    """Regression check: build_model_frame's new log_offset parameter
    must not have changed GPS's own behaviour (it defaults to
    GPS_LOG_OFFSET_M, same as before the parameter existed)."""
    sensing, ema = load_sensing_and_ema()

    result = run_one_feature("gps_distance", sensing, ema)

    assert result["n_occasions"] > 1000
    assert result["primary_fit"]["converged"]
    # Sign/magnitude sanity check against the previously-reported real
    # result (beta1 ~ -0.24 to -0.28 across engines) -- not an exact
    # pin, since the Python-fallback engine differs slightly run to run.
    assert result["primary_fit"]["x_within_beta"] < 0
