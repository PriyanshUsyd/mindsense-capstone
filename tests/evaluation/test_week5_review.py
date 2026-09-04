import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "benchmarks/fixtures/week5_evaluation_alignment.json"
REVIEW = REPO_ROOT / "docs/evaluation/week5-development-review.md"


def test_public_mapping_records_evaluation_lead_approval():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["status"] == "approved_public_development_mapping_v1"
    assert manifest["evaluation_review"] == {
        "reviewer": "Chonghao Shen",
        "review_date": "2026-09-04",
        "record": "docs/evaluation/week5-development-review.md",
    }
    assert len(manifest["cases"]) == 8


def test_review_reports_executed_and_uncovered_cases_separately():
    text = " ".join(REVIEW.read_text(encoding="utf-8").split())

    assert "6/6 Pass" in text
    assert "14/14 Pass" in text
    assert "2/2 Pass" in text
    assert "Q2 and Q8 remain not covered" in text
    assert "do not establish" in text


def test_review_does_not_claim_joint_acceptance_or_held_out_performance():
    text = " ".join(REVIEW.read_text(encoding="utf-8").lower().split())

    assert "independent review" in text
    assert "does not approve a final model" in text
    assert "held-out performance" in text
