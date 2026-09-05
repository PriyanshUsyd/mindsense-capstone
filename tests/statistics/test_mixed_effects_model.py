"""
Tests for backend/statistics/mixed_effects_model.py — Moe Tanaka's Week 5
deliverable. Additive to tests/statistics/test_eligibility.py (Week 4's
22 cold-start tests); nothing there is modified or replaced.

Unit tests use small synthetic frames. The end-to-end test fits the real
model against the real local CES dataset and is skipped automatically
when that dataset isn't present (gitignored) — same pattern as
tests/integration/test_ces_eligibility_scripts_agree.py.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.statistics import r_bridge
from backend.statistics.mixed_effects_model import (
    ALIGNMENT_WINDOW_DAYS,
    OCCASION_MIN_VALID_SENSOR_DAYS,
    _between_within_denominator_df,
    adjust_confirmatory_family,
    adjust_exploratory_family,
    build_model_frame,
    build_trailing_predictor,
    classify_evidence_strength,
    compute_time_covariates,
    fit_ar1_effect,
    fit_ar1_robustness_check,
    fit_mixed_effects_model,
)

R_AVAILABLE = r_bridge.r_bridge_available()
requires_r = pytest.mark.skipif(
    not R_AVAILABLE,
    reason="R + rpy2 + lme4/lmerTest/pbkrtest/nlme not usable in this environment "
    "(see docs/statistics/r-bridge-setup.md — on Windows this must be checked from a "
    "native process, not git-bash/MSYS)",
)

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


def _synthetic_sensing(uid: str, n_days: int, value: float = 5.0) -> pd.DataFrame:
    start = pd.Timestamp("2020-01-01")
    days = [int((start + pd.Timedelta(days=i)).strftime("%Y%m%d")) for i in range(n_days)]
    return pd.DataFrame({"uid": uid, "day": days, "loc_dist_ep_0_log": value})


def test_locked_constants_match_the_spec():
    assert ALIGNMENT_WINDOW_DAYS == 14
    assert OCCASION_MIN_VALID_SENSOR_DAYS == 7


def test_trailing_predictor_computes_calendar_correct_rolling_mean():
    sensing = _synthetic_sensing("a", n_days=20, value=10.0)
    # Introduce a gap and a different value for the last few days.
    sensing.loc[sensing.index[-3:], "loc_dist_ep_0_log"] = 20.0

    out = build_trailing_predictor(sensing, window_days=14)
    last_row = out.iloc[-1]
    # Trailing 14-day window ending on the last day: 11 days at 10.0, 3 days at 20.0.
    expected = (11 * 10.0 + 3 * 20.0) / 14
    assert last_row["x_it"] == pytest.approx(expected)
    assert last_row["valid_sensor_days_in_window"] == 14


def test_trailing_predictor_reindexes_gaps_as_invalid_not_missing_rows():
    sensing = pd.DataFrame(
        {
            "uid": ["a", "a"],
            "day": [20200101, 20200110],  # 9-day gap
            "loc_dist_ep_0_log": [5.0, 5.0],
        }
    )
    out = build_trailing_predictor(sensing, window_days=14)
    # The reindexed range must include the gap days, not just the two observed rows.
    assert len(out) == 10


def test_occasion_validity_gate_drops_not_imputes():
    """An EMA occasion whose trailing window has < 7 valid sensor-days
    must be excluded from the model frame entirely, not filled in."""
    sensing = _synthetic_sensing("a", n_days=14, value=5.0)
    # Blank out all but 3 days of sensing data.
    sensing = sensing.iloc[:3]

    ema = pd.DataFrame({"uid": ["a"], "day": [20200114], "phq4_score": [4.0]})
    frame = build_model_frame(sensing, ema, min_valid_sensor_days=7)
    assert len(frame) == 0


def test_within_and_between_person_centring():
    """Two participants with different mean travel levels: x_within must
    be centred on each person's own mean (so a person who always travels
    the same amount has x_within == 0 for every occasion), and x_between
    must separate the two people's overall levels."""
    sensing_a = _synthetic_sensing("a", n_days=20, value=5.0)  # constant
    sensing_b = _synthetic_sensing("b", n_days=20, value=10.0)  # constant, different level
    sensing = pd.concat([sensing_a, sensing_b], ignore_index=True)

    ema = pd.DataFrame(
        {
            "uid": ["a", "a", "b", "b"],
            "day": [20200115, 20200120, 20200115, 20200120],
            "phq4_score": [3.0, 4.0, 5.0, 6.0],
        }
    )
    frame = build_model_frame(sensing, ema)

    assert frame["x_within"].abs().max() < 1e-9  # constant feature -> always centred to ~0
    a_between = frame[frame["uid"] == "a"]["x_between"].iloc[0]
    b_between = frame[frame["uid"] == "b"]["x_between"].iloc[0]
    assert b_between > a_between  # b travels more on average than a


