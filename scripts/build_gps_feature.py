from pathlib import Path

import numpy as np
import pandas as pd

import statsmodels.formula.api as smf


# Paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = PROJECT_ROOT / "dataset"


def resolve_ces_root():
    """
    Locate the CES dataset only when real data access is required.

    Keeping dataset resolution inside a function makes this module safe
    to import in tests and CI environments where the gitignored CES
    dataset is not present.
    """

    direct_root = DATASET_ROOT
    nested_root = DATASET_ROOT / "ces"

    if (
        (direct_root / "Sensing").exists()
        and (direct_root / "EMA").exists()
    ):
        return direct_root

    if (
        (nested_root / "Sensing").exists()
        and (nested_root / "EMA").exists()
    ):
        return nested_root

    raise FileNotFoundError(
        "Could not locate CES dataset. Expected either "
        "'dataset/Sensing' and 'dataset/EMA', or "
        "'dataset/ces/Sensing' and 'dataset/ces/EMA'."
    )


def get_ces_files():
    """
    Resolve the real CES sensing and EMA files lazily.
    """

    ces_root = resolve_ces_root()

    sensing_file = ces_root / "Sensing" / "sensing.csv"
    ema_file = ces_root / "EMA" / "general_ema.csv"

    return sensing_file, ema_file

# CES fields

PARTICIPANT_COL = "uid"
DAY_COL = "day"

GPS_COL = "loc_dist_ep_0"
PHQ4_COL = "phq4_score"
QUALITY_LOC_COL = "quality_loc"
LOC_HOME_COL = "loc_home_dur"
UNLOCK_COL = "unlock_num_ep_0"
PLATFORM_COL = "is_ios"

def load_gps():
    """
    Load only the CES fields required for the GPS
    vertical slice.
    """

    print("\n=== 1. LOAD GPS DISTANCE ===")
    sensing_file, _ = get_ces_files()
    df = pd.read_csv(
        sensing_file,
        usecols=[
            PARTICIPANT_COL,
            DAY_COL,
            GPS_COL,
            QUALITY_LOC_COL,
            LOC_HOME_COL,
            UNLOCK_COL,
            PLATFORM_COL,
        ],
    )

    print(f"Rows loaded: {len(df):,}")
    print(
        f"Participants: "
        f"{df[PARTICIPANT_COL].nunique()}"
    )

    return df


