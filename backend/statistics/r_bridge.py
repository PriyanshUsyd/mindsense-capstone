"""
R bridge for backend/statistics/mixed_effects_model.py's two genuinely
rigorous paths that the pure-Python implementation could not provide:

  (a) Satterthwaite / Kenward-Roger denominator-df and p-values for the
      fixed effects, via R `lme4::lmer` + `lmerTest` (Kenward-Roger via
      `lmerTest`'s own `pbkrtest`-backed `ddf="Kenward-Roger"` option —
      no separate pbkrtest call needed; `pbkrtest` is still required as
      `lmerTest`'s dependency for that path and is checked explicitly
      below so a missing install fails loudly, not silently).
  (b) A true joint mixed-effects fit with an AR(1) residual structure,
      via R `nlme::lme(correlation = corAR1(...))`, including real
      empirical-Bayes (BLUP) per-person random effects.

An earlier revision of `mixed_effects_model.py` flagged both as
"cannot be implemented — no R in this environment" and used documented
Python approximations instead (a between-within denominator-df rule, and
a population-averaged GEE AR(1) robustness check). R was subsequently
installed (Windows, no-admin, per-user install — see
`docs/statistics/r-bridge-setup.md` for exactly how, and an important
git-bash/rpy2 interaction caveat) specifically to replace those
approximations with the real thing where R is available.

**This module is allowed to fail.** R, rpy2, or any of the four R
packages (lme4, lmerTest, pbkrtest, nlme) might not be present in some
other environment (a teammate's machine, CI, a future clean checkout).
Every public function here either returns a real result or raises
`RBridgeUnavailable` with a clear reason; `mixed_effects_model.py` catches
that and falls back to its Python-only approximations, which remain
fully implemented and tested — not deleted, just no longer primary here.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


class RBridgeUnavailable(RuntimeError):
    """R/rpy2/lme4/lmerTest/pbkrtest/nlme aren't usable in this
    environment. Callers should catch this and fall back to the
    pure-Python approximations in mixed_effects_model.py."""


@functools.lru_cache(maxsize=1)
def _load_r() -> tuple:
    """Imports rpy2 and the four required R packages exactly once per
    process, raising RBridgeUnavailable with a specific reason on any
    failure. Cached so repeated calls (e.g. from many tests) don't pay
    the R-startup cost or re-attempt a load known to fail.

    Known environment gotcha (see docs/statistics/r-bridge-setup.md):
    rpy2 on Windows must be imported from a native Windows process
    (PowerShell/cmd, or a Python process launched from one) — imported
    from git-bash/MSYS, rpy2's R_HOME detection dispatches to R's
    Unix-style `bin/config.sh`, which needs `make` and fails outright.
    That failure surfaces here as RBridgeUnavailable, same as R/rpy2
    genuinely not being installed — both mean "use the Python fallback".
    """
    try:
        import rpy2.robjects as ro
        from rpy2.robjects import pandas2ri
        from rpy2.robjects.conversion import Converter, localconverter
        from rpy2.robjects.packages import PackageNotInstalledError, importr
    except Exception as exc:  # noqa: BLE001 - any import-time failure means "R backend unavailable"
        raise RBridgeUnavailable(f"rpy2 import failed: {type(exc).__name__}: {exc}") from exc

    try:
        base = importr("base")
        lme4 = importr("lme4")
        lmerTest = importr("lmerTest")
        importr("pbkrtest")  # lmerTest's Kenward-Roger path depends on this; checked explicitly
        nlme = importr("nlme")
    except PackageNotInstalledError as exc:
        raise RBridgeUnavailable(f"required R package not installed: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - genuinely any R-side failure means "unavailable"
        raise RBridgeUnavailable(f"R package import failed: {type(exc).__name__}: {exc}") from exc

    converter = pandas2ri.converter
    return ro, base, lme4, lmerTest, nlme, converter, localconverter


def r_bridge_available() -> bool:
    """True if R + rpy2 + lme4/lmerTest/pbkrtest/nlme are all usable
    right now in this process. Cheap to call repeatedly (cached)."""
    try:
        _load_r()
        return True
    except RBridgeUnavailable:
        return False


def _random_effects_formula(uid_col: str, include_random_slope: bool) -> str:
    return f"(x_within | {uid_col})" if include_random_slope else f"(1 | {uid_col})"


@dataclass
class RSatterthwaiteResult:
    """Result of `fit_lmer_with_denominator_df` — a real R `lme4::lmer`
    fit, with Satterthwaite or Kenward-Roger denominator df and p-values
    from `lmerTest`."""

    method: str  # "Satterthwaite" or "Kenward-Roger"
    used_random_slope: bool
    fallback_reason: str | None
    converged: bool
    is_singular: bool
    n_observations: int
    n_groups: int
    params: dict[str, float]
    se: dict[str, float]
    df: dict[str, float]
    pvalues: dict[str, float]


def fit_lmer_with_denominator_df(
    data: pd.DataFrame,
    outcome_col: str,
    fixed_effect_names: list[str],
    uid_col: str,
    method: str = "Satterthwaite",
) -> RSatterthwaiteResult:
    """Fits `outcome_col ~ fixed_effect_names... + (x_within | uid_col)`
    via R `lme4::lmer`, then reports fixed-effect df/p-values via
    `lmerTest::summary(model, ddf=method)` — `method` is `"Satterthwaite"`
    (default) or `"Kenward-Roger"`.

    Mirrors `fit_mixed_effects_model`'s own convergence policy: attempts
    the random-slope model first, falling back to random-intercept-only
    (with `fallback_reason` recorded) if `lme4::isSingular()` flags it or
    the fit raises. Raises `RBridgeUnavailable` if R/rpy2/the required
    packages aren't usable at all — that is a different failure mode
    from "converged but singular", which is handled here, not raised.
    """
    if method not in ("Satterthwaite", "Kenward-Roger"):
        raise ValueError(f"method must be 'Satterthwaite' or 'Kenward-Roger', got {method!r}")

    ro, base, lme4, lmerTest, nlme, converter, localconverter = _load_r()

    fixed_formula = f"{outcome_col} ~ " + " + ".join(fixed_effect_names)

    with localconverter(ro.default_converter + converter):
        ro.globalenv["r_df"] = data

    fallback_reason = None
    used_random_slope = True

    full_formula = f"{fixed_formula} + {_random_effects_formula(uid_col, include_random_slope=True)}"
    try:
        ro.r(f'model <- lmerTest::lmer({full_formula!r}, data = r_df)')
        is_singular = bool(ro.r("lme4::isSingular(model)")[0])
        n_conv_messages = int(ro.r("length(model@optinfo$conv$lme4$messages)")[0])
        if is_singular or n_conv_messages > 0:
            fallback_reason = "singular fit" if is_singular else "lme4 reported a convergence message"
            raise RuntimeError(fallback_reason)
    except Exception as exc:  # noqa: BLE001 - any lme4-side failure triggers the documented fallback
        if fallback_reason is None:
            fallback_reason = f"random-slope lmer fit raised {type(exc).__name__}: {exc}"
        used_random_slope = False
        reduced_formula = f"{fixed_formula} + {_random_effects_formula(uid_col, include_random_slope=False)}"
        ro.r(f'model <- lmerTest::lmer({reduced_formula!r}, data = r_df)')
        is_singular = bool(ro.r("lme4::isSingular(model)")[0])

    ro.r(f'r_summary <- summary(model, ddf = {method!r})')
    coef_table = ro.r("as.data.frame(coef(r_summary))")
    with localconverter(ro.default_converter + converter):
        coef_df = ro.conversion.get_conversion().rpy2py(coef_table)

    # A "boundary (singular) fit" notice lands in the same
    # optinfo$conv$lme4$messages slot as genuine optimizer-failure
    # messages, but lme4 treats it as a distinct condition (isSingular())
    # from actual non-convergence — already captured separately in
    # `is_singular`. Reporting `converged=False` just because the
    # (already-recorded-as-singular) fallback model repeats that same
    # notice would conflate the two; filtered out here so `converged`
    # reflects genuine optimizer problems only.
    n_genuine_messages_final = int(
        ro.r('length(grep("singular", model@optinfo$conv$lme4$messages, ignore.case = TRUE, invert = TRUE, value = TRUE))')[0]
    )

    return RSatterthwaiteResult(
        method=method,
        used_random_slope=used_random_slope,
        fallback_reason=fallback_reason,
        converged=(n_genuine_messages_final == 0),
        is_singular=is_singular,
        n_observations=int(ro.r("nobs(model)")[0]),
        n_groups=int(data[uid_col].nunique()),
        params=coef_df["Estimate"].to_dict(),
        se=coef_df["Std. Error"].to_dict(),
        df=coef_df["df"].to_dict(),
        pvalues=coef_df["Pr(>|t|)"].to_dict(),
    )


@dataclass
class RAr1Result:
    """Result of `fit_lme_ar1` — a real joint R `nlme::lme` fit with an
    AR(1) residual structure and real per-person BLUPs (not a
    population-averaged robustness check)."""

    used_random_slope: bool
    fallback_reason: str | None
    ar1_phi: float
    n_observations: int
    n_groups: int
    params: dict[str, float]
    se: dict[str, float]
    pvalues: dict[str, float]
    blups: dict[str, dict[str, float]] = field(default_factory=dict)


def fit_lme_ar1(
    data: pd.DataFrame,
    outcome_col: str,
    fixed_effect_names: list[str],
    uid_col: str,
) -> RAr1Result:
    """Fits `outcome_col ~ fixed_effect_names...` via R `nlme::lme`, with
    `random = ~ x_within | uid_col` and `correlation = corAR1(form = ~ 1
    | uid_col)` — a real AR(1) residual structure *inside* the mixed
    model (not GEE's population-averaged working-correlation
    approximation), including real empirical-Bayes (BLUP) per-person
    random effects (`nlme::ranef`).

    Note (flagged, not silently glossed over): `corAR1` treats each
    person's occasions as equally spaced by *occasion index*, not by the
    actual calendar-day gap between EMAs — the same discrete-occasion-
    order simplification the earlier GEE fallback also made. R's
    `corCAR1` (continuous-time AR(1)) would use the real day gaps
    instead; it was not requested here and is not implemented by this
    function.

    Same convergence policy as `fit_lmer_with_denominator_df`: random
    slope attempted first, falling back to random-intercept-only (with
    `fallback_reason` recorded) if the fit raises (nlme signals
    non-convergence via an R error, not a warning/flag). Raises
    `RBridgeUnavailable` if R/rpy2/nlme aren't usable at all.
    """
    ro, base, lme4, lmerTest, nlme, converter, localconverter = _load_r()

    fixed_formula = f"{outcome_col} ~ " + " + ".join(fixed_effect_names)

    with localconverter(ro.default_converter + converter):
        ro.globalenv["r_df"] = data

    fallback_reason = None
    used_random_slope = True

    try:
        ro.r(
            f'model <- nlme::lme(fixed = as.formula({fixed_formula!r}), '
            f'random = ~ x_within | {uid_col}, '
            f'correlation = nlme::corAR1(form = ~ 1 | {uid_col}), '
            f'data = r_df, control = nlme::lmeControl(msMaxIter = 200, niterEM = 50))'
        )
    except Exception as exc:  # noqa: BLE001 - any nlme-side failure triggers the documented fallback
        fallback_reason = f"random-slope lme(AR1) fit raised {type(exc).__name__}: {exc}"
        used_random_slope = False
        ro.r(
            f'model <- nlme::lme(fixed = as.formula({fixed_formula!r}), '
            f'random = ~ 1 | {uid_col}, '
            f'correlation = nlme::corAR1(form = ~ 1 | {uid_col}), '
            f'data = r_df, control = nlme::lmeControl(msMaxIter = 200, niterEM = 50))'
        )

    ar1_phi = float(
        np.asarray(ro.r("as.numeric(coef(model$modelStruct$corStruct, unconstrained = FALSE))")).reshape(-1)[0]
    )

    t_table = ro.r("as.data.frame(summary(model)$tTable)")
    with localconverter(ro.default_converter + converter):
        t_df = ro.conversion.get_conversion().rpy2py(t_table)

    ranef_r = ro.r("as.data.frame(nlme::ranef(model))")
    with localconverter(ro.default_converter + converter):
        ranef_df = ro.conversion.get_conversion().rpy2py(ranef_r)
    blups = {str(uid): row.to_dict() for uid, row in ranef_df.iterrows()}

    return RAr1Result(
        used_random_slope=used_random_slope,
        fallback_reason=fallback_reason,
        ar1_phi=ar1_phi,
        n_observations=int(ro.r("nobs(model)")[0]),
        n_groups=int(data[uid_col].nunique()),
        params=t_df["Value"].to_dict(),
        se=t_df["Std.Error"].to_dict(),
        pvalues=t_df["p-value"].to_dict(),
        blups=blups,
    )
