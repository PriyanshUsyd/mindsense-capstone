import pandas as pd

from scripts.validate_ces import (
    participant_check,
    phq4_repeat_density,
    observation_days_check,
    eligible_participant_check,
)


def test_participant_check_matches_sensing_and_phq4():
    """
    Only participants who have both sensing data and at least one
    valid PHQ-4 measurement should be returned.
    """
    ema = pd.DataFrame(
        {
            "uid": ["A", "A", "B", "C"],
            "day": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-01",
                "2026-01-01",
            ],
            "phq4_score": [2.0, 3.0, None, 4.0],
        }
    )

    sensing = pd.DataFrame(
        {
            "uid": ["A", "B", "D"],
            "day": [
                "2026-01-01",
                "2026-01-01",
                "2026-01-01",
            ],
        }
    )

    matched = participant_check(ema, sensing)

    assert matched == {"A"}


def test_phq4_repeat_density_counts_unique_days():
    """
    PHQ-4 repeat density should count unique measurement days,
    not duplicate rows.
    """
    ema = pd.DataFrame(
        {
            "uid": ["A", "A", "A", "B", "B"],
            "day": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-02",
                "2026-01-01",
                "2026-01-02",
            ],
            "phq4_score": [1.0, 2.0, 2.0, 3.0, None],
        }
    )

    repeat_counts = phq4_repeat_density(ema)

    assert repeat_counts["A"] == 2
    assert repeat_counts["B"] == 1


def test_observation_days_counts_unique_days():
    """
    Sensing coverage should count unique observation days
    per participant.
    """
    sensing = pd.DataFrame(
        {
            "uid": ["A", "A", "A", "B"],
            "day": [
                "2026-01-01",
                "2026-01-01",
                "2026-01-02",
                "2026-01-01",
            ],
        }
    )

    observation_days = observation_days_check(sensing)

    assert observation_days["A"] == 2
    assert observation_days["B"] == 1


def test_eligibility_requires_repeated_phq4():
    """
    A participant with enough sensing and Tier-1 coverage should
    still be excluded if fewer than two PHQ-4 occasions exist.
    """
    days = pd.date_range(
        "2026-01-01",
        periods=30,
        freq="D",
    ).strftime("%Y-%m-%d")

    sensing_rows = []

    for uid in ["A", "B"]:
        for day in days:
            sensing_rows.append(
                {
                    "uid": uid,
                    "day": day,
                }
            )

    sensing = pd.DataFrame(sensing_rows)

    ema = pd.DataFrame(
        {
            "uid": ["A", "A", "B"],
            "day": [
                "2026-02-01",
                "2026-02-15",
                "2026-02-01",
            ],
            "phq4_score": [2.0, 3.0, 4.0],
        }
    )

    tier1_rows = []

    for uid in ["A", "B"]:
        for day in days:
            tier1_rows.append(
                {
                    "uid": uid,
                    "day": day,
                    "loc_dist_ep_0": 5000.0,
                    "loc_home_dur": 12.0,
                    "unlock_num_ep_0": 80.0,
                }
            )

    tier1_df = pd.DataFrame(tier1_rows)

    eligible = eligible_participant_check(
        ema,
        sensing,
        tier1_df=tier1_df,
    )

    assert eligible == {"A"}


def test_eligibility_requires_all_tier1_features():
    """
    A participant must have at least 30 valid days for every
    locked Tier-1 feature.
    """
    days = pd.date_range(
        "2026-01-01",
        periods=30,
        freq="D",
    ).strftime("%Y-%m-%d")

    sensing_rows = []
    tier1_rows = []

    for uid in ["A", "B"]:
        for index, day in enumerate(days):
            sensing_rows.append(
                {
                    "uid": uid,
                    "day": day,
                }
            )

            tier1_rows.append(
                {
                    "uid": uid,
                    "day": day,
                    "loc_dist_ep_0": (
                        5000.0
                        if uid == "A" or index < 29
                        else None
                    ),
                    "loc_home_dur": 12.0,
                    "unlock_num_ep_0": 80.0,
                }
            )

    sensing = pd.DataFrame(sensing_rows)
    tier1_df = pd.DataFrame(tier1_rows)

    ema = pd.DataFrame(
        {
            "uid": ["A", "A", "B", "B"],
            "day": [
                "2026-02-01",
                "2026-02-15",
                "2026-02-01",
                "2026-02-15",
            ],
            "phq4_score": [2.0, 3.0, 4.0, 5.0],
        }
    )

    eligible = eligible_participant_check(
        ema,
        sensing,
        tier1_df=tier1_df,
    )

    assert eligible == {"A"}