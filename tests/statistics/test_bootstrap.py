"""
Tests for backend/statistics/bootstrap.py.

Pure-Python aggregation/checkpoint logic is tested directly (no R needed).
Anything that actually fits a model (`_run_parametric_iteration`,
`_run_cluster_iteration`, `fit_real_model`) requires the R nlme engine —
same `requires_r` skip convention as tests/statistics/test_mixed_effects_model.py
and tests/statistics/test_r_bridge.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.statistics import bootstrap, r_bridge
from backend.statistics.mixed_effects_model import Ar1EffectResult

R_AVAILABLE = r_bridge.r_bridge_available()
requires_r = pytest.mark.skipif(
    not R_AVAILABLE,
    reason="R + rpy2 + lme4/lmerTest/pbkrtest/nlme not usable in this environment "
    "(see docs/statistics/r-bridge-setup.md — on Windows this must be checked from a "
    "native process, not git-bash/MSYS)",
)


def _synthetic_frame_with_dates(n_people: int, n_occasions: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    start = pd.Timestamp("2020-01-01")
    for p in range(n_people):
        uid = f"synthetic_{p}"
        person_level = rng.normal(9.0, 0.5)
        for occasion in range(n_occasions):
            x_within_true = rng.normal(0.0, 1.0)
            phq4 = 5.0 - 1.0 * x_within_true + rng.normal(0, 0.5)
            rows.append(
                {
                    "uid": uid,
                    "x_within": x_within_true,
                    "x_between": person_level - 9.0,
                    "phq4_score": phq4,
                    "date": start + pd.Timedelta(days=occasion * 5),
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Seed derivation
# ---------------------------------------------------------------------------


def test_derive_seed_is_deterministic():
    a = bootstrap.derive_seed(42, "parametric", 7)
    b = bootstrap.derive_seed(42, "parametric", 7)
    assert a == b


def test_derive_seed_differs_across_method_and_index():
    seeds = {
        bootstrap.derive_seed(42, "parametric", 0),
        bootstrap.derive_seed(42, "parametric", 1),
        bootstrap.derive_seed(42, "cluster", 0),
        bootstrap.derive_seed(42, "cluster", 1),
    }
    assert len(seeds) == 4


def test_derive_seed_differs_across_master_seed():
    assert bootstrap.derive_seed(1, "parametric", 0) != bootstrap.derive_seed(2, "parametric", 0)


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------


def test_checkpoint_round_trip(tmp_path):
    path = tmp_path / "checkpoint.jsonl"
    assert bootstrap.load_records(path) == []
    assert bootstrap.load_completed_keys(path) == set()

    rec1 = {"method": "parametric", "iteration_index": 0, "seed": 1, "usable": True}
    rec2 = {"method": "cluster", "iteration_index": 3, "seed": 2, "usable": False}
    bootstrap.append_record(path, rec1)
    bootstrap.append_record(path, rec2)

    records = bootstrap.load_records(path)
    assert records == [rec1, rec2]
    assert bootstrap.load_completed_keys(path) == {("parametric", 0), ("cluster", 3)}


def test_pending_tasks_skips_completed_and_resumes(tmp_path):
    path = tmp_path / "checkpoint.jsonl"
    bootstrap.append_record(path, {"method": "parametric", "iteration_index": 0, "seed": 1})
    bootstrap.append_record(path, {"method": "parametric", "iteration_index": 1, "seed": 2})

    config = bootstrap.BootstrapRunConfig(
        master_seed=42, n_iterations=3, checkpoint_path=path, methods=("parametric",)
    )
    pending = bootstrap._pending_tasks(config)
    assert [t[1] for t in pending] == [2]  # only iteration 2 remains


# ---------------------------------------------------------------------------
# Per-person / population aggregation (fabricated records, no R)
# ---------------------------------------------------------------------------


def _rec(method, usable=True, beta=-0.3, blups=None, uid_map=None, error=None, used_random_slope=True):
    return {
        "method": method,
        "usable": usable,
        "error": error,
        "used_random_slope": used_random_slope,
        "beta": {"x_within": beta},
        "blups": blups or {},
        "uid_map": uid_map,
        "selection_counts": None,
    }


def test_collect_person_slope_draws_parametric_pools_across_iterations():
    records = [
        _rec("parametric", beta=-0.30, blups={"p1": {"x_within": 0.10}, "p2": {"x_within": -0.05}}),
        _rec("parametric", beta=-0.28, blups={"p1": {"x_within": 0.08}, "p2": {"x_within": -0.02}}),
    ]
    draws = bootstrap.collect_person_slope_draws(records, "parametric")
    assert draws["p1"] == pytest.approx([-0.30 + 0.10, -0.28 + 0.08])
    assert draws["p2"] == pytest.approx([-0.30 - 0.05, -0.28 - 0.02])


def test_collect_person_slope_draws_cluster_maps_synthetic_to_real_uid():
    records = [
        _rec(
            "cluster",
            beta=-0.3,
            blups={"p1__boot0": {"x_within": 0.1}, "p1__boot1": {"x_within": 0.2}, "p2__boot2": {"x_within": -0.1}},
            uid_map={"p1__boot0": "p1", "p1__boot1": "p1", "p2__boot2": "p2"},
        ),
    ]
    draws = bootstrap.collect_person_slope_draws(records, "cluster")
    # p1 was drawn twice in this one iteration -> two pooled draws for p1.
    assert draws["p1"] == pytest.approx([-0.3 + 0.1, -0.3 + 0.2])
    assert draws["p2"] == pytest.approx([-0.3 - 0.1])


def test_collect_person_slope_draws_excludes_unusable_and_other_method():
    records = [
        _rec("parametric", usable=False, blups={"p1": {"x_within": 0.1}}),
        _rec("cluster", usable=True, blups={"p1": {"x_within": 0.1}}, uid_map={"p1": "p1"}),
        _rec("parametric", usable=True, blups={"p1": {"x_within": 0.5}}),
    ]
    draws = bootstrap.collect_person_slope_draws(records, "parametric")
    assert draws["p1"] == pytest.approx([-0.3 + 0.5])


def test_per_person_se_nan_below_min_draws():
    out = bootstrap.per_person_se({"p1": [1.0], "p2": [1.0, 2.0, 3.0]}, min_draws=2)
    by_uid = out.set_index("uid")
    assert np.isnan(by_uid.loc["p1", "slope_se"])
    assert by_uid.loc["p1", "n_bootstrap_draws"] == 1
    assert not np.isnan(by_uid.loc["p2", "slope_se"])
    assert by_uid.loc["p2", "slope_se"] == pytest.approx(np.std([1.0, 2.0, 3.0], ddof=1))


def test_population_beta_se_matches_numpy_std_of_usable_draws():
    records = [
        _rec("parametric", beta=-0.30),
        _rec("parametric", beta=-0.25),
        _rec("parametric", beta=-0.35),
        _rec("parametric", beta=-0.10, usable=False),  # excluded
        _rec("cluster", beta=999.0),  # different method, excluded
    ]
    se = bootstrap.population_beta_se(records, "parametric")
    assert se == pytest.approx(np.std([-0.30, -0.25, -0.35], ddof=1))


def test_failure_summary_counts_errors_and_fallbacks_separately():
    records = [
        _rec("parametric", usable=True),
        _rec("parametric", usable=False, error="boom", used_random_slope=True),
        _rec("parametric", usable=False, error=None, used_random_slope=False),
        _rec("cluster", usable=True),  # different method, excluded
    ]
    summary = bootstrap.failure_summary(records, "parametric")
    assert summary["n_total"] == 3
    assert summary["n_usable"] == 1
    assert summary["n_error"] == 1
    assert summary["n_fallback_to_intercept_only"] == 1
    assert summary["failure_rate"] == pytest.approx(2 / 3)


def test_selection_count_distribution_reads_cluster_records_only():
    # selection_counts never contains a 0 entry in practice (pd.value_counts
    # only counts uids actually drawn at least once) -- a person absent from
    # an iteration simply has no entry for it, which is the "missingness".
    records = [
        {"method": "cluster", "iteration_index": 0, "selection_counts": {"p1": 2}},
        {"method": "parametric", "iteration_index": 0, "selection_counts": None},
    ]
    out = bootstrap.selection_count_distribution(records)
    assert len(out) == 1
    assert out.iloc[0]["uid"] == "p1"
    assert out.iloc[0]["times_selected"] == 2


# ---------------------------------------------------------------------------
# Parametric simulation (pure NumPy, no R)
# ---------------------------------------------------------------------------


def test_simulate_parametric_outcome_is_deterministic_given_seed():
    data = pd.DataFrame(
        {
            "uid": ["a", "a", "a", "b", "b"],
            "x_within": [0.1, -0.2, 0.3, 0.5, -0.1],
            "x_between": [0.0, 0.0, 0.0, 1.0, 1.0],
        }
    )
    beta = {"Intercept": 5.0, "x_within": -0.3, "x_between": 0.2}
    cov = {"Intercept": {"Intercept": 1.0, "x_within": 0.0}, "x_within": {"Intercept": 0.0, "x_within": 0.05}}

    out1 = bootstrap._simulate_parametric_outcome(
        data, "uid", ["x_within", "x_between"], beta, cov, sigma=1.0, phi=0.5, rng=np.random.default_rng(123)
    )
    out2 = bootstrap._simulate_parametric_outcome(
        data, "uid", ["x_within", "x_between"], beta, cov, sigma=1.0, phi=0.5, rng=np.random.default_rng(123)
    )
    assert np.array_equal(out1, out2)
    assert len(out1) == len(data)


def test_simulate_parametric_outcome_varies_across_seeds():
    data = pd.DataFrame({"uid": ["a"] * 5, "x_within": [0.1, -0.2, 0.3, 0.5, -0.1], "x_between": [0.0] * 5})
    beta = {"Intercept": 5.0, "x_within": -0.3, "x_between": 0.2}
    cov = {"Intercept": {"Intercept": 1.0, "x_within": 0.0}, "x_within": {"Intercept": 0.0, "x_within": 0.05}}

    out1 = bootstrap._simulate_parametric_outcome(
        data, "uid", ["x_within", "x_between"], beta, cov, sigma=1.0, phi=0.5, rng=np.random.default_rng(1)
    )
    out2 = bootstrap._simulate_parametric_outcome(
        data, "uid", ["x_within", "x_between"], beta, cov, sigma=1.0, phi=0.5, rng=np.random.default_rng(2)
    )
    assert not np.array_equal(out1, out2)


# ---------------------------------------------------------------------------
# R-backed smoke tests
# ---------------------------------------------------------------------------


def test_fit_real_model_raises_without_r_backed_blups(monkeypatch):
    """Mirrors evidence.extract_person_slopes's own guard: bootstrapping
    needs real per-person BLUPs and variance components, which only the R
    engine provides — must fail loudly, not silently, if that's missing."""
    gee_like = Ar1EffectResult(
        engine="GEE (Python fallback, population-averaged, R unavailable in this environment)",
        ar1_coefficient=0.0,
        used_random_slope=None,
        fallback_reason=None,
        n_observations=10,
        n_groups=2,
        params={"x_within": -0.3, "x_between": 0.1, "Intercept": 5.0},
        pvalues={"x_within": 0.01, "x_between": 0.5, "Intercept": 1e-10},
        blups=None,
    )
    monkeypatch.setattr(bootstrap, "fit_ar1_effect", lambda *a, **k: gee_like)
    frame = pd.DataFrame(
        {
            "uid": ["a", "b"],
            "date": [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-02")],
            "phq4_score": [1.0, 2.0],
            "x_within": [0.1, -0.1],
            "x_between": [0.0, 0.0],
        }
    )
    with pytest.raises(ValueError, match="real BLUPs"):
        bootstrap.fit_real_model(frame)


@requires_r
def test_fit_real_model_on_synthetic_data():
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=1)
    real_fit = bootstrap.fit_real_model(frame)
    assert real_fit.ar1_result.blups is not None
    assert real_fit.ar1_result.sigma is not None
    assert real_fit.ar1_result.sigma > 0
    assert real_fit.ar1_result.random_effects_cov is not None
    assert "Intercept" in real_fit.ar1_result.random_effects_cov
    if real_fit.ar1_result.used_random_slope:
        assert "x_within" in real_fit.ar1_result.random_effects_cov
    # model_frame must be sorted by [uid, date] for the AR(1)-by-occasion-order assumption
    for _uid, group in real_fit.model_frame.groupby("uid"):
        assert list(group["date"]) == sorted(group["date"])


