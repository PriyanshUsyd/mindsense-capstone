from pathlib import Path

import pandas as pd


# Automatically detect the project root directory and locate the CES dataset within it.
#
# PATH FIX (2026-09-05, Priyansh/Integration-QA): this originally pointed at
# dataset/ces/, which doesn't match this repo's actual local dataset layout
# (dataset/EMA/, dataset/Sensing/ directly - no "ces" subfolder, same
# convention used by backend/data_pipeline/verify_ces.py and
# ces_eligibility.py). As committed, the script could not run against the
# real local dataset copy at all (FileNotFoundError on the very first
# check). Falls back to dataset/ces/ if that layout is ever used instead,
# so this still works for whichever convention is actually present.

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_DATASET_DIRECT = PROJECT_ROOT / "dataset"
_DATASET_CES_SUBDIR = PROJECT_ROOT / "dataset" / "ces"
CES_ROOT = _DATASET_DIRECT if (_DATASET_DIRECT / "EMA").exists() else _DATASET_CES_SUBDIR

EMA_FILE = CES_ROOT / "EMA" / "general_ema.csv"
SENSING_FILE = CES_ROOT / "Sensing" / "sensing.csv"


# Define the key fields required for CES dataset validation.

PARTICIPANT_COL = "uid"
TIME_COL = "day"
WELLBEING_COL = "phq4_score"


def check_files():
    # Verify that the actual CES data file exists.

    print("\n=== 1. FILE CHECK ===")

    required_files = {
        "EMA": EMA_FILE,
        "Sensing": SENSING_FILE,
    }

    for name, path in required_files.items():
        if path.exists():
            print(f"[PASS] {name}: {path}")
        else:
            print(f"[FAIL] {name}: {path}")
            raise FileNotFoundError(
                f"Required file not found: {path}"
            )


def load_data():

    print("\n=== 2. LOADING DATA ===")

    ema = pd.read_csv(
        EMA_FILE,
        usecols=[
            PARTICIPANT_COL,
            TIME_COL,
            WELLBEING_COL,
        ],
    )

    sensing = pd.read_csv(
        SENSING_FILE,
        usecols=[
            PARTICIPANT_COL,
            TIME_COL,
        ],
    )

    print(f"EMA rows loaded: {len(ema):,}")
    print(f"Sensing rows loaded: {len(sensing):,}")

    return ema, sensing


def participant_check(ema, sensing):
    # Check how many participants are eligible for use in the project.

    print("\n=== 3. PARTICIPANT COUNT ===")

    ema_participants = set(
        ema[PARTICIPANT_COL].dropna().unique()
    )

    sensing_participants = set(
        sensing[PARTICIPANT_COL].dropna().unique()
    )

    phq4_participants = set(
        ema.loc[
            ema[WELLBEING_COL].notna(),
            PARTICIPANT_COL,
        ].unique()
    )

    matched_participants = (
        sensing_participants & phq4_participants
    )

    print(f"EMA participants:            {len(ema_participants)}")
    print(f"Sensing participants:        {len(sensing_participants)}")
    print(f"Participants with PHQ-4:     {len(phq4_participants)}")
    print(f"Matched sensing + PHQ-4:     {len(matched_participants)}")

    return matched_participants


def phq4_repeat_density(ema):
    # Validate that the wellbeing outcome is measured repeatedly for each participant.

    print("\n=== 4. PHQ-4 REPEAT DENSITY ===")

    valid_phq4 = ema[
        ema[WELLBEING_COL].notna()
    ].copy()

    repeat_counts = (
        valid_phq4
        .groupby(PARTICIPANT_COL)[TIME_COL]
        .nunique()
    )

    if repeat_counts.empty:
        print("[FAIL] No valid PHQ-4 measurements found.")
        return

    print(
        f"Participants with >= 1 PHQ-4: "
        f"{(repeat_counts >= 1).sum()}"
    )

    print(
        f"Participants with >= 2 PHQ-4: "
        f"{(repeat_counts >= 2).sum()}"
    )

    print(
        f"Participants with >= 5 PHQ-4: "
        f"{(repeat_counts >= 5).sum()}"
    )

    print(
        f"Participants with >= 10 PHQ-4: "
        f"{(repeat_counts >= 10).sum()}"
    )

    print("\nPHQ-4 measurements per participant:")

    print(f"Minimum: {repeat_counts.min()}")
    print(f"Median:  {repeat_counts.median():.1f}")
    print(f"Mean:    {repeat_counts.mean():.1f}")
    print(f"Maximum: {repeat_counts.max()}")

    if (repeat_counts >= 2).sum() > 0:
        print(
            "\n[PASS] PHQ-4 is repeatedly measured "
            "for participants."
        )
    else:
        print(
            "\n[FAIL] PHQ-4 is not repeatedly measured."
        )


