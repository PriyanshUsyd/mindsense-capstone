"""
Integration check, added 2026-08-29: Priyansh's independent cross-check
script (verify_ces.py) and Honghao's reconstructed real script
(ces_eligibility.py) were built independently, at different times, using
different code paths. They must agree on the official eligible-participant
count and percentage — if they don't, something about the reconciliation
in docs/data-pipeline/eligibility-methodology-note.md is wrong.

Skipped automatically if the real CES dataset isn't present locally
(it's gitignored, per Readme.md).
"""

from pathlib import Path

import pytest

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"

pytestmark = pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot cross-check against it",
)


def test_both_scripts_report_the_same_eligible_count():
    from backend.data_pipeline import ces_eligibility, verify_ces

    honghao_result = ces_eligibility.summarize(
        ces_eligibility.compute_eligibility(*ces_eligibility.load_eligibility_inputs())
    )
    priyansh_result = verify_ces.verify()

    assert honghao_result["n_eligible_participants"] == priyansh_result["n_eligible_participants_gated_check"]
    assert honghao_result["eligible_pct"] == priyansh_result["eligible_pct_gated_check"]


def test_official_figure_is_97_point_3_percent():
    from backend.data_pipeline import ces_eligibility

    result = ces_eligibility.summarize(
        ces_eligibility.compute_eligibility(*ces_eligibility.load_eligibility_inputs())
    )
    assert result["eligible_pct"] == 97.3


def test_both_scripts_agree_on_total_participant_count():
    from backend.data_pipeline import ces_eligibility, verify_ces

    honghao_result = ces_eligibility.summarize(
        ces_eligibility.compute_eligibility(*ces_eligibility.load_eligibility_inputs())
    )
    priyansh_result = verify_ces.verify()

    assert honghao_result["n_total_participants"] == priyansh_result["n_sensing_participants"]


def test_ces_eligibility_threshold_matches_moes_real_locked_spec():
    """Genuine cross-role integration point: Honghao's reconstructed script
    hardcodes MIN_VALID_SENSOR_DAYS=20 as a module constant, independently
    of Moe's real backend/statistics/eligibility.py, which defines the same
    number as STATE_C_MIN_VALID_SENSOR_DAYS. If these ever drift apart,
    Honghao's 97.3% figure silently stops meaning "eligible per Moe's real
    spec" and becomes an arbitrary, disconnected threshold again."""
    from backend.data_pipeline.ces_eligibility import MIN_VALID_SENSOR_DAYS
    from backend.statistics.eligibility import STATE_C_MIN_VALID_SENSOR_DAYS

    assert MIN_VALID_SENSOR_DAYS == STATE_C_MIN_VALID_SENSOR_DAYS


def test_ces_eligibility_uses_the_same_locked_feature_columns_as_the_data_pipeline_skill():
    """Cross-check against skills/data-pipeline-ces.md's named columns
    (loc_dist_ep_0, unlock_num_ep_0) rather than assuming they still match."""
    from backend.data_pipeline.ces_eligibility import GPS_COL, UNLOCK_COL

    skill_text = (Path(__file__).resolve().parents[2] / "skills" / "data-pipeline-ces.md").read_text(encoding="utf-8")
    assert GPS_COL in skill_text
    assert UNLOCK_COL in skill_text
