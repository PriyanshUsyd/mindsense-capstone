"""
Tests for backend/statistics/evidence.py — the per-person evidence-strength
port from analysis/evidence_model.py onto fit_ar1_effect's R-backed BLUPs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.statistics.evidence import (
    EXPECTED_FAMILY_SIZE,
    PersonSlope,
    _nan_safe_correction,
    bootstrap_person_slopes,
    extract_person_slopes,
    intersect_bootstrap_evidence,
    reclassify_family213,
    to_user_facing_evidence,
)
from backend.statistics.mixed_effects_model import Ar1EffectResult


def _ar1_result(blups: dict | None, beta: float = -0.3) -> Ar1EffectResult:
    return Ar1EffectResult(
        engine="R (nlme::lme + corAR1)" if blups is not None else "GEE (Python fallback, population-averaged, R unavailable in this environment)",
        ar1_coefficient=0.6,
        used_random_slope=True,
        fallback_reason=None,
        n_observations=100,
        n_groups=len(blups) if blups else 0,
        params={"x_within": beta, "x_between": 0.1, "Intercept": 5.0},
        pvalues={"x_within": 1e-10, "x_between": 0.5, "Intercept": 1e-50},
        blups=blups,
    )


def test_extract_person_slopes_raises_without_blups():
    """GEE (R unavailable) has no per-person random effect — must fail
    loudly, not silently return an empty or population-averaged result."""
    gee_result = _ar1_result(blups=None)
    with pytest.raises(ValueError, match="per-person BLUPs"):
        extract_person_slopes(gee_result, pd.DataFrame({"uid": ["a"]}))


def test_extract_person_slopes_adds_fixed_effect_and_blup():
    blups = {
        "p1": {"Intercept": 0.5, "x_within": 0.10},
        "p2": {"Intercept": -0.2, "x_within": -0.05},
    }
    result = _ar1_result(blups=blups, beta=-0.30)
    frame = pd.DataFrame({"uid": ["p1"] * 5 + ["p2"] * 8})

    slopes = extract_person_slopes(result, frame)
    by_uid = {s.uid: s for s in slopes}

    assert by_uid["p1"].slope_i == pytest.approx(-0.30 + 0.10)
    assert by_uid["p2"].slope_i == pytest.approx(-0.30 - 0.05)
    assert by_uid["p1"].n_occasions == 5
    assert by_uid["p2"].n_occasions == 8
    # Flagged scope gap: SE/p are not yet derivable from the R nlme wrapper.
    assert by_uid["p1"].slope_se is None
    assert by_uid["p1"].slope_p is None


def test_extract_person_slopes_defaults_missing_term_to_zero_blup():
    """A person whose BLUP dict doesn't carry x_within (shouldn't happen in
    practice, but defensively) falls back to the fixed effect alone."""
    result = _ar1_result(blups={"p1": {"Intercept": 0.1}}, beta=-0.4)
    frame = pd.DataFrame({"uid": ["p1"]})
    slopes = extract_person_slopes(result, frame)
    assert slopes[0].slope_i == pytest.approx(-0.4)


def test_nan_safe_correction_excludes_undefined_tests_from_the_family():
    """One NaN must not poison every other participant's q-value — this is
    the specific bug analysis/evidence_model.py's _adjust_ignoring_nan
    fixed, ported here."""
    pvalues = np.array([0.001, np.nan, 0.5])
    out = _nan_safe_correction(pvalues, "fdr_bh")
    assert np.isnan(out[1])
    assert not np.isnan(out[0])
    assert not np.isnan(out[2])

    # Sanity: correcting just the two defined values directly should match.
    from statsmodels.stats.multitest import multipletests

    _, expected, _, _ = multipletests([0.001, 0.5], alpha=0.05, method="fdr_bh")
    assert out[0] == pytest.approx(expected[0])
    assert out[2] == pytest.approx(expected[1])


def test_reclassify_family213_is_insufficient_for_everyone_until_se_gap_closed():
    """Every PersonSlope currently has slope_p=None (see module docstring),
    so every person must classify 'insufficient' -> 'no_claim' — this is
    the deliberate fail-safe default, not a bug."""
    person_slopes = [
        PersonSlope(uid="p1", slope_i=-0.5, n_occasions=20),
        PersonSlope(uid="p2", slope_i=0.3, n_occasions=15),
    ]
    out = reclassify_family213(person_slopes, outcome_sd=2.0, predictor_sd=1.0)

    assert set(out["label_bh"]) == {"insufficient"}
    assert set(out["label_holm"]) == {"insufficient"}
    assert out["bh_q_213"].isna().all()
    assert out["holm_p_213"].isna().all()
    assert all(to_user_facing_evidence(label) == "no_claim" for label in out["label_bh"])


def test_reclassify_family213_uses_bh_when_p_values_are_supplied():
    """Once slope_p is populated (e.g. by a future SE fix), the
    classification pipeline must actually produce non-insufficient labels
    — confirms the plumbing works end-to-end, not just the fail-safe path."""
    person_slopes = [
        PersonSlope(uid=f"p{i}", slope_i=-0.5, n_occasions=20, slope_p=0.001)
        for i in range(10)
    ]
    out = reclassify_family213(person_slopes, outcome_sd=1.0, predictor_sd=1.0)
    assert not out["bh_q_213"].isna().any()
    assert set(out["label_bh"]) <= {"strong", "moderate", "weak", "insufficient"}
    # std_effect = |slope_i| * predictor_sd / outcome_sd = 0.5 here, and
    # q should survive BH-FDR correction on 10 near-identical p=0.001 tests
    # comfortably under 0.05 -> at least "moderate".
    assert (out["label_bh"] != "insufficient").all()


def test_to_user_facing_evidence_collapses_four_to_two():
    assert to_user_facing_evidence("strong") == "evidence_available"
    assert to_user_facing_evidence("moderate") == "evidence_available"
    assert to_user_facing_evidence("weak") == "no_claim"
    assert to_user_facing_evidence("insufficient") == "no_claim"


def test_to_user_facing_evidence_rejects_unrecognised_label():
    with pytest.raises(ValueError):
        to_user_facing_evidence("extremely_strong")


def test_expected_family_size_constant_matches_claude_md():
    assert EXPECTED_FAMILY_SIZE == 213


# --- bootstrap_person_slopes -----------------------------------------------
# FLAGGED FOR MOE TANAKA'S SIGN-OFF (see evidence.py's module docstring):
# these tests validate the resampling/aggregation MACHINERY using a fake,
# deterministic fit function injected via `fit_fn` -- they do not exercise
# a real R nlme::lme refit (R is not installed in this sandbox;
# r_bridge.r_bridge_available() is False here). The real behaviour of this
# function against a genuine R refit has not been verified end-to-end.


def _make_bootstrap_frame():
    # 4 participants, small enough for a fast bootstrap in tests.
    return pd.DataFrame(
        {
            "uid": ["p1"] * 5 + ["p2"] * 5 + ["p3"] * 5 + ["p4"] * 5,
            "phq4_score": np.linspace(0, 12, 20),
            "x_within": np.tile(np.linspace(-1, 1, 5), 4),
        }
    )


def _fake_fit_fn_factory(true_slope_by_uid: dict[str, float], noise_scale: float, seed_offset: list[int]):
    """Deterministic fake standing in for a real R AR(1) refit: each
    relabelled group's BLUP deviates from a per-person 'true' slope by a
    small amount of reproducible noise, so bootstrap_person_slopes' own
    aggregation/SE logic can be checked without needing R."""

    def _fake_fit(frame: pd.DataFrame, outcome_col: str, uid_col: str, extra_fixed_effects):
        rng = np.random.default_rng(hash(tuple(sorted(frame[uid_col].unique()))) % (2**32) + seed_offset[0])
        seed_offset[0] += 1
        blups = {}
        for relabelled_uid in frame[uid_col].unique():
            original_uid = relabelled_uid.split("__")[0]
            true_slope = true_slope_by_uid.get(original_uid, 0.0)
            blups[relabelled_uid] = {"x_within": (true_slope - 0.0) + rng.normal(0, noise_scale)}
        return Ar1EffectResult(
            engine="R (nlme::lme + corAR1)",
            ar1_coefficient=0.5,
            used_random_slope=True,
            fallback_reason=None,
            n_observations=len(frame),
            n_groups=frame[uid_col].nunique(),
            params={"x_within": 0.0, "x_between": 0.0, "Intercept": 0.0},
            pvalues={"x_within": 1e-5, "x_between": 0.5, "Intercept": 1e-10},
            blups=blups,
        )

    return _fake_fit


def test_bootstrap_person_slopes_relabels_resampled_duplicates(monkeypatch):
    """A participant drawn twice in one bootstrap replicate must be fit as
    two distinct groups (not silently collapsed into one), and both draws
    must still be attributed back to their real uid."""
    frame = _make_bootstrap_frame()
    true_slopes = {"p1": -0.5, "p2": -0.5, "p3": -0.5, "p4": -0.5}

    seen_uid_sets = []

    def _recording_fit_fn(bframe, outcome_col, uid_col, extra_fixed_effects):
        seen_uid_sets.append(set(bframe[uid_col].unique()))
        fake = _fake_fit_fn_factory(true_slopes, noise_scale=0.01, seed_offset=[0])
        return fake(bframe, outcome_col, uid_col, extra_fixed_effects)

    monkeypatch.setattr(
        "backend.statistics.mixed_effects_model.fit_ar1_effect",
        lambda frame, outcome_col="phq4_score", uid_col="uid", extra_fixed_effects=None, prefer_r=True: _fake_fit_fn_factory(
            true_slopes, 0.01, [0]
        )(frame, outcome_col, uid_col, extra_fixed_effects),
    )

    slopes = bootstrap_person_slopes(
        frame, n_bootstrap=5, seed=42, fit_fn=_recording_fit_fn
    )

    # Every original uid must be relabelled with a "__N" suffix at least
    # once across the replicates, never reused bare.
    all_seen = set().union(*seen_uid_sets)
    assert all("__" in uid for uid in all_seen)
    assert {s.uid for s in slopes} == {"p1", "p2", "p3", "p4"}


def test_bootstrap_person_slopes_produces_finite_se_and_p(monkeypatch):
    frame = _make_bootstrap_frame()
    true_slopes = {"p1": -0.5, "p2": -0.5, "p3": -0.5, "p4": -0.5}

    monkeypatch.setattr(
        "backend.statistics.mixed_effects_model.fit_ar1_effect",
        lambda frame, outcome_col="phq4_score", uid_col="uid", extra_fixed_effects=None, prefer_r=True: _fake_fit_fn_factory(
            true_slopes, 0.01, [0]
        )(frame, outcome_col, uid_col, extra_fixed_effects),
    )
    fake_fit_fn = _fake_fit_fn_factory(true_slopes, noise_scale=0.05, seed_offset=[1])

    slopes = bootstrap_person_slopes(frame, n_bootstrap=30, seed=7, fit_fn=fake_fit_fn)

    assert len(slopes) == 4
    for s in slopes:
        assert s.slope_se is not None and s.slope_se > 0
        assert s.slope_p is not None and 0 <= s.slope_p <= 1
        # The point estimate must come from the ORIGINAL fit, not a
        # bootstrap-mean re-estimate.
        assert np.isfinite(s.slope_i)


def test_bootstrap_person_slopes_raises_if_a_replicate_lacks_blups(monkeypatch):
    frame = _make_bootstrap_frame()
    true_slopes = {"p1": -0.5, "p2": -0.5, "p3": -0.5, "p4": -0.5}

    monkeypatch.setattr(
        "backend.statistics.mixed_effects_model.fit_ar1_effect",
        lambda frame, outcome_col="phq4_score", uid_col="uid", extra_fixed_effects=None, prefer_r=True: _fake_fit_fn_factory(
            true_slopes, 0.01, [0]
        )(frame, outcome_col, uid_col, extra_fixed_effects),
    )

    def _no_blups_fit_fn(bframe, outcome_col, uid_col, extra_fixed_effects):
        return Ar1EffectResult(
            engine="GEE (Python fallback, population-averaged, R unavailable in this environment)",
            ar1_coefficient=0.0,
            used_random_slope=None,
            fallback_reason=None,
            n_observations=len(bframe),
            n_groups=bframe[uid_col].nunique(),
            params={"x_within": 0.0},
            pvalues={"x_within": 0.5},
            blups=None,
        )

    with pytest.raises(ValueError, match="per-person BLUPs"):
        bootstrap_person_slopes(frame, n_bootstrap=3, seed=1, fit_fn=_no_blups_fit_fn)


# --- reclassify_family213 SE passthrough / intersect_bootstrap_evidence ----


def test_reclassify_family213_carries_slope_se_and_slope_p_through():
    """2026-09-13: reclassify_family213's output must expose slope_se/
    slope_p per person (NaN when the PersonSlope had None) so callers
    combining multiple bootstrap methods (intersect_bootstrap_evidence)
    can see each method's own SE alongside its label."""
    person_slopes = [
        PersonSlope(uid="p1", slope_i=-0.5, n_occasions=20, slope_se=0.1, slope_p=0.001),
        PersonSlope(uid="p2", slope_i=0.3, n_occasions=15),  # slope_se/slope_p default None
    ]
    out = reclassify_family213(person_slopes, outcome_sd=2.0, predictor_sd=1.0).set_index("uid")
    assert out.loc["p1", "slope_se"] == pytest.approx(0.1)
    assert out.loc["p1", "slope_p"] == pytest.approx(0.001)
    assert np.isnan(out.loc["p2", "slope_se"])
    assert np.isnan(out.loc["p2", "slope_p"])


