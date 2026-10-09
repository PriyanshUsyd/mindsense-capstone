"""
Tests for backend/statistics/bootstrap_cache.py (week7 item 2, decisions
a-d). No R needed: fingerprints take an explicit `environment`, and the
aggregation runs on a synthetic RealFit stand-in with hand-made records.
"""

from __future__ import annotations

import json
import subprocess
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import backend.statistics.tier1_runner as runner
from backend.statistics import bootstrap, bootstrap_cache as bc, private_files as pf
from backend.statistics.feature_specs import TIER1_FEATURE_SPECS

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = TIER1_FEATURE_SPECS["loc_dist_ep_0"]
ENV = {"python": "3.x", "R": "R 4.x", "nlme": "3.1"}
B = 4
UIDS = ["a", "b", "c"]


def _no_git_changes(_root, _files):
    return []


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for rel in (*bc.ESTIMATION_CODE_FILES, *bc.AGGREGATION_CODE_FILES):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(f"# {rel}\nX = 1\n".encode("utf-8"))  # LF regardless of platform
    return root


def _frame() -> pd.DataFrame:
    rows = []
    for i, uid in enumerate(UIDS):
        for t in range(5):
            rows.append(
                {
                    "uid": uid,
                    "date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=5 * t),
                    "phq4_score": 3.0 + i + 0.1 * t,
                    "x_within": 0.2 * t - 0.4 + 0.01 * i,
                    "x_between": float(i),
                }
            )
    return pd.DataFrame(rows)


def _keys(fake_repo: Path, frame: pd.DataFrame | None = None, **kw) -> dict:
    prepared = bootstrap.prepare_model_frame(_frame() if frame is None else frame)
    return bc.raw_key_dict(prepared, SPEC, engine="nlme", repo_root=fake_repo, environment=ENV, **kw)


def _real_fit() -> SimpleNamespace:
    return SimpleNamespace(
        ar1_result=SimpleNamespace(
            params={"x_within": -0.2},
            blups={u: {"x_within": 0.05 * i} for i, u in enumerate(UIDS)},
        ),
        model_frame=bootstrap.prepare_model_frame(_frame()),
        uid_col="uid",
        outcome_col="phq4_score",
    )


def _records(n: int = B) -> list[dict]:
    rng = np.random.default_rng(0)
    out = []
    for method in ("parametric", "cluster"):
        for i in range(n):
            out.append(
                {
                    "method": method,
                    "iteration_index": i,
                    "usable": True,
                    "error": None,
                    "used_random_slope": True,
                    "beta": {"x_within": float(-0.2 + rng.normal(0, 0.02))},
                    "blups": {u: {"x_within": float(rng.normal(0, 0.05))} for u in UIDS},
                    "uid_map": None,
                }
            )
    return out


# ---------------------------------------------------------------------------
# Fingerprint layers
# ---------------------------------------------------------------------------


def test_keys_cover_all_three_layers(fake_repo):
    keys = _keys(fake_repo)
    prefixes = {k.split(".", 1)[0] for k in keys}
    assert prefixes == {"input", "code", "env", "config"}
    for rel in bc.ESTIMATION_CODE_FILES:
        assert f"code.{rel}" in keys


def test_fingerprint_is_deterministic(fake_repo):
    assert bc.fingerprint_hash(_keys(fake_repo)) == bc.fingerprint_hash(_keys(fake_repo))


def test_frame_digest_detects_a_single_changed_cell(fake_repo):
    changed = _frame()
    changed.loc[3, "x_within"] += 1e-9
    diff = bc.diff_keys(_keys(fake_repo), _keys(fake_repo, changed))
    assert [d.split(":")[0] for d in diff] == ["input.model_frame_sha256"]


def test_code_change_names_the_file(fake_repo):
    before = _keys(fake_repo)
    (fake_repo / "backend/statistics/r_bridge.py").write_text("# edited\n", encoding="utf-8")
    diff = bc.diff_keys(before, _keys(fake_repo))
    assert [d.split(":")[0] for d in diff] == ["code.backend/statistics/r_bridge.py"]


