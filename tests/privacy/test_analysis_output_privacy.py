"""Privacy gates for generated statistics artefacts."""

from __future__ import annotations

import csv
import os
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_CES_UID = re.compile(r"^[0-9a-f]{32}$")
RAW_CES_UID_IN_TEXT = re.compile(r"(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])")
SYNTHETIC_UIDS = {
    "a" * 32,
    "b" * 32,
    "c" * 32,
}
TRACKED_TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def _shared_analysis_csvs() -> list[Path]:
    """Return tracked or unignored files that would be shared by Git."""
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "analysis/output",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        REPO_ROOT / relative_path
        for relative_path in result.stdout.splitlines()
        if relative_path.endswith(".csv")
    ]


def test_analysis_outputs_do_not_expose_raw_ces_uids():
    """Files shared by Git must use opaque references, never raw CES uids."""
    leak_count = 0
    examples: list[str] = []

    for path in _shared_analysis_csvs():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "uid" not in reader.fieldnames:
                continue

            for line_number, row in enumerate(reader, start=2):
                value = (row.get("uid") or "").strip()
                if not RAW_CES_UID.fullmatch(value):
                    continue

                leak_count += 1
                if len(examples) < 5:
                    examples.append(f"{path.relative_to(REPO_ROOT)}:{line_number}")

    assert leak_count == 0, (
        f"Found {leak_count} raw CES uid rows in analysis outputs. "
        "Keep participant-level exports local or replace raw identifiers with "
        f"approved opaque references. First locations: {', '.join(examples)}"
    )


def _tracked_text_paths() -> list[Path]:
    """Inventory the selected scope before any file contents are accessed."""
    scope = os.environ.get("MINDSENSE_CI_SCOPE", "full")
    if scope not in {"full", "sealed-excluded"}:
        raise ValueError("unknown MINDSENSE_CI_SCOPE")
    exclusions = (
        [":(exclude)tests/evaluation/held_out/**"] if scope == "sealed-excluded" else []
    )
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--",
            "analysis",
            "backend",
            "benchmarks",
            "docs",
            "frontend/src",
            "privacy",
            "tests",
            *exclusions,
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = []
    for relative_path in result.stdout.splitlines():
        relative = Path(relative_path)
        if scope == "sealed-excluded" and relative.is_relative_to(
            "tests/evaluation/held_out"
        ):
            continue
        paths.append(REPO_ROOT / relative)
    return paths


def test_tracked_text_does_not_embed_raw_ces_uid_shaped_values():
    """Shared source and documentation must not publish raw CES identifiers."""
    leaks: list[str] = []

    for path in _tracked_text_paths():
        if not path.is_file() or path.suffix not in TRACKED_TEXT_SUFFIXES:
            continue
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            matches = {
                match.group(0) for match in RAW_CES_UID_IN_TEXT.finditer(line)
            } - SYNTHETIC_UIDS
            if matches:
                leaks.append(f"{path.relative_to(REPO_ROOT)}:{line_number}")

    assert not leaks, (
        "Tracked source or documentation contains raw CES uid-shaped values. "
        "Shared artefacts must use an approved opaque local "
        f"reference instead. Locations: {', '.join(leaks)}"
    )


def test_sealed_excluded_scan_filters_before_any_file_access(monkeypatch, tmp_path):
    """Even an over-inclusive inventory cannot open or stat sealed content."""
    public = tmp_path / "public.md"
    public.write_text("Public synthetic fixture.", encoding="utf-8")
    sealed = tmp_path / "tests/evaluation/held_out/sentinel.json"
    commands = []

    def inventory(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(
            stdout="public.md\ntests/evaluation/held_out/sentinel.json\n"
        )

    original_is_file = Path.is_file
    original_read_text = Path.read_text

    def guarded_is_file(path):
        assert path != sealed, "sealed path inspected before exclusion"
        return original_is_file(path)

    def guarded_read_text(path, *args, **kwargs):
        assert path != sealed, "sealed content accessed"
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setenv("MINDSENSE_CI_SCOPE", "sealed-excluded")
    monkeypatch.setattr(f"{__name__}.REPO_ROOT", tmp_path)
    monkeypatch.setattr(subprocess, "run", inventory)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    test_tracked_text_does_not_embed_raw_ces_uid_shaped_values()

    assert ":(exclude)tests/evaluation/held_out/**" in commands[0]


@pytest.mark.parametrize("scope", ["full", "sealed-excluded"])
def test_selected_scan_still_rejects_public_identifier_leaks(
    monkeypatch, tmp_path, scope
):
    """Scope selection never disables the public-source identifier gate."""
    (tmp_path / "public.md").write_text("0123456789abcdef" * 2, encoding="utf-8")
    monkeypatch.setenv("MINDSENSE_CI_SCOPE", scope)
    monkeypatch.setattr(f"{__name__}.REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="public.md\n")
    )

    with pytest.raises(AssertionError, match="raw CES uid-shaped values"):
        test_tracked_text_does_not_embed_raw_ces_uid_shaped_values()


def test_default_scope_keeps_full_inventory(monkeypatch, tmp_path):
    """Full-mode inventory is preserved; this test reads no repository content."""
    monkeypatch.delenv("MINDSENSE_CI_SCOPE", raising=False)
    monkeypatch.setattr(f"{__name__}.REPO_ROOT", tmp_path)
    commands = []

    def inventory(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(stdout="tests/evaluation/held_out/sentinel.json\n")

    monkeypatch.setattr(subprocess, "run", inventory)
    assert _tracked_text_paths() == [
        tmp_path / "tests/evaluation/held_out/sentinel.json"
    ]
    assert not any(arg.startswith(":(exclude)") for arg in commands[0])


def test_unknown_scope_fails_before_inventory(monkeypatch):
    monkeypatch.setenv("MINDSENSE_CI_SCOPE", "unsupported")
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: pytest.fail("inventory must not run")
    )
    with pytest.raises(ValueError, match="unknown MINDSENSE_CI_SCOPE"):
        _tracked_text_paths()
