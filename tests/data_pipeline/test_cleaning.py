"""
Tests for backend/data_pipeline/cleaning.py against Moe Tanaka's locked
loc_dist_ep_0 spec (weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md
Section 1.4). Uses small synthetic frames so these don't depend on the
real (gitignored) CES dataset.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from backend.data_pipeline.cleaning import (
    GPS_IMPLAUSIBILITY_THRESHOLD_M,
    GPS_LOG_OFFSET_M,
    QUALITY_LOC_MIN_HOURS,
    clean_gps_distance,
)


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_locked_thresholds_match_the_spec():
    assert QUALITY_LOC_MIN_HOURS == 8
    assert GPS_IMPLAUSIBILITY_THRESHOLD_M == 500_000
    assert GPS_LOG_OFFSET_M == 1000


def test_quality_gate_drops_low_quality_days_to_na():
    df = _frame(
        [
            {"uid": "a", "quality_loc": 7, "loc_dist_ep_0": 5000.0},  # below 8h -> NA
            {"uid": "a", "quality_loc": 8, "loc_dist_ep_0": 5000.0},  # exactly 8h -> kept
        ]
    )
    out = clean_gps_distance(df)
    assert math.isnan(out.loc[0, "loc_dist_ep_0_clean"])
    assert out.loc[1, "loc_dist_ep_0_clean"] == 5000.0


def test_implausibility_filter_drops_not_caps():
    """500,001 m must become NaN, not clamped to 500,000."""
    df = _frame(
        [
            {"uid": "a", "quality_loc": 24, "loc_dist_ep_0": 500_001.0},
            {"uid": "a", "quality_loc": 24, "loc_dist_ep_0": 500_000.0},
        ]
    )
    out = clean_gps_distance(df)
    assert math.isnan(out.loc[0, "loc_dist_ep_0_clean"])
    assert out.loc[1, "loc_dist_ep_0_clean"] == 500_000.0


def test_genuine_zero_travel_day_is_kept_when_quality_is_sufficient():
    df = _frame(
        [
            {"uid": "a", "quality_loc": 24, "loc_dist_ep_0": 0.0},
            {"uid": "a", "quality_loc": 24, "loc_dist_ep_0": 100.0},
            {"uid": "a", "quality_loc": 24, "loc_dist_ep_0": 200.0},
        ]
    )
    out = clean_gps_distance(df)
    assert not math.isnan(out.loc[0, "loc_dist_ep_0_clean"])


def test_winsorization_is_per_person_not_global():
    """Person 'a' travels far routinely; person 'b' does not. A value that
    is an outlier for 'b' should not be clamped using 'a's distribution,
    and vice versa."""
    rows = [{"uid": "a", "quality_loc": 24, "loc_dist_ep_0": float(d)} for d in range(100, 100_000, 1000)]
    rows += [{"uid": "b", "quality_loc": 24, "loc_dist_ep_0": float(d)} for d in [100, 110, 120, 130, 140, 50_000]]
    df = _frame(rows)
    out = clean_gps_distance(df)

    b_rows = out[out["uid"] == "b"]
    # b's 50,000 m day is an outlier relative to b's own ~100-140 m days,
    # so it must be winsorized down, even though 50,000 is unremarkable
    # for 'a'.
    b_outlier_clean = b_rows[b_rows["loc_dist_ep_0"] == 50_000.0]["loc_dist_ep_0_clean"].iloc[0]
    assert b_outlier_clean < 50_000.0


def test_log_transform_uses_1000m_offset():
    df = _frame([{"uid": "a", "quality_loc": 24, "loc_dist_ep_0": 0.0}])
    out = clean_gps_distance(df)
    # With only one valid value, winsorization is a no-op (clip to itself).
    assert out.loc[0, "loc_dist_ep_0_clean"] == 0.0
    assert out.loc[0, "loc_dist_ep_0_log"] == pytest.approx(math.log(1000))


def test_row_count_and_order_are_preserved():
    df = _frame(
        [
            {"uid": "a", "quality_loc": 24, "loc_dist_ep_0": 100.0},
            {"uid": "a", "quality_loc": 3, "loc_dist_ep_0": 999_999.0},
            {"uid": "b", "quality_loc": 24, "loc_dist_ep_0": 200.0},
        ]
    )
    out = clean_gps_distance(df)
    assert len(out) == len(df)
    assert list(out["uid"]) == list(df["uid"])


def test_person_with_all_dropped_days_gets_all_na_not_a_crash():
    df = _frame(
        [
            {"uid": "a", "quality_loc": 1, "loc_dist_ep_0": 100.0},
            {"uid": "a", "quality_loc": 2, "loc_dist_ep_0": 200.0},
        ]
    )
    out = clean_gps_distance(df)
    assert out["loc_dist_ep_0_clean"].isna().all()
