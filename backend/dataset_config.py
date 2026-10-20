"""
The one dataset setting: `MINDSENSE_DATASET_DIR`.

Default (unset or empty): the real CES copy at `dataset/` (gitignored, never
distributed). Any other directory is reported as `synthetic` — today the only
non-default dataset is the client-approved synthetic one written by
`scripts/make_synthetic_dataset.py` to `data/synthetic/` (committed; generated
values only, no real CES rows).
A relative value is resolved against the repository root, not the current
working directory, so the backend reads the same files wherever it is started.

Every CES reader that serves the app (`participant_evidence` — evidence
builder and local-demo selection — and `tier1_runner.load_sensing_and_ema`,
which the bootstrap cache CLI uses) reads `dataset_dir()` at call time.

Caches never mix: the default dataset keeps the existing cache root and
fingerprint unchanged, so the real cache stays valid. A non-default dataset
gets its own cache root (`bootstrap_cache_root()`) and an extra
`config.dataset` fingerprint key (`fingerprint_label()`).
"""

from __future__ import annotations

import os
from pathlib import Path

DATASET_DIR_ENV = "MINDSENSE_DATASET_DIR"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = REPO_ROOT / "dataset"
DEFAULT_CACHE_ROOT = REPO_ROOT / "outputs" / "bootstrap_cache"
# Non-default datasets: `<this>/<dataset folder name>/`, a sibling of the
# real cache root, never inside it.
DATASET_CACHE_PARENT = REPO_ROOT / "outputs" / "bootstrap_cache_datasets"

REAL = "real"
SYNTHETIC = "synthetic"


def dataset_dir() -> Path:
    """The dataset directory selected by `MINDSENSE_DATASET_DIR`."""
    raw = os.environ.get(DATASET_DIR_ENV, "").strip()
    if not raw:
        return DEFAULT_DATASET_DIR
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def is_default_dataset() -> bool:
    return dataset_dir() == DEFAULT_DATASET_DIR.resolve()


def dataset_kind() -> str:
    """`real` for the default dataset, `synthetic` for any other."""
    return REAL if is_default_dataset() else SYNTHETIC


def bootstrap_cache_root() -> Path:
    """The real dataset keeps `outputs/bootstrap_cache/`; any other dataset
    has its own folder, so the two caches can never be read for each other."""
    if is_default_dataset():
        return DEFAULT_CACHE_ROOT
    return DATASET_CACHE_PARENT / dataset_dir().name


def fingerprint_label() -> str | None:
    """`None` for the real dataset (its fingerprint is unchanged, so the
    existing real cache stays valid); `synthetic:<folder name>` otherwise.
    Only the folder name is recorded, never a local path."""
    if is_default_dataset():
        return None
    return f"{SYNTHETIC}:{dataset_dir().name}"
