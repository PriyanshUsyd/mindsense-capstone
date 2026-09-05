"""
Tests for backend/statistics/mixed_effects_model.py — Moe Tanaka's Week 5
deliverable. Additive to tests/statistics/test_eligibility.py (Week 4's
22 cold-start tests); nothing there is modified or replaced.

Unit tests use small synthetic frames. The end-to-end test fits the real
model against the real local CES dataset and is skipped automatically
when that dataset isn't present (gitignored) — same pattern as
tests/integration/test_ces_eligibility_scripts_agree.py.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.statistics.mixed_effects_model import (
    ALIGNMENT_WINDOW_DAYS,
    OCCASION_MIN_VALID_SENSOR_DAYS,
    build_model_frame,
    build_trailing_predictor,
    fit_mixed_effects_model,
)

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


def _synthetic_sensing(uid: str, n_days: int, value: float = 5.0) -> pd.DataFrame:
    start = pd.Timestamp("2020-01-01")
    days = [int((start + pd.Timedelta(days=i)).strftime("%Y%m%d")) for i in range(n_days)]
    return pd.DataFrame({"uid": uid, "day": days, "loc_dist_ep_0_log": value})


def test_locked_constants_match_the_spec():
    assert ALIGNMENT_WINDOW_DAYS == 14
    assert OCCASION_MIN_VALID_SENSOR_DAYS == 7


def test_trailing_predictor_computes_calendar_correct_rolling_mean():
    sensing = _synthetic_sensing("a", n_days=20, value=10.0)
    # Introduce a gap and a different value for the last few days.
    sensing.loc[sensing.index[-3:], "loc_dist_ep_0_log"] = 20.0

    out = build_trailing_predictor(sensing, window_days=14)
    last_row = out.iloc[-1]
    # Trailing 14-day window ending on the last day: 11 days at 10.0, 3 days at 20.0.
    expected = (11 * 10.0 + 3 * 20.0) / 14
    assert last_row["x_it"] == pytest.approx(expected)
    assert last_row["valid_sensor_days_in_window"] == 14


def test_trailing_predictor_reindexes_gaps_as_invalid_not_missing_rows():
    sensing = pd.DataFrame(
        {
            "uid": ["a", "a"],
            "day": [20200101, 20200110],  # 9-day gap
            "loc_dist_ep_0_log": [5.0, 5.0],
        }
    )
    out = build_trailing_predictor(sensing, window_days=14)
    # The reindexed range must include the gap days, not just the two observed rows.
    assert len(out) == 10


def test_occasion_validity_gate_drops_not_imputes():
    """An EMA occasion whose trailing window has < 7 valid sensor-days
    must be excluded from the model frame entirely, not filled in."""
    sensing = _synthetic_sensing("a", n_days=14, value=5.0)
    # Blank out all but 3 days of sensing data.
    sensing = sensing.iloc[:3]

    ema = pd.DataFrame({"uid": ["a"], "day": [20200114], "phq4_score": [4.0]})
    frame = build_model_frame(sensing, ema, min_valid_sensor_days=7)
    assert len(frame) == 0


def test_within_and_between_person_centring():
    """Two participants with different mean travel levels: x_within must
    be centred on each person's own mean (so a person who always travels
    the same amount has x_within == 0 for every occasion), and x_between
    must separate the two people's overall levels."""
    sensing_a = _synthetic_sensing("a", n_days=20, value=5.0)  # constant
    sensing_b = _synthetic_sensing("b", n_days=20, value=10.0)  # constant, different level
    sensing = pd.concat([sensing_a, sensing_b], ignore_index=True)

    ema = pd.DataFrame(
        {
            "uid": ["a", "a", "b", "b"],
            "day": [20200115, 20200120, 20200115, 20200120],
            "phq4_score": [3.0, 4.0, 5.0, 6.0],
        }
    )
    frame = build_model_frame(sensing, ema)

    assert frame["x_within"].abs().max() < 1e-9  # constant feature -> always centred to ~0
    a_between = frame[frame["uid"] == "a"]["x_between"].iloc[0]
    b_between = frame[frame["uid"] == "b"]["x_between"].iloc[0]
    assert b_between > a_between  # b travels more on average than a


def test_fit_mixed_effects_model_on_synthetic_data_with_a_real_signal():
    """Builds a frame with a genuine within-person relationship (more
    travel -> lower PHQ-4) across many synthetic participants, and
    confirms the fit converges and recovers a negative x_within
    coefficient with reasonable precision."""
    rng = np.random.default_rng(42)
    rows = []
    for p in range(40):
        uid = f"synthetic_{p}"
        person_level = rng.normal(9.0, 0.5)
        for occasion in range(15):
            x_within_true = rng.normal(0.0, 1.0)
            x_it = person_level + x_within_true
            phq4 = 5.0 - 1.0 * x_within_true + rng.normal(0, 0.5)
            rows.append(
                {
                    "uid": uid,
                    "x_it": x_it,
                    "x_within": x_within_true,
                    "x_between": person_level - 9.0,
                    "phq4_score": phq4,
                }
            )
    frame = pd.DataFrame(rows)

    fit = fit_mixed_effects_model(frame)

    assert fit.converged
    assert fit.n_observations == len(frame)
    assert fit.n_groups == 40
    assert fit.params["x_within"] < 0  # recovers the true negative relationship
    assert fit.pvalues["x_within"] < 0.01  # 40 groups x 15 occasions with a strong true effect


def test_fallback_to_random_intercept_only_is_recorded_when_random_slope_fails():
    """Only 2 occasions per group is too few to estimate a per-group
    slope variance, which should make the random-slope model unstable
    (fail to converge, or yield a degenerate covariance) while the
    simpler random-intercept-only fallback can still fit real
    (non-degenerate) outcome/predictor variation. We assert the
    *contract*: converged is a real bool, and if a fallback happened,
    used_random_slope is False and fallback_reason is set."""
    rng = np.random.default_rng(7)
    rows = []
    for p in range(30):
        uid = f"tiny_{p}"
        for occasion in range(2):
            x_within = rng.normal(0.0, 1.0)
            rows.append(
                {
                    "uid": uid,
                    "x_within": x_within,
                    "x_between": rng.normal(0.0, 0.5),
                    "phq4_score": 5.0 - 0.5 * x_within + rng.normal(0, 1.0),
                }
            )
    frame = pd.DataFrame(rows)

    fit = fit_mixed_effects_model(frame)

    assert isinstance(fit.converged, bool)
    if not fit.used_random_slope:
        assert fit.fallback_reason is not None


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_end_to_end_fit_against_the_real_dataset():
    """Real dataset, real cleaning, real model fit — not fixtures."""
    from backend.data_pipeline.gps_distance_feature import build_gps_distance_feature, load_sensing_days

    sensing_days = load_sensing_days()
    cleaned = build_gps_distance_feature(sensing_days)
    ema = pd.read_csv(DATASET_DIR / "EMA" / "general_ema.csv", usecols=["uid", "day", "phq4_score"])

    frame = build_model_frame(cleaned, ema)
    assert len(frame) > 1000  # real data should yield thousands of valid occasions

    fit = fit_mixed_effects_model(frame)

    assert fit.converged
    assert fit.n_groups > 100  # most of the 220-participant cohort should contribute occasions
    assert "x_within" in fit.params
    assert "x_between" in fit.params
    assert np.isfinite(fit.params["x_within"])
    assert np.isfinite(fit.pvalues["x_within"])
