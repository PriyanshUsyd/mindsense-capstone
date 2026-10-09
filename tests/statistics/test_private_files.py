"""
Tests for backend/statistics/private_files.py (fail-closed owner-only
permissions) and for its use by tier1_runner's per-person outputs.
"""

from __future__ import annotations

import os

import pandas as pd
import pytest

import backend.statistics.tier1_runner as runner
from backend.statistics import bootstrap_cache as bc, private_files as pf

# ---------------------------------------------------------------------------
# Parsing / verifying an icacls read-back (pure; runs on every platform)
# ---------------------------------------------------------------------------

# Real output shape from this machine (Japanese Windows; the trailing status
# line is localised and must be ignored).
ICACLS_BEFORE = (
    "outputs\\tier1\\x  __mt\\CodexSandboxUsers:(I)(OI)(CI)(M,DC)\n"
    "                  S-1-5-21-3525978156-2330114368-1935517631-4126721600:(I)(OI)(CI)(M,DC)\n"
    "                  NT AUTHORITY\\SYSTEM:(I)(OI)(CI)(F)\n"
    "                  BUILTIN\\Administrators:(I)(OI)(CI)(F)\n"
    "                  __MT\\moetn_fp7yru7:(I)(OI)(CI)(F)\n"
    "\n"
    "1 個のファイルが正常に処理されました\n"
)
ICACLS_AFTER = "outputs\\tier1\\x  __MT\\moetn_fp7yru7:(OI)(CI)(F)\n\nSuccessfully processed 1 files\n"


def test_parse_icacls_reads_every_ace_and_ignores_the_status_line():
    aces = pf.parse_icacls(ICACLS_BEFORE, pf.Path("outputs\\tier1\\x"))
    assert [p for p, _ in aces] == [
        "__mt\\CodexSandboxUsers",
        "S-1-5-21-3525978156-2330114368-1935517631-4126721600",
        "NT AUTHORITY\\SYSTEM",
        "BUILTIN\\Administrators",
        "__MT\\moetn_fp7yru7",
    ]
    assert aces[0][1] == ["I", "OI", "CI", "M,DC"]


def test_acl_with_other_principals_is_not_owner_only():
    aces = pf.parse_icacls(ICACLS_BEFORE, pf.Path("outputs\\tier1\\x"))
    assert not pf.acl_is_owner_only(aces, "__MT\\moetn_fp7yru7")


def test_acl_with_only_the_current_user_is_owner_only_case_insensitively():
    aces = pf.parse_icacls(ICACLS_AFTER, pf.Path("outputs\\tier1\\x"))
    assert pf.acl_is_owner_only(aces, "__mt\\MOETN_fp7yru7")


def test_empty_or_unparsable_acl_is_not_owner_only():
    assert not pf.acl_is_owner_only([], "HOST\\u")
    assert not pf.acl_is_owner_only(pf.parse_icacls("garbage\n", pf.Path("x")), "HOST\\u")


def test_deny_or_partial_rights_are_not_owner_only():
    assert not pf.acl_is_owner_only([("HOST\\u", ["R"])], "HOST\\u")
    assert not pf.acl_is_owner_only([("HOST\\u", ["F", "DENY"])], "HOST\\u")


# ---------------------------------------------------------------------------
# Failing closed
# ---------------------------------------------------------------------------


@pytest.fixture
def cannot_restrict(monkeypatch):
    def boom(*a, **k):
        raise OSError("permission change refused")

    monkeypatch.setattr(pf.os, "chmod", boom)
    monkeypatch.setattr(pf.subprocess, "run", boom)


def test_restrict_failure_raises(tmp_path, cannot_restrict):
    with pytest.raises(pf.PermissionRestrictionError):
        pf.restrict_to_owner(tmp_path, is_dir=True)


def test_write_private_text_writes_nothing_when_restriction_fails(tmp_path, cannot_restrict):
    target = tmp_path / "per_person.csv"
    with pytest.raises(pf.PermissionRestrictionError):
        pf.write_private_text(target, "uid\nsecret\n")
    assert not target.exists()
    assert not list(tmp_path.iterdir())  # no temp file left behind either


def test_content_is_written_only_after_the_temp_file_is_restricted(tmp_path, monkeypatch):
    seen = {}

    def fake_restrict(path, *, is_dir):
        seen["content_at_restrict_time"] = path.read_bytes()

    monkeypatch.setattr(pf, "restrict_to_owner", fake_restrict)
    monkeypatch.setattr(pf, "is_owner_only", lambda path, *, is_dir: True)
    pf.write_private_text(tmp_path / "f.csv", "uid\nsecret\n")
    assert seen["content_at_restrict_time"] == b""
    assert (tmp_path / "f.csv").read_text(encoding="utf-8") == "uid\nsecret\n"


def test_restrict_that_does_not_read_back_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "is_owner_only", lambda path, *, is_dir: False)
    monkeypatch.setattr(pf, "_icacls", lambda args: "")
    monkeypatch.setattr(pf, "current_identity", lambda: "HOST\\u")
    monkeypatch.setattr(pf.os, "chmod", lambda *a, **k: None)
    with pytest.raises(pf.PermissionRestrictionError, match="read back"):
        pf.restrict_to_owner(tmp_path, is_dir=True)


