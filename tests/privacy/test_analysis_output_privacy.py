"""Privacy gates for generated statistics artefacts."""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_CES_UID = re.compile(r"^[0-9a-f]{32}$")


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