def test_crlf_checkout_does_not_change_the_hash(fake_repo):
    before = _keys(fake_repo)
    p = fake_repo / "backend/statistics/bootstrap.py"
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    assert bc.diff_keys(before, _keys(fake_repo)) == []


@pytest.mark.parametrize(
    "kwargs, key",
    [
        ({"master_seed": 1}, "config.master_seed"),
        ({"n_iterations": 7}, "config.n_iterations"),
        ({"engine": "other"}, "config.engine"),
    ],
)
def test_config_changes_are_named(fake_repo, kwargs, key):
    kw = {"engine": "nlme", **kwargs}
    prepared = bootstrap.prepare_model_frame(_frame())
    other = bc.raw_key_dict(prepared, SPEC, repo_root=fake_repo, environment=ENV, **kw)
    diff = bc.diff_keys(_keys(fake_repo), other)
    assert [d.split(":")[0] for d in diff] == [key]


def test_environment_change_is_named(fake_repo):
    prepared = bootstrap.prepare_model_frame(_frame())
    other = bc.raw_key_dict(
        prepared, SPEC, engine="nlme", repo_root=fake_repo, environment={**ENV, "nlme": "9.9"}
    )
    assert [d.split(":")[0] for d in bc.diff_keys(_keys(fake_repo), other)] == ["env.nlme"]


def test_aggregated_key_depends_on_evidence_py_and_keeps_raw_keys(fake_repo):
    raw = _keys(fake_repo)
    before = bc.aggregated_key_dict(raw, fake_repo)
    (fake_repo / "backend/statistics/evidence.py").write_text("# edited\n", encoding="utf-8")
    after = bc.aggregated_key_dict(raw, fake_repo)
    assert [d.split(":")[0] for d in bc.diff_keys(before, after)] == ["code.backend/statistics/evidence.py"]
    assert all(f"raw.{k}" in before for k in raw)
    assert "thresholds.classify_evidence_strength_sha256" in before


def test_evidence_py_change_does_not_touch_the_raw_fingerprint(fake_repo):
    before = bc.fingerprint_hash(_keys(fake_repo))
    (fake_repo / "backend/statistics/evidence.py").write_text("# edited\n", encoding="utf-8")
    assert bc.fingerprint_hash(_keys(fake_repo)) == before


# ---------------------------------------------------------------------------
# Aggregated cache: missing vs stale (decision c)
# ---------------------------------------------------------------------------


def _write_cache(fake_repo: Path, cache_root: Path) -> Path:
    return bc.write_aggregated_cache(
        SPEC.name,
        _real_fit(),
        _records(),
        _keys(fake_repo, n_iterations=B),
        n_iterations=B,
        cache_root=cache_root,
        repo_root=fake_repo,
        git_status=_no_git_changes,
    )


def _load(fake_repo: Path, cache_root: Path, frame: pd.DataFrame | None = None, **kw):
    return bc.load_aggregated_cache(
        SPEC,
        _frame() if frame is None else frame,
        engine="nlme",
        n_iterations=B,
        cache_root=cache_root,
        repo_root=fake_repo,
        environment=ENV,
        **kw,
    )


def test_missing_cache_is_none_not_an_error(fake_repo, tmp_path):
    assert _load(fake_repo, tmp_path / "cache") is None


def test_roundtrip_returns_se_and_intersection(fake_repo, tmp_path):
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # family-size warning: 3 != 214
        _write_cache(fake_repo, root)
        cached = _load(fake_repo, root)
    assert cached is not None
    assert set(cached.se["method"]) == {"parametric", "cluster"}
    assert len(cached.se) == 2 * len(UIDS)
    assert {"label_intersection", "label_parametric", "label_cluster"} <= set(cached.intersection.columns)
    assert sorted(cached.intersection["uid"]) == UIDS
    assert cached.failure_summary["parametric"]["n_total"] == B


