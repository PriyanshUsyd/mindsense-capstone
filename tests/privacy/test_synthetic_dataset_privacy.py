"""Privacy gates for the committed synthetic demo dataset (data/synthetic/).

Only the generated folder may be shared. The real CES copy at dataset/ must
stay ignored and untracked, the synthetic folder must hold only the expected
generated files with SYN- identifiers, and its contents must be exactly what
the seeded generator produces.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_DIR = REPO_ROOT / "data" / "synthetic"
EXPECTED_FILES = {
    "README.md",
    "Sensing/sensing.csv",
    "EMA/general_ema.csv",
    "Demographics/demographics.csv",
}
CSV_FILES = sorted(f for f in EXPECTED_FILES if f.endswith(".csv"))
SYNTHETIC_UID = re.compile(r"^SYN-\d{3}$")
RAW_CES_UID_IN_TEXT = re.compile(r"(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])")
# Real CES layout, including files that are not present on CI machines.
REAL_DATASET_PATHS = [
    "dataset/Sensing/sensing.csv",
    "dataset/EMA/general_ema.csv",
    "dataset/Demographics/demographics.csv",
    "dataset/Raw Sensing/example.csv",
    "dataset/any_new_file.parquet",
]


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize("path", REAL_DATASET_PATHS)
def test_real_ces_files_are_ignored(path):
    # --no-index: judge the path by the ignore rules alone, even if absent.
    result = _git("check-ignore", "--no-index", "-q", path)
    assert result.returncode == 0, f"{path} is not ignored; real CES data could be committed"


def test_no_real_ces_file_is_tracked():
    result = _git("ls-files", "--", "dataset")
    assert result.returncode == 0
    assert result.stdout.strip() == "", "files under dataset/ are tracked"


@pytest.mark.parametrize("path", sorted(EXPECTED_FILES))
def test_synthetic_files_are_shareable(path):
    result = _git("check-ignore", "--no-index", "-q", f"data/synthetic/{path}")
    assert result.returncode == 1, f"data/synthetic/{path} is ignored"


def test_synthetic_folder_holds_only_the_expected_files():
    present = {
        p.relative_to(SYNTHETIC_DIR).as_posix()
        for p in SYNTHETIC_DIR.rglob("*")
        if p.is_file()
    }
    assert present == EXPECTED_FILES


@pytest.mark.parametrize("name", CSV_FILES)
def test_synthetic_files_use_only_synthetic_identifiers(name):
    path = SYNTHETIC_DIR / name
    frame = pd.read_csv(path, dtype={"uid": str})
    assert frame["uid"].map(lambda uid: bool(SYNTHETIC_UID.fullmatch(uid))).all()
    assert not RAW_CES_UID_IN_TEXT.search(path.read_text(encoding="utf-8"))


def _generator():
    spec = importlib.util.spec_from_file_location(
        "make_synthetic_dataset", REPO_ROOT / "scripts" / "make_synthetic_dataset.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up
    spec.loader.exec_module(module)
    return module


def test_committed_files_are_exactly_the_generator_output(tmp_path):
    """Every row is generated: regenerating with the fixed seed reproduces the
    committed files value for value (line endings aside)."""
    generator = _generator()
    generator.main(["--out", str(tmp_path)])
    for name in CSV_FILES:
        committed = pd.read_csv(SYNTHETIC_DIR / name)
        regenerated = pd.read_csv(tmp_path / name)
        pd.testing.assert_frame_equal(committed, regenerated, check_exact=True)


def test_generator_refuses_to_write_into_the_real_dataset_folder():
    generator = _generator()
    with pytest.raises(SystemExit):
        generator.main(["--out", str(REPO_ROOT / "dataset")])
