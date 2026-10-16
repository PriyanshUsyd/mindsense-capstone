"""Tests for backend/statistics/lme_ar1_python.py, the NumPy/SciPy engine for the
bootstrap model. No R needed, except the cross-engine check at the bottom."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.statistics import lme_ar1_python as lme
from backend.statistics import r_bridge

FIXED = ["x_within", "x_between"]
TRUE = {"beta": (2.0, -0.4, 0.3), "D": np.array([[1.0, 0.1], [0.1, 0.09]]), "sigma": 1.2, "phi": 0.5}


def _simulate(n_people=150, n_occ=25, seed=0, x_scale=1.0):
    rng = np.random.default_rng(seed)
    b0, bw, bb = TRUE["beta"]
    rows = []
    for p in range(n_people):
        u = rng.multivariate_normal([0.0, 0.0], TRUE["D"])
        xb = rng.normal()
        n = int(rng.integers(n_occ // 2, n_occ + 1))
        x = rng.normal(size=n)
        e = np.empty(n)
        e[0] = TRUE["sigma"] * rng.normal()
        for t in range(1, n):
            e[t] = TRUE["phi"] * e[t - 1] + TRUE["sigma"] * np.sqrt(1 - TRUE["phi"] ** 2) * rng.normal()
        y = b0 + u[0] + (bw + u[1]) * x + bb * xb + e
        for t in range(n):
            rows.append({"uid": f"p{p}", "x_within": x[t] * x_scale, "x_between": xb, "phq4_score": y[t]})
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def frame():
    return _simulate()


@pytest.fixture(scope="module")
def fit(frame):
    return lme.fit_lme_ar1(frame, "phq4_score", FIXED, "uid")


def test_recovers_the_generating_parameters(fit):
    assert fit.used_random_slope and fit.fallback_reason is None and fit.converged
    b0, bw, bb = TRUE["beta"]
    assert fit.params["Intercept"] == pytest.approx(b0, abs=0.25)
    assert fit.params["x_within"] == pytest.approx(bw, abs=0.08)
    assert fit.params["x_between"] == pytest.approx(bb, abs=0.25)
    assert fit.ar1_phi == pytest.approx(TRUE["phi"], abs=0.05)
    assert fit.sigma == pytest.approx(TRUE["sigma"], abs=0.08)
    assert fit.random_effects_cov["x_within"]["x_within"] == pytest.approx(0.09, abs=0.04)
    assert fit.random_effects_cov["Intercept"]["x_within"] == fit.random_effects_cov["x_within"]["Intercept"]


def test_outputs_have_the_r_result_shape(fit, frame):
    assert set(fit.params) == set(fit.se) == set(fit.pvalues) == {"Intercept", *FIXED}
    assert set(fit.blups) == set(frame["uid"])
    assert all(set(b) == {"Intercept", "x_within"} for b in fit.blups.values())
    assert fit.n_observations == len(frame) and fit.n_groups == frame["uid"].nunique()


@pytest.mark.parametrize("n", [1, 2, 3, 7])
def test_ar1_gram_algebra_matches_the_explicit_inverse(n):
    rng = np.random.default_rng(n)
    cols = rng.normal(size=(n, 3))
    phi = 0.63
    grams = lme._Grams(cols, np.zeros(n, dtype=int), 1)
    R = phi ** np.abs(np.subtract.outer(np.arange(n), np.arange(n)))
    np.testing.assert_allclose(grams.quad(phi)[0], cols.T @ np.linalg.inv(R) @ cols, rtol=1e-10, atol=1e-10)


def test_rescaling_a_covariate_only_reparametrises_the_model(fit):
    scaled = lme.fit_lme_ar1(_simulate(x_scale=1000.0), "phq4_score", FIXED, "uid")
    assert scaled.ar1_phi == pytest.approx(fit.ar1_phi, rel=1e-6)
    assert scaled.sigma == pytest.approx(fit.sigma, rel=1e-6)
    assert scaled.params["x_within"] * 1000 == pytest.approx(fit.params["x_within"], rel=1e-5)
    assert scaled.pvalues["x_within"] == pytest.approx(fit.pvalues["x_within"], rel=1e-4)
    uid = next(iter(fit.blups))
    assert scaled.blups[uid]["x_within"] * 1000 == pytest.approx(fit.blups[uid]["x_within"], rel=1e-4, abs=1e-8)


def test_denominator_df_follows_nlme(fit, frame):
    problem = lme._Problem(frame, "phq4_score", FIXED, "uid", True)
    df = lme._denominator_df(problem, frame, FIXED, "uid")
    n, g = len(frame), frame["uid"].nunique()
    assert df == {"Intercept": n - g - 1, "x_within": n - g - 1, "x_between": g - 2}


def test_falls_back_to_random_intercept_when_the_slope_model_does_not_converge(frame, monkeypatch):
    real = lme._converged
    calls = []

    def first_fails(problem, res):
        calls.append(problem.q)
        return False if problem.q == 2 else real(problem, res)

    monkeypatch.setattr(lme, "_converged", first_fails)
    out = lme.fit_lme_ar1(frame, "phq4_score", FIXED, "uid")
    assert calls == [2, 1]
    assert out.used_random_slope is False and "did not converge" in out.fallback_reason
    assert set(out.random_effects_cov) == {"Intercept"}


def test_row_order_within_person_is_respected(frame):
    shuffled_people = pd.concat([g for _, g in frame.groupby("uid", sort=False)][::-1], ignore_index=True)
    a = lme.fit_lme_ar1(frame, "phq4_score", FIXED, "uid")
    b = lme.fit_lme_ar1(shuffled_people, "phq4_score", FIXED, "uid")
    assert b.params["x_within"] == pytest.approx(a.params["x_within"], rel=1e-6)
    assert b.ar1_phi == pytest.approx(a.ar1_phi, rel=1e-6)


@pytest.mark.skipif(not r_bridge.r_bridge_available(), reason="R + rpy2 + nlme not usable in this environment")
def test_matches_r_nlme_on_the_same_data(frame, fit):
    r = r_bridge.fit_lme_ar1(frame, "phq4_score", FIXED, "uid")
    norm = {"(Intercept)": "Intercept"}
    for k, v in r.params.items():
        assert fit.params[norm.get(k, k)] == pytest.approx(v, rel=1e-4, abs=1e-6)
    assert fit.ar1_phi == pytest.approx(r.ar1_phi, abs=1e-5)
    assert fit.sigma == pytest.approx(r.sigma, rel=1e-5)
    for uid, effects in r.blups.items():
        for k, v in effects.items():
            assert fit.blups[str(uid)][norm.get(k, k)] == pytest.approx(v, abs=1e-4)
