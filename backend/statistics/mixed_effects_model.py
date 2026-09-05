"""
Mixed-effects model fitting, implementing the Week 5 Statistical Analysis
Lead task from Weekly_Plan.md: "Implement baseline/evidence logic for
that one feature using the named statistical model."

Implements the LMM named in
weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md Sections
1.1-1.7, plus Section 2 (multiple-comparison control) and Section 7
(evidence-strength classification): person-mean-centred within/between
predictors, optional week-in-study / term-phase fixed effects, a
person-level random intercept (+ random slope, with the spec's own
convergence fallback), REML estimation, an AR(1)-aware robustness check,
an approximate denominator-df correction, Holm-Bonferroni /
Benjamini-Hochberg adjustment, and Section 7's evidence-strength labels.
Fit with `statsmodels.regression.mixed_linear_model.MixedLM` (the spec
names this as the Python cross-check tool; R `lme4::lmer` is named as
primary but is not available in this Python codebase or environment — no
R installation — see "NOT IMPLEMENTED" and "APPROXIMATED" below).

Core model fit by `fit_mixed_effects_model` (spec Section 1.2's full
formula, reduced to its primary and time-trend terms):

    PHQ4_it = β0 + β1 * x_within_it + β3 * x_between_i
              (+ β4 * week_in_study_it + β5 * term_phase_it, if
                 `extra_fixed_effects` requests them)
              + u0_i + u1_i * x_within_it + e_it

where `x_it` is the trailing 14-day mean of the cleaned, log-transformed
GPS-distance feature ending on the EMA date (Section 1.3), gated on
>= 7 valid sensor-days in that window (occasions failing the gate are
excluded, never imputed — per spec).

IMPLEMENTED THIS PASS, with the library/method and any approximation used
named explicitly (spec's own bar: flag a workaround clearly rather than
present it as the real thing):

- **β4 (week_in_study) / β5 (term_phase) fixed effects** —
  `compute_time_covariates` adds both columns to the model frame;
  `fit_mixed_effects_model(..., extra_fixed_effects=[...])` adds them to
  the formula. `week_in_study` is exact (weeks since the person's first
  occasion in the frame). **`term_phase` is an APPROXIMATION**: the CES
  dataset has no explicit academic-calendar/term field, so this uses a
  generic Northern-Hemisphere US academic-year heuristic (winter break
  ~Dec 15-Jan 15, spring break ~Mar 8-16, summer break ~May 15-Aug 25,
  else in-term) rather than Dartmouth's actual calendar for the study
  years — a coarse proxy, not ground truth.
- **REML estimation** — `MixedLM.fit(reml=True)`, made explicit at both
  call sites. Note this was already statsmodels' *default*; the prior
  revision of this docstring incorrectly stated statsmodels defaults to
  ML. REML was already satisfied; it's just no longer implicit.
- **Denominator df approximation** — `_between_within_denominator_df`
  implements the classical **between-within (containment-style)** df
  rule (SAS PROC MIXED's `BETWITHIN` method): `df = n_obs - n_groups -
  n_within_params` for within-person terms, `df = n_groups -
  n_between_params - 1` for between-person terms. **This is NOT
  Satterthwaite or Kenward-Roger.** statsmodels has no Satterthwaite/KR
  implementation for `MixedLM`; the spec's primary tool for this
  (R `lme4::lmerTest` for Satterthwaite, `pbkrtest` for Kenward-Roger)
  requires an R installation, which is not available in this environment
  (`which R` / `which Rscript` both fail here). Between-within is a
  real, published, but more conservative/less accurate approximation —
  flagged as a genuine reduction in rigour, not a silent substitute.
- **AR(1) residual structure** — `fit_ar1_robustness_check` fits a
  **population-averaged GEE** (`statsmodels.genmod.generalized_estimating
  _equations.GEE` with `cov_struct=Autoregressive(grid=False)`, the
  Rosner & Munoz 1988 method for *unequally spaced* observations, which
  fits this dataset's irregular ~5-day median EMA gap) as a **supplementary
  robustness check** alongside the primary MixedLM fit, per spec 1.7's own
  framing of AR(1) as a robustness/limitation item. **This is not the same
  model as the primary fit**: GEE is population-averaged (no random
  effects / no BLUPs), so it cannot replace `fit_mixed_effects_model` for
  Section 1.6's per-person estimates — it only lets β1's estimate/SE be
  compared against an AR(1)-aware alternative. `MixedLM` itself still has
  no native serial-correlation covariance option (unlike R
  `nlme::lme(correlation = corAR1())`, which would fit AR(1) inside the
  actual mixed model — not available here, no R). The dependence-parameter
  search itself can fail to converge on data with little genuine serial
  correlation (a documented property of the Rosner & Munoz estimator, not
  specific to this dataset); `fit_ar1_robustness_check` falls back to an
  independence working structure (`ar1_rho=0.0`) and records
  `fallback_reason` when that happens, mirroring the existing
  random-slope fallback pattern rather than silently swallowing it.
- **Multiple-comparison correction (Section 2)** —
  `adjust_confirmatory_family` (Holm-Bonferroni, FWER) and
  `adjust_exploratory_family` (Benjamini-Hochberg, FDR) both wrap
  `statsmodels.stats.multitest.multipletests` with `method="holm"` and
  `method="fdr_bh"` respectively — the standard library implementation,
  not hand-rolled.
- **Evidence-strength classification (Section 7)** —
  `classify_evidence_strength` implements the table's four tiers
  (strong/moderate/weak/insufficient) directly. **"Strong" requires a
  same-sign check at lag 0 *and* lag 1**; the lag-1 term (β2, below) is
  out of this task's scope, so `lag0_lag1_consistent_sign` is `None`
  unless a caller supplies it, and "strong" is then unreachable — a
  flagged scope gap, not silently dropped.

NOT IMPLEMENTED (flagged, not silently dropped) — spec terms/steps this
module still does not cover, out of scope for this pass:

- **β2 (1-occasion lag)** fixed effect (spec Section 1.2) — the primary
  within/between terms and the new time-trend terms are fit; the lag
  term is not. This is also why `classify_evidence_strength`'s "strong"
  tier is unreachable without a caller-supplied lag comparison (above).
- **Empirical-Bayes (BLUP) per-person slope extraction** (Section 1.6) —
  `fit_mixed_effects_model` returns the fitted `MixedLMResults` object,
  which exposes `.random_effects` for this, but no dedicated
  per-participant BLUP-extraction helper is implemented here yet.

Given all of the above, this module's output should be read as "the
model converges, produces a within-person coefficient estimate with an
AR(1)-aware robustness comparison and an approximate denominator df, on
the real cleaned feature data, with correction and evidence-labelling
utilities available for whoever wires up the per-person report" — not as
the full publication-ready confirmatory analysis Section 2 describes
(that still needs the lag term, BLUP extraction, and — ideally — a real
Satterthwaite/Kenward-Roger and joint AR(1) fit via R, which this
environment cannot run).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from statsmodels.genmod.cov_struct import Autoregressive, Independence
from statsmodels.genmod.generalized_estimating_equations import GEE, GEEResultsWrapper
from statsmodels.regression.mixed_linear_model import MixedLM, MixedLMResultsWrapper
from statsmodels.stats.multitest import multipletests

ALIGNMENT_WINDOW_DAYS = 14  # PHQ-4's "last 2 weeks" recall period, spec Section 1.3
OCCASION_MIN_VALID_SENSOR_DAYS = 7  # spec Section 1.3 occasion-validity gate

# spec Section 1.2 term_phase heuristic (APPROXIMATION — see module
# docstring): (start_month-day, end_month-day) ranges, inclusive, treated
# as "break"; a range that wraps the new year (winter break) is handled
# separately in _is_break_month_day below.
_BREAK_RANGES_MMDD = [("03-08", "03-16"), ("05-15", "08-25")]
_WINTER_BREAK_START_MMDD = "12-15"  # -> wraps to...
_WINTER_BREAK_END_MMDD = "01-15"  # ...the following year


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


def _is_break_month_day(month_day: pd.Series) -> pd.Series:
    """Vectorised APPROXIMATE in-term/break classifier — see module
    docstring's `term_phase` caveat. `month_day` is a Series of "MM-DD"
    strings (safe to compare lexically since both parts are zero-padded)."""
    is_break = (month_day >= _WINTER_BREAK_START_MMDD) | (month_day <= _WINTER_BREAK_END_MMDD)
    for start, end in _BREAK_RANGES_MMDD:
        is_break = is_break | ((month_day >= start) & (month_day <= end))
    return is_break


def compute_time_covariates(
    valid: pd.DataFrame,
    uid_col: str = "uid",
    date_col: str = "date",
) -> pd.DataFrame:
    """Spec Section 1.2, β4/β5: adds `week_in_study` and `term_phase` to
    `valid` (expects one row per occasion, with a `date_col` datetime
    column already present — i.e. called on the frame `build_model_frame`
    is assembling, not on raw input).

    - `week_in_study`: exact. Weeks elapsed (float) since this person's
      *first occasion in this model frame*, i.e. the linear time /
      practice trend the spec names for β4.
    - `term_phase`: 1 = in-term, 0 = break. **APPROXIMATION** (see module
      docstring): the CES dataset carries no explicit academic-calendar
      field, so this uses a generic US academic-year heuristic (winter
      break ~Dec 15-Jan 15, spring break ~Mar 8-16, summer break ~May
      15-Aug 25), not the real Dartmouth calendar for the study years.
    """
    out = valid.copy()
    first_date = out.groupby(uid_col)[date_col].transform("min")
    out["week_in_study"] = (out[date_col] - first_date).dt.days / 7.0

    month_day = out[date_col].dt.strftime("%m-%d")
    out["term_phase"] = (~_is_break_month_day(month_day)).astype(int)
    return out


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

    valid = compute_time_covariates(valid, uid_col=uid_col, date_col="date")

    return valid.reset_index(drop=True)


# spec Section 1.2: terms that vary within a person (needed to classify
# each fixed effect as "within" or "between" for the between-within
# denominator-df approximation below). x_between is the one built-in
# between-person term; every extra_fixed_effect not listed here is
# assumed within-person (true for week_in_study; term_phase also varies
# within a person over calendar time, so it belongs here too).
_BETWEEN_PERSON_TERMS = {"x_between"}


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
    reml: bool = True
    denom_df: dict[str, float] = field(default_factory=dict)
    denom_df_method: str | None = None


def _between_within_denominator_df(
    data: pd.DataFrame,
    uid_col: str,
    fixed_effect_names: list[str],
) -> dict[str, float]:
    """Between-within (containment-style) denominator-df approximation —
    SAS PROC MIXED's `BETWITHIN` method. **Not Satterthwaite or
    Kenward-Roger** (see module docstring for why: no R in this
    environment). For a within-person term: `df = n_obs - n_groups -
    n_within_params`. For a between-person term: `df = n_groups -
    n_between_params - 1` (the -1 accounts for the intercept, itself a
    between-person quantity).
    """
    n_obs = len(data)
    n_groups = data[uid_col].nunique()
    within_terms = [t for t in fixed_effect_names if t not in _BETWEEN_PERSON_TERMS]
    between_terms = [t for t in fixed_effect_names if t in _BETWEEN_PERSON_TERMS]

    df_within = float(n_obs - n_groups - len(within_terms))
    df_between = float(n_groups - len(between_terms) - 1)

    return {
        **{t: df_within for t in within_terms},
        **{t: df_between for t in between_terms},
    }


def fit_mixed_effects_model(
    model_frame: pd.DataFrame,
    outcome_col: str = "phq4_score",
    uid_col: str = "uid",
    extra_fixed_effects: list[str] | None = None,
) -> MixedEffectsFitResult:
    """Fits the LMM: `phq4_score ~ x_within + x_between [+ extra_fixed_effects]`,
    person-level random intercept, with a random slope on `x_within`
    attempted first, via REML.

    `extra_fixed_effects` (spec Section 1.2, β4/β5): optionally adds
    `week_in_study` and/or `term_phase` (produced by
    `compute_time_covariates` / `build_model_frame`) to the fixed-effects
    formula. Backward compatible: omitted (the default), the formula and
    behaviour are exactly what they were before this parameter existed.

    Convergence policy (spec Section 1.5): "if a random-slope model fails
    to converge or yields a degenerate covariance, fall back to
    random-intercept-only ... and record the fallback." Implemented here
    by attempting the random-slope fit, and falling back to
    random-intercept-only if it raises, fails to converge
    (`result.converged is False`), or yields a non-positive-definite
    random-effects covariance.

    Estimator (spec Section 1.5): REML — `reml=True` is passed explicitly
    to both `.fit()` calls below (this was already statsmodels'
    `MixedLM.fit` default; it's just no longer implicit).
    """
    extra_fixed_effects = extra_fixed_effects or []
    fixed_effect_names = ["x_within", "x_between", *extra_fixed_effects]
    formula = f"{outcome_col} ~ " + " + ".join(fixed_effect_names)

    data = model_frame.dropna(subset=[outcome_col, *fixed_effect_names])

    fallback_reason = None
    used_random_slope = True
    result = None

    try:
        model = MixedLM.from_formula(
            formula,
            data=data,
            groups=data[uid_col],
            re_formula="~x_within",
        )
        result = model.fit(reml=True)
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
            formula,
            data=data,
            groups=data[uid_col],
        )
        result = model.fit(reml=True)

    denom_df = _between_within_denominator_df(data, uid_col, fixed_effect_names)

    return MixedEffectsFitResult(
        converged=bool(result.converged),
        used_random_slope=used_random_slope,
        fallback_reason=fallback_reason,
        n_observations=int(result.nobs),
        n_groups=data[uid_col].nunique(),
        params={k: float(v) for k, v in result.params.items()},
        pvalues={k: float(v) for k, v in result.pvalues.items()},
        result=result,
        reml=True,
        denom_df=denom_df,
        denom_df_method="between-within (containment-style approximation, not Satterthwaite/Kenward-Roger)",
    )


@dataclass
class Ar1RobustnessResult:
    """Output of `fit_ar1_robustness_check` — a population-averaged,
    AR(1)-aware comparison fit, not a replacement for
    `MixedEffectsFitResult` (see that function's docstring)."""

    converged: bool
    ar1_rho: float
    n_observations: int
    n_groups: int
    params: dict[str, float]
    pvalues: dict[str, float]
    result: GEEResultsWrapper
    fallback_reason: str | None = None


def fit_ar1_robustness_check(
    model_frame: pd.DataFrame,
    outcome_col: str = "phq4_score",
    uid_col: str = "uid",
    date_col: str = "date",
    extra_fixed_effects: list[str] | None = None,
) -> Ar1RobustnessResult:
    """AR(1) residual structure (spec Sections 1.2/1.7): a supplementary
    robustness check, run alongside — not instead of —
    `fit_mixed_effects_model`.

    Fits `phq4_score ~ x_within + x_between [+ extra_fixed_effects]` via
    **GEE** (`statsmodels.genmod.generalized_estimating_equations.GEE`)
    with an **`Autoregressive(grid=False)`** working-correlation
    structure — the Rosner & Munoz (1988) method for unequally spaced
    repeated measures, `time=` given as days since this person's first
    occasion in the frame, matching this dataset's irregular ~5-day
    median EMA gap (spec Section 1.3/§8).

    Why GEE and not a native AR(1) `MixedLM`: statsmodels' `MixedLM` has
    no serial-correlation (AR(1)) residual-covariance option — only
    variance-components structures. GEE is **population-averaged** (no
    random intercept/slope, no BLUPs), so its coefficients are not
    directly the same estimand as the primary mixed model's, and it
    cannot serve Section 1.6's per-person BLUP requirement. Comparing its
    `x_within` estimate/SE against `fit_mixed_effects_model`'s is exactly
    the "robustness check" role Section 1.7 assigns to AR(1) — not a
    replacement for the primary fit. A true joint ML fit of the mixed
    model *with* an AR(1) residual (e.g. R `nlme::lme(correlation =
    corAR1())`) is not available in this environment (no R installation).
    """
    extra_fixed_effects = extra_fixed_effects or []
    fixed_effect_names = ["x_within", "x_between", *extra_fixed_effects]
    formula = f"{outcome_col} ~ " + " + ".join(fixed_effect_names)

    data = model_frame.dropna(subset=[outcome_col, date_col, *fixed_effect_names]).copy()
    data = data.sort_values([uid_col, date_col]).reset_index(drop=True)

    first_date = data.groupby(uid_col)[date_col].transform("min")
    time = ((data[date_col] - first_date).dt.days.to_numpy().astype(float)).reshape(-1, 1)

    # The Rosner & Munoz dependence-parameter search (scipy `brent`) can
    # fail to bracket a minimum when the data shows little to no genuine
    # serial correlation (a real, documented edge case of this estimator,
    # not specific to our data). Recorded as an explicit fallback to an
    # independence working structure (rho = 0), mirroring this module's
    # existing convergence-fallback pattern in `fit_mixed_effects_model`
    # — not silently swallowed.
    fallback_reason = None
    try:
        model = GEE.from_formula(
            formula,
            groups=data[uid_col],
            data=data,
            time=time,
            cov_struct=Autoregressive(grid=False),
        )
        result = model.fit()
        ar1_rho = float(np.asarray(model.cov_struct.dep_params).reshape(-1)[0])
    except Exception as exc:  # noqa: BLE001 - genuinely any GEE/optimizer failure triggers the independence fallback
        fallback_reason = f"AR(1) dependence-parameter estimation raised {type(exc).__name__}: {exc}"
        model = GEE.from_formula(
            formula,
            groups=data[uid_col],
            data=data,
            time=time,
            cov_struct=Independence(),
        )
        result = model.fit()
        ar1_rho = 0.0

    return Ar1RobustnessResult(
        converged=bool(getattr(result, "converged", True)),
        ar1_rho=ar1_rho,
        n_observations=int(result.nobs),
        n_groups=data[uid_col].nunique(),
        params={k: float(v) for k, v in result.params.items()},
        pvalues={k: float(v) for k, v in result.pvalues.items()},
        result=result,
        fallback_reason=fallback_reason,
    )


def adjust_confirmatory_family(
    pvalues: dict[str, float],
    alpha: float = 0.05,
) -> dict[str, dict[str, float | bool]]:
    """Spec Section 2: confirmatory family correction — **Holm-Bonferroni**,
    controls FWER at `alpha`. Wraps
    `statsmodels.stats.multitest.multipletests(method="holm")` (the
    standard library implementation, not hand-rolled).

    `pvalues`: {test_name: raw p-value}. Returns
    {test_name: {"p_adjusted": ..., "reject": ...}}.
    """
    names = list(pvalues.keys())
    reject, p_adjusted, _, _ = multipletests(
        [pvalues[name] for name in names], alpha=alpha, method="holm"
    )
    return {
        name: {"p_adjusted": float(p_adj), "reject": bool(rej)}
        for name, p_adj, rej in zip(names, p_adjusted, reject)
    }


def adjust_exploratory_family(
    pvalues: dict[str, float],
    q: float = 0.05,
) -> dict[str, dict[str, float | bool]]:
    """Spec Section 2: secondary/exploratory family AND per-person weekly
    report correction — **Benjamini-Hochberg FDR**, controls FDR at `q`.
    Wraps `statsmodels.stats.multitest.multipletests(method="fdr_bh")`
    (the standard library implementation, not hand-rolled).

    `pvalues`: {test_name: raw p-value}. Returns
    {test_name: {"q_value": ..., "reject": ...}}.
    """
    names = list(pvalues.keys())
    reject, q_values, _, _ = multipletests(
        [pvalues[name] for name in names], alpha=q, method="fdr_bh"
    )
    return {
        name: {"q_value": float(q_val), "reject": bool(rej)}
        for name, q_val, rej in zip(names, q_values, reject)
    }


_EVIDENCE_STRENGTH_TIERS = ("strong", "moderate", "weak", "insufficient")


def classify_evidence_strength(
    q_value: float,
    standardized_effect: float,
    n_occasions: int,
    lag0_lag1_consistent_sign: bool | None = None,
) -> str:
    """Spec Section 7 — evidence-strength classification, applied to a
    candidate historical-relationship statement for one person/feature
    using the BLUP `slope_i` (Section 1.6) as `standardized_effect`.

    | Label | q | |effect| | occasions | consistency |
    |---|---|---|---|---|
    | strong | < 0.01 | >= 0.20 | >= 12 | same sign at lag 0 AND lag 1 |
    | moderate | < 0.05 | >= 0.10 | >= 8 | same sign at lag 0 |
    | weak | < 0.10 | >= 0.10 | >= 8 | (none required) |
    | insufficient | otherwise | | | |

    `lag0_lag1_consistent_sign`: the lag-1 term (β2) is out of this
    module's scope (see module docstring), so this is `None` unless a
    caller supplies it from elsewhere — in which case "strong" can never
    be reached here. This is a flagged scope gap, not a silent "always
    insufficient for strong" bug.
    """
    abs_effect = abs(standardized_effect)

    if (
        q_value < 0.01
        and abs_effect >= 0.20
        and n_occasions >= 12
        and lag0_lag1_consistent_sign is True
    ):
        return "strong"
    if q_value < 0.05 and abs_effect >= 0.10 and n_occasions >= 8:
        return "moderate"
    if q_value < 0.10 and abs_effect >= 0.10 and n_occasions >= 8:
        return "weak"
    return "insufficient"
