"""
Tests for backend/statistics/run_tier1_evidence.py — confirms both
signed-off Tier-1 features (GPS distance, unlock frequency) actually run
through the full baseline/evidence pipeline, not just GPS alone.

FLAGGED FOR MOE TANAKA'S REVIEW, same as the unlock cleaning module and
the runner script itself: this is the first time unlock frequency has
been run through this pipeline, and its cleaning/transform choices are a
port, not a locked spec.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import backend.statistics.run_tier1_evidence as runner
from backend.statistics.run_tier1_evidence import (
    FEATURES,
    load_sensing_and_ema,
    run_one_feature,
)

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


def test_both_features_registered():
    assert set(FEATURES) == {"gps_distance", "unlock_frequency"}


@pytest.mark.parametrize("feature_name", ["gps_distance", "unlock_frequency"])
def test_registered_feature_runs_through_orchestration_with_synthetic_data(
    monkeypatch: pytest.MonkeyPatch, feature_name: str
):
    """Exercise runner wiring in CI without requiring private CES data."""
    spec = FEATURES[feature_name]
    sensing = pd.DataFrame({"uid": ["p1", "p2"], "day": [1, 1]})
    ema = pd.DataFrame({"uid": ["p1", "p2"], "day": [1, 1], "phq4_score": [2.0, 3.0]})
    calls: dict[str, object] = {}

    def clean_fn(frame: pd.DataFrame) -> pd.DataFrame:
        calls["clean_input"] = frame
        return frame.assign(**{spec["clean_col"]: [1.0, 2.0]})

    def build_frame(
        cleaned: pd.DataFrame,
        ema_frame: pd.DataFrame,
        *,
        value_col: str,
        log_offset: float,
    ) -> pd.DataFrame:
        calls["cleaned"] = cleaned
        calls["ema"] = ema_frame
        calls["value_col"] = value_col
        calls["log_offset"] = log_offset
        return pd.DataFrame(
            {
                "uid": ["p1", "p2"],
                "phq4_score": [2.0, 3.0],
                "x_within": [-0.2, 0.2],
            }
        )

    monkeypatch.setitem(spec, "clean_fn", clean_fn)
    monkeypatch.setattr(runner, "build_model_frame", build_frame)
    monkeypatch.setattr(
        runner,
        "fit_mixed_effects_model",
        lambda frame: SimpleNamespace(
            engine="synthetic",
            converged=True,
            used_random_slope=False,
            params={"x_within": 0.1},
            pvalues={"x_within": 0.5},
            denom_df_method="synthetic",
        ),
    )
    monkeypatch.setattr(
        runner,
        "fit_ar1_effect",
        lambda frame: SimpleNamespace(
            engine="synthetic-no-blups",
            ar1_coefficient=0.0,
            params={"x_within": 0.1},
            fallback_reason="synthetic CI path",
            blups=None,
        ),
    )

    result = run_one_feature(feature_name, sensing, ema)

    assert calls["clean_input"] is sensing
    assert calls["ema"] is ema
    assert calls["value_col"] == spec["clean_col"]
    assert calls["log_offset"] == spec["log_offset"]
    assert result["feature"] == feature_name
    assert result["n_occasions"] == 2
    assert result["n_participants"] == 2
    assert result["primary_fit"]["converged"] is True
    assert result["evidence"]["skipped_reason"].startswith(
        "ar1_result has no BLUPs"
    )


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_unlock_frequency_runs_end_to_end_against_the_real_dataset():
    """Real dataset, real cleaning, real model fit for the SECOND Tier-1
    feature -- this is the actual "extend to both features" check, not a
    synthetic-fixture stand-in."""
    sensing, ema = load_sensing_and_ema()

    result = run_one_feature("unlock_frequency", sensing, ema)

    assert result["n_occasions"] > 1000
    assert result["n_participants"] > 100
    assert result["primary_fit"]["converged"]
    assert result["primary_fit"]["x_within_beta"] is not None
    # This is a real fit result, not a hardcoded expectation on direction/
    # significance -- unlock frequency's association with PHQ-4 is an open
    # empirical question this run answers, not something to assert a
    # particular sign for.


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)
def test_gps_distance_still_runs_end_to_end_after_the_log_offset_fix():
    """Regression check: build_model_frame's new log_offset parameter
    must not have changed GPS's own behaviour (it defaults to
    GPS_LOG_OFFSET_M, same as before the parameter existed)."""
    sensing, ema = load_sensing_and_ema()

    result = run_one_feature("gps_distance", sensing, ema)

    assert result["n_occasions"] > 1000
    assert result["primary_fit"]["converged"]
    # Sign/magnitude sanity check against the previously-reported real
    # result (beta1 ~ -0.24 to -0.28 across engines) -- not an exact
    # pin, since the Python-fallback engine differs slightly run to run.
    assert result["primary_fit"]["x_within_beta"] < 0