def test_fit_mixed_effects_model_on_synthetic_data_with_a_real_signal():
    """Builds a frame with a genuine within-person relationship (more
    travel -> lower PHQ-4) across many synthetic participants, and
    confirms the fit converges and recovers a negative x_within
    coefficient with reasonable precision."""
    rng = np.random.default_rng(42)
    rows = []
    for p in range(40):
        uid = f"synthetic_{p}"
        person_level = rng.normal(9.0, 0.5)
        for occasion in range(15):
            x_within_true = rng.normal(0.0, 1.0)
            x_it = person_level + x_within_true
            phq4 = 5.0 - 1.0 * x_within_true + rng.normal(0, 0.5)
            rows.append(
                {
                    "uid": uid,
                    "x_it": x_it,
                    "x_within": x_within_true,
                    "x_between": person_level - 9.0,
                    "phq4_score": phq4,
                }
            )
    frame = pd.DataFrame(rows)

    fit = fit_mixed_effects_model(frame)

    assert fit.converged
    assert fit.n_observations == len(frame)
    assert fit.n_groups == 40
    assert fit.params["x_within"] < 0  # recovers the true negative relationship
    assert fit.pvalues["x_within"] < 0.01  # 40 groups x 15 occasions with a strong true effect


def test_fallback_to_random_intercept_only_is_recorded_when_random_slope_fails():
    """Only 2 occasions per group is too few to estimate a per-group
    slope variance, which should make the random-slope model unstable
    (fail to converge, or yield a degenerate covariance) while the
    simpler random-intercept-only fallback can still fit real
    (non-degenerate) outcome/predictor variation. We assert the
    *contract*: converged is a real bool, and if a fallback happened,
    used_random_slope is False and fallback_reason is set."""
    rng = np.random.default_rng(7)
    rows = []
    for p in range(30):
        uid = f"tiny_{p}"
        for occasion in range(2):
            x_within = rng.normal(0.0, 1.0)
            rows.append(
                {
                    "uid": uid,
                    "x_within": x_within,
                    "x_between": rng.normal(0.0, 0.5),
                    "phq4_score": 5.0 - 0.5 * x_within + rng.normal(0, 1.0),
                }
            )
    frame = pd.DataFrame(rows)

    fit = fit_mixed_effects_model(frame)

    assert isinstance(fit.converged, bool)
    if not fit.used_random_slope:
        assert fit.fallback_reason is not None


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


def test_compute_time_covariates_week_in_study_is_weeks_since_first_occasion():
    frame = pd.DataFrame(
        {
            "uid": ["a", "a", "a"],
            "date": pd.to_datetime(["2020-01-01", "2020-01-08", "2020-01-22"]),
        }
    )
    out = compute_time_covariates(frame)
    assert out["week_in_study"].tolist() == pytest.approx([0.0, 1.0, 3.0])


def test_compute_time_covariates_term_phase_flags_known_break_and_term_dates():
    frame = pd.DataFrame(
        {
            "uid": ["a", "a", "a"],
            # Dec 25 (winter break), Jan 20 (in-term), Jul 1 (summer break).
            "date": pd.to_datetime(["2020-12-25", "2021-01-20", "2021-07-01"]),
        }
    )
    out = compute_time_covariates(frame)
    assert out["term_phase"].tolist() == [0, 1, 0]


def test_extra_fixed_effects_are_estimated_when_requested():
    """Backward compatibility: omitting extra_fixed_effects must leave the
    formula exactly `phq4_score ~ x_within + x_between` (already covered
    by the other tests in this file, which don't pass it). Passing it
    should add the term to both the formula and the returned params."""
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=1)
    frame = compute_time_covariates(frame)

    fit = fit_mixed_effects_model(frame, extra_fixed_effects=["week_in_study"])

    assert "week_in_study" in fit.params
    assert "week_in_study" in fit.pvalues
    assert "week_in_study" in fit.denom_df


