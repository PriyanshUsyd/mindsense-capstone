"""MINDSENSE_DATASET_DIR: the one dataset setting (backend/dataset_config.py).

Covers the setting itself, that every app reader follows it, that real and
synthetic bootstrap caches can never be read for each other, that /health and
/models report the dataset, and the synthetic generator's guarantees.
No real CES file is read here.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import dataset_config
from backend.api.app import create_app
from backend.statistics import bootstrap_cache as bc
from backend.statistics import participant_evidence as pe
from backend.statistics import tier1_runner
from scripts import make_synthetic_dataset as synth
from tests.statistics import test_bootstrap_cache as cache_tests

ENV_NAME = dataset_config.DATASET_DIR_ENV
# Reuse the cache tests' toy repo, frame and read/write helpers.
fake_repo = cache_tests.fake_repo
_keys, _load, _write_cache = cache_tests._keys, cache_tests._load, cache_tests._write_cache


@pytest.fixture
def synthetic_dir(tmp_path: Path, monkeypatch) -> Path:
    """A generated synthetic dataset in a temp folder, selected via the env var."""
    # Not "dataset_synthetic": its cache root would be the local demo cache.
    out = tmp_path / "synthetic_under_test"
    synth.main(["--out", str(out)])
    monkeypatch.setenv(ENV_NAME, str(out))
    # participant_evidence caches loaded frames per process; start empty.
    monkeypatch.setattr(pe, "_CLEANED_SENSING_CACHE", {})
    monkeypatch.setattr(pe, "_EMA_CACHE", None)
    monkeypatch.setattr(pe, "_EVIDENCE_TABLE_CACHE", {})
    return out


# --- the setting ---------------------------------------------------------------


@pytest.mark.parametrize("value", [None, "", "   "])
def test_unset_or_blank_means_the_real_dataset(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(ENV_NAME, raising=False)
    else:
        monkeypatch.setenv(ENV_NAME, value)
    assert dataset_config.dataset_dir() == dataset_config.DEFAULT_DATASET_DIR
    assert dataset_config.dataset_kind() == "real"
    assert dataset_config.bootstrap_cache_root() == bc.CACHE_ROOT
    assert dataset_config.fingerprint_label() is None


def test_explicit_default_path_is_still_real(monkeypatch):
    monkeypatch.setenv(ENV_NAME, "dataset")
    assert dataset_config.dataset_kind() == "real"


def test_relative_path_resolves_against_the_repo_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(ENV_NAME, "dataset_synthetic")
    assert dataset_config.dataset_dir() == (dataset_config.REPO_ROOT / "dataset_synthetic").resolve()
    assert dataset_config.dataset_kind() == "synthetic"


def test_synthetic_cache_root_is_separate_from_the_real_one(monkeypatch):
    monkeypatch.setenv(ENV_NAME, "dataset_synthetic")
    root = dataset_config.bootstrap_cache_root()
    assert root != bc.CACHE_ROOT
    assert bc.CACHE_ROOT not in root.parents
    assert root.name == "dataset_synthetic"
    assert dataset_config.fingerprint_label() == "synthetic:dataset_synthetic"
    # cache_dir with no explicit root follows the selected dataset
    assert bc.cache_dir("loc_dist_ep_0") == root / "loc_dist_ep_0"


# --- cache separation ------------------------------------------------------------


def test_real_fingerprint_has_no_dataset_key(monkeypatch, fake_repo):
    monkeypatch.delenv(ENV_NAME, raising=False)
    assert "config.dataset" not in _keys(fake_repo)


def test_synthetic_fingerprint_names_the_dataset(monkeypatch, fake_repo):
    monkeypatch.delenv(ENV_NAME, raising=False)
    real = _keys(fake_repo)
    monkeypatch.setenv(ENV_NAME, "dataset_synthetic")
    synthetic = _keys(fake_repo)
    assert synthetic["config.dataset"] == "synthetic:dataset_synthetic"
    assert bc.fingerprint_hash(real) != bc.fingerprint_hash(synthetic)


def test_a_cache_built_on_one_dataset_is_stale_for_the_other(monkeypatch, fake_repo, tmp_path):
    """Even pointed at the same root with an identical model frame."""
    root = tmp_path / "cache"
    monkeypatch.delenv(ENV_NAME, raising=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # family-size warning on the toy cohort
        _write_cache(fake_repo, root)
    assert _load(fake_repo, root) is not None

    monkeypatch.setenv(ENV_NAME, "dataset_synthetic")
    with pytest.raises(bc.BootstrapCacheStale) as excinfo:
        _load(fake_repo, root)
    assert any("config.dataset" in line for line in excinfo.value.changed)


def test_synthetic_cache_does_not_validate_as_real(monkeypatch, fake_repo, tmp_path):
    root = tmp_path / "cache"
    monkeypatch.setenv(ENV_NAME, "dataset_synthetic")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _write_cache(fake_repo, root)
    monkeypatch.delenv(ENV_NAME, raising=False)
    with pytest.raises(bc.BootstrapCacheStale):
        _load(fake_repo, root)


# --- every reader follows the setting --------------------------------------------


def test_app_readers_follow_the_setting(synthetic_dir):
    sensing, ema = tier1_runner.load_sensing_and_ema()
    assert sensing["uid"].str.startswith("SYN-").all()
    assert ema["uid"].str.startswith("SYN-").all()

    for feature in ("gps_distance", "unlock_count"):
        assert pe._cleaned_sensing(feature)["uid"].str.startswith("SYN-").all()
    assert pe._ema()["uid"].str.startswith("SYN-").all()


def test_demo_selection_picks_the_generated_demo_participant(synthetic_dir):
    _sensing, _ema, _demo, demo_uid = synth.generate()
    assert pe.select_local_demo_participant("gps_distance") == demo_uid
    assert pe.select_local_demo_participant("unlock_count") == demo_uid


def test_synthetic_dataset_never_reads_the_real_cache(synthetic_dir):
    """No synthetic cache exists in the temp dataset's own root, so evidence is
    unavailable (no_claim) rather than borrowed from the real cache."""
    demo = pe.select_local_demo_participant("gps_distance")
    packet = pe.build_evidence_packet(demo, feature_id="gps_distance")
    assert packet.evidence is None
    assert "per-person evidence unavailable: no bootstrap cache" in packet.uncertainty.item_level


# --- /health and /models ---------------------------------------------------------


@pytest.mark.parametrize("value,kind", [(None, "real"), ("dataset_synthetic", "synthetic")])
def test_health_and_models_report_the_dataset(monkeypatch, value, kind):
    if value is None:
        monkeypatch.delenv(ENV_NAME, raising=False)
    else:
        monkeypatch.setenv(ENV_NAME, value)
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok", "dataset": kind}
    assert client.get("/models").json()["dataset"] == kind


# --- the generator ---------------------------------------------------------------


def test_generator_layout_and_dates(synthetic_dir):
    sensing = pd.read_csv(synthetic_dir / "Sensing" / "sensing.csv")
    ema = pd.read_csv(synthetic_dir / "EMA" / "general_ema.csv")
    demographics = pd.read_csv(synthetic_dir / "Demographics" / "demographics.csv")

    assert list(sensing.columns) == ["uid", "day", "quality_loc", "loc_dist_ep_0", "unlock_num_ep_0", "is_ios"]
    assert list(ema.columns) == ["uid", "day", "phq4_score"]
    assert list(demographics.columns) == ["uid"]
    assert sorted(demographics["uid"]) == [f"SYN-{i:03d}" for i in range(1, 201)]
    assert sensing["day"].dtype == "int64" and ema["day"].dtype == "int64"
    days = set(sensing["day"])
    assert max(days) == 20261019
    assert {20261014, 20261015} <= days
    assert 20271215 not in days
    assert set(sensing["is_ios"]) == {0, 1}
    assert ema["phq4_score"].dropna().between(0, 12).all()


def test_generator_is_deterministic():
    a = synth.generate()
    b = synth.generate()
    pd.testing.assert_frame_equal(a[0], b[0])
    pd.testing.assert_frame_equal(a[1], b[1])
    assert a[3] == b[3]


def test_generator_refuses_the_real_dataset_folder():
    with pytest.raises(SystemExit):
        synth.main(["--out", str(dataset_config.DEFAULT_DATASET_DIR)])
