"""
General per-participant-day feature cleaning pipeline.

Implements Moe Tanaka's locked spec at
weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md Section 1.4
("Feature cleaning and sanity bounds") for the one feature that section
locks concrete numbers for: `loc_dist_ep_0` (daily distance travelled,
metres). The general 4-step pipeline is:

  1. Quality gate -> NA
  2. Physical-implausibility filter -> NA (not capped)
  3. Per-person winsorisation -> clamp
  4. Variance-stabilising transform for modelling

Locked `loc_dist_ep_0` thresholds (spec's table, verbatim):

| Step               | Rule                                              |
|---------------------|----------------------------------------------------|
| Quality gate        | `quality_loc >= 12` h required, else NA            |
| Implausibility      | daily distance `> 500,000 m` (500 km) -> NA        |
| Winsorisation       | per-person [1st, 99th] percentile                  |
| Transform           | `log(loc_dist_ep_0 + 1000)` (log1p, 1 km offset)   |
| Zeros               | kept if `quality_loc >= 12` h (genuine stay-home)  |

**Fixed 2026-09-12 — the 8h-vs-12h question this module used to flag as
open is now closed.** The pending day-count-cost report the general spec
note asked for came back at **1.63% of valid days** (see
`analysis/cleaning.py` and `CLAUDE.md`'s "Finalised decisions"), which the
Statistical Analysis Lead judged small enough to take the stricter option,
per the spec's own tie-breaking rule ("we take the stricter option if the
cost is small"). This module previously used 8h because the day-count-cost
report didn't exist *in this module's own tree* yet — `analysis/cleaning.py`
had already finalised 12h independently, and this module had drifted from
it. `QUALITY_LOC_MIN_HOURS` below is now 12, matching that decision; the
two modules should not diverge on this constant again.
- Spec step 3's *general* pipeline offers an alternative winsorisation
  rule ("median +/- 5*MAD, whichever is more stable in the run") for
  cases where percentile winsorisation is unstable. For `loc_dist_ep_0`
  specifically, the locked table is unambiguous (1st/99th percentile), so
  this module implements only that — it does not attempt to pick between
  the two general-pipeline options, since the spec already picked for
  this feature.
- The two Data-Pipeline-Lead diagnostics the spec explicitly asks for
  before the rule is "finalised" (device-concentration of implausible
  values; null-island lat/lon trajectories, §1.4) are NOT computed here —
  they require raw GPS coordinates, which are not present in
  `Sensing/sensing.csv` (only the pre-aggregated daily distance). Flagging
  this rather than fabricating a coordinate-based check.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

QUALITY_LOC_MIN_HOURS = 12  # Finalised 2026-09-12 (was 8h); see module docstring — cost is 1.63% of valid days
GPS_IMPLAUSIBILITY_THRESHOLD_M = 500_000  # 500 km/day -> NA, per spec (not capped)
GPS_WINSORIZE_LOWER_QUANTILE = 0.01
GPS_WINSORIZE_UPPER_QUANTILE = 0.99
GPS_LOG_OFFSET_M = 1000  # log(distance + 1000), i.e. a 1 km offset


def clean_gps_distance(
    sensing: pd.DataFrame,
    gps_col: str = "loc_dist_ep_0",
    quality_col: str = "quality_loc",
    uid_col: str = "uid",
) -> pd.DataFrame:
    """Applies Moe's locked loc_dist_ep_0 cleaning pipeline (Section 1.4).

    Input: one row per participant-day with at least
    ``[uid_col, gps_col, quality_col]``. Row count/order is preserved — a
    dropped *day* is represented as NaN in the new columns, never a
    removed row (so callers can still count "valid vs dropped days" per
    participant afterward).

    Adds two columns:
      - ``f"{gps_col}_clean"``: the quality-gated, implausibility-filtered,
        per-person-winsorised distance (metres).
      - ``f"{gps_col}_log"``: ``log(clean + 1000)``, NaN wherever ``clean``
        is NaN.
    """
    df = sensing.copy()
    raw = df[gps_col]

    # Step 1: quality gate -> NA.
    quality_ok = df[quality_col] >= QUALITY_LOC_MIN_HOURS
    step1 = raw.where(quality_ok)

    # Step 2: physical-implausibility filter -> NA (not capped). Genuine
    # zero-travel days are never touched by this filter (0 <= threshold).
    step2 = step1.where(step1 <= GPS_IMPLAUSIBILITY_THRESHOLD_M)

    # Step 3: per-person winsorisation to each participant's own [1st, 99th]
    # percentile, computed over their surviving (non-NA) values only.
    def _winsorize(group: pd.Series) -> pd.Series:
        valid = group.dropna()
        if valid.empty:
            return group
        lower = valid.quantile(GPS_WINSORIZE_LOWER_QUANTILE)
        upper = valid.quantile(GPS_WINSORIZE_UPPER_QUANTILE)
        return group.clip(lower=lower, upper=upper)

    step3 = step2.groupby(df[uid_col], group_keys=False).apply(_winsorize, include_groups=False)
    step3 = step3.reindex(df.index)

    clean_col = f"{gps_col}_clean"
    log_col = f"{gps_col}_log"
    df[clean_col] = step3
    df[log_col] = np.log(step3 + GPS_LOG_OFFSET_M)

    return df


UNLOCK_WINSORIZE_LOWER_QUANTILE = 0.01
UNLOCK_WINSORIZE_UPPER_QUANTILE = 0.99


def clean_unlock_frequency(
    sensing: pd.DataFrame,
    unlock_col: str = "unlock_num_ep_0",
    uid_col: str = "uid",
) -> pd.DataFrame:
    """Cleans phone-unlock-count (`unlock_num_ep_0`), the second confirmed
    Tier-1 feature (`feature-list-signoff.md` / `freeze-decision.md`,
    2026-08-26). Confirmed spec (Statistical Analysis Lead, see
    `docs/statistics/preregistration.md` section 1.6):

    | Step | Rule |
    |---|---|
    | Quality gate | **none** — CES has no screen/device-uptime quality column (quality fields exist only for activity, audio, light, location) |
    | Implausibility | negative counts -> NA; **no upper cutoff** |
    | Winsorisation | per-person [1st, 99th] percentile, **positive values only** |
    | Transform | **none** — see `backend.statistics.feature_specs.identity_transform` |
    | Zeros | kept as real values, never recoded to NA |

    **No quality gate.** Unlike GPS's `quality_loc` (hours of valid
    location sensing that day), CES has no equivalent screen/unlock
    quality field — checked: `Sensing/sensing.csv`'s columns have no
    `quality_unlock` or similar. A zero-unlock day therefore cannot be
    distinguished from a day screen-sensing simply wasn't running; this
    function cannot apply a gate analogous to GPS's and does not attempt
    to guess one.

    **Implausibility filter: negative counts -> NA, no upper cutoff.** A
    negative unlock count cannot occur. Unlike GPS's 500 km cutoff (an
    empirical implausibility threshold on an otherwise-valid range),
    there is no analogous empirical upper bound on a daily unlock count,
    so none is applied.

    **Genuine zero-unlock days are kept, not recoded to NA.** Confirmed
    rationale (Statistical Analysis Lead): zero days number 3,736 of
    216,065 participant-days (1.73%), affecting 215 of 220 participants,
    with a median of 12 zero days among affected participants against a
    maximum of 231 — too large and too concentrated in specific
    participants to discard, and (per the "no quality gate" point above)
    a true zero cannot be ruled out to begin with.

    **Per-person [1st, 99th] percentile winsorisation on positive values
    only** — zeros are never clipped (winsorising a series padded with
    thousands of structural zeros would not describe the positive-value
    tail at all; a positive-values-only percentile does).

    **No transform.** Raw `unlock_num_ep_0` is only mildly skewed (skew
    1.73, kurtosis 6.32, max 754) — nowhere near GPS's raw distribution
    (skew 160.5, kurtosis 35,552, max 1.2e9), which is what
    `log(mean + 1000)` exists to tame. Two log variants were checked and
    both make things worse: `log(unlock + 1)` has skew -2.38 — the 3,736
    genuine zero-unlock days all collapse onto `log(1) = 0`, turning the
    distribution bimodal rather than reducing its skew. `log(unlock +
    1000)` (GPS's offset, applied here structurally) compresses the
    transformed range to SD 0.0509 over [6.91, 7.47] — a 1000-unit offset
    is two to three orders of magnitude larger than unlock's own 0-754
    range, so nearly all real variation is flattened into numerical
    noise. See `docs/statistics/preregistration.md` section 1.6.2 for the
    full numbers. `backend.statistics.feature_specs.UNLOCK_FREQUENCY_SPEC`
    uses `identity_transform` accordingly — this function itself never
    applies a transform, unlike `clean_gps_distance`, which is why it
    adds only one new column, not two.

    Input: one row per participant-day with at least ``[uid_col,
    unlock_col]``. Row count/order is preserved — a dropped *day* is
    represented as NaN in the new column, never a removed row.

    Adds one column:
      - ``f"{unlock_col}_clean"``: implausibility-filtered, per-person
        (positive-values-only) winsorised unlock count. No
        ``f"{unlock_col}_log"`` diagnostic column is added (contrast
        `clean_gps_distance`) — there is no transform to diagnose;
        producing a `log(unlock + 1)` column here, even labelled
        "diagnostics only", would risk being read as an endorsed
        transform when the analysis above rules it out.
    """
    df = sensing.copy()
    raw = df[unlock_col]

    # Step 1 (implausibility filter only -- no quality gate available, see
    # docstring): negative counts are impossible -> NA. Zeros are valid.
    step1 = raw.where(raw >= 0)

    # Step 2: per-person winsorisation to each participant's own [1st, 99th]
    # percentile, computed over their surviving POSITIVE values only --
    # genuine zero-unlock days are never clipped.
    def _winsorize_positive(group: pd.Series) -> pd.Series:
        # Cast to float up front: winsorisation quantiles are rarely whole
        # numbers, and clipping an int64 Series to a float bound raises
        # (pandas refuses the implicit int->float coercion on setitem) --
        # the output is a per-person WINSORISED count, so it is expected to
        # become float, same as clean_gps_distance's output.
        group = group.astype(float)
        positive = group.where(group > 0).dropna()
        if positive.empty:
            return group
        lower = positive.quantile(UNLOCK_WINSORIZE_LOWER_QUANTILE)
        upper = positive.quantile(UNLOCK_WINSORIZE_UPPER_QUANTILE)
        clipped = group.copy()
        mask = group > 0
        clipped[mask] = group[mask].clip(lower=lower, upper=upper)
        return clipped

    step2 = step1.groupby(df[uid_col], group_keys=False).apply(_winsorize_positive, include_groups=False)
    step2 = step2.reindex(df.index)

    df[f"{unlock_col}_clean"] = step2

    return df