@requires_r
def test_run_parametric_iteration_smoke_and_reproducibility():
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=2)
    real_fit = bootstrap.fit_real_model(frame)
    beta = {k: float(v) for k, v in real_fit.ar1_result.params.items()}
    cov = real_fit.ar1_result.random_effects_cov
    sigma = real_fit.ar1_result.sigma
    phi = real_fit.ar1_result.ar1_coefficient

    seed = bootstrap.derive_seed(99, "parametric", 0)
    rec1 = bootstrap._run_parametric_iteration(
        0, seed, real_fit.model_frame, real_fit.outcome_col, real_fit.uid_col, real_fit.date_col,
        real_fit.fixed_effect_names, beta, cov, sigma, phi,
    )
    rec2 = bootstrap._run_parametric_iteration(
        0, seed, real_fit.model_frame, real_fit.outcome_col, real_fit.uid_col, real_fit.date_col,
        real_fit.fixed_effect_names, beta, cov, sigma, phi,
    )
    assert rec1["error"] is None
    assert rec1["blups"] is not None
    assert rec1["beta"]["x_within"] == pytest.approx(rec2["beta"]["x_within"])


@requires_r
def test_run_cluster_iteration_smoke_and_uid_relabeling():
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=3)
    real_fit = bootstrap.fit_real_model(frame)
    seed = bootstrap.derive_seed(99, "cluster", 0)

    rec = bootstrap._run_cluster_iteration(
        0, seed, real_fit.model_frame, real_fit.outcome_col, real_fit.uid_col, real_fit.date_col,
        real_fit.fixed_effect_names,
    )
    assert rec["error"] is None
    assert sum(rec["selection_counts"].values()) == real_fit.model_frame["uid"].nunique()
    if rec["blups"] is not None:
        for synthetic_uid in rec["blups"]:
            assert synthetic_uid in rec["uid_map"]


@requires_r
def test_run_bootstrap_serial_b10_both_methods(tmp_path):
    """Step 1 of the implementation order: a small serial run exercises
    the full pipeline (fit, simulate/resample, refit, checkpoint) end to
    end on synthetic data before any real-data or parallel run."""
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=4)
    real_fit = bootstrap.fit_real_model(frame)

    checkpoint = tmp_path / "b10.jsonl"
    config = bootstrap.BootstrapRunConfig(master_seed=7, n_iterations=10, checkpoint_path=checkpoint)
    records = bootstrap.run_bootstrap_serial(real_fit, config)

    assert len(records) == 20  # 10 iterations x 2 methods
    assert {r["method"] for r in records} == {"parametric", "cluster"}

    # resuming with the same config must not redo completed work
    records_again = bootstrap.run_bootstrap_serial(real_fit, config)
    assert len(records_again) == 20

    draws = bootstrap.collect_person_slope_draws(records, "parametric")
    se_df = bootstrap.per_person_se(draws)
    assert len(se_df) > 0
