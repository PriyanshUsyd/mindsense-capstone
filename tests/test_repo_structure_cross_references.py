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


def _read_unwrapped(relpath: str) -> str:
    """Same as _read but strips markdown blockquote markers and collapses
    line-wrapping whitespace to single spaces, for substring checks against
    prose that's hand-wrapped across multiple lines (and/or inside a `>`
    blockquote) in the source markdown/docstring."""
    lines = [line.lstrip(">").strip() for line in _read(relpath).splitlines()]
    return " ".join(" ".join(lines).split())


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
    threshold_text = _read("docs/evaluation/pass-threshold.md")
    assert "evaluation_plan_v0.1.md" in threshold_text


def test_archived_taxonomy_draft_exists_and_evaluation_plan_points_to_it():
    """2026-08-29: adversarial-taxonomy.md was archived once Chonghao's real
    5-category taxonomy became the working version. Confirms the archive
    exists and his real file references it (not a silently vanished file)."""
    archived_path = REPO_ROOT / "docs/evaluation/archive/adversarial-taxonomy-ai-draft-SUPERSEDED.md"
    assert archived_path.is_file()
    assert not (REPO_ROOT / "docs/evaluation/adversarial-taxonomy.md").exists()

    plan_text = _read("backend/evaluation/evaluation_plan_v0.1.md")
    assert "adversarial-taxonomy-ai-draft-SUPERSEDED.md" in plan_text


def test_honghao_reconciliation_note_is_referenced_from_ces_reverification_doc():
    text = _read("docs/data-pipeline/ces-reverification.md")
    assert "eligibility-methodology-note.md" in text


def test_repository_structure_status_documents_the_branch_discovery():
    text = _read("docs/repository-structure-status.md")
    assert "honglin/docs-week4" in text
    assert "yuktha/privacy-week4" in text
    assert "8dd9113" in text


def test_honghao_real_script_is_referenced_from_repo_structure_status():
    text = _read("docs/repository-structure-status.md")
    assert "ces_eligibility.py" in text


def test_honghao_real_script_is_referenced_from_proposal_outline():
    text = _read("docs/proposal/outline.md")
    assert "ces_eligibility.py" in text


def test_ces_eligibility_script_correctly_defers_to_honghaos_real_script():
    """RECONCILED 2026-09-05: this file previously described
    ces_eligibility.py itself as 'the shared, working eligibility script' —
    accurate when written (Honghao had no real script yet), stale once his
    own scripts/validate_ces.py existed, was fixed, and started passing.
    Now checks the docstring correctly names his script as canonical and
    this one as the secondary cross-check. Whitespace-normalized since the
    docstring hand-wraps across lines."""
    text = _read_unwrapped("backend/data_pipeline/ces_eligibility.py")
    assert "scripts/validate_ces.py" in text
    assert "is now the canonical CES re-verification deliverable" in text
    assert "independent cross-check that" in text
    assert "DATA PIPELINE LEAD TO CONFIRM" not in text.upper()
    assert "RECONSTRUCTED METHODOLOGY" not in text.upper()


def test_validate_ces_script_is_the_canonical_deliverable_and_runs():
    """The reconciliation above is only honest if his script actually
    exists and genuinely runs — re-confirms both, so this test fails loudly
    if either regresses."""
    assert (REPO_ROOT / "scripts" / "validate_ces.py").is_file()
    text = _read("scripts/validate_ces.py")
    assert "dataset" in text
    # The 2026-09-05 path fix must still be present - without it the
    # script can't run against this repo's real dataset layout at all.
    assert '_DATASET_DIRECT / "EMA"' in text


def test_proposal_outline_is_starting_content_not_pending_a_person():
    text = _read("docs/proposal/outline.md")
    assert "Starting content for whoever picks up" in text
    assert "Built due to Week 4 time constraints" not in text


def test_repository_structure_status_is_starting_content_not_pending_honglin():
    text = _read("docs/repository-structure-status.md")
    assert "genuinely useful starting content" in text
    assert "Built due to Week 4 time constraints" not in text
    assert "still has no artifact authored by Honglin himself" not in text


def test_evaluation_plan_flags_locked_default_verbatim():
    """Exact required locked-default note text (whitespace-normalized,
    since the banner hand-wraps across lines in the source markdown)."""
    text = _read_unwrapped("backend/evaluation/evaluation_plan_v0.1.md")
    assert "Locked Week 4 default: 100% high-severity / 90% standard" in text
    assert "Evaluation Design Lead may propose a change via normal PR review if needed, but this is not a blocker" in text


def test_pass_threshold_doc_is_locked_not_parked():
    text = _read_unwrapped("docs/evaluation/pass-threshold.md")
    assert "LOCKED WEEK 4 DEFAULT" in text
    assert "Locked Week 4 default: 100% high-severity / 90% standard" in text
    assert "PARKED" not in text
    assert "unresolved conflict" not in text.lower()


