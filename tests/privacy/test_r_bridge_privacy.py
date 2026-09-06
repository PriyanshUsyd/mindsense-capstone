"""Privacy regression tests for the optional embedded-R statistics path."""

from __future__ import annotations

import ast
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any

import numpy as np
import pandas as pd
import pytest

from backend.statistics import r_bridge

FORBIDDEN_PYTHON_MODULES = {
    "httpx",
    "logging",
    "requests",
    "socket",
    "subprocess",
    "urllib",
}
FORBIDDEN_R_CAPABILITIES = {
    "browseurl(",
    "curl::",
    "download.file(",
    "httr2::",
    "httr::",
    "install.packages(",
    "pak::",
    "pipe(",
    "rcurl::",
    "remotes::",
    "save(",
    "saverds(",
    "serialize(",
    "shell(",
    "socketconnection(",
    "source(",
    "system(",
    "system2(",
    "url(",
    "write.",
}
APPROVED_R_PACKAGES = {"base", "lme4", "lmerTest", "nlme", "pbkrtest"}


def _source_tree() -> ast.Module:
    source = Path(r_bridge.__file__).read_text(encoding="utf-8")
    return ast.parse(source)


def _string_content(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            value.value for value in node.values if isinstance(value, ast.Constant)
        )
    return ""


def test_r_bridge_has_no_python_network_shell_or_logging_imports():
    imported_modules: set[str] = set()
    for node in ast.walk(_source_tree()):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])

    assert imported_modules.isdisjoint(FORBIDDEN_PYTHON_MODULES)


def test_r_expressions_exclude_network_shell_install_and_file_write_calls():
    expressions: list[str] = []
    for node in ast.walk(_source_tree()):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "ro"
            and node.func.attr == "r"
            and node.args
        ):
            expressions.append(_string_content(node.args[0]).lower())

    combined = "\n".join(expressions)
    found = sorted(
        capability for capability in FORBIDDEN_R_CAPABILITIES if capability in combined
    )
    assert found == []


def test_r_package_allowlist_requires_privacy_review_for_new_imports():
    imported_packages = {
        node.args[0].value
        for node in ast.walk(_source_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "importr"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }

    assert imported_packages == APPROVED_R_PACKAGES


class _FakeRObjects:
    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.globalenv = dict(values or {})


@pytest.mark.parametrize("fail_inside_scope", [False, True])
def test_temporary_workspace_removes_new_objects_on_every_exit(fail_inside_scope: bool):
    ro = _FakeRObjects({"unrelated": "preserve"})

    if fail_inside_scope:
        with (
            pytest.raises(RuntimeError, match="forced failure"),
            r_bridge._temporary_r_workspace(ro),
        ):
            for name in r_bridge._R_WORKSPACE_NAMES:
                ro.globalenv[name] = "sensitive"
            raise RuntimeError("forced failure")
    else:
        with r_bridge._temporary_r_workspace(ro):
            for name in r_bridge._R_WORKSPACE_NAMES:
                ro.globalenv[name] = "sensitive"

    assert ro.globalenv == {"unrelated": "preserve"}


def test_temporary_workspace_restores_pre_existing_objects():
    sentinels = {name: object() for name in r_bridge._R_WORKSPACE_NAMES}
    ro = _FakeRObjects(sentinels)

    with r_bridge._temporary_r_workspace(ro):
        for name in r_bridge._R_WORKSPACE_NAMES:
            ro.globalenv[name] = "temporary"

    assert all(ro.globalenv[name] is sentinel for name, sentinel in sentinels.items())


def test_r_workspace_scope_serialises_concurrent_fits(monkeypatch: pytest.MonkeyPatch):
    ro = _FakeRObjects()
    state_lock = Lock()
    active = 0
    maximum_active = 0
    monkeypatch.setattr(r_bridge, "_load_r", lambda: (ro,))

    @r_bridge._r_workspace_scoped
    def simulated_fit(value: str) -> str:
        nonlocal active, maximum_active
        with state_lock:
            active += 1
            maximum_active = max(maximum_active, active)
        ro.globalenv[".mindsense_r_df"] = value
        time.sleep(0.03)
        with state_lock:
            active -= 1
        return value

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(simulated_fit, ("first", "second")))

    assert results == ["first", "second"]
    assert maximum_active == 1
    assert ro.globalenv == {}


def _synthetic_frame() -> pd.DataFrame:
    rng = np.random.default_rng(62)
    rows = []
    for person in range(12):
        for _ in range(8):
            x_within = rng.normal()
            rows.append(
                {
                    "uid": f"synthetic_{person}",
                    "x_within": x_within,
                    "x_between": rng.normal(),
                    "phq4_score": 5.0 - x_within + rng.normal(scale=0.4),
                }
            )
    return pd.DataFrame(rows)


requires_r = pytest.mark.skipif(
    not r_bridge.r_bridge_available(),
    reason="R + rpy2 + lme4/lmerTest/pbkrtest/nlme not usable in this environment",
)


def _assert_no_mindsense_objects_remain(ro: Any) -> None:
    for name in r_bridge._R_WORKSPACE_NAMES:
        with pytest.raises(KeyError):
            ro.globalenv[name]


@requires_r
def test_real_r_fit_does_not_retain_input_or_model_objects():
    ro = r_bridge._load_r()[0]
    _assert_no_mindsense_objects_remain(ro)

    result = r_bridge.fit_lmer_with_denominator_df(
        _synthetic_frame(),
        "phq4_score",
        ["x_within", "x_between"],
        "uid",
    )

    assert result.n_observations == 96
    _assert_no_mindsense_objects_remain(ro)


@requires_r
def test_real_r_fit_cleans_workspace_after_an_r_error():
    from rpy2.rinterface_lib.embedded import RRuntimeError

    ro = r_bridge._load_r()[0]
    _assert_no_mindsense_objects_remain(ro)

    with pytest.raises(RRuntimeError, match="missing_outcome"):
        r_bridge.fit_lmer_with_denominator_df(
            _synthetic_frame(),
            "missing_outcome",
            ["x_within", "x_between"],
            "uid",
        )

    _assert_no_mindsense_objects_remain(ro)