def _cohort(n: int) -> tuple[SimpleNamespace, list[dict]]:
    """A synthetic real fit and bootstrap records for `n` participants."""
    uids = [f"u{i:03d}" for i in range(n)]
    rng = np.random.default_rng(1)
    frame = pd.DataFrame(
        [
            {"uid": u, "phq4_score": 3.0 + 0.01 * i + 0.1 * t, "x_within": 0.2 * t - 0.4}
            for i, u in enumerate(uids)
            for t in range(5)
        ]
    )
    fit = SimpleNamespace(
        ar1_result=SimpleNamespace(
            params={"x_within": -0.2}, blups={u: {"x_within": 0.001 * i} for i, u in enumerate(uids)}
        ),
        model_frame=frame,
        uid_col="uid",
        outcome_col="phq4_score",
    )
    records = [
        {
            "method": method,
            "iteration_index": k,
            "usable": True,
            "error": None,
            "used_random_slope": True,
            "beta": {"x_within": float(-0.2 + rng.normal(0, 0.02))},
            "blups": {u: {"x_within": float(rng.normal(0, 0.05))} for u in uids},
            "uid_map": None,
        }
        for method in ("parametric", "cluster")
        for k in range(B)
    ]
    return fit, records


def _family_size_warnings(caught) -> list[str]:
    return [str(w.message) for w in caught if "EXPECTED_FAMILY_SIZE" in str(w.message)]


@pytest.mark.parametrize("feature", ["loc_dist_ep_0", "unlock_num_ep_0"])
def test_aggregation_matches_the_calibrated_family_size_without_warning(feature):
    from backend.statistics import evidence

    fit, records = _cohort(evidence.EXPECTED_FAMILY_SIZE[feature])  # 214 / 216
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _, intersection, _ = bc.aggregate_checkpoint(feature, fit, records, B)
    assert len(intersection) == evidence.EXPECTED_FAMILY_SIZE[feature]
    assert _family_size_warnings(caught) == []


def test_aggregation_actually_runs_the_family_size_check(monkeypatch):
    # The no-warning test above cannot tell "check passed" from "check
    # skipped" (feature_id=None skips silently); this one can.
    from backend.statistics import evidence

    monkeypatch.setitem(evidence.EXPECTED_FAMILY_SIZE, "loc_dist_ep_0", 999)
    fit, records = _cohort(214)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        bc.aggregate_checkpoint("loc_dist_ep_0", fit, records, B)
    assert any("(214)" in m and "(999)" in m for m in _family_size_warnings(caught))


def test_stale_cache_raises_and_names_the_changed_key(fake_repo, tmp_path):
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _write_cache(fake_repo, root)
    (fake_repo / "backend/statistics/bootstrap.py").write_text("# edited\n", encoding="utf-8")
    with pytest.raises(bc.BootstrapCacheStale) as excinfo:
        _load(fake_repo, root)
    assert any(c.startswith("raw.code.backend/statistics/bootstrap.py") for c in excinfo.value.changed)
    assert "raw.code.backend/statistics/bootstrap.py" in str(excinfo.value)
    assert "Next step" in str(excinfo.value)


def test_changed_input_data_is_stale(fake_repo, tmp_path):
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _write_cache(fake_repo, root)
    other = _frame()
    other.loc[0, "phq4_score"] += 1.0
    with pytest.raises(bc.BootstrapCacheStale, match="raw.input.model_frame_sha256"):
        _load(fake_repo, root, other)


def test_corrupt_cache_raises(fake_repo, tmp_path):
    root = tmp_path / "cache" / SPEC.name
    root.mkdir(parents=True)
    (root / bc.AGGREGATED_NAME).write_text("{not json", encoding="utf-8")
    with pytest.raises(bc.BootstrapCacheError):
        _load(fake_repo, tmp_path / "cache")