def test_between_within_denominator_df_matches_the_containment_formula():
    data = pd.DataFrame({"uid": ["a"] * 5 + ["b"] * 5 + ["c"] * 5})
    denom = _between_within_denominator_df(data, "uid", ["x_within", "x_between"])
    n_obs, n_groups = 15, 3
    assert denom["x_within"] == n_obs - n_groups - 1
    assert denom["x_between"] == n_groups - 1 - 1


def test_between_within_denominator_df_is_not_confused_with_satterthwaite():
    """The one thing this test protects: the Python fallback path's
    denom_df_method must never silently start claiming to be
    Satterthwaite/Kenward-Roger. Forces prefer_r=False so this checks the
    fallback path's own labelling regardless of whether R happens to be
    available in the environment running this test — R being primary
    when available is exactly the point of test_fit_mixed_effects_model_
    uses_r_as_the_primary_engine_when_available below, not this test."""
    frame = _synthetic_frame_with_dates(n_people=20, n_occasions=10, seed=2)
    fit = fit_mixed_effects_model(frame, prefer_r=False)
    assert fit.engine == "statsmodels (Python fallback)"
    assert fit.denom_df_method is not None
    assert "between-within" in fit.denom_df_method
    assert "Satterthwaite" not in fit.denom_df_method
    assert "Kenward-Roger" not in fit.denom_df_method


def test_fit_mixed_effects_model_uses_python_fallback_when_r_is_forced_off():
    """prefer_r=False must produce identical behaviour to the pre-R-bridge
    implementation, regardless of whether R happens to be available."""
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=1)
    fit = fit_mixed_effects_model(frame, prefer_r=False)
    assert fit.engine == "statsmodels (Python fallback)"
    assert fit.params["x_within"] < 0


@requires_r
def test_fit_mixed_effects_model_uses_r_as_the_primary_engine_when_available():
    """When R is available, fit_mixed_effects_model must use it by
    default (prefer_r defaults to True) — this is the whole point of
    wiring the R bridge in as primary, not just available-but-unused."""
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=5)
    fit = fit_mixed_effects_model(frame)
    assert fit.engine == "R (lme4::lmer + lmerTest)"
    assert fit.denom_df_method == "Satterthwaite (R lme4::lmer + lmerTest)"
    assert set(fit.denom_df) == {"x_within", "x_between"}
    assert fit.params["x_within"] < 0
    assert fit.pvalues["x_within"] < 0.01


@requires_r
def test_fit_mixed_effects_model_kenward_roger_via_r():
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=6)
    fit = fit_mixed_effects_model(frame, df_method="Kenward-Roger")
    assert fit.engine == "R (lme4::lmer + lmerTest)"
    assert fit.denom_df_method == "Kenward-Roger (R lme4::lmer + lmerTest)"
    assert np.isfinite(fit.denom_df["x_within"])
    assert np.isfinite(fit.pvalues["x_within"])


@requires_r
def test_fit_mixed_effects_model_r_and_python_agree_on_point_estimates():
    """R lmer and statsmodels MixedLM fit the same REML model — their
    x_within point estimates should be very close (both are legitimate
    numerical fits of the same specification, not expected to be bit-
    identical given different optimizers)."""
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=7)
    r_fit = fit_mixed_effects_model(frame, prefer_r=True)
    py_fit = fit_mixed_effects_model(frame, prefer_r=False)
    assert r_fit.params["x_within"] == pytest.approx(py_fit.params["x_within"], abs=0.01)


@requires_r
def test_r_bridge_is_not_confused_with_satterthwaite_python_fallback_split():
    """Sanity check on the engine split itself: forcing prefer_r=False
    must never accidentally still hit R (e.g. via a bug that ignores the
    flag)."""
    frame = _synthetic_frame_with_dates(n_people=20, n_occasions=10, seed=8)
    fit = fit_mixed_effects_model(frame, prefer_r=False)
    assert fit.engine == "statsmodels (Python fallback)"


def test_ar1_robustness_check_runs_and_reports_a_rho_or_a_flagged_fallback():
    """Mirrors the defensive style of
    test_fallback_to_random_intercept_only_is_recorded_when_random_slope_fails:
    the Rosner & Munoz dependence-parameter search can itself fail to
    converge on data with little genuine serial correlation (a documented
    property of the estimator). We assert the contract: a real float rho
    is always returned, and if the fallback path was used,
    fallback_reason is set (not silently swallowed)."""
    frame = _synthetic_frame_with_dates(n_people=25, n_occasions=15, seed=3)

    result = fit_ar1_robustness_check(frame)

    assert isinstance(result.ar1_rho, float)
    assert np.isfinite(result.ar1_rho)
    assert "x_within" in result.params
    if result.fallback_reason is not None:
        assert result.ar1_rho == 0.0