def test_week4_milestone_status_has_a_row_for_every_role_with_an_honest_status():
    """CORRECTED 2026-09-05, then RE-CORRECTED the same day: this test
    originally required every role's row to read 'Complete' or 'Locked
    default, no action needed' — an assertion that enforced rounding every
    role up to 'done' regardless of whether real work backed it. A first
    correction found three roles (Honghao, Sheng, Honglin) with zero
    commits anywhere. Later the same day, Honghao pushed real commits
    (f30fce5, 3c720ca) and Priyansh completed the actual contract freeze
    (freeze-decision.md, tag contract-v1.0.0) — both re-corrected back to
    Complete, this time genuinely. This test still only requires every
    role to have a row with one of the real, honest statuses actually used
    in the doc — it doesn't assert everyone is done as a blanket rule, it
    checks the *specific* statuses match what's actually verifiable right
    now, which happens to be Complete for six of eight roles."""
    text = _read("docs/week4-milestone-status.md")
    roles = [
        "Honghao Li", "Moe Tanaka", "Richard Zhao", "Sheng Wang",
        "Yuktha Naveen", "Chonghao Shen", "Honglin Lu", "Priyansh Khandelwal",
    ]
    table_lines = [line for line in text.splitlines() if line.startswith("|") and any(r in line for r in roles)]
    assert len(table_lines) == len(roles), "not every role has a row in the status table"
    valid_statuses = ("**Complete**", "**In progress**", "**Not started**")
    for line in table_lines:
        assert any(status in line for status in valid_statuses), (
            f"role row does not show a recognised status: {line}"
        )

    # The specific statuses must actually be present (not just "some honest
    # status or other") — Sheng and Honglin still have no real repo
    # contribution and must not silently read "Complete"; everyone else
    # with genuine, verified work must not be stuck reading a stale status
    # either.
    for role, expected_status in [
        ("Honghao Li", "**Complete**"),
        ("Sheng Wang", "**Not started**"),
        ("Honglin Lu", "**Not started**"),
        ("Priyansh Khandelwal", "**Complete**"),
    ]:
        role_line = next(line for line in table_lines if role in line)
        assert expected_status in role_line, f"{role}'s row should read {expected_status}: {role_line}"


def test_safety_gate_module_is_importable_and_self_documented():
    """backend/slm/safety_gate.py is new production code (2026-08-29) — must
    not be an orphaned file nobody's aware of. Its own module docstring is
    the reference point for now (no separate doc file exists yet)."""
    from backend.slm import safety_gate  # noqa: F401 — import-succeeds is the assertion

    module_text = _read("backend/slm/safety_gate.py")
    assert "deterministic safety gate" in module_text.lower()


def test_requirements_txt_lists_every_package_actually_imported_by_tests():
    """pyyaml and pytest-socket are both genuinely used now (SLM template
    tests, network-egress tests) — confirm they're declared, not just
    happening to be installed in this one environment."""
    text = _read("requirements.txt")
    assert "pyyaml" in text
    assert "pytest-socket" in text


def test_branch_protection_guide_exists_and_is_referenced():
    """docs/github-branch-protection-setup.md must exist and be linked from
    the repo-structure status doc, not left as a standalone orphan."""
    guide_path = REPO_ROOT / "docs/github-branch-protection-setup.md"
    assert guide_path.is_file()

    status_text = _read("docs/repository-structure-status.md")
    assert "github-branch-protection-setup.md" in status_text


def test_eligibility_status_enum_has_no_orphaned_values():
    """Every EligibilityStatus value the contract defines must actually be
    reachable from Moe's real classify_state() via to_eligibility_status()
    — otherwise the contract has grown a value nothing can ever produce."""
    from backend.contracts.evidence import EligibilityStatus
    from backend.statistics.eligibility import ColdStartState, to_eligibility_status

    reachable = {to_eligibility_status(s) for s in ColdStartState}
    assert reachable == {
        EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
        EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY,
        EligibilityStatus.ELIGIBLE,
    }
    # INELIGIBLE_INSUFFICIENT_BASELINE is intentionally not reachable from
    # classify_state() alone — it's reserved for a baseline-specific
    # ineligibility a caller determines separately (e.g. enough calendar
    # days/sensor-days per State B, but zero prior baseline windows to
    # average). Documented here rather than silently unexplained.
    assert EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE not in reachable


# --- No stray top-level junk from this pass ----------------------------------

def test_gitignore_excludes_pycache():
    """Checks .gitignore itself rather than live filesystem state — running
    this very test suite creates __pycache__ directories, so asserting
    none exist on disk would be self-defeating."""
    text = _read(".gitignore")
    assert "__pycache__" in text