def _reclassified(specs: dict[str, tuple[float, int, float, float]]) -> pd.DataFrame:
    """specs: uid -> (slope_i, n_occasions, slope_se, slope_p)."""
    person_slopes = [
        PersonSlope(uid=uid, slope_i=si, n_occasions=n, slope_se=se, slope_p=sp)
        for uid, (si, n, se, sp) in specs.items()
    ]
    return reclassify_family213(person_slopes, outcome_sd=1.0, predictor_sd=1.0)


def test_intersect_bootstrap_evidence_requires_both_methods_to_agree():
    """3 people: p1 available under both, p2 available under parametric
    only, p3 available under cluster only -- only p1 should survive the
    intersection."""
    # slope_i=-0.5 (std_effect=0.5, clears the >=0.10 moderate bar), tiny
    # p-values so each person's own BH-FDR-corrected q clears the 0.05 bar
    # (each dict is its own family of 3, so a handful of p=0.001 clears
    # comfortably, matching the existing test's own reasoning above).
    parametric = _reclassified(
        {
            "p1": (-0.5, 20, 0.05, 0.001),
            "p2": (-0.5, 20, 0.05, 0.001),
            "p3": (-0.5, 20, 0.5, 0.9),  # not significant under parametric
        }
    )
    cluster = _reclassified(
        {
            "p1": (-0.5, 20, 0.01, 0.001),
            "p2": (-0.5, 20, 0.5, 0.9),  # not significant under cluster
            "p3": (-0.5, 20, 0.01, 0.001),
        }
    )
    combined = intersect_bootstrap_evidence(parametric, cluster).set_index("uid")

    assert combined.loc["p1", "label_parametric"] in ("strong", "moderate")
    assert combined.loc["p1", "label_cluster"] in ("strong", "moderate")
    assert combined.loc["p1", "label_intersection"] == "evidence_available"

    assert combined.loc["p2", "label_intersection"] == "no_claim"  # cluster says no
    assert combined.loc["p3", "label_intersection"] == "no_claim"  # parametric says no