def test_ensure_owner_only_leaves_a_verified_path_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "is_owner_only", lambda path, *, is_dir: True)
    monkeypatch.setattr(pf, "restrict_to_owner", lambda *a, **k: pytest.fail("must not re-restrict"))
    pf.ensure_owner_only(tmp_path, is_dir=True)


# ---------------------------------------------------------------------------
# Real filesystem on this platform
# ---------------------------------------------------------------------------


def test_restrict_actually_applies_and_reads_back(tmp_path):
    d = tmp_path / "private"
    d.mkdir()
    f = d / "x.json"
    f.write_text("{}")
    pf.restrict_to_owner(d, is_dir=True)
    pf.restrict_to_owner(f, is_dir=False)
    assert pf.is_owner_only(d, is_dir=True)
    assert pf.is_owner_only(f, is_dir=False)
    if os.name == "posix":
        assert (d.stat().st_mode & 0o777) == 0o700
        assert (f.stat().st_mode & 0o777) == 0o600
    assert f.read_text() == "{}"  # still readable by the owner


def test_restrict_tree_covers_existing_files(tmp_path):
    d = tmp_path / "run"
    d.mkdir()
    (d / "a.csv").write_text("uid\n")
    (d / "sub").mkdir()
    (d / "sub" / "b.json").write_text("{}")
    handled = pf.restrict_tree(d)
    assert len(handled) == 4
    assert all(pf.is_owner_only(p, is_dir=p.is_dir()) for p in handled)


# ---------------------------------------------------------------------------
# tier1_runner: per-person outputs
# ---------------------------------------------------------------------------


def _result(name: str) -> runner.FeatureRunResult:
    return runner.FeatureRunResult(
        feature=name, transform_name="t", n_occasions=2, n_participants=2, participant_uids=["a", "b"],
        primary_fit={"engine": "e", "x_within_beta": 0.1, "x_within_p": 0.5},
        ar1_fit={}, evidence_summary={}, evidence_per_person=pd.DataFrame({"uid": ["a", "b"]}),
    )


def test_every_tier1_output_is_owner_only(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "load_sensing_and_ema", lambda: (None, None))
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(runner, "run_one_feature", lambda spec, s, e, prefer_r=True: _result(spec.name))
    out = runner.main()
    files = sorted(out.iterdir())
    assert {f.name for f in files} == {
        "loc_dist_ep_0_summary.json",
        "loc_dist_ep_0_evidence_per_person.csv",
        "unlock_num_ep_0_summary.json",
        "unlock_num_ep_0_evidence_per_person.csv",
        "participant_set_reconciliation.json",
    }
    assert pf.is_owner_only(out, is_dir=True)
    assert all(pf.is_owner_only(f, is_dir=False) for f in files)
    assert (out / "loc_dist_ep_0_evidence_per_person.csv").read_text(encoding="utf-8").splitlines() == [
        "uid", "a", "b",
    ]


def test_unrestrictable_output_dir_writes_no_per_person_file_for_any_feature(monkeypatch, tmp_path, cannot_restrict):
    monkeypatch.setattr(runner, "load_sensing_and_ema", lambda: (None, None))
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(runner, "run_one_feature", lambda spec, s, e, prefer_r=True: _result(spec.name))
    with pytest.raises(pf.PermissionRestrictionError):
        runner.main()
    assert list(tmp_path.rglob("*")) == []  # no file, no leftover directory


def test_permission_error_in_one_feature_aborts_the_run_and_writes_nothing(monkeypatch, tmp_path):
    """Unlike a stale cache (design d: the healthy feature is still written),
    a permission failure stops everything: no per-person output for the
    other feature either."""
    monkeypatch.setattr(runner, "load_sensing_and_ema", lambda: (None, None))
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path)
    ran = []

    def fake_run(spec, sensing, ema, prefer_r=True):
        ran.append(spec.name)
        if spec.name == "loc_dist_ep_0":
            raise pf.PermissionRestrictionError("cache dir not owner-only")
        return _result(spec.name)

    monkeypatch.setattr(runner, "run_one_feature", fake_run)
    with pytest.raises(pf.PermissionRestrictionError):
        runner.main()
    assert list(tmp_path.rglob("*")) == []
    assert ran == ["loc_dist_ep_0"]  # stopped at once, did not go on to the other feature


def test_stale_cache_is_still_collected_per_feature(monkeypatch, tmp_path):
    """The design-d behaviour is unchanged for statistical failures."""
    monkeypatch.setattr(runner, "load_sensing_and_ema", lambda: (None, None))
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path)

    def fake_run(spec, sensing, ema, prefer_r=True):
        if spec.name == "loc_dist_ep_0":
            raise bc.BootstrapCacheStale("stale!", ["code.x: a -> b"])
        return _result(spec.name)

    monkeypatch.setattr(runner, "run_one_feature", fake_run)
    with pytest.raises(runner.Tier1RunFailed) as excinfo:
        runner.main()
    assert (excinfo.value.out_dir / "unlock_num_ep_0_summary.json").exists()