def test_hash_not_matching_its_own_keys_is_rejected(fake_repo, tmp_path):
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        path = _write_cache(fake_repo, root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["fingerprint"]["keys"]["config.master_seed"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(bc.BootstrapCacheError, match="malformed"):
        _load(fake_repo, root)


def test_incomplete_checkpoint_is_not_aggregated(fake_repo, tmp_path):
    with pytest.raises(bc.BootstrapCacheError, match="only a complete run"):
        bc.write_aggregated_cache(
            SPEC.name, _real_fit(), _records(B - 1), _keys(fake_repo), n_iterations=B,
            cache_root=tmp_path / "cache", repo_root=fake_repo, git_status=_no_git_changes,
        )


# ---------------------------------------------------------------------------
# Write guard and resume safety
# ---------------------------------------------------------------------------


def test_write_refused_when_a_keyed_file_is_dirty(fake_repo, tmp_path):
    with pytest.raises(bc.BootstrapCacheWriteRefused, match="r_bridge"):
        bc.prepare_raw_checkpoint(
            SPEC.name, _keys(fake_repo), cache_root=tmp_path / "cache", repo_root=fake_repo,
            git_status=lambda _r, _f: [" M backend/statistics/r_bridge.py"],
        )
    assert not (tmp_path / "cache").exists()  # nothing written


def test_write_refused_for_aggregated_when_dirty(fake_repo, tmp_path):
    with pytest.raises(bc.BootstrapCacheWriteRefused):
        bc.write_aggregated_cache(
            SPEC.name, _real_fit(), _records(), _keys(fake_repo), n_iterations=B,
            cache_root=tmp_path / "cache", repo_root=fake_repo,
            git_status=lambda _r, _f: ["?? backend/statistics/evidence.py"],
        )


def test_git_porcelain_flags_untracked_and_modified_files(tmp_path):
    git = ["git", "-C", str(tmp_path)]
    subprocess.run([*git, "init", "-q"], check=True)
    (tmp_path / "f.py").write_text("x = 1\n")
    assert bc._git_porcelain(tmp_path, ["f.py"]) == ["?? f.py"]
    subprocess.run([*git, "add", "f.py"], check=True)
    subprocess.run([*git, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c"], check=True)
    assert bc._git_porcelain(tmp_path, ["f.py"]) == []
    (tmp_path / "f.py").write_text("x = 2\n")
    assert bc._git_porcelain(tmp_path, ["f.py"]) == [" M f.py"]


def test_resume_with_same_fingerprint_is_allowed_even_if_tree_is_now_dirty(fake_repo, tmp_path):
    root = tmp_path / "cache"
    keys = _keys(fake_repo)
    first = bc.prepare_raw_checkpoint(SPEC.name, keys, cache_root=root, repo_root=fake_repo, git_status=_no_git_changes)
    again = bc.prepare_raw_checkpoint(
        SPEC.name, keys, cache_root=root, repo_root=fake_repo,
        git_status=lambda _r, _f: pytest.fail("a matching resume must not need git"),
    )
    assert first == again


def test_resume_with_changed_code_is_refused(fake_repo, tmp_path):
    root = tmp_path / "cache"
    bc.prepare_raw_checkpoint(
        SPEC.name, _keys(fake_repo), cache_root=root, repo_root=fake_repo, git_status=_no_git_changes
    )
    (fake_repo / "backend/statistics/bootstrap.py").write_text("# edited\n", encoding="utf-8")
    with pytest.raises(bc.BootstrapCacheStale, match="resume refused") as excinfo:
        bc.prepare_raw_checkpoint(
            SPEC.name, _keys(fake_repo), cache_root=root, repo_root=fake_repo, git_status=_no_git_changes
        )
    assert excinfo.value.changed == [c for c in excinfo.value.changed if "bootstrap.py" in c]


def test_checkpoint_without_sidecar_is_refused(fake_repo, tmp_path):
    d = tmp_path / "cache" / SPEC.name
    d.mkdir(parents=True)
    (d / bc.RAW_CHECKPOINT_NAME).write_text('{"method": "parametric"}\n', encoding="utf-8")
    with pytest.raises(bc.BootstrapCacheError, match="unknown"):
        bc.prepare_raw_checkpoint(
            SPEC.name, _keys(fake_repo), cache_root=tmp_path / "cache", repo_root=fake_repo,
            git_status=_no_git_changes,
        )


# ---------------------------------------------------------------------------
# Permissions are fail-closed (Privacy & Security Lead, PR #49)
# ---------------------------------------------------------------------------


@pytest.fixture
def cannot_restrict(monkeypatch):
    """Both mechanisms (chmod on POSIX, icacls on Windows) fail."""

    def boom(*a, **k):
        raise OSError("permission change refused")

    monkeypatch.setattr(pf.os, "chmod", boom)
    monkeypatch.setattr(pf.subprocess, "run", boom)


@pytest.fixture
def fake_acl(monkeypatch):
    """Call `.install()` AFTER building a real cache: from then on, permissions
    read back as NOT owner-only until `restrict_to_owner` has been applied to
    that very path (the folder 'as found'). `.attempts` records the paths
    restricted since."""
    state = SimpleNamespace(restricted=set(), attempts=[])

    def fake_is_owner_only(path, *, is_dir):
        return str(path) in state.restricted

    def fake_restrict(path, *, is_dir):
        state.attempts.append(str(path))
        state.restricted.add(str(path))

    def install():
        monkeypatch.setattr(pf, "is_owner_only", fake_is_owner_only)
        monkeypatch.setattr(pf, "restrict_to_owner", fake_restrict)
        monkeypatch.setattr(bc, "restrict_to_owner", fake_restrict)

    state.install = install
    return state


def test_permission_error_is_not_a_cache_error():
    assert not issubclass(pf.PermissionRestrictionError, bc.BootstrapCacheError)
    assert not issubclass(bc.BootstrapCacheError, pf.PermissionRestrictionError)


def test_raw_checkpoint_not_written_when_restriction_fails(fake_repo, tmp_path, cannot_restrict):
    root = tmp_path / "cache"
    with pytest.raises(pf.PermissionRestrictionError):
        bc.prepare_raw_checkpoint(
            SPEC.name, _keys(fake_repo), cache_root=root, repo_root=fake_repo, git_status=_no_git_changes
        )
    d = root / SPEC.name
    assert not (d / bc.RAW_FINGERPRINT_NAME).exists()
    assert not (d / bc.RAW_CHECKPOINT_NAME).exists()
    assert not list(root.rglob("*.tmp"))


def test_aggregated_cache_not_written_when_restriction_fails(fake_repo, tmp_path, cannot_restrict):
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(pf.PermissionRestrictionError):
            _write_cache(fake_repo, root)
    assert not list(root.rglob("*.json")) and not list(root.rglob("*.tmp"))


def test_not_written_if_restriction_succeeds_but_does_not_read_back(fake_repo, tmp_path, monkeypatch):
    """The OS reports success but the permissions read back are not
    owner-only: still a refusal, and no uid reaches disk."""
    monkeypatch.setattr(pf, "is_owner_only", lambda path, *, is_dir: False)
    monkeypatch.setattr(pf, "_icacls", lambda args: "")
    monkeypatch.setattr(pf, "current_identity", lambda: "HOST\\someone")
    monkeypatch.setattr(pf.os, "chmod", lambda *a, **k: None)
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(pf.PermissionRestrictionError, match="read back"):
            _write_cache(fake_repo, root)
    assert not list(root.rglob("*.json"))


def test_existing_unrestricted_cache_is_restricted_once_on_load(fake_repo, tmp_path, fake_acl):
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        path = _write_cache(fake_repo, root)
    fake_acl.install()
    cached = _load(fake_repo, root)
    assert cached is not None
    assert sorted(fake_acl.attempts) == sorted({str(root), str(path.parent), str(path)})  # once each


def test_already_restricted_cache_is_not_touched_on_load(fake_repo, tmp_path, fake_acl):
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        path = _write_cache(fake_repo, root)
    fake_acl.install()
    for p in (root, path.parent, path):  # restricted earlier, as far as the fake can tell
        fake_acl.restricted.add(str(p))
    assert _load(fake_repo, root) is not None
    assert fake_acl.attempts == []


def test_existing_unrestricted_cache_that_cannot_be_restricted_raises_on_load(fake_repo, tmp_path, monkeypatch):
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _write_cache(fake_repo, root)

    def refuse(path, *, is_dir):
        raise pf.PermissionRestrictionError(f"cannot restrict {path}")

    monkeypatch.setattr(pf, "is_owner_only", lambda path, *, is_dir: False)
    monkeypatch.setattr(pf, "restrict_to_owner", refuse)
    with pytest.raises(pf.PermissionRestrictionError):
        _load(fake_repo, root)


def test_existing_unrestricted_cache_is_checked_before_resume(fake_repo, tmp_path, fake_acl):
    keys = _keys(fake_repo)
    root = tmp_path / "cache"
    bc.prepare_raw_checkpoint(SPEC.name, keys, cache_root=root, repo_root=fake_repo, git_status=_no_git_changes)
    fake_acl.install()
    bc.prepare_raw_checkpoint(SPEC.name, keys, cache_root=root, repo_root=fake_repo, git_status=_no_git_changes)
    d = root / SPEC.name
    assert {str(root), str(d), str(d / bc.RAW_FINGERPRINT_NAME), str(d / bc.RAW_CHECKPOINT_NAME)} <= set(
        fake_acl.attempts
    )


def test_resume_of_unrestricted_cache_that_cannot_be_restricted_raises(fake_repo, tmp_path, monkeypatch):
    keys = _keys(fake_repo)
    root = tmp_path / "cache"
    bc.prepare_raw_checkpoint(SPEC.name, keys, cache_root=root, repo_root=fake_repo, git_status=_no_git_changes)

    def refuse(path, *, is_dir):
        raise pf.PermissionRestrictionError("no")

    monkeypatch.setattr(pf, "is_owner_only", lambda path, *, is_dir: False)
    monkeypatch.setattr(pf, "restrict_to_owner", refuse)
    with pytest.raises(pf.PermissionRestrictionError):
        bc.prepare_raw_checkpoint(SPEC.name, keys, cache_root=root, repo_root=fake_repo, git_status=_no_git_changes)


def test_written_cache_is_owner_only_on_this_platform(fake_repo, tmp_path):
    root = tmp_path / "cache"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        path = _write_cache(fake_repo, root)
    assert pf.is_owner_only(root, is_dir=True)
    assert pf.is_owner_only(path.parent, is_dir=True)
    assert pf.is_owner_only(path, is_dir=False)
    assert bc.AGGREGATED_NAME in path.name and path.read_text(encoding="utf-8")  # owner can still read it


# ---------------------------------------------------------------------------
# Import-graph completeness
# ---------------------------------------------------------------------------


def test_every_backend_module_on_the_estimation_path_is_fingerprinted_or_excluded():
    """Imports the estimation entry points in a fresh interpreter and checks
    every `backend.*` module it pulls in is either hashed (layer B / the
    aggregated layer) or on EXCLUDED_MODULES with a reason. A new module
    on the estimation path fails here instead of silently serving stale
    estimates."""
    code = (
        "import sys, json\n"
        "import backend.statistics.bootstrap, backend.statistics.feature_specs\n"
        "print(json.dumps(sorted(m for m in sys.modules if m == 'backend' or m.startswith('backend.'))))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],  # not -I: needs cwd (the repo root) on sys.path
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    imported = json.loads(out.strip().splitlines()[-1])

    covered = {
        rel.removesuffix(".py").replace("/", ".")
        for rel in (*bc.ESTIMATION_CODE_FILES, *bc.AGGREGATION_CODE_FILES)
    }
    unaccounted = [m for m in imported if m not in covered and m not in bc.EXCLUDED_MODULES]
    assert not unaccounted, (
        f"modules on the estimation import path that are neither fingerprinted nor excluded: {unaccounted}. "
        "Add them to ESTIMATION_CODE_FILES (preferred) or EXCLUDED_MODULES with a reason."
    )
    # and the lists themselves must not rot
    for rel in (*bc.ESTIMATION_CODE_FILES, *bc.AGGREGATION_CODE_FILES):
        assert (REPO_ROOT / rel).is_file(), rel


def test_excluded_modules_are_not_also_fingerprinted():
    covered = {rel.removesuffix(".py").replace("/", ".") for rel in bc.ESTIMATION_CODE_FILES}
    assert not (covered & set(bc.EXCLUDED_MODULES))


def test_tier1_runner_and_cache_module_are_deliberately_outside_the_fingerprint():
    # Consumers/orchestration: editing them does not change any estimate.
    for rel in (
        "backend/statistics/tier1_runner.py",
        "backend/statistics/bootstrap_cache.py",
        "backend/statistics/private_files.py",
    ):
        assert rel not in bc.ESTIMATION_CODE_FILES
        assert rel not in bc.AGGREGATION_CODE_FILES


def test_private_files_is_not_on_the_estimation_import_path():
    """Only bootstrap_cache and tier1_runner may import it. If `bootstrap` or
    `feature_specs` ever did, it would join the estimation path and an edit to
    it would silently invalidate a B=500 run (the import-graph test above
    would fail too)."""
    code = (
        "import sys\n"
        "import backend.statistics.bootstrap, backend.statistics.feature_specs\n"
        "print('backend.statistics.private_files' in sys.modules)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    assert out.strip().splitlines()[-1] == "False"


# ---------------------------------------------------------------------------
# tier1_runner.main: independent features (decision d)
# ---------------------------------------------------------------------------


def _result(name: str) -> runner.FeatureRunResult:
    return runner.FeatureRunResult(
        feature=name, transform_name="t", n_occasions=2, n_participants=2, participant_uids=["a", "b"],
        primary_fit={"engine": "e", "x_within_beta": 0.1, "x_within_p": 0.5},
        ar1_fit={}, evidence_summary={}, evidence_per_person=pd.DataFrame({"uid": ["a", "b"]}),
    )


def test_one_stale_feature_does_not_stop_the_other(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "load_sensing_and_ema", lambda: (None, None))
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path)

    def fake_run(spec, sensing, ema, prefer_r=True):
        if spec.name == "loc_dist_ep_0":
            raise bc.BootstrapCacheStale("stale!", ["code.x: a -> b"])
        return _result(spec.name)

    monkeypatch.setattr(runner, "run_one_feature", fake_run)
    with pytest.raises(runner.Tier1RunFailed) as excinfo:
        runner.main()
    assert set(excinfo.value.failures) == {"loc_dist_ep_0"}
    assert "stale!" in str(excinfo.value)
    # the healthy feature's output was written before failing closed
    out = excinfo.value.out_dir
    assert out is not None and (out / "unlock_num_ep_0_summary.json").exists()
    assert not (out / "loc_dist_ep_0_summary.json").exists()


def test_main_without_failures_returns_the_output_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "load_sensing_and_ema", lambda: (None, None))
    monkeypatch.setattr(runner, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(runner, "run_one_feature", lambda spec, s, e, prefer_r=True: _result(spec.name))
    out = runner.main()
    assert (out / "loc_dist_ep_0_summary.json").exists() and (out / "unlock_num_ep_0_summary.json").exists()
