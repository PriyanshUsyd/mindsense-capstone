"""Feature cleaning pipeline (Week 4 Deliverable, doc section 1.4).

Locked thresholds for loc_dist_ep_0 (daily distance travelled, metres):
  1. quality_loc < 12h                    -> NA
     quality_loc missing                  -> NA (GPS uptime cannot be verified)
  2. loc_dist_ep_0 > 500,000 m (500 km)   -> NA (not capped; sensor error)
  3. per-person winsorise survivors to [1st, 99th] pct
  4. transform for modelling: log(distance + 1000)

Genuine zero-travel days with quality_loc >= 12h are real signal and are kept:
the phone was tracking and recorded no movement.

ORDER OF OPERATIONS (Week 4 decision -- do not reorder):

    daily cleaning -> 14-day window MEAN of `<value_col>_clean`
                   -> log(mean + LOG_OFFSET_M)

The `<value_col>_log` column produced here is the DAILY log and exists for
diagnostics only. Averaging it over a window yields mean(log(x)), which is a
different quantity from log(mean(x)) (Jensen's inequality). Modelling code
must average `<value_col>_clean` and take the log afterwards.

KNOWN LIMITATIONS (documented, not fixed):
  - Winsorisation bounds come from each person's full history, so a day's
    cleaned value depends on data recorded after it. Acceptable for the
    retrospective analysis; deployment would need an expanding window.
  - Participants with fewer than MIN_OBS_FOR_WINSOR valid days are left
    un-winsorised (too few points for a stable percentile).
  - loc_dist_ep_0 is supplied pre-computed, so the (0,0) "null island"
    hypothesis for extreme values cannot be verified from raw coordinates.
"""

import numpy as np
import pandas as pd

# Week 4 で 12h に確定。8h から 12h に上げるコストは有効日数の 1.63%。
# 変更する場合は Statistical Analysis Lead の承認が必要。
QUALITY_THRESHOLD_HOURS = 12

IMPLAUSIBLE_MAX_M = 500_000
IMPLAUSIBLE_MIN_M = 0  # negative distance is physically impossible

WINSOR_LOW, WINSOR_HIGH = 0.01, 0.99
LOG_OFFSET_M = 1000
MIN_OBS_FOR_WINSOR = 5


def _winsorize_group(s: pd.Series) -> pd.Series:
    valid = s.dropna()
    if len(valid) < MIN_OBS_FOR_WINSOR:
        return s
    lo, hi = valid.quantile([WINSOR_LOW, WINSOR_HIGH])
    return s.clip(lower=lo, upper=hi)


def clean_loc_dist(
    df: pd.DataFrame,
    uid_col: str = "uid",
    value_col: str = "loc_dist_ep_0",
    quality_col: str = "quality_loc",
) -> pd.DataFrame:
    """Return df with two added columns: `<value_col>_clean` (winsorised, NA-gated)
    and `<value_col>_log` (daily log transform, diagnostics only -- see the
    module docstring on order of operations)."""
    out = df.copy()

    quality = pd.to_numeric(out[quality_col], errors="coerce")
    value = pd.to_numeric(out[value_col], errors="coerce")

    # A missing quality_loc means GPS uptime is unknown for that day, so the
    # distance cannot be trusted. `NaN < threshold` evaluates to False, which
    # would silently let these days through the gate, so they are gated
    # explicitly.
    quality_missing = quality.isna()
    quality_gate = quality_missing | (quality < QUALITY_THRESHOLD_HOURS)

    implausible = (value > IMPLAUSIBLE_MAX_M) | (value < IMPLAUSIBLE_MIN_M)

    raw = value.where(~(quality_gate | implausible))

    clean_col = f"{value_col}_clean"
    out[clean_col] = raw.groupby(out[uid_col]).transform(_winsorize_group)

    log_col = f"{value_col}_log"
    out[log_col] = np.log(out[clean_col] + LOG_OFFSET_M)

    out["_quality_gated"] = quality_gate
    out["_quality_missing"] = quality_missing
    out["_implausible"] = implausible
    return out


def cleaning_diagnostics(df: pd.DataFrame, value_col: str = "loc_dist_ep_0") -> dict:
    n = len(df)
    n_quality_dropped = int(df["_quality_gated"].sum())
    n_quality_missing = int(df["_quality_missing"].sum())
    n_implausible_dropped = int(df["_implausible"].sum())
    n_valid_clean = int(df[f"{value_col}_clean"].notna().sum())
    return {
        "n_daily_obs": n,
        # n_dropped_quality_gate now includes days with a missing quality_loc;
        # n_quality_missing reports that subset separately so the figure stays
        # comparable with earlier runs.
        "n_dropped_quality_gate": n_quality_dropped,
        "n_quality_missing": n_quality_missing,
        "n_dropped_implausible": n_implausible_dropped,
        "n_valid_after_cleaning": n_valid_clean,
        "pct_valid_after_cleaning": round(100 * n_valid_clean / n, 2) if n else None,
    }