def test_ar1_robustness_check_recovers_the_same_sign_as_the_primary_fit():
    """Not the same estimand as the MixedLM fit (population-averaged vs.
    person-specific), but on data with a genuine strong within-person
    relationship, both should agree on the sign of x_within."""
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=4)

    primary = fit_mixed_effects_model(frame)
    ar1 = fit_ar1_robustness_check(frame)

    assert primary.params["x_within"] < 0
    assert ar1.params["x_within"] < 0


def test_fit_ar1_effect_falls_back_to_gee_when_r_is_forced_off():
    frame = _synthetic_frame_with_dates(n_people=25, n_occasions=15, seed=9)
    result = fit_ar1_effect(frame, prefer_r=False)
    assert result.engine.startswith("GEE (Python fallback")
    assert result.blups is None
    assert result.used_random_slope is None
    assert "x_within" in result.params


@requires_r
def test_fit_ar1_effect_uses_r_as_the_primary_engine_when_available():
    """When R is available, fit_ar1_effect must use the real joint
    AR(1) mixed model by default — this is the whole point of wiring the
    R bridge in as primary, not just available-but-unused. Also confirms
    real per-person BLUPs come back, which GEE structurally cannot
    provide."""
    frame = _synthetic_frame_with_dates(n_people=30, n_occasions=15, seed=10)
    result = fit_ar1_effect(frame)
    assert result.engine == "R (nlme::lme + corAR1)"
    assert np.isfinite(result.ar1_coefficient)
    assert result.blups is not None
    assert len(result.blups) == 30
    sample_uid = next(iter(result.blups))
    assert "Intercept" in result.blups[sample_uid]


@requires_r
def test_r_bridge_ar1_bypasses_the_gee_fallback_entirely():
    """Sanity check on the engine split: forcing prefer_r=False on
    fit_ar1_effect must genuinely produce the GEE result (no BLUPs),
    distinguishable from the R engine's result (has BLUPs)."""
    frame = _synthetic_frame_with_dates(n_people=25, n_occasions=15, seed=11)
    r_result = fit_ar1_effect(frame, prefer_r=True)
    gee_result = fit_ar1_effect(frame, prefer_r=False)
    assert r_result.blups is not None
    assert gee_result.blups is None
    assert gee_result.engine != r_result.engine


@requires_r
def test_end_to_end_r_backed_fit_against_the_real_dataset():
    """Real dataset, real R fit — the primary path, not synthetic data."""
    from backend.data_pipeline.gps_distance_feature import build_gps_distance_feature, load_sensing_days

    sensing_days = load_sensing_days()
    cleaned = build_gps_distance_feature(sensing_days)
    ema = pd.read_csv(DATASET_DIR / "EMA" / "general_ema.csv", usecols=["uid", "day", "phq4_score"])
    frame = build_model_frame(cleaned, ema)

    fit = fit_mixed_effects_model(frame)
    assert fit.engine == "R (lme4::lmer + lmerTest)"
    assert fit.converged
    assert fit.n_groups > 100
    assert np.isfinite(fit.params["x_within"])
    assert np.isfinite(fit.pvalues["x_within"])
    assert np.isfinite(fit.denom_df["x_within"])

    ar1 = fit_ar1_effect(frame)
    assert ar1.engine == "R (nlme::lme + corAR1)"
    assert np.isfinite(ar1.ar1_coefficient)
    assert ar1.blups is not None
    assert len(ar1.blups) == fit.n_groups


def test_adjust_confirmatory_family_matches_holm_bonferroni():
    from statsmodels.stats.multitest import multipletests

    pvalues = {"feature_a": 0.001, "feature_b": 0.02, "feature_c": 0.2}
    result = adjust_confirmatory_family(pvalues, alpha=0.05)

    reject, p_adjusted, _, _ = multipletests(list(pvalues.values()), alpha=0.05, method="holm")
    for name, expected_reject, expected_p in zip(pvalues, reject, p_adjusted):
        assert result[name]["reject"] == bool(expected_reject)
        assert result[name]["p_adjusted"] == pytest.approx(float(expected_p))