def observation_days_check(sensing):
    # Report longitudinal sensing coverage per participant.

    print("\n=== 5. SENSING OBSERVATION DAYS ===")

    observation_days = (
        sensing
        .dropna(subset=[PARTICIPANT_COL, TIME_COL])
        .groupby(PARTICIPANT_COL)[TIME_COL]
        .nunique()
    )

    print(f"Participants: {len(observation_days)}")

    print("\nObservation days per participant:")
    print(f"Minimum: {observation_days.min()}")
    print(f"Median:  {observation_days.median():.1f}")
    print(f"Mean:    {observation_days.mean():.1f}")
    print(f"Maximum: {observation_days.max()}")

    for threshold in [7, 14, 30]:
        count = (observation_days >= threshold).sum()

        print(
            f"Participants with >= {threshold} days: "
            f"{count} / {len(observation_days)}"
        )


def inspect_feature_columns():
    # Inspect the real CES sensing schema and identify candidate behavioural feature families.

    print("\n=== 6. FEATURE AVAILABILITY ===")

    sensing_columns = pd.read_csv(
        SENSING_FILE,
        nrows=0
    ).columns.tolist()

    print(f"Total sensing columns: {len(sensing_columns)}")

    feature_patterns = {
        "Mobility / Location": ["loc_"],
        "Physical Activity": ["act_"],
        "Unlock / Device Use": ["unlock"],
    }

    for feature_name, patterns in feature_patterns.items():

        matched_columns = [
            col
            for col in sensing_columns
            if any(pattern.lower() in col.lower()
                   for pattern in patterns)
        ]

        print(f"\n{feature_name}:")
        print(f"  Matching columns: {len(matched_columns)}")

        if matched_columns:
            print("  [PASS] Feature family found")

            for col in matched_columns[:10]:
                print(f"    - {col}")

            if len(matched_columns) > 10:
                print(
                    f"    ... and "
                    f"{len(matched_columns) - 10} more"
                )

        else:
            print("  [FAIL] No matching columns found")

def show_candidate_features():
    # Group the relevant CES fields into key feature families.
    # And evaluate and identify the daily features that are suitable for the Tier-1 feature set.

    print("\n=== 7. CANDIDATE TIER-1 FEATURES ===")

    sensing_columns = pd.read_csv(
        SENSING_FILE,
        nrows=0
    ).columns.tolist()

    keywords = [
        "loc_dist",
        "loc_entropy",
        "walking",
        "still",
        "unlock_num",
        "unlock_duration",
    ]

    for keyword in keywords:

        matches = [
            col for col in sensing_columns
            if keyword.lower() in col.lower()
        ]

        print(f"\n{keyword}: {len(matches)} columns")

        for col in matches:
            print(f"  - {col}")

def feature_completeness_check():
    # Check completeness of candidate Tier-1 behavioural features.


    print("\n=== 8. FEATURE COMPLETENESS ===")

    candidate_features = {
        "Mobility (distance travelled)": "loc_dist_ep_0",
        "Physical inactivity (still duration)": "act_still_ep_0",
        "Unlock frequency": "unlock_num_ep_0",
        "Device engagement (unlock duration)": "unlock_duration_ep_0",
    }

    required_cols = [
        PARTICIPANT_COL,
        TIME_COL,
        *candidate_features.values(),
    ]

    # Load only the required columns from the large sensing file
    df = pd.read_csv(
        SENSING_FILE,
        usecols=required_cols,
    )

    total_rows = len(df)
    total_participants = df[PARTICIPANT_COL].nunique()

    print(f"Rows evaluated: {total_rows:,}")
    print(f"Participants evaluated: {total_participants}")

    for feature_name, column in candidate_features.items():

        print(f"\n{feature_name}")
        print(f"CES field: {column}")

        # Row completeness

        valid_rows = df[column].notna().sum()

        non_null_rate = (
            valid_rows / total_rows * 100
            if total_rows > 0
            else 0
        )

        missing_rate = 100 - non_null_rate

        # Participant coverage

        participants_with_data = (
            df.loc[df[column].notna(), PARTICIPANT_COL]
            .nunique()
        )

        participant_coverage = (
            participants_with_data / total_participants * 100
            if total_participants > 0
            else 0
        )

        # Valid observation days

        valid_days = (
            df.loc[df[column].notna()]
            .groupby(PARTICIPANT_COL)[TIME_COL]
            .nunique()
        )

        print(
            f"  Non-null rows: "
            f"{valid_rows:,} / {total_rows:,} "
            f"({non_null_rate:.1f}%)"
        )

        print(
            f"  Missing rate: "
            f"{missing_rate:.1f}%"
        )

        print(
            f"  Participant coverage: "
            f"{participants_with_data} / "
            f"{total_participants} "
            f"({participant_coverage:.1f}%)"
        )

        if not valid_days.empty:

            print(
                f"  Valid days/person "
                f"(median): {valid_days.median():.1f}"
            )

            print(
                f"  Participants with >= 30 valid days: "
                f"{(valid_days >= 30).sum()} / "
                f"{total_participants}"
            )

        else:
            print("  [FAIL] No valid observations found")

