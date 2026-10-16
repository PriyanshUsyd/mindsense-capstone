"""Explicit-path provenance, immutable evidence and Qwen execution checks."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from benchmarks import slm_dual_model_review as companion

# The Week 9 Qwen companion (benchmarks/slm_dual_model_review.py) is pinned to
# the rc-eval-1 sources by hash. Its three replay tests (end-to-end run,
# offline failures, LF/CRLF baseline) were removed on 2026-10-16: they could
# only run on a checkout of tag rc-eval-1, so on any later tree they were
# permanently skipped, and re-pinning would rewrite the frozen Week 9 evidence
# baseline. Replay them on `git checkout rc-eval-1`. Source-drift refusal and
# baseline-edit rejection are still tested below.


def test_provenance_git_status_is_always_path_scoped(monkeypatch):
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(companion.subprocess, "run", run)
    metadata = companion.provenance()
    status = next(c for c in commands if "status" in c)
    assert status[status.index("--") + 1 :] == list(companion.SOURCE_FILES)
    assert metadata["working_tree_dirty"] is None


def test_unlisted_path_rejected_before_filesystem_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected filesystem access")

    monkeypatch.setattr(companion.Path, "is_symlink", forbidden)
    with pytest.raises(ValueError, match="allow-list"):
        companion.allowed_path("not-an-allowed-source.json")


def test_source_drift_rejected_before_any_generation():
    protocol = json.loads(companion.allowed_path(companion.PROTOCOL).read_text())
    hashes = companion.source_fingerprints()
    hashes["raw"]["backend/slm/service.py"] = "drift"
    hashes["lf"]["backend/slm/service.py"] = "drift"
    with pytest.raises(ValueError, match="source drift"):
        companion.validate_baseline(protocol, hashes)


def test_existing_output_is_never_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(companion, "ROOT", tmp_path)
    history = tmp_path / "benchmarks/history"
    history.mkdir(parents=True)
    output = history / "existing.json"
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit):
        companion.main(["--out", str(output)])
    assert output.read_text(encoding="utf-8") == "keep"


def test_baseline_record_edit_is_rejected(monkeypatch):
    protocol = json.loads(companion.allowed_path(companion.PROTOCOL).read_text())
    hashes = companion.source_fingerprints()
    target = companion.allowed_path(companion.BASELINE)
    altered = target.read_bytes().replace(b"phi4-mini:3.8b", b"different-model")
    original = Path.read_bytes
    monkeypatch.setattr(
        Path, "read_bytes", lambda path: altered if path == target else original(path)
    )
    with pytest.raises(ValueError, match="snapshot changed"):
        companion.validate_baseline(protocol, hashes)


def test_unlisted_output_rejected_before_filesystem_access(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected filesystem access")

    monkeypatch.setattr(companion.Path, "is_symlink", forbidden)
    monkeypatch.setattr(companion.Path, "exists", forbidden)
    with pytest.raises(SystemExit):
        companion.main(["--out", str(tmp_path / "outside.json")])


def test_new_explicit_output_keeps_checkpoint_without_running_a_model(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(companion, "ROOT", tmp_path)
    history = tmp_path / "benchmarks/history"
    history.mkdir(parents=True)
    output = history / "new-public-run.json"
    expected = {
        "records": [],
        "status": "development_checks_passed_human_review_pending",
    }

    def run(*, on_checkpoint):
        on_checkpoint(expected)
        return expected

    monkeypatch.setattr(companion, "run_companion", run)
    assert companion.main(["--out", str(output)]) == 0
    assert json.loads(output.read_text()) == expected
