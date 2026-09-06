import numpy as np
import pandas as pd

from scripts.build_gps_feature import (
    PARTICIPANT_COL,
    DAY_COL,
    GPS_COL,
    QUALITY_LOC_COL,
    LOC_HOME_COL,
    UNLOCK_COL,
    PLATFORM_COL,
    clean_gps_base,
    clean_home_duration,
    clean_unlock,
    build_tier1_feature_windows,
)


def test_gps_quality_gate_and_cutoff():
    df = pd.DataFrame(
        {
            PARTICIPANT_COL: ["u1"] * 5,
            DAY_COL: pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-04",
                    "2026-01-05",
                ]
            ),
            GPS_COL: [
                1000,
                2000,
                500000,
                500001,
                0,
            ],
            QUALITY_LOC_COL: [
                11,
                12,
                12,
                12,
                12,
            ],
        }
    )

    out = clean_gps_base(
        df,
        quality_threshold=12,
        cutoff_m=500_000,
    )

    # quality < 12 -> NA
    assert np.isnan(out.loc[0, GPS_COL])

    # valid normal GPS value retained
    assert out.loc[1, GPS_COL] == 2000

    # exactly 500 km retained
    assert out.loc[2, GPS_COL] == 500000

    # strictly above 500 km -> NA
    assert np.isnan(out.loc[3, GPS_COL])

    # zero is valid
    assert out.loc[4, GPS_COL] == 0


def test_home_duration_cleaning():
    df = pd.DataFrame(
        {
            LOC_HOME_COL: [
                -1,
                0,
                12,
                24,
                24.01,
            ]
        }
    )

    out = clean_home_duration(df)

    # negative -> NA
    assert np.isnan(out.loc[0, LOC_HOME_COL])

    # zero retained
    assert out.loc[1, LOC_HOME_COL] == 0

    # normal value retained
    assert out.loc[2, LOC_HOME_COL] == 12

    # exactly 24 retained
    assert out.loc[3, LOC_HOME_COL] == 24

    # > 24 -> NA
    assert np.isnan(out.loc[4, LOC_HOME_COL])


def test_unlock_cleaning_zero_and_negative():
    df = pd.DataFrame(
        {
            PARTICIPANT_COL: [
                "u1",
                "u1",
                "u1",
                "u1",
                "u1",
            ],
            UNLOCK_COL: [
                -1,
                0,
                10,
                20,
                30,
            ],
        }
    )

    out = clean_unlock(df)

    # negative -> NA
    assert np.isnan(out.loc[0, UNLOCK_COL])

    # zero is retained
    assert out.loc[1, UNLOCK_COL] == 0

    # valid values remain non-missing
    assert out.loc[2, UNLOCK_COL] >= 0
    assert out.loc[3, UNLOCK_COL] >= 0
    assert out.loc[4, UNLOCK_COL] >= 0


def test_feature_window_excludes_ema_day():
    dates = pd.date_range(
        "2026-01-01",
        periods=16,
        freq="D",
    )

    sensing = pd.DataFrame(
        {
            PARTICIPANT_COL: ["u1"] * 16,
            DAY_COL: dates,
            GPS_COL: np.arange(1, 17, dtype=float),
            LOC_HOME_COL: np.arange(1, 17, dtype=float),
            UNLOCK_COL: np.arange(1, 17, dtype=float),
            PLATFORM_COL: [True] * 16,
        }
    )

    phq4 = pd.DataFrame(
        {
            PARTICIPANT_COL: ["u1"],
            DAY_COL: [pd.Timestamp("2026-01-16")],
            "phq4_score": [3.0],
        }
    )

    result = build_tier1_feature_windows(
        sensing,
        phq4,
        window_days=14,
        min_valid_days=7,
    )

    # Window should be:
    # 2026-01-02 through 2026-01-15
    assert (
        result["window_start"]
        == pd.Timestamp("2026-01-02")
    ).all()

    assert (
        result["window_end"]
        == pd.Timestamp("2026-01-15")
    ).all()

    # All 14 days present
    assert (result["observed_days"] == 14).all()
    assert (result["expected_days"] == 14).all()
    assert (result["coverage_ratio"] == 1.0).all()
    assert result["occasion_valid"].all()
    assert (result["platform"] == "iOS").all()


def test_feature_window_minimum_valid_days():
    dates = pd.date_range(
        "2026-01-01",
        periods=14,
        freq="D",
    )

    sensing = pd.DataFrame(
        {
            PARTICIPANT_COL: ["u1"] * 14,
            DAY_COL: dates,
            GPS_COL: [
                1,
                2,
                3,
                4,
                5,
                6,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                np.nan,
            ],
            LOC_HOME_COL: [5.0] * 14,
            UNLOCK_COL: [10.0] * 14,
            PLATFORM_COL: [True] * 14,
        }
    )

    phq4 = pd.DataFrame(
        {
            PARTICIPANT_COL: ["u1"],
            DAY_COL: [pd.Timestamp("2026-01-15")],
            "phq4_score": [2.0],
        }
    )

    result = build_tier1_feature_windows(
        sensing,
        phq4,
        window_days=14,
        min_valid_days=7,
    )

    gps_row = result[
        result["feature_id"]
        == "mobility_distance"
    ].iloc[0]

    home_row = result[
        result["feature_id"]
        == "home_duration"
    ].iloc[0]

    unlock_row = result[
        result["feature_id"]
        == "unlock_frequency"
    ].iloc[0]

    # GPS only has 6 valid days -> invalid
    assert gps_row["observed_days"] == 6
    assert not gps_row["occasion_valid"]
    assert np.isnan(gps_row["value"])
    assert (
        gps_row["quality_flags"]
        == "insufficient_coverage"
    )

    # Home and unlock have 14 valid days -> valid
    assert home_row["occasion_valid"]
    assert unlock_row["occasion_valid"]


def test_feature_window_marks_mixed_platform():
    dates = pd.date_range(
        "2026-01-01",
        periods=14,
        freq="D",
    )

    sensing = pd.DataFrame(
        {
            PARTICIPANT_COL: ["u1"] * 14,
            DAY_COL: dates,
            GPS_COL: [1000.0] * 14,
            LOC_HOME_COL: [10.0] * 14,
            UNLOCK_COL: [50.0] * 14,
            PLATFORM_COL: (
                [True] * 7
                + [False] * 7
            ),
        }
    )

    phq4 = pd.DataFrame(
        {
            PARTICIPANT_COL: ["u1"],
            DAY_COL: [pd.Timestamp("2026-01-15")],
            "phq4_score": [3.0],
        }
    )

    result = build_tier1_feature_windows(
        sensing,
        phq4,
        window_days=14,
        min_valid_days=7,
    )

    assert (result["platform"] == "mixed").all()