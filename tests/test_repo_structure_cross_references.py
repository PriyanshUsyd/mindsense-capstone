"""
Cross-cutting checks, added 2026-08-29: confirm build-reference.md's
Section 8 repo-structure listing is actually reflected on disk, and that
the major artifacts built during the Week 4 gap-fill pass are referenced
from somewhere a reader would actually find them (not orphaned files
nobody links to).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8")


# --- build-reference.md Section 8 folders actually exist ---------------------

EXPECTED_DIRS = [
    "docs",
    "backend/contracts",
    "backend/data_pipeline",
    "backend/statistics",
    "backend/slm/prompts",
    "backend/privacy",
    "backend/evaluation",
    "backend/api",
    "frontend/src/api",
    "frontend/src/components",
    "frontend/src/features/chat",
    "tests",
    "dataset",
]


def test_every_build_reference_folder_exists():
    missing = [d for d in EXPECTED_DIRS if not (REPO_ROOT / d).is_dir()]
    assert not missing, f"folders missing vs build-reference.md Section 8: {missing}"


def test_backend_db_py_not_yet_required_but_no_other_file_imports_sqlite3():
    """build-reference.md: 'db.py — The ONLY file that imports sqlite3.'
    db.py doesn't exist yet (no code needs it yet), but nothing else in
    backend/ should be importing sqlite3 directly in the meantime."""
    offenders = []
    for path in (REPO_ROOT / "backend").rglob("*.py"):
        if path.name == "db.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "import sqlite3" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"files importing sqlite3 outside db.py: {offenders}"


# --- Key Week 4 artifacts are referenced from Weekly_Plan.md's own area or docs/ ---

def test_evidence_contract_referenced_from_build_reference():
    text = _read("build-reference.md")
    assert "evidence contract" in text.lower() or "Section 5" in text


def test_moe_real_deliverable_is_referenced_from_the_docs_that_supersede_it():
    """The AI-drafted statistics doc must point at Moe's real file, not
    leave it as a disconnected, hard-to-find artifact."""
    text = _read("docs/statistics/model-and-coldstart-spec.md")
    assert "weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md" in text


def test_yuktha_real_privacy_work_is_referenced_from_docs_privacy_readme():
    text = _read("docs/privacy/README.md")
    assert "privacy/privacy_architecture_principles.md" in text
    assert "benchmarks/slm_latency_benchmark.py" in text


def test_chonghao_real_evaluation_plan_is_referenced_from_the_flagged_conflict_notes():
    taxonomy_text = _read("docs/evaluation/adversarial-taxonomy.md")
    threshold_text = _read("docs/evaluation/pass-threshold.md")
    assert "evaluation_plan_v0.1.md" in taxonomy_text
    assert "evaluation_plan_v0.1.md" in threshold_text


def test_honghao_reconciliation_note_is_referenced_from_ces_reverification_doc():
    text = _read("docs/data-pipeline/ces-reverification.md")
    assert "eligibility-methodology-note.md" in text


def test_repository_structure_status_documents_the_branch_discovery():
    text = _read("docs/repository-structure-status.md")
    assert "honglin/docs-week4" in text
    assert "yuktha/privacy-week4" in text
    assert "8dd9113" in text


# --- No stray top-level junk from this pass ----------------------------------

def test_gitignore_excludes_pycache():
    """Checks .gitignore itself rather than live filesystem state — running
    this very test suite creates __pycache__ directories, so asserting
    none exist on disk would be self-defeating."""
    text = _read(".gitignore")
    assert "__pycache__" in text