def eligible_participant_check(ema, sensing):
    # Check how many participants are eligible for inclusion in the downstream statistical pipeline.

    """
    Eligibility criteria:
    1. At least 30 sensing observation days
    2. At least 2 valid PHQ-4 measurements
    3. Required Tier-1 features are available
    """

    print("\n=== 9. ELIGIBLE PARTICIPANT CHECK ===")

    MIN_SENSING_DAYS = 30
    MIN_PHQ4_MEASUREMENTS = 2

    tier1_features = [
        "loc_dist_ep_0",
        "unlock_duration_ep_0",
        "unlock_num_ep_0",
    ]

    # Participants with >= 30 sensing days

    sensing_days = (
        sensing
        .dropna(subset=[PARTICIPANT_COL, TIME_COL])
        .groupby(PARTICIPANT_COL)[TIME_COL]
        .nunique()
    )

    sensing_eligible = set(
        sensing_days[
            sensing_days >= MIN_SENSING_DAYS
        ].index
    )

    # Participants with >= 2 PHQ-4 measurements

    valid_phq4 = ema[
        ema[WELLBEING_COL].notna()
    ]

    phq4_counts = (
        valid_phq4
        .groupby(PARTICIPANT_COL)[TIME_COL]
        .nunique()
    )

    phq4_eligible = set(
        phq4_counts[
            phq4_counts >= MIN_PHQ4_MEASUREMENTS
        ].index
    )

    MIN_TIER1_VALID_DAYS = 30

    # 3. Load Tier-1 features
    tier1_df = pd.read_csv(
        SENSING_FILE,
        usecols=[
            PARTICIPANT_COL,
            TIME_COL,
            *tier1_features,
        ],
    )

    # Start with all sensing participants
    tier1_eligible = set(
        tier1_df[PARTICIPANT_COL].dropna().unique()
    )

    for feature in tier1_features:
        valid_days_per_participant = (
            tier1_df.loc[
                tier1_df[feature].notna()
            ]
            .groupby(PARTICIPANT_COL)[TIME_COL]
            .nunique()
        )

        participants_with_enough_feature_days = set(
            valid_days_per_participant[
                valid_days_per_participant >= MIN_TIER1_VALID_DAYS
                ].index
        )

        print(
            f"Participants with >= {MIN_TIER1_VALID_DAYS} valid days "
            f"for {feature}: "
            f"{len(participants_with_enough_feature_days)}"
        )

        tier1_eligible &= participants_with_enough_feature_days

    # Intersection of all requirements

    eligible = (
        sensing_eligible
        & phq4_eligible
        & tier1_eligible
    )

    total_participants = len(
        set(sensing[PARTICIPANT_COL].dropna().unique())
        | set(ema[PARTICIPANT_COL].dropna().unique())
    )

    # Report

    print(
        f"Participants with >= {MIN_SENSING_DAYS} sensing days: "
        f"{len(sensing_eligible)}"
    )

    print(
        f"Participants with >= {MIN_PHQ4_MEASUREMENTS} PHQ-4 measurements: "
        f"{len(phq4_eligible)}"
    )

    print(
        f"Participants with >= {MIN_TIER1_VALID_DAYS} valid days "
        f"for ALL required Tier-1 features: "
        f"{len(tier1_eligible)}"
    )

    print("-" * 55)

    print(
        f"FINAL ELIGIBLE PARTICIPANTS: "
        f"{len(eligible)} / {total_participants}"
    )

    if eligible:
        print("[PASS] Eligible cohort available for downstream analysis.")
    else:
        print("[FAIL] No participants satisfy the full data contract.")

    return eligible



def main():

    print("=" * 55)
    print("CES DATA CONTRACT VALIDATION")
    print("=" * 55)

    check_files()

    ema, sensing = load_data()

    participant_check(
        ema,
        sensing,
    )

    phq4_repeat_density(
        ema,
    )

    observation_days_check(
        sensing,
    )

    observation_days_check(
        sensing,
    )

    inspect_feature_columns()

    show_candidate_features()

    feature_completeness_check()

    eligible_participant_check(
        ema,
        sensing,
    )
    print("\n" + "=" * 55)
    print("FIRST-PASS VALIDATION COMPLETE")
    print("=" * 55)


if __name__ == "__main__":
    main()