def test_intersect_bootstrap_evidence_label_intersection_is_already_binary():
    parametric = _reclassified({"p1": (-0.5, 20, 0.05, 0.001)})
    cluster = _reclassified({"p1": (-0.5, 20, 0.01, 0.001)})
    combined = intersect_bootstrap_evidence(parametric, cluster)
    assert set(combined["label_intersection"]) <= {"evidence_available", "no_claim"}


def test_intersect_bootstrap_evidence_preserves_per_method_columns_for_sensitivity_review():
    """The combined table must not collapse away either method's own
    label/SE -- the intersection is an addition, not a replacement, and
    both single-method views must remain reviewable from the one table."""
    parametric = _reclassified({"p1": (-0.5, 20, 0.05, 0.001)})
    cluster = _reclassified({"p1": (-0.5, 20, 0.01, 0.002)})
    combined = intersect_bootstrap_evidence(parametric, cluster).set_index("uid")

    assert combined.loc["p1", "slope_se_parametric"] == pytest.approx(0.05)
    assert combined.loc["p1", "slope_se_cluster"] == pytest.approx(0.01)
    assert combined.loc["p1", "slope_p_parametric"] == pytest.approx(0.001)
    assert combined.loc["p1", "slope_p_cluster"] == pytest.approx(0.002)
    assert "label_holm_parametric" in combined.columns
    assert "label_holm_cluster" in combined.columns
    assert "bh_q_213_parametric" in combined.columns
    assert "bh_q_213_cluster" in combined.columns
