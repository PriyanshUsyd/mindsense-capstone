"""
Mixed-effects model fitting — Moe Tanaka's Week 5 deliverable (Statistical
Analysis Lead), per Weekly_Plan.md: "Implement baseline/evidence logic for
that one feature using the named statistical model."

Implements the CORE of the LMM named in
weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md Sections
1.1-1.3: person-mean-centred within/between predictors, a person-level
random intercept (+ random slope, with the spec's own convergence
fallback), fit with `statsmodels.regression.mixed_linear_model.MixedLM`
(the spec names this as the Python cross-check tool; R `lme4::lmer` is
named as primary but is not available in this Python codebase — see
"NOT IMPLEMENTED" below).

Model actually fit here (spec Section 1.2's full formula, reduced):

    PHQ4_it = β0 + β1 * x_within_it + β3 * x_between_i
              + u0_i + u1_i * x_within_it + e_it

where `x_it` is the trailing 14-day mean of the cleaned, log-transformed
GPS-distance feature ending on the EMA date (Section 1.3), gated on
>= 7 valid sensor-days in that window (occasions failing the gate are
excluded, never imputed — per spec).

NOT IMPLEMENTED (flagged, not silently dropped) — spec terms/steps this
module does not yet cover:

- **β2 (1-occasion lag)** and **β4 (week_in_study)** / **β5 (term_phase)**
  fixed effects (spec Section 1.2) — only the primary within/between
  terms are fit.
- **AR(1) residual structure** within person (spec notes this is needed
  given 14-day window overlap) — `MixedLM` here uses independent residual
  errors; the spec's own robustness/limitation note applies.
- **REML + Satterthwaite/Kenward-Roger df** (spec Section 1.5) —
  `statsmodels.MixedLM` defaults to ML, and does not implement
  Satterthwaite/Kenward-Roger degrees of freedom; this module uses
  statsmodels' default asymptotic (z-based) inference instead. This is a
  genuine reduction in inferential rigour versus the spec's primary tool
  (R `lme4`/`lmerTest`), not a silent equivalent substitution.
- **Holm-Bonferroni / Benjamini-Hochberg correction** (Section 2) and the
  **evidence-strength classification** (Section 7) — this module reports
  raw coefficients/p-values only; adjustment and evidence-strength
  labelling are a separate step, not yet wired up.
- **Empirical-Bayes (BLUP) per-person slope extraction** (Section 1.6) —
  `fit_mixed_effects_model` returns the fitted `MixedLMResults` object,
  which exposes `.random_effects` for this, but no dedicated
  per-participant BLUP-extraction helper is implemented here yet.

Given all of the above, this module's output should be read as "the
model converges and produces a within-person coefficient estimate on the
real cleaned feature data" — a necessary foundation — not as the
publication-ready confirmatory analysis Section 2 describes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.regression.mixed_linear_model import MixedLM, MixedLMResultsWrapper

ALIGNMENT_WINDOW_DAYS = 14  # PHQ-4's "last 2 weeks" recall period, spec Section 1.3
OCCASION_MIN_VALID_SENSOR_DAYS = 7  # spec Section 1.3 occasion-validity gate


def _to_datetime(day_col: pd.Series) -> pd.Series:
    """The dataset's `day` column is a YYYYMMDD integer; both
    Sensing/sensing.csv and EMA/general_ema.csv use the same format."""
    return pd.to_datetime(day_col.astype(str), format="%Y%m%d")


def build_trailing_predictor(
    cleaned_sensing_days: pd.DataFrame,
    log_col: str = "loc_dist_ep_0_log",
    window_days: int = ALIGNMENT_WINDOW_DAYS,
    uid_col: str = "uid",
    day_col: str = "day",
) -> pd.DataFrame:
    """For every calendar day in each participant's observed date range,
    computes the trailing `window_days`-day mean of `log_col` (ending on
    that day, inclusive) and the count of valid (non-NaN) sensor-days in
    that window.

    Reindexes each participant to a *continuous* daily date range first,
    so the rolling window is calendar-correct (a day with no sensing row
    counts as a gap, not as "outside the window").

    Returns one row per (uid, date) with columns:
      - `x_it`: trailing window mean of `log_col` (NaN if no valid days)
      - `valid_sensor_days_in_window`: count of valid days in that window
    """
    parts = []
    for uid, group in cleaned_sensing_days.groupby(uid_col):
        dates = _to_datetime(group[day_col])
        series = pd.Series(group[log_col].to_numpy(), index=dates).sort_index()
        series = series[~series.index.duplicated(keep="first")]
        full_range = pd.date_range(series.index.min(), series.index.max(), freq="D")
        daily = series.reindex(full_range)

        x_it = daily.rolling(window=window_days, min_periods=1).mean()
        valid_days = daily.rolling(window=window_days, min_periods=1).count()

        parts.append(
            pd.DataFrame(
                {
                    uid_col: uid,
                    "date": full_range,
                    "x_it": x_it.to_numpy(),
                    "valid_sensor_days_in_window": valid_days.to_numpy().astype(int),
                }
            )
        )

    return pd.concat(parts, ignore_index=True)


def build_model_frame(
    cleaned_sensing_days: pd.DataFrame,
    ema: pd.DataFrame,
    outcome_col: str = "phq4_score",
    log_col: str = "loc_dist_ep_0_log",
    uid_col: str = "uid",
    day_col: str = "day",
    window_days: int = ALIGNMENT_WINDOW_DAYS,
    min_valid_sensor_days: int = OCCASION_MIN_VALID_SENSOR_DAYS,
) -> pd.DataFrame:
    """Joins EMA occasions to the trailing GPS predictor, applies the
    occasion-validity gate (drop, don't impute), and computes the
    person-mean-centred within/between terms (spec Section 1.2).

    `x_bar_i` (the person's mean of the cleaned feature) is computed over
    **all of that person's valid occasion-level `x_it` values used in
    this model fit** — the "full-history person mean for the model fit"
    the spec distinguishes from the trailing-window runtime baseline
    (Section 1.2's closing note). `x_between_i` is grand-mean-centred
    against the mean of the per-person means (the standard Mundlak
    convention; the spec does not specify unweighted-vs-observation-
    weighted grand mean, so this choice is stated here rather than
    guessed silently).
    """
    predictor = build_trailing_predictor(
        cleaned_sensing_days, log_col=log_col, window_days=window_days, uid_col=uid_col, day_col=day_col
    )

    occasions = ema[[uid_col, day_col, outcome_col]].dropna(subset=[outcome_col]).copy()
    occasions["date"] = _to_datetime(occasions[day_col])

    merged = occasions.merge(predictor, on=[uid_col, "date"], how="left")

    # Occasion-validity gate: excluded (dropped), not imputed, per spec.
    valid = merged[
        merged["x_it"].notna() & (merged["valid_sensor_days_in_window"] >= min_valid_sensor_days)
    ].copy()

    person_means = valid.groupby(uid_col)["x_it"].transform("mean")
    grand_mean_of_person_means = valid.groupby(uid_col)["x_it"].mean().mean()

    valid["x_within"] = valid["x_it"] - person_means
    valid["x_between"] = person_means - grand_mean_of_person_means

    return valid.reset_index(drop=True)


@dataclass
class MixedEffectsFitResult:
    converged: bool
    used_random_slope: bool
    fallback_reason: str | None
    n_observations: int
    n_groups: int
    params: dict[str, float]
    pvalues: dict[str, float]
    result: MixedLMResultsWrapper


def fit_mixed_effects_model(
    model_frame: pd.DataFrame,
    outcome_col: str = "phq4_score",
    uid_col: str = "uid",
) -> MixedEffectsFitResult:
    """Fits the LMM: `phq4_score ~ x_within + x_between`, person-level
    random intercept, with a random slope on `x_within` attempted first.

    Convergence policy (spec Section 1.5): "if a random-slope model fails
    to converge or yields a degenerate covariance, fall back to
    random-intercept-only ... and record the fallback." Implemented here
    by attempting the random-slope fit, and falling back to
    random-intercept-only if it raises, fails to converge
    (`result.converged is False`), or yields a non-positive-definite
    random-effects covariance.
    """
    data = model_frame.dropna(subset=[outcome_col, "x_within", "x_between"])

    fallback_reason = None
    used_random_slope = True
    result = None

    try:
        model = MixedLM.from_formula(
            f"{outcome_col} ~ x_within + x_between",
            data=data,
            groups=data[uid_col],
            re_formula="~x_within",
        )
        result = model.fit()
        cov_re = np.asarray(result.cov_re)
        degenerate = cov_re.shape[0] > 1 and np.linalg.eigvalsh(cov_re).min() <= 1e-8
        if not result.converged or degenerate:
            fallback_reason = (
                "random-slope model did not converge" if not result.converged else "degenerate random-effects covariance"
            )
            result = None
    except Exception as exc:  # noqa: BLE001 - genuinely any statsmodels/linalg failure triggers the spec's fallback
        fallback_reason = f"random-slope fit raised {type(exc).__name__}: {exc}"
        result = None

    if result is None:
        used_random_slope = False
        model = MixedLM.from_formula(
            f"{outcome_col} ~ x_within + x_between",
            data=data,
            groups=data[uid_col],
        )
        result = model.fit()

    return MixedEffectsFitResult(
        converged=bool(result.converged),
        used_random_slope=used_random_slope,
        fallback_reason=fallback_reason,
        n_observations=int(result.nobs),
        n_groups=data[uid_col].nunique(),
        params={k: float(v) for k, v in result.params.items()},
        pvalues={k: float(v) for k, v in result.pvalues.items()},
        result=result,
    )