def standardise_dates(df):
    """
    Convert CES YYYYMMDD day values into pandas dates.
    """

    print("\n=== 2. DATE STANDARDISATION ===")

    df = df.copy()

    df[DAY_COL] = pd.to_datetime(
        df[DAY_COL].astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    invalid_dates = df[DAY_COL].isna().sum()

    print(f"Invalid dates: {invalid_dates:,}")

    return df


def audit_gps_values(df):
    """
    Inspect GPS-distance quality before applying
    the final project cleaning policy.
    """

    print("\n=== 3. GPS QUALITY AUDIT ===")

    gps = pd.to_numeric(
        df[GPS_COL],
        errors="coerce",
    )

    print(f"Total rows: {len(gps):,}")
    print(f"Missing GPS values: {gps.isna().sum():,}")
    print(f"Non-null GPS values: {gps.notna().sum():,}")

    print(
        f"Negative GPS values: "
        f"{(gps < 0).sum():,}"
    )

    print(
        f"Zero GPS values: "
        f"{(gps == 0).sum():,}"
    )

    valid = gps.dropna()

    if not valid.empty:
        print("\nGPS distance distribution (metres/day):")

        print(f"Minimum: {valid.min():,.2f}")
        print(f"Median:  {valid.median():,.2f}")
        print(f"Mean:    {valid.mean():,.2f}")
        print(f"Maximum: {valid.max():,.2f}")

        print("\nUpper percentiles:")

        for q in [0.95, 0.99, 0.999, 0.9999]:
            print(
                f"{q * 100:>6.2f}%: "
                f"{valid.quantile(q):,.2f}"
            )

def sanity_bound_diagnostic(df):
    """
    Audit candidate Tier-1 features before defining
    cleaning rules.

    This stage DOES NOT modify data.
    It only reports theoretical violations and
    empirical distributions.
    """

    print("\n" + "=" * 60)
    print("TIER-1 SANITY-BOUND DIAGNOSTIC")
    print("=" * 60)

    feature_specs = {
        LOC_HOME_COL: {
            "unit": "hours/day",
            "min": 0,
            "max": 24,
        },
        UNLOCK_COL: {
            "unit": "count/day",
            "min": 0,
            "max": None,   # no theoretical upper bound
        },
    }

    for feature, spec in feature_specs.items():

        values = pd.to_numeric(
            df[feature],
            errors="coerce",
        )

        print(f"\n--- {feature} ---")
        print(f"Unit: {spec['unit']}")

        print(f"Total rows: {len(values):,}")
        print(f"Missing values: {values.isna().sum():,}")
        print(f"Valid values: {values.notna().sum():,}")

        negatives = (values < spec["min"]).sum()
        print(f"Negative values: {negatives:,}")

        if spec["max"] is not None:
            above_max = (values > spec["max"]).sum()
            print(
                f"Values above {spec['max']}: "
                f"{above_max:,}"
            )

        valid = values.dropna()

        print("\nDistribution:")

        print(valid.describe(
            percentiles=[
                0.50,
                0.90,
                0.95,
                0.99,
                0.999,
            ]
        ).to_string())

        print("\nMaximum values:")

        print(
            valid.nlargest(10)
            .to_string(index=False)
        )

def unlock_zero_day_diagnostic(df):
    """
    Audit zero-valued unlock days.

    Zero unlock counts may represent genuine behaviour,
    but may also reflect missing screen/device sensing.
    This diagnostic does not recode zero values.
    """

    print("\n" + "=" * 60)
    print("UNLOCK ZERO-DAY DIAGNOSTIC")
    print("=" * 60)

    data = df.copy()

    data[UNLOCK_COL] = pd.to_numeric(
        data[UNLOCK_COL],
        errors="coerce",
    )

    total_rows = len(data)

    valid_mask = data[UNLOCK_COL].notna()
    zero_mask = valid_mask & (data[UNLOCK_COL] == 0)

    valid_days = int(valid_mask.sum())
    zero_days = int(zero_mask.sum())

    affected_participants = data.loc[
        zero_mask,
        PARTICIPANT_COL,
    ].nunique()

    total_participants = data[
        PARTICIPANT_COL
    ].nunique()

    print(f"Total participant-days: {total_rows:,}")
    print(f"Valid unlock days: {valid_days:,}")
    print(f"Zero unlock days: {zero_days:,}")

    if total_rows > 0:
        print(
            f"Zero days as % of all participant-days: "
            f"{zero_days / total_rows * 100:.2f}%"
        )

    if valid_days > 0:
        print(
            f"Zero days as % of valid unlock days: "
            f"{zero_days / valid_days * 100:.2f}%"
        )

    print(
        f"Participants with >=1 zero day: "
        f"{affected_participants} / {total_participants}"
    )

    if zero_days > 0:

        zero_counts = (
            data.loc[zero_mask]
            .groupby(PARTICIPANT_COL)
            .size()
        )

        print(
            f"Median zero days among affected participants: "
            f"{zero_counts.median():.1f}"
        )

        print(
            f"Maximum zero days for one participant: "
            f"{zero_counts.max():,}"
        )

def home_duration_violation_diagnostic(df):
    """
    Quantify impossible loc_home_dur values and determine
    whether violations are concentrated in a small number
    of participants or broadly distributed.
    """

    print("\n" + "=" * 60)
    print("HOME-DURATION VIOLATION DIAGNOSTIC")
    print("=" * 60)

    data = df.copy()

    data[LOC_HOME_COL] = pd.to_numeric(
        data[LOC_HOME_COL],
        errors="coerce",
    )

    total_rows = len(data)

    violation_mask = (
        data[LOC_HOME_COL].notna()
        & (
            (data[LOC_HOME_COL] < 0)
            | (data[LOC_HOME_COL] > 24)
        )
    )

    violation_days = int(
        violation_mask.sum()
    )

    affected_participants = data.loc[
        violation_mask,
        PARTICIPANT_COL,
    ].nunique()

    total_participants = data[
        PARTICIPANT_COL
    ].nunique()

    print(f"Total participant-days: {total_rows:,}")

    print(
        f"Impossible home-duration days: "
        f"{violation_days:,}"
    )

    if total_rows > 0:
        print(
            f"Violation rate: "
            f"{violation_days / total_rows * 100:.2f}%"
        )

    print(
        f"Participants affected: "
        f"{affected_participants} / {total_participants}"
    )

    if affected_participants > 0:

        counts = (
            data.loc[violation_mask]
            .groupby(PARTICIPANT_COL)
            .size()
            .sort_values(ascending=False)
        )

        print(
            f"Median violations among affected participants: "
            f"{counts.median():.1f}"
        )

        print(
            f"Maximum violations for one participant: "
            f"{counts.max():,}"
        )

        print("\nTop 10 participants by violations:")

        print(
            counts.head(10).to_string()
        )

        top_5_share = (
            counts.head(5).sum()
            / counts.sum()
            * 100
        )

        print(
            f"\nShare of violations from top 5 participants: "
            f"{top_5_share:.1f}%"
        )


def quality_gate_diagnostic(df):
    """
    Compare the day-count cost of requiring
    >= 8 hours vs >= 12 hours of valid location sensing.
    """

    print("\n=== 4. LOCATION QUALITY GATE DIAGNOSTIC ===")

    quality = pd.to_numeric(
        df[QUALITY_LOC_COL],
        errors="coerce",
    )

    gps = pd.to_numeric(
        df[GPS_COL],
        errors="coerce",
    )

    total_rows = len(df)

    print(f"Total participant-days: {total_rows:,}")
    print(
        f"Missing quality_loc: "
        f"{quality.isna().sum():,}"
    )

    for threshold in [8, 12]:

        valid_quality_mask = quality >= threshold

        # A usable GPS day needs both sufficient
        # location quality and a non-null GPS value.
        usable_mask = (
            valid_quality_mask
            & gps.notna()
        )

        valid_days = usable_mask.sum()

        participants = (
            df.loc[
                usable_mask,
                PARTICIPANT_COL,
            ]
            .nunique()
        )

        print(f"\nQuality threshold: >= {threshold} h")
        print(
            f"  Days passing quality gate: "
            f"{valid_quality_mask.sum():,}"
        )
        print(
            f"  Usable GPS days after quality gate: "
            f"{valid_days:,}"
        )
        print(
            f"  Participants with usable GPS: "
            f"{participants}"
        )

    usable_8h = (
        (quality >= 8)
        & gps.notna()
    ).sum()

    usable_12h = (
        (quality >= 12)
        & gps.notna()
    ).sum()

    additional_loss = usable_8h - usable_12h

    loss_pct = (
        additional_loss / usable_8h * 100
        if usable_8h > 0
        else 0
    )

    print("\n8 h → 12 h additional cost:")
    print(
        f"  GPS days lost: "
        f"{additional_loss:,}"
    )
    print(
        f"  Relative loss: "
        f"{loss_pct:.2f}%"
    )

def cold_start_sufficiency_diagnostic(
    df,
    quality_threshold=12,
    window_days=28,
    min_valid_days=20,
):
    """
    Re-verify the cold-start sufficiency rule after the
    locked location quality gate.

    Rule:
        >= 20 valid sensor-days within a 28-day window.

    For this diagnostic, a valid GPS sensor-day requires:
        - non-missing GPS distance
        - quality_loc >= 12 hours

    This check intentionally happens before cutoff and
    winsorisation, because the purpose is to re-check the
    sufficiency gate after tightening the quality threshold.
    """

    print("\n" + "=" * 60)
    print("COLD-START SUFFICIENCY DIAGNOSTIC")
    print("=" * 60)

    data = df.copy()

    data[GPS_COL] = pd.to_numeric(
        data[GPS_COL],
        errors="coerce",
    )

    data[QUALITY_LOC_COL] = pd.to_numeric(
        data[QUALITY_LOC_COL],
        errors="coerce",
    )

    # One row per participant-day.
    data = (
        data.sort_values(
            [PARTICIPANT_COL, DAY_COL]
        )
        .drop_duplicates(
            [PARTICIPANT_COL, DAY_COL],
            keep="last",
        )
    )

    data["valid_sensor_day"] = (
        data[GPS_COL].notna()
        & data[QUALITY_LOC_COL].notna()
        & (
            data[QUALITY_LOC_COL]
            >= quality_threshold
        )
    )

    participant_results = []

    for uid, group in data.groupby(
        PARTICIPANT_COL
    ):
        group = group.sort_values(DAY_COL)

        if group.empty:
            continue

        first_day = group[DAY_COL].min()
        window_end = (
            first_day
            + pd.Timedelta(days=window_days - 1)
        )

        first_window = group[
            (group[DAY_COL] >= first_day)
            & (group[DAY_COL] <= window_end)
        ]

        valid_days = int(
            first_window["valid_sensor_day"].sum()
        )

        participant_results.append(
            {
                PARTICIPANT_COL: uid,
                "window_start": first_day,
                "window_end": window_end,
                "expected_days": window_days,
                "valid_sensor_days": valid_days,
                "sufficient": (
                    valid_days >= min_valid_days
                ),
            }
        )

    result = pd.DataFrame(
        participant_results
    )

    sufficient = int(
        result["sufficient"].sum()
    )

    insufficient = int(
        (~result["sufficient"]).sum()
    )

    total = len(result)

    print(
        f"Quality threshold: "
        f">= {quality_threshold} h"
    )

    print(
        f"Cold-start window: "
        f"{window_days} days"
    )

    print(
        f"Sufficiency requirement: "
        f">= {min_valid_days} valid days"
    )

    print(
        f"Participants evaluated: "
        f"{total:,}"
    )

    print(
        f"Participants sufficient: "
        f"{sufficient:,}"
    )

    print(
        f"Participants insufficient: "
        f"{insufficient:,}"
    )

    if total > 0:
        print(
            f"Sufficiency rate: "
            f"{sufficient / total * 100:.1f}%"
        )

    print(
        f"Median valid days in first "
        f"{window_days}-day window: "
        f"{result['valid_sensor_days'].median():.1f}"
    )

    print(
        "\nValid-day distribution:"
    )

    print(
        result["valid_sensor_days"]
        .describe()
        .to_string()
    )

    return result

def rolling_baseline_sufficiency_diagnostic(
    gps_df,
    phq4_df,
    quality_threshold=12,
    baseline_days=28,
    min_valid_days=20,
):
    """
    Evaluate the rolling baseline sufficiency rule relative
    to each PHQ-4 assessment date.

    Locked 28-day baseline:
        [assessment_date - 42, assessment_date - 15]

    Locked comparison window:
        [assessment_date - 14, assessment_date - 1]

    A valid baseline GPS day requires:
        - non-missing GPS distance
        - quality_loc >= quality_threshold

    The baseline sufficiency rule is:
        >= 20 valid days within the 28-day baseline.
    """

    print("\n" + "=" * 60)
    print("ROLLING BASELINE SUFFICIENCY DIAGNOSTIC")
    print("=" * 60)

    gps = gps_df.copy()
    phq4 = phq4_df.copy()

    gps[GPS_COL] = pd.to_numeric(
        gps[GPS_COL],
        errors="coerce",
    )

    gps[QUALITY_LOC_COL] = pd.to_numeric(
        gps[QUALITY_LOC_COL],
        errors="coerce",
    )

    # One row per participant-day.
    gps = (
        gps.sort_values([PARTICIPANT_COL, DAY_COL])
        .drop_duplicates(
            [PARTICIPANT_COL, DAY_COL],
            keep="last",
        )
    )

    gps["valid_sensor_day"] = (
        gps[GPS_COL].notna()
        & gps[QUALITY_LOC_COL].notna()
        & (gps[QUALITY_LOC_COL] >= quality_threshold)
    )

    records = []

    for uid, participant_phq4 in phq4.groupby(PARTICIPANT_COL):

        participant_gps = gps[
            gps[PARTICIPANT_COL] == uid
        ].copy()

        if participant_gps.empty:
            continue

        for _, ema_row in participant_phq4.iterrows():

            assessment_date = ema_row[DAY_COL]

            # Locked rolling 28-day baseline:
            # [-42, -15]
            baseline_start = (
                assessment_date
                - pd.Timedelta(days=42)
            )

            baseline_end = (
                assessment_date
                - pd.Timedelta(days=15)
            )

            baseline = participant_gps[
                (participant_gps[DAY_COL] >= baseline_start)
                & (participant_gps[DAY_COL] <= baseline_end)
            ]

            valid_days = int(
                baseline["valid_sensor_day"].sum()
            )

            sufficient = (
                valid_days >= min_valid_days
            )

            records.append(
                {
                    PARTICIPANT_COL: uid,
                    "assessment_date": assessment_date,
                    "baseline_start": baseline_start,
                    "baseline_end": baseline_end,
                    "expected_days": baseline_days,
                    "valid_sensor_days": valid_days,
                    "sufficient": sufficient,
                }
            )

    result = pd.DataFrame(records)

    if result.empty:
        print("No rolling baseline occasions available.")
        return result

    total_occasions = len(result)

    sufficient_occasions = int(
        result["sufficient"].sum()
    )

    participants = result[
        PARTICIPANT_COL
    ].nunique()

    participants_with_sufficient = result.loc[
        result["sufficient"],
        PARTICIPANT_COL,
    ].nunique()

    print(
        f"Baseline window: "
        f"[assessment - 42, assessment - 15]"
    )

    print(
        f"Required valid days: "
        f">= {min_valid_days} / {baseline_days}"
    )

    print(
        f"Assessment occasions evaluated: "
        f"{total_occasions:,}"
    )

    print(
        f"Sufficient assessment occasions: "
        f"{sufficient_occasions:,} / "
        f"{total_occasions:,} "
        f"({sufficient_occasions / total_occasions * 100:.1f}%)"
    )

    print(
        f"Participants evaluated: "
        f"{participants:,}"
    )

    print(
        f"Participants with >=1 sufficient occasion: "
        f"{participants_with_sufficient:,} / "
        f"{participants:,} "
        f"({participants_with_sufficient / participants * 100:.1f}%)"
    )

    print(
        f"Median valid baseline days: "
        f"{result['valid_sensor_days'].median():.1f}"
    )

    print("\nValid baseline-day distribution:")

    print(
        result["valid_sensor_days"]
        .describe()
        .to_string()
    )

    return result

def gps_cutoff_diagnostic(df, quality_threshold=12):
    """
    Compare GPS hard-cutoff sensitivity at
    250 km, 500 km, and 1000 km per day.

    Only days that already pass the location-quality
    gate are considered.
    """

    print("\n=== 5. GPS HARD-CUTOFF DIAGNOSTIC ===")

    quality = pd.to_numeric(
        df[QUALITY_LOC_COL],
        errors="coerce",
    )

    gps = pd.to_numeric(
        df[GPS_COL],
        errors="coerce",
    )

    base_mask = (
        (quality >= quality_threshold)
        & gps.notna()
    )

    base = df.loc[
        base_mask,
        [
            PARTICIPANT_COL,
            DAY_COL,
            GPS_COL,
        ],
    ].copy()

    base[GPS_COL] = pd.to_numeric(
        base[GPS_COL],
        errors="coerce",
    )

    print(
        f"Quality gate used: "
        f">= {quality_threshold} h"
    )
    print(
        f"GPS days entering cutoff check: "
        f"{len(base):,}"
    )

    cutoffs = {
        "250 km": 250_000,
        "500 km": 500_000,
        "1000 km": 1_000_000,
    }

    for label, cutoff in cutoffs.items():

        extreme_mask = (
            base[GPS_COL] > cutoff
        )

        extreme_days = extreme_mask.sum()

        affected_participants = (
            base.loc[
                extreme_mask,
                PARTICIPANT_COL,
            ]
            .nunique()
        )

        remaining_days = (
            len(base) - extreme_days
        )

        print(f"\nCutoff: {label}")
        print(
            f"  Days set to NA: "
            f"{extreme_days:,}"
        )
        print(
            f"  Participants affected: "
            f"{affected_participants}"
        )
        print(
            f"  Remaining valid days: "
            f"{remaining_days:,}"
        )

def extreme_participant_diagnostic(
    df,
    quality_threshold=12,
    cutoff_m=500_000,
    top_n=15,
):
    """
    Check whether extreme GPS days are concentrated
    in a small number of participants.
    """

    print(
        "\n=== 6. EXTREME GPS PARTICIPANT DIAGNOSTIC ==="
    )

    quality = pd.to_numeric(
        df[QUALITY_LOC_COL],
        errors="coerce",
    )

    gps = pd.to_numeric(
        df[GPS_COL],
        errors="coerce",
    )

    extreme_mask = (
        (quality >= quality_threshold)
        & gps.notna()
        & (gps > cutoff_m)
    )

    extreme = df.loc[
        extreme_mask,
        [
            PARTICIPANT_COL,
            DAY_COL,
            GPS_COL,
        ],
    ].copy()

    print(
        f"Extreme threshold: "
        f">{cutoff_m / 1000:,.0f} km/day"
    )

    print(
        f"Extreme participant-days: "
        f"{len(extreme):,}"
    )

    print(
        f"Participants affected: "
        f"{extreme[PARTICIPANT_COL].nunique()}"
    )

    if extreme.empty:
        print("No extreme GPS observations found.")
        return

    counts = (
        extreme
        .groupby(PARTICIPANT_COL)
        .size()
        .sort_values(ascending=False)
    )

    print(
        f"\nTop {top_n} participants "
        f"by number of extreme GPS days:"
    )

    print(
        counts.head(top_n).to_string()
    )

    total_extreme = counts.sum()

    top_5_share = (
        counts.head(5).sum()
        / total_extreme
        * 100
    )

    print(
        f"\nShare of all extreme days "
        f"from top 5 participants: "
        f"{top_5_share:.1f}%"
    )

def clean_gps_base(
    df,
    quality_threshold=12,
    cutoff_m=500_000,
):
    """
    Base GPS cleaning before winsorisation / transformation.

    Cleaning order:
    1. quality_loc >= quality_threshold
    2. negative distance -> NA
    3. distance > cutoff_m -> NA
    4. valid zeros are preserved
    """

    out = df.copy()

    out[GPS_COL] = pd.to_numeric(
        out[GPS_COL],
        errors="coerce",
    )

    out[QUALITY_LOC_COL] = pd.to_numeric(
        out[QUALITY_LOC_COL],
        errors="coerce",
    )

    # Preserve original value for auditing.
    out["gps_distance_raw"] = out[GPS_COL]

    out["gps_quality_flag"] = "ok"

    # Existing missing GPS value
    missing_mask = out[GPS_COL].isna()
    out.loc[
        missing_mask,
        "gps_quality_flag"
    ] = "missing"

    # Day-validity gate FIRST
    low_quality_mask = (
        out[QUALITY_LOC_COL].isna()
        | (out[QUALITY_LOC_COL] < quality_threshold)
    )

    out.loc[
        low_quality_mask,
        GPS_COL
    ] = np.nan

    out.loc[
        low_quality_mask,
        "gps_quality_flag"
    ] = "insufficient_location_hours"

    # Invalid negative values
    negative_mask = out[GPS_COL] < 0

    out.loc[
        negative_mask,
        GPS_COL
    ] = np.nan

    out.loc[
        negative_mask,
        "gps_quality_flag"
    ] = "invalid_negative"

    # Hard implausibility cutoff
    extreme_mask = out[GPS_COL] > cutoff_m

    out.loc[
        extreme_mask,
        GPS_COL
    ] = np.nan

    out.loc[
        extreme_mask,
        "gps_quality_flag"
    ] = "above_distance_cutoff"

    return out

def build_cutoff_variants(df):
    print("\n=== GPS CUTOFF VARIANTS ===")

    cutoffs = {
        "250km": 250_000,
        "500km": 500_000,
        "1000km": 1_000_000,
    }

    variants = {}

    for label, cutoff_m in cutoffs.items():

        cleaned = clean_gps_base(
            df,
            quality_threshold=12,
            cutoff_m=cutoff_m,
        )

        valid_mask = cleaned[GPS_COL].notna()

        valid_days = int(valid_mask.sum())

        participants = cleaned.loc[
            valid_mask,
            PARTICIPANT_COL
        ].nunique()

        removed_by_cutoff = (
            cleaned["gps_quality_flag"]
            == "above_distance_cutoff"
        ).sum()

        print(f"\n--- {label} cutoff ---")
        print(
            f"Valid GPS participant-days: "
            f"{valid_days:,}"
        )
        print(
            f"Participants with valid GPS: "
            f"{participants}"
        )
        print(
            f"Days removed by cutoff: "
            f"{removed_by_cutoff:,}"
        )

        variants[label] = cleaned

    return variants

def build_phq4_windows(
    gps_df,
    phq4_df,
    window_days=14,
    min_valid_days=7,
):
    """
    Build GPS trailing windows aligned to PHQ-4 observations.

    The EMA day itself is excluded to avoid post-response leakage.

    Intended 14-day rule:
        window_start = EMA date - 14 days
        window_end   = EMA date - 1 day

    A PHQ-4 occasion is valid only when at least 7 cleaned
    GPS participant-days are available in the window.
    """

    print("\n=== BUILD PHQ-4 GPS WINDOWS ===")

    records = []

    gps_df = gps_df.copy()
    phq4_df = phq4_df.copy()

    for uid, participant_phq4 in phq4_df.groupby(PARTICIPANT_COL):

        participant_gps = gps_df[
            gps_df[PARTICIPANT_COL] == uid
        ].copy()

        if participant_gps.empty:
            continue

        participant_gps = participant_gps.sort_values(DAY_COL)

        for _, ema_row in participant_phq4.iterrows():

            ema_date = ema_row[DAY_COL]

            window_end = ema_date - pd.Timedelta(days=1)

            window_start = (
                ema_date
                - pd.Timedelta(days=window_days)
            )

            window = participant_gps[
                (participant_gps[DAY_COL] >= window_start)
                & (participant_gps[DAY_COL] <= window_end)
            ]

            valid_values = window[GPS_COL].dropna()

            observed_days = len(valid_values)
            expected_days = window_days

            coverage_ratio = (
                observed_days / expected_days
                if expected_days > 0
                else np.nan
            )

            occasion_valid = (
                observed_days >= min_valid_days
            )

            if occasion_valid:
                gps_mean = valid_values.mean()

                gps_sd = (
                    valid_values.std(ddof=1)
                    if observed_days >= 2
                    else np.nan
                )
            else:
                gps_mean = np.nan
                gps_sd = np.nan

            records.append(
                {
                    PARTICIPANT_COL: uid,
                    "ema_date": ema_date,
                    PHQ4_COL: ema_row[PHQ4_COL],
                    "window_start": window_start,
                    "window_end": window_end,
                    "expected_days": expected_days,
                    "observed_days": observed_days,
                    "coverage_ratio": coverage_ratio,
                    "occasion_valid": occasion_valid,
                    "gps_mean_m": gps_mean,
                    "gps_sd_m": gps_sd,
                }
            )

    result = pd.DataFrame(records)

    print(f"PHQ-4 occasions built: {len(result):,}")

    if not result.empty:
        valid_n = int(result["occasion_valid"].sum())

        print(
            f"Valid occasions (>= {min_valid_days} GPS days): "
            f"{valid_n:,}"
        )

        print(
            f"Invalid occasions: "
            f"{len(result) - valid_n:,}"
        )

        print(
            f"Participants represented: "
            f"{result[PARTICIPANT_COL].nunique()}"
        )

        print(
            f"Median observed GPS days/window: "
            f"{result['observed_days'].median():.1f}"
        )
        valid_windows = result[
            result["occasion_valid"]
        ]

        print(
            f"Participants surviving >={min_valid_days}-day gate: "
            f"{valid_windows[PARTICIPANT_COL].nunique():,}"
        )

    return result

def winsorise_percentile(df):
    """
    Per-person 1st-99th percentile winsorisation.
    Applied after quality gate and hard cutoff.
    """

    out = df.copy()

    lower = (
        out.groupby(PARTICIPANT_COL)[GPS_COL]
        .transform(lambda s: s.quantile(0.01))
    )

    upper = (
        out.groupby(PARTICIPANT_COL)[GPS_COL]
        .transform(lambda s: s.quantile(0.99))
    )

    valid_mask = out[GPS_COL].notna()

    out.loc[valid_mask, GPS_COL] = (
        out.loc[valid_mask, GPS_COL]
        .clip(
            lower=lower[valid_mask],
            upper=upper[valid_mask],
        )
    )

    return out

def clean_home_duration(df):
    """
    Final locked cleaning for loc_home_dur.

    Policy:
    - numeric coercion
    - values < 0 or > 24 hours/day -> NA
    - valid values in [0, 24] retained
    """
    out = df.copy()

    out[LOC_HOME_COL] = pd.to_numeric(
        out[LOC_HOME_COL],
        errors="coerce",
    )

    invalid = (
        (out[LOC_HOME_COL] < 0)
        | (out[LOC_HOME_COL] > 24)
    )

    out.loc[invalid, LOC_HOME_COL] = np.nan

    return out


def clean_unlock(df):
    """
    Final locked cleaning for unlock_num_ep_0.

    Policy:
    - numeric coercion
    - negative counts -> NA
    - zero is retained as a genuine zero
    - positive values use per-person 1st-99th percentile winsorisation
    - no unlock-specific quality gate is available
    """
    out = df.copy()

    out[UNLOCK_COL] = pd.to_numeric(
        out[UNLOCK_COL],
        errors="coerce",
    )

    # Negative counts are impossible.
    out.loc[
        out[UNLOCK_COL] < 0,
        UNLOCK_COL,
    ] = np.nan

    # Winsorise positive values only.
    # Genuine zero-unlock days must remain exactly zero.
    positive = out[UNLOCK_COL] > 0

    positive_values = out[UNLOCK_COL].where(positive)

    lower = positive_values.groupby(
        out[PARTICIPANT_COL]
    ).transform(
        lambda s: s.quantile(0.01)
    )

    upper = positive_values.groupby(
        out[PARTICIPANT_COL]
    ).transform(
        lambda s: s.quantile(0.99)
    )

    out.loc[positive, UNLOCK_COL] = (
        out.loc[positive, UNLOCK_COL]
        .clip(
            lower=lower[positive],
            upper=upper[positive],
        )
    )

    return out

def build_clean_tier1_daily(df):
    """
    Build the final cleaned daily Tier-1 sensing table.

    Tier-1:
    - loc_dist_ep_0
    - loc_home_dur
    - unlock_num_ep_0
    """

    out = df.copy()

    # -----------------------------------
    # GPS
    # -----------------------------------

    # Locked GPS cleaning:
    # quality_loc >= 12 h
    # > 500 km/day -> NA
    # zero retained
    gps_clean = clean_gps_base(
        out,
        quality_threshold=12,
        cutoff_m=500_000,
    )

    gps_clean = winsorise_percentile(
        gps_clean
    )

    out[GPS_COL] = gps_clean[GPS_COL]

    # -----------------------------------
    # Home duration
    # -----------------------------------

    home_clean = clean_home_duration(out)

    out[LOC_HOME_COL] = (
        home_clean[LOC_HOME_COL]
    )

    # -----------------------------------
    # Unlock frequency
    # -----------------------------------

    unlock_clean = clean_unlock(out)

    out[UNLOCK_COL] = (
        unlock_clean[UNLOCK_COL]
    )

    return out

def build_tier1_feature_windows(
    sensing,
    phq4,
    window_days=14,
    min_valid_days=7,
):
    """
    Build production-style Tier-1 FeatureWindow records
    aligned to each PHQ-4 assessment.

    Window:
        [EMA_date - 14, EMA_date - 1]

    Minimum coverage:
        >= 7 valid days

    Output:
        one row per participant x EMA occasion x feature
    """

    print("\n" + "=" * 60)
    print("BUILD FINAL TIER-1 FEATURE WINDOWS")
    print("=" * 60)

    records = []

    feature_specs = {
        GPS_COL: {
            "feature_id": "mobility_distance",
            "unit": "metres/day",
        },
        LOC_HOME_COL: {
            "feature_id": "home_duration",
            "unit": "hours/day",
        },
        UNLOCK_COL: {
            "feature_id": "unlock_frequency",
            "unit": "count/day",
        },
    }

    sensing_by_uid = {
        uid: group.sort_values(DAY_COL)
        for uid, group in sensing.groupby(
            PARTICIPANT_COL
        )
    }

    for _, ema_row in phq4.iterrows():

        uid = ema_row[PARTICIPANT_COL]
        ema_date = ema_row[DAY_COL]

        if uid not in sensing_by_uid:
            continue

        participant = sensing_by_uid[uid]

        window_start = (
            ema_date
            - pd.Timedelta(days=window_days)
        )

        window_end = (
            ema_date
            - pd.Timedelta(days=1)
        )

        window = participant[
            (participant[DAY_COL] >= window_start)
            & (participant[DAY_COL] <= window_end)
        ]

        platform_values = (
            window[PLATFORM_COL]
            .dropna()
            .unique()
        )

        if len(platform_values) == 1:
            platform = (
                "iOS"
                if bool(platform_values[0])
                else "Android"
            )
        elif len(platform_values) > 1:
            platform = "mixed"
        else:
            platform = "unknown"

        for column, spec in feature_specs.items():

            values = window[column].dropna()

            observed_days = len(values)
            expected_days = window_days

            coverage_ratio = (
                observed_days / expected_days
            )

            valid = (
                observed_days >= min_valid_days
            )

            if valid:
                value = values.mean()
            else:
                value = np.nan

            quality_flags = []

            if observed_days == 0:
                quality_flags.append(
                    "no_valid_days"
                )
            elif not valid:
                quality_flags.append(
                    "insufficient_coverage"
                )

            records.append(
                {
                    PARTICIPANT_COL: uid,
                    "ema_date": ema_date,
                    PHQ4_COL: ema_row[PHQ4_COL],

                    "feature_id": spec["feature_id"],
                    "source_column": column,
                    "unit": spec["unit"],

                    "window_start": window_start,
                    "window_end": window_end,

                    "value": value,

                    "observed_days": observed_days,
                    "expected_days": expected_days,
                    "coverage_ratio": coverage_ratio,
                    "platform": platform,
                    "occasion_valid": valid,

                    "quality_flags": (
                        "|".join(quality_flags)
                        if quality_flags
                        else ""
                    ),
                }
            )

    result = pd.DataFrame(records)

    print(
        f"FeatureWindow rows: "
        f"{len(result):,}"
    )

    if not result.empty:

        print("\nRows by feature:")
        print(
            result["feature_id"]
            .value_counts()
            .sort_index()
        )

        print("\nValid windows by feature:")
        print(
            result.groupby("feature_id")[
                "occasion_valid"
            ].sum()
        )

    return result

def winsorise_mad(df):
    """
    Per-person median +/- 5 MAD winsorisation.
    Applied after quality gate and hard cutoff.
    """

    out = df.copy()

    # Participant-specific median
    median = (
        out.groupby(PARTICIPANT_COL)[GPS_COL]
        .transform("median")
    )

    # Absolute deviation from participant median
    absolute_deviation = (
        out[GPS_COL] - median
    ).abs()

    # Participant-specific MAD
    mad = (
        absolute_deviation
        .groupby(out[PARTICIPANT_COL])
        .transform("median")
    )

    lower = (
        median - 5 * mad
    ).clip(lower=0)

    upper = (
        median + 5 * mad
    )

    # Preserve missing values.
    # If MAD == 0, leave that participant's values unchanged.
    valid_mask = (
        out[GPS_COL].notna()
        & mad.notna()
        & (mad > 0)
    )

    out.loc[valid_mask, GPS_COL] = (
        out.loc[valid_mask, GPS_COL]
        .clip(
            lower=lower[valid_mask],
            upper=upper[valid_mask],
        )
    )

    return out


def winsorisation_impact_diagnostic(gps_500):
    """
    Report how many valid GPS day-values each winsorisation
    method changes and the median participant-specific
    upper cap.

    This is descriptive only. The locked method is the
    per-person 1st-99th percentile method.
    """

    print("\n" + "=" * 60)
    print("WINSORISATION IMPACT DIAGNOSTIC")
    print("=" * 60)

    base = gps_500.copy()

    base[GPS_COL] = pd.to_numeric(
        base[GPS_COL],
        errors="coerce",
    )

    valid_mask = base[GPS_COL].notna()
    valid_days = int(valid_mask.sum())

    # --------------------------------------------------
    # 1st-99th percentile
    # --------------------------------------------------

    percentile_cleaned = winsorise_percentile(base)

    percentile_changed = (
        valid_mask
        & (
            percentile_cleaned[GPS_COL]
            != base[GPS_COL]
        )
    )

    percentile_changed_n = int(
        percentile_changed.sum()
    )

    participant_p99 = (
        base.loc[valid_mask]
        .groupby(PARTICIPANT_COL)[GPS_COL]
        .quantile(0.99)
    )

    participant_p01 = (
        base.loc[valid_mask]
        .groupby(PARTICIPANT_COL)[GPS_COL]
        .quantile(0.01)
    )

    print("\n--- Per-person 1st-99th percentile ---")

    print(
        f"Valid GPS day-values: "
        f"{valid_days:,}"
    )

    print(
        f"Values changed: "
        f"{percentile_changed_n:,}"
    )

    if valid_days > 0:
        print(
            f"Percent of valid values changed: "
            f"{percentile_changed_n / valid_days * 100:.2f}%"
        )

    print(
        f"Median participant lower cap (P1): "
        f"{participant_p01.median():,.2f} m/day"
    )

    print(
        f"Median participant upper cap (P99): "
        f"{participant_p99.median():,.2f} m/day"
    )

    # --------------------------------------------------
    # Median +/- 5 MAD
    # --------------------------------------------------

    mad_cleaned = winsorise_mad(base)

    mad_changed = (
        valid_mask
        & (
            mad_cleaned[GPS_COL]
            != base[GPS_COL]
        )
    )

    mad_changed_n = int(
        mad_changed.sum()
    )

    participant_median = (
        base.loc[valid_mask]
        .groupby(PARTICIPANT_COL)[GPS_COL]
        .median()
    )

    def participant_mad(series):
        med = series.median()
        return (series - med).abs().median()

    participant_mad_values = (
        base.loc[valid_mask]
        .groupby(PARTICIPANT_COL)[GPS_COL]
        .apply(participant_mad)
    )

    mad_upper = (
        participant_median
        + 5 * participant_mad_values
    )

    mad_lower = (
        participant_median
        - 5 * participant_mad_values
    ).clip(lower=0)

    print("\n--- Per-person median +/- 5 MAD ---")

    print(
        f"Values changed: "
        f"{mad_changed_n:,}"
    )

    if valid_days > 0:
        print(
            f"Percent of valid values changed: "
            f"{mad_changed_n / valid_days * 100:.2f}%"
        )

    print(
        f"Median participant lower cap: "
        f"{mad_lower.median():,.2f} m/day"
    )

    print(
        f"Median participant upper cap: "
        f"{mad_upper.median():,.2f} m/day"
    )

def within_person_mobility_correlation(gps_500):
    """
    Estimate the within-person correlation between:

        person-mean-centred log(GPS distance + 1000)
        person-mean-centred loc_home_dur

    GPS uses the locked cleaning policy:
        quality_loc >= 12 h
        >500 km -> NA
        per-person 1st-99th winsorisation

    Impossible home-duration values outside [0, 24]
    are treated as missing.
    """

    print("\n" + "=" * 60)
    print("WITHIN-PERSON MOBILITY CORRELATION")
    print("=" * 60)

    data = winsorise_percentile(
        gps_500.copy()
    )

    data[LOC_HOME_COL] = pd.to_numeric(
        data[LOC_HOME_COL],
        errors="coerce",
    )

    invalid_home = (
        (data[LOC_HOME_COL] < 0)
        | (data[LOC_HOME_COL] > 24)
    )

    data.loc[
        invalid_home,
        LOC_HOME_COL
    ] = np.nan

    data["log_gps"] = np.log(
        data[GPS_COL] + 1000
    )

    paired = data.dropna(
        subset=[
            PARTICIPANT_COL,
            "log_gps",
            LOC_HOME_COL,
        ]
    ).copy()

    paired["log_gps_person_mean"] = (
        paired
        .groupby(PARTICIPANT_COL)["log_gps"]
        .transform("mean")
    )

    paired["home_person_mean"] = (
        paired
        .groupby(PARTICIPANT_COL)[LOC_HOME_COL]
        .transform("mean")
    )

    paired["log_gps_within"] = (
        paired["log_gps"]
        - paired["log_gps_person_mean"]
    )

    paired["home_within"] = (
        paired[LOC_HOME_COL]
        - paired["home_person_mean"]
    )

    correlation = paired[
        "log_gps_within"
    ].corr(
        paired["home_within"]
    )

    print(
        f"Paired participant-days: "
        f"{len(paired):,}"
    )

    print(
        f"Participants represented: "
        f"{paired[PARTICIPANT_COL].nunique():,}"
    )

    print(
        f"Within-person correlation: "
        f"r = {correlation:.4f}"
    )

    print(
        f"Absolute correlation: "
        f"|r| = {abs(correlation):.4f}"
    )

    if abs(correlation) >= 0.6:
        print(
            "Interpretation: high overlap "
            "(|r| >= 0.6); consider avoiding both "
            "features in Tier 1."
        )
    else:
        print(
            "Interpretation: below the provisional "
            "|r| = 0.6 overlap threshold."
        )

    return correlation

def compare_winsorisation(
    gps_500,
    phq4,
):
    print("\n" + "=" * 60)
    print("WINSORISATION COMPARISON")
    print("=" * 60)

    variants = {
        "percentile_1_99": winsorise_percentile(
            gps_500
        ),
        "mad_5": winsorise_mad(
            gps_500
        ),
    }

    results = {}

    for label, gps_df in variants.items():

        print(
            f"\n--- {label} ---"
        )

        windows = build_phq4_windows(
            gps_df,
            phq4,
            window_days=14,
            min_valid_days=7,
        )

        model_df = prepare_model_data(
            windows,
            transform="log",
        )

        results[label] = fit_primary_lmm(
            model_df,
            label,
        )

    beta_pct = (
        results["percentile_1_99"]["beta1"]
    )

    beta_mad = (
        results["mad_5"]["beta1"]
    )

    pct_difference = (
        abs(beta_pct - beta_mad)
        / abs(beta_pct)
        * 100
        if beta_pct != 0
        else np.nan
    )

    print(
        "\n=== WINSORISATION BETA1 COMPARISON ==="
    )

    print(
        f"1st-99th beta1: "
        f"{beta_pct:.6f}"
    )

    print(
        f"Median +/- 5 MAD beta1: "
        f"{beta_mad:.6f}"
    )

    print(
        f"Relative difference: "
        f"{pct_difference:.2f}%"
    )

    if pct_difference < 10:
        print(
            "Decision rule: <10% difference "
            "-> default to 1st-99th percentile."
        )
    else:
        print(
            "Decision rule: >=10% difference "
        )

    return results

def run_final_cutoff_sensitivity(
    gps,
    phq4,
):
    """
    Run the pre-registered GPS hard-cutoff sensitivity
    analysis under the FINAL locked preprocessing spec.

    Final spec:
        1. quality_loc >= 12 h
        2. hard cutoff -> NA
        3. per-person 1st-99th percentile winsorisation
        4. PHQ-4 comparison window [EMA-14, EMA-1]
        5. require >= 7 valid GPS days
        6. aggregate daily GPS using the window mean
        7. transform once: log(mean + 1000)
        8. person-mean centre
        9. fit the same mixed-effects sensitivity model
    """

    print("\n" + "=" * 60)
    print("FINAL-SPEC GPS CUTOFF SENSITIVITY")
    print("=" * 60)

    cutoffs = {
        "250km": 250_000,
        "500km": 500_000,
        "1000km": 1_000_000,
    }

    results = {}

    for label, cutoff_m in cutoffs.items():

        print(
            f"\n{'=' * 60}\n"
            f"FINAL SPEC — {label}\n"
            f"{'=' * 60}"
        )

        # Step 1-2:
        # 12 h quality gate + hard cutoff -> NA
        cleaned = clean_gps_base(
            gps,
            quality_threshold=12,
            cutoff_m=cutoff_m,
        )

        # Step 3:
        # Locked per-person 1st-99th percentile winsorisation
        cleaned = winsorise_percentile(
            cleaned
        )

        # Step 4-5:
        # Locked PHQ-4 window [EMA-14, EMA-1]
        # and >=7 valid GPS days
        windows = build_phq4_windows(
            cleaned,
            phq4,
            window_days=14,
            min_valid_days=7,
        )

        valid_windows = windows[
            windows["occasion_valid"]
        ]

        valid_occasions = len(
            valid_windows
        )

        valid_participants = (
            valid_windows[PARTICIPANT_COL]
            .nunique()
        )

        print(
            f"Final-spec valid occasions: "
            f"{valid_occasions:,}"
        )

        print(
            f"Final-spec participants: "
            f"{valid_participants:,}"
        )

        # Step 6-8:
        # mean -> log(mean + 1000) -> person-mean centre
        model_df = prepare_model_data(
            windows,
            transform="log",
        )

        # Step 9:
        model_result = fit_primary_lmm(
            model_df,
            f"final_{label}",
        )

        model_result[
            "valid_window_occasions"
        ] = valid_occasions

        model_result[
            "valid_window_participants"
        ] = valid_participants

        results[label] = model_result

    # --------------------------------------------------
    # Compare against locked 500 km reference
    # --------------------------------------------------

    reference_beta = results["500km"]["beta1"]

    print("\n" + "=" * 60)
    print("FINAL-SPEC CUTOFF COMPARISON")
    print("=" * 60)

    for label in [
        "250km",
        "500km",
        "1000km",
    ]:

        r = results[label]

        beta = r["beta1"]

        if label == "500km":
            pct_change = 0.0
        else:
            pct_change = (
                abs(beta - reference_beta)
                / abs(reference_beta)
                * 100
                if reference_beta != 0
                else np.nan
            )

        sign_flip = (
            np.sign(beta)
            != np.sign(reference_beta)
        )

        print(f"\n{label}")

        print(
            f"  Valid occasions: "
            f"{r['valid_window_occasions']:,}"
        )

        print(
            f"  Participants: "
            f"{r['valid_window_participants']:,}"
        )

        print(
            f"  beta1: "
            f"{beta:.6f}"
        )

        print(
            f"  95% CI: "
            f"[{r['ci_low']:.6f}, "
            f"{r['ci_high']:.6f}]"
        )

        print(
            f"  p-value: "
            f"{r['p_value']:.6g}"
        )

        print(
            f"  % change vs 500km: "
            f"{pct_change:.2f}%"
        )

        print(
            f"  Sign flip: "
            f"{sign_flip}"
        )

    return results


def prepare_model_data(window_df, transform="log"):
    """
    Prepare valid PHQ-4/GPS windows for the primary within-person model.

    Order:
    1. Keep valid PHQ-4 occasions
    2. Transform window mean GPS distance
    3. Person-mean centre the transformed predictor
    """

    df = window_df.loc[
        window_df["occasion_valid"]
        & window_df["gps_mean_m"].notna()
        & window_df[PHQ4_COL].notna()
    ].copy()

    if transform == "log":
        df["gps_transformed"] = np.log(
            df["gps_mean_m"] + 1000
        )

    elif transform == "sqrt":
        df["gps_transformed"] = np.sqrt(
            df["gps_mean_m"]
        )

    else:
        raise ValueError(
            "transform must be 'log' or 'sqrt'"
        )

    # Person-specific mean of transformed GPS predictor
    df["gps_person_mean"] = (
        df.groupby(PARTICIPANT_COL)["gps_transformed"]
        .transform("mean")
    )

    # Within-person centred predictor
    df["gps_within"] = (
        df["gps_transformed"]
        - df["gps_person_mean"]
    )

    print(f"\nModel preparation — transform: {transform}")
    print(f"Model-ready occasions: {len(df):,}")
    print(
        f"Participants: "
        f"{df[PARTICIPANT_COL].nunique()}"
    )

    return df


def fit_primary_lmm(df, label):
    """
    Primary within-person model:
        PHQ-4 ~ person-mean-centred GPS
        random intercept + random slope
    """

    print(f"\n=== PRIMARY LMM — {label} ===")

    model = smf.mixedlm(
        f"{PHQ4_COL} ~ gps_within",
        data=df,
        groups=df[PARTICIPANT_COL],
        re_formula="~gps_within",
    )

    result = model.fit(
        method="lbfgs",
        reml=False,
    )

    beta1 = result.params["gps_within"]

    ci = result.conf_int().loc["gps_within"]
    ci_low = ci.iloc[0]
    ci_high = ci.iloc[1]

    p_value = result.pvalues["gps_within"]

    significant = (
        ci_low > 0
        or ci_high < 0
    )

    print(f"beta1: {beta1:.6f}")
    print(
        f"95% CI: "
        f"[{ci_low:.6f}, {ci_high:.6f}]"
    )
    print(f"p-value: {p_value:.6g}")
    print(f"Significant: {significant}")

    return {
        "label": label,
        "beta1": beta1,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "p_value": p_value,
        "significant": significant,
        "n_occasions": len(df),
        "n_participants": df[PARTICIPANT_COL].nunique(),
        "result": result,
    }

def load_phq4():
    """
    Load valid longitudinal PHQ-4 outcomes.
    """

    print("\n=== 5. LOAD PHQ-4 OUTCOMES ===")
    _, ema_file = get_ces_files()

    ema = pd.read_csv(
        ema_file,
        usecols=[
            PARTICIPANT_COL,
            DAY_COL,
            PHQ4_COL,
        ],
    )

    ema[DAY_COL] = pd.to_datetime(
        ema[DAY_COL].astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    ema[PHQ4_COL] = pd.to_numeric(
        ema[PHQ4_COL],
        errors="coerce",
    )

    ema = ema.dropna(
        subset=[
            PARTICIPANT_COL,
            DAY_COL,
            PHQ4_COL,
        ]
    )

    # One PHQ-4 outcome per participant × date
    ema = (
        ema
        .sort_values([PARTICIPANT_COL, DAY_COL])
        .drop_duplicates(
            subset=[PARTICIPANT_COL, DAY_COL],
            keep="last",
        )
    )

    print(f"Valid PHQ-4 outcomes: {len(ema):,}")
    print(
        f"Participants: "
        f"{ema[PARTICIPANT_COL].nunique()}"
    )

    return ema

def compare_cutoff_betas(results):
    print("\n=== CUTOFF BETA1 COMPARISON ===")

    reference_beta = results["500km"]["beta1"]

    for label in ["250km", "500km", "1000km"]:

        r = results[label]
        beta = r["beta1"]

        if label == "500km":
            pct_change = 0.0
        else:
            pct_change = (
                abs(beta - reference_beta)
                / abs(reference_beta)
                * 100
                if reference_beta != 0
                else np.nan
            )

        sign_flip = (
            np.sign(beta)
            != np.sign(reference_beta)
        )

        print(f"\n{label}")
        print(f"  beta1: {beta:.6f}")
        print(
            f"  95% CI: "
            f"[{r['ci_low']:.6f}, "
            f"{r['ci_high']:.6f}]"
        )
        print(
            f"  % change vs 500km: "
            f"{pct_change:.2f}%"
        )
        print(f"  Sign flip: {sign_flip}")
        print(
            f"  Significant: "
            f"{r['significant']}"
        )

def save_tier1_feature_windows(
    feature_windows,
):
    output_dir = (
        PROJECT_ROOT
        / "outputs"
        / "data-pipeline"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / "tier1_feature_windows.csv"
    )

    feature_windows.to_csv(
        output_file,
        index=False,
    )

    print(
        f"\nSaved Tier-1 feature windows to:"
        f"\n{output_file}"
    )

    return output_file

def main():

    print("=" * 60)
    print("CES GPS DISTANCE — END-TO-END PIPELINE")
    print("=" * 60)

    gps = load_gps()

    gps = standardise_dates(gps)

    audit_gps_values(gps)

    sanity_bound_diagnostic(gps)

    unlock_zero_day_diagnostic(gps)

    home_duration_violation_diagnostic(gps)

    quality_gate_diagnostic(gps)

    # Historical first-28 diagnostic retained only
    # as a dataset-quality description.
    first_28_results = (
        cold_start_sufficiency_diagnostic(
            gps,
            quality_threshold=12,
            window_days=28,
            min_valid_days=20,
        )
    )

    gps_cutoff_diagnostic(
        gps,
        quality_threshold=12,
    )

    extreme_participant_diagnostic(
        gps,
        quality_threshold=12,
        cutoff_m=500_000,
    )

    # Locked GPS base cleaning:
    # quality >= 12 h
    # >500 km -> NA
    gps_500 = clean_gps_base(
        gps,
        quality_threshold=12,
        cutoff_m=500_000,
    )

    winsorisation_impact_diagnostic(
        gps_500
    )

    within_person_mobility_correlation(
        gps_500
    )

    phq4 = load_phq4()

    rolling_baseline_results = (
        rolling_baseline_sufficiency_diagnostic(
            gps,
            phq4,
            quality_threshold=12,
            baseline_days=28,
            min_valid_days=20,
        )
    )

    final_cutoff_results = (
        run_final_cutoff_sensitivity(
            gps,
            phq4,
        )
    )

    # Locked final GPS winsorisation.
    gps_final = winsorise_percentile(
        gps_500
    )

    final_windows = build_phq4_windows(
        gps_final,
        phq4,
        window_days=14,
        min_valid_days=7,
    )

    tier1_daily = build_clean_tier1_daily(
        gps
    )

    tier1_windows = build_tier1_feature_windows(
        tier1_daily,
        phq4,
        window_days=14,
        min_valid_days=7,
    )

    save_tier1_feature_windows(
        tier1_windows
    )

    print("\n" + "=" * 60)
    print("LOCKED GPS PREPROCESSING DIAGNOSTICS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