def test_adjust_exploratory_family_matches_benjamini_hochberg():
    from statsmodels.stats.multitest import multipletests

    pvalues = {"feature_a": 0.001, "feature_b": 0.02, "feature_c": 0.2, "feature_d": 0.03}
    result = adjust_exploratory_family(pvalues, q=0.05)

    reject, q_values, _, _ = multipletests(list(pvalues.values()), alpha=0.05, method="fdr_bh")
    for name, expected_reject, expected_q in zip(pvalues, reject, q_values):
        assert result[name]["reject"] == bool(expected_reject)
        assert result[name]["q_value"] == pytest.approx(float(expected_q))


def test_classify_evidence_strength_all_four_tiers():
    # Strong: needs the lag0/lag1 consistency flag explicitly True.
    assert classify_evidence_strength(0.005, 0.25, 15, lag0_lag1_consistent_sign=True) == "strong"
    # Moderate.
    assert classify_evidence_strength(0.03, 0.12, 9) == "moderate"
    # Weak.
    assert classify_evidence_strength(0.08, 0.11, 8) == "weak"
    # Insufficient (fails every gate).
    assert classify_evidence_strength(0.5, 0.05, 3) == "insufficient"


def test_classify_evidence_strength_strong_is_unreachable_without_lag_comparison():
    """Flagged scope gap (module docstring / Section 7): without the
    lag-1 term (out of scope for this module), callers can't supply
    lag0_lag1_consistent_sign, so a result that would otherwise qualify
    as 'strong' is capped at 'moderate' instead of silently upgraded."""
    assert classify_evidence_strength(0.005, 0.25, 15) == "moderate"
    assert classify_evidence_strength(0.005, 0.25, 15, lag0_lag1_consistent_sign=False) == "moderate"


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_end_to_end_fit_against_the_real_dataset():
    """Real dataset, real cleaning, real model fit — not fixtures."""
    from backend.data_pipeline.gps_distance_feature import build_gps_distance_feature, load_sensing_days

    sensing_days = load_sensing_days()
    cleaned = build_gps_distance_feature(sensing_days)
    ema = pd.read_csv(DATASET_DIR / "EMA" / "general_ema.csv", usecols=["uid", "day", "phq4_score"])

    frame = build_model_frame(cleaned, ema)
    assert len(frame) > 1000  # real data should yield thousands of valid occasions
    assert "week_in_study" in frame.columns
    assert "term_phase" in frame.columns

    fit = fit_mixed_effects_model(frame)

    assert fit.converged
    assert fit.n_groups > 100  # most of the 220-participant cohort should contribute occasions
    assert "x_within" in fit.params
    assert "x_between" in fit.params
    assert np.isfinite(fit.params["x_within"])
    assert np.isfinite(fit.pvalues["x_within"])
    assert fit.reml is True
    assert fit.denom_df_method is not None
    assert set(fit.denom_df) == {"x_within", "x_between"}


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_end_to_end_fit_with_time_covariates_against_the_real_dataset():
    """Same real dataset/pipeline as the test above, but requesting the
    new week_in_study/term_phase fixed effects — confirms the extended
    formula still converges on real data, not just synthetic fixtures."""
    from backend.data_pipeline.gps_distance_feature import build_gps_distance_feature, load_sensing_days

    sensing_days = load_sensing_days()
    cleaned = build_gps_distance_feature(sensing_days)
    ema = pd.read_csv(DATASET_DIR / "EMA" / "general_ema.csv", usecols=["uid", "day", "phq4_score"])

    frame = build_model_frame(cleaned, ema)

    fit = fit_mixed_effects_model(frame, extra_fixed_effects=["week_in_study", "term_phase"])
    assert fit.converged
    assert "week_in_study" in fit.params
    assert "term_phase" in fit.params
    assert np.isfinite(fit.params["week_in_study"])
    assert np.isfinite(fit.params["term_phase"])


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_end_to_end_ar1_robustness_check_against_the_real_dataset():
    """Real dataset AR(1) robustness check — confirms the GEE
    Autoregressive fit (or its documented independence fallback) runs to
    completion on the real, irregularly-spaced EMA data."""
    from backend.data_pipeline.gps_distance_feature import build_gps_distance_feature, load_sensing_days

    sensing_days = load_sensing_days()
    cleaned = build_gps_distance_feature(sensing_days)
    ema = pd.read_csv(DATASET_DIR / "EMA" / "general_ema.csv", usecols=["uid", "day", "phq4_score"])

    frame = build_model_frame(cleaned, ema)

    result = fit_ar1_robustness_check(frame)
    assert np.isfinite(result.ar1_rho)
    assert "x_within" in result.params
    assert np.isfinite(result.params["x_within"])
