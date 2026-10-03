"""Tests for both registered Tier 1 features in the current runner."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import backend.statistics.tier1_runner as runner
from backend.statistics.feature_specs import TIER1_FEATURE_SPECS, FeatureSpec
from backend.statistics.tier1_runner import load_sensing_and_ema, run_one_feature

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


def test_both_features_registered():
    assert set(TIER1_FEATURE_SPECS) == {"loc_dist_ep_0", "unlock_num_ep_0"}


@pytest.mark.parametrize("feature_name", ["loc_dist_ep_0", "unlock_num_ep_0"])
def test_registered_feature_runs_through_orchestration_with_synthetic_data(
    monkeypatch: pytest.MonkeyPatch, feature_name: str
):
    """Exercise current runner wiring in CI without private CES data."""
    registered_spec = TIER1_FEATURE_SPECS[feature_name]
    sensing = pd.DataFrame({"uid": ["p1", "p2"], "day": [1, 1]})
    ema = pd.DataFrame(
        {"uid": ["p1", "p2"], "day": [1, 1], "phq4_score": [2.0, 3.0]}
    )
    calls: dict[str, object] = {}

    def clean_fn(frame: pd.DataFrame) -> pd.DataFrame:
        calls["clean_input"] = frame
        return frame.assign(**{registered_spec.value_col: [1.0, 2.0]})

    spec = FeatureSpec(
        name=registered_spec.name,
        transform=registered_spec.transform,
        transform_name=registered_spec.transform_name,
        clean_fn=clean_fn,
    )

    def build_frame(
        cleaned: pd.DataFrame,
        ema_frame: pd.DataFrame,
        frame_spec: FeatureSpec,
    ) -> pd.DataFrame:
        calls["cleaned"] = cleaned
        calls["ema"] = ema_frame
        calls["spec"] = frame_spec
        return pd.DataFrame(
            {
                "uid": ["p1", "p2"],
                "phq4_score": [2.0, 3.0],
                "x_within": [-0.2, 0.2],
            }
        )

    monkeypatch.setattr(runner, "build_model_frame", build_frame)
    monkeypatch.setattr(
        runner,
        "fit_mixed_effects_model",
        lambda frame, *, prefer_r: SimpleNamespace(
            engine="synthetic",
            converged=True,
            used_random_slope=False,
            fallback_reason=None,
            params={"x_within": 0.1},
            se={"x_within": 0.05},
            pvalues={"x_within": 0.5},
            denom_df_method="synthetic",
            denom_df={"x_within": 10.0},
        ),
    )
    monkeypatch.setattr(
        runner,
        "fit_ar1_effect",
        lambda frame, *, prefer_r: SimpleNamespace(
            engine="synthetic-no-blups",
            ar1_coefficient=0.0,
            params={"x_within": 0.1},
            pvalues={"x_within": 0.5},
            fallback_reason="synthetic CI path",
            blups=None,
        ),
    )

    result = run_one_feature(spec, sensing, ema, prefer_r=False)

    assert calls["clean_input"] is sensing
    assert calls["ema"] is ema
    assert calls["spec"] is spec
    assert result.feature == feature_name
    assert result.transform_name == registered_spec.transform_name
    assert result.n_occasions == 2
    assert result.n_participants == 2
    assert result.primary_fit["converged"] is True
    assert result.evidence_summary["skipped_reason"].startswith(
        "ar1_result has no BLUPs"
    )


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) - cannot run end-to-end",
)
def test_unlock_frequency_runs_end_to_end_against_the_real_dataset():
    sensing, ema = load_sensing_and_ema()

    result = run_one_feature(TIER1_FEATURE_SPECS["unlock_num_ep_0"], sensing, ema)

    assert result.n_occasions > 1000
    assert result.n_participants > 100
    assert result.primary_fit["converged"]
    assert result.primary_fit["x_within_beta"] is not None


@pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) - cannot run end-to-end",
)
def test_gps_distance_still_runs_end_to_end_with_registered_transform():
    sensing, ema = load_sensing_and_ema()

    result = run_one_feature(TIER1_FEATURE_SPECS["loc_dist_ep_0"], sensing, ema)

    assert result.n_occasions > 1000
    assert result.primary_fit["converged"]
    assert result.primary_fit["x_within_beta"] < 0
