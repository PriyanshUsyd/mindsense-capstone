"""Explicit-path provenance, immutable evidence and Qwen execution checks."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.slm.client import SLMUnavailableError
from backend.slm.runtime import create_local_service
from benchmarks import slm_dual_model_review as companion


class GroundedTransport:
    def __init__(self, offline=False):
        self.payloads = []
        self.offline = offline

    def post_json(self, endpoint, payload, timeout_seconds):
        self.payloads.append(payload)
        if self.offline:
            raise SLMUnavailableError("synthetic unavailable model")
        user = json.loads(payload["messages"][1]["content"])
        return {
            "message": {
                "content": json.dumps(
                    {
                        "packet_id": user["evidence_packet"]["identity"]["packet_id"],
                        **user["allowed_response_options"][0],
                    }
                )
            }
        }


def service(offline=False):
    result = create_local_service(model_tag=companion.MODEL)
    result.client.transport = GroundedTransport(offline)
    return result


def _sources_match_frozen_baseline() -> bool:
    protocol = json.loads(companion.allowed_path(companion.PROTOCOL).read_text())
    try:
        companion.validate_baseline(protocol, companion.source_fingerprints())
    except ValueError:
        return False
    return True


# The 2026-10-09 companion is pinned to the rc-eval-1 sources (request policy
# 0.3.1). rc-eval-2 changed request_policy.py/service.py (ME-P01 fixes), so a
# rerun is correctly refused as source drift; that refusal is still tested by
# test_source_drift_rejected_before_any_generation. These end-to-end replays
# run again on a checkout of the pinned sources (e.g. tag rc-eval-1).
requires_frozen_sources = pytest.mark.skipif(
    not _sources_match_frozen_baseline(),
    reason="Week 9 companion is pinned to rc-eval-1 sources; current sources drifted (policy 0.3.2)",
)


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


@requires_frozen_sources
def test_qwen_companion_retains_all_cases_contexts_and_empty_human_ratings():
    slm = service()
    transport = slm.client.transport
    checkpoints = []
    result = companion.run_companion(
        service=slm, on_checkpoint=lambda r: checkpoints.append(len(r["records"]))
    )
    assert result["status"] == "development_checks_passed_human_review_pending"
    assert len(result["records"]) == 288
    assert len(transport.payloads) == 36
    assert {p["model"] for p in transport.payloads} == {companion.MODEL}
    assert checkpoints[-1] == 288
    assert result["source_verification"]["all_sources_unchanged"]
    assert slm.client.transport is transport
    for row in result["records"]:
        assert all(v is None for v in row["human_review"].values())
        assert all(v is None for v in row["rubric_review"].values())
        if row["response"]:
            assert row["checks"]["model_context_matches_variant"]
    for summary in result["summaries"].values():
        assert summary["groups"]["source_plan"]["not_covered_case_ids"] == [
            "plan_q2",
            "plan_q8",
        ]
        assert summary["model_invocations"] == 9


@requires_frozen_sources
def test_failures_are_retained_without_selective_retry():
    slm = service(offline=True)
    transport = slm.client.transport
    result = companion.run_companion(service=slm)
    assert len(result["records"]) == 288
    assert result["status"] == "development_checks_failed_human_review_pending"
    assert len(transport.payloads) == 36
    assert any(r["automated_checks_passed"] is False for r in result["records"])


def test_existing_output_is_never_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(companion, "ROOT", tmp_path)
    history = tmp_path / "benchmarks/history"
    history.mkdir(parents=True)
    output = history / "existing.json"
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit):
        companion.main(["--out", str(output)])
    assert output.read_text(encoding="utf-8") == "keep"


@requires_frozen_sources
@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n"])
def test_lf_and_crlf_checkouts_accept_same_baseline_content(monkeypatch, line_ending):
    # Model Git conversion in memory; never rewrite source/evidence on disk.
    names = (*companion.SOURCE_FILES, companion.BASELINE)
    converted = {}
    for name in names:
        path = companion.allowed_path(name)
        converted[path] = (
            path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", line_ending)
        )
    original = Path.read_bytes
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda path: converted[path] if path in converted else original(path),
    )
    protocol = json.loads(converted[companion.allowed_path(companion.PROTOCOL)])
    hashes = companion.source_fingerprints()
    baseline = companion.validate_baseline(protocol, hashes)
    assert baseline["requested_model_tag"] == "phi4-mini:3.8b"
    assert any(
        hashes["raw"][name] != digest
        for name, digest in baseline["provenance"]["sha256_raw_bytes"].items()
    )

    changed = companion.allowed_path("backend/slm/service.py")
    converted[changed] += b"# real source change\n"
    with pytest.raises(ValueError, match="source drift"):
        companion.validate_baseline(protocol, companion.source_fingerprints())


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
