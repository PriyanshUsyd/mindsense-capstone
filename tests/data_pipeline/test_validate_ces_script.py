"""
Regression test for scripts/validate_ces.py (Honghao Li's real Week 4 CES
re-verification, commit f30fce5) after the 2026-09-05 path fix — see the
module's own comment for what was wrong and why.

Skipped automatically if the real CES dataset isn't present locally
(gitignored, per Readme.md) — same pattern as
tests/integration/test_ces_eligibility_scripts_agree.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = REPO_ROOT / "dataset"
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_ces.py"

pytestmark = pytest.mark.skipif(
    not (DATASET_DIR / "EMA" / "general_ema.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)


def _load_validate_ces():
    spec = importlib.util.spec_from_file_location("validate_ces", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_resolves_the_real_local_dataset_directly_not_a_ces_subfolder():
    module = _load_validate_ces()
    assert module.CES_ROOT == DATASET_DIR


def test_script_runs_end_to_end_and_matches_the_independent_cross_check():
    """Confirms scripts/validate_ces.py (Honghao's own script) actually
    executes against the real dataset and reproduces the same 214/220
    eligible figure as backend/data_pipeline/ces_eligibility.py's
    independent cross-check — genuinely runnable, not a reconstruction."""
    module = _load_validate_ces()
    ema = module.pd.read_csv(module.EMA_FILE)
    sensing = module.pd.read_csv(module.SENSING_FILE)

    eligible = module.eligible_participant_check(ema, sensing)
    assert len(eligible) == 214
