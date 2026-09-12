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

# Unlock-frequency cleaning constants — see clean_unlock_frequency's
# docstring. Winsorisation quantiles match the locked GPS spec (same
# per-person 1st/99th percentile convention); there is no quality-gate
# constant here because CES has no screen/unlock quality field (unlike
# quality_loc for GPS) — see the docstring's "no quality gate" note.
UNLOCK_WINSORIZE_LOWER_QUANTILE = 0.01
UNLOCK_WINSORIZE_UPPER_QUANTILE = 0.99
UNLOCK_LOG_OFFSET = 1  # log(count + 1) -- NOT Moe-locked, see docstring flag


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


def clean_unlock_frequency(
    sensing: pd.DataFrame,
    unlock_col: str = "unlock_num_ep_0",
    uid_col: str = "uid",
) -> pd.DataFrame:
    """Cleans phone-unlock-count (`unlock_num_ep_0`), the second signed-off
    Tier-1 feature (`feature-list-signoff.md`), the same general 4-step
    pipeline as `clean_gps_distance` (impossible-value filter -> per-person
    winsorisation -> transform), adapted for a count variable that has no
    dedicated data-quality field.

    **FLAGGED FOR MOE TANAKA'S REVIEW — not a locked spec, unlike GPS.**
    Nothing in `weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md`
    or `Week5_Statistical_Analysis_Deliverable.md` locks concrete unlock
    thresholds the way §1.4 locks GPS's 12h/500km/[1,99] numbers — those
    documents only ever discuss `unlock_num_ep_0` as a *candidate* feature.
    This module ports the one existing implementation
    (`scripts/build_gps_feature.py::clean_unlock`) into `backend/` rather
    than inventing new thresholds, but the choices below are still a
    methodology call, not a bug fix, and should not be treated as final
    until Moe Tanaka signs off:

    1. **No quality gate.** GPS has `quality_loc` (hours of valid location
       sensing that day); CES has no equivalent screen/unlock quality
       field (checked: `Sensing/sensing.csv`'s columns have no
       `quality_unlock` or similar). `Week5_Statistical_Analysis_
       Deliverable.md` item 15 flags this directly: a zero-unlock day
       cannot be distinguished from a day screen-sensing simply wasn't
       running. This module therefore cannot apply a gate analogous to
       GPS's — it can only filter impossible values and note the same
       ambiguity in its output.
    2. **Impossibility filter: negative counts -> NA.** A negative unlock
       count cannot occur; unlike GPS's 500km cutoff (an empirical
       implausibility threshold on an otherwise-valid range), there is no
       analogous empirical upper cutoff proposed anywhere in the repo, so
       none is applied here — ported as-is from `scripts/build_gps_
       feature.py::clean_unlock`.
    3. **Genuine zero-unlock days are kept**, per the same source module
       and consistent with Week 5 item 15's framing (a true zero cannot be
       ruled out, so it is not recoded to NA even though it also can't be
       confirmed genuine).
    4. **Per-person [1st, 99th] percentile winsorisation on positive
       values only** (zeros are never clipped) — same convention as GPS,
       ported from `scripts/build_gps_feature.py::clean_unlock`.
    5. **Transform: `log(mean + 1)`**, i.e. a 1-count offset (log1p-style),
       NOT GPS's `+1000` metre offset — chosen because unlock counts and
       GPS metres are on unrelated scales; a metre-sized offset would
       swamp a small count. This specific offset choice has no locked
       precedent anywhere in the repo and is this port's own call —
       flagged here and in the calling module/commit message for Moe's
       sign-off, exactly like the "no quality gate" point above.

    Adds two columns, matching `clean_gps_distance`'s output shape so
    downstream statistics code can treat either feature identically:
      - ``f"{unlock_col}_clean"``: impossibility-filtered, per-person
        winsorised unlock count.
      - ``f"{unlock_col}_log"``: ``log(clean + 1)``, NaN wherever `clean`
        is NaN.
    """
    df = sensing.copy()
    raw = df[unlock_col]

    # Step 1 (impossibility filter only -- no quality gate available, see
    # docstring): negative counts are impossible -> NA. Zeros are valid.
    step1 = raw.where(raw >= 0)

    # Step 2: per-person winsorisation to each participant's own [1st, 99th]
    # percentile, computed over their surviving POSITIVE values only --
    # genuine zero-unlock days are never clipped, mirroring
    # scripts/build_gps_feature.py::clean_unlock.
    def _winsorize_positive(group: pd.Series) -> pd.Series:
        # Cast to float up front: winsorisation quantiles are rarely whole
        # numbers, and clipping an int64 Series to a float bound raises
        # (pandas refuses the implicit int->float coercion on setitem) —
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

    clean_col = f"{unlock_col}_clean"
    log_col = f"{unlock_col}_log"
    df[clean_col] = step2
    df[log_col] = np.log(step2 + UNLOCK_LOG_OFFSET)

    return df
