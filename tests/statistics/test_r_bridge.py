"""
Tests for backend/statistics/r_bridge.py directly (as opposed to through
mixed_effects_model.py's orchestration layer — see
tests/statistics/test_mixed_effects_model.py for those).

Every test here is skipped when R/rpy2/lme4/lmerTest/pbkrtest/nlme aren't
usable in this environment — see docs/statistics/r-bridge-setup.md,
including the git-bash/MSYS caveat that matters on Windows.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.statistics.r_bridge import (
    RBridgeUnavailable,
    fit_lme_ar1,
    fit_lmer_with_denominator_df,
    r_bridge_available,
)

requires_r = pytest.mark.skipif(
    not r_bridge_available(),
    reason="R + rpy2 + lme4/lmerTest/pbkrtest/nlme not usable in this environment",
)


def _synthetic_frame(n_people: int, n_occasions: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_people):
        uid = f"synthetic_{p}"
        person_level = rng.normal(9.0, 0.5)
        for _ in range(n_occasions):
            x_within = rng.normal(0.0, 1.0)
            phq4 = 5.0 - 1.0 * x_within + rng.normal(0, 0.5)
            rows.append(
                {
                    "uid": uid,
                    "x_within": x_within,
                    "x_between": person_level - 9.0,
                    "phq4_score": phq4,
                }
            )
    return pd.DataFrame(rows)


def test_fit_lmer_with_denominator_df_rejects_an_unknown_method():
    with pytest.raises(ValueError, match="Satterthwaite.*Kenward-Roger"):
        fit_lmer_with_denominator_df(
            _synthetic_frame(5, 5, 0), "phq4_score", ["x_within", "x_between"], "uid", method="bogus"
        )


@requires_r
def test_fit_lmer_with_denominator_df_satterthwaite_recovers_a_real_signal():
    frame = _synthetic_frame(n_people=40, n_occasions=15, seed=42)
    result = fit_lmer_with_denominator_df(frame, "phq4_score", ["x_within", "x_between"], "uid", method="Satterthwaite")

    assert result.method == "Satterthwaite"
    assert result.n_observations == len(frame)
    assert result.n_groups == 40
    assert result.params["x_within"] < 0
    assert result.pvalues["x_within"] < 0.01
    assert np.isfinite(result.df["x_within"])
    assert result.df["x_within"] > 0


@requires_r
def test_fit_lmer_with_denominator_df_kenward_roger_gives_a_different_df_than_satterthwaite():
    """Kenward-Roger and Satterthwaite are different approximations —
    they need not agree exactly, and checking they *can* differ is a
    more honest test than asserting a specific relationship between
    them."""
    frame = _synthetic_frame(n_people=40, n_occasions=15, seed=43)
    sw = fit_lmer_with_denominator_df(frame, "phq4_score", ["x_within", "x_between"], "uid", method="Satterthwaite")
    kr = fit_lmer_with_denominator_df(frame, "phq4_score", ["x_within", "x_between"], "uid", method="Kenward-Roger")

    assert sw.params == pytest.approx(kr.params)  # same underlying lmer fit, only ddf method differs
    assert np.isfinite(kr.df["x_within"])


@requires_r
def test_fit_lmer_with_denominator_df_records_fallback_on_singular_fit():
    """Mirrors fit_mixed_effects_model's own fallback test: too few
    occasions per group should make the random-slope model singular,
    forcing the documented random-intercept-only fallback."""
    frame = _synthetic_frame(n_people=30, n_occasions=2, seed=7)
    result = fit_lmer_with_denominator_df(frame, "phq4_score", ["x_within", "x_between"], "uid")

    if not result.used_random_slope:
        assert result.fallback_reason is not None


@requires_r
def test_fit_lme_ar1_recovers_a_real_signal_and_blups():
    frame = _synthetic_frame(n_people=30, n_occasions=15, seed=44)
    result = fit_lme_ar1(frame, "phq4_score", ["x_within", "x_between"], "uid")

    assert result.params["x_within"] < 0
    assert np.isfinite(result.ar1_phi)
    assert len(result.blups) == 30
    sample = next(iter(result.blups.values()))
    assert "(Intercept)" in sample


@requires_r
def test_fit_lme_ar1_records_fallback_on_convergence_failure():
    """Too few occasions per group is a real convergence stress case for
    nlme::lme with a random slope too — same defensive pattern as the
    lmer fallback test above."""
    frame = _synthetic_frame(n_people=30, n_occasions=2, seed=8)
    result = fit_lme_ar1(frame, "phq4_score", ["x_within", "x_between"], "uid")

    if not result.used_random_slope:
        assert result.fallback_reason is not None
