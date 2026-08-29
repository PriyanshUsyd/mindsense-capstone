"""
Real frontend build check, added 2026-08-29 (and re-run after all 4
teammate branches were merged in) — confirms the Vite+React+TS scaffold
still builds cleanly with `npm run build`, not just that the files exist.
Skipped if npm isn't on PATH or node_modules hasn't been installed, rather
than failing the whole suite in an environment that can't run it.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

npm_path = shutil.which("npm")

pytestmark = pytest.mark.skipif(
    npm_path is None or not (FRONTEND_DIR / "node_modules").exists(),
    reason="npm not on PATH or node_modules not installed — run `npm install` in frontend/ first",
)


def test_npm_run_build_succeeds():
    result = subprocess.run(
        [npm_path, "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"frontend build failed after merging all teammate branches:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_build_output_exists():
    dist_dir = FRONTEND_DIR / "dist"
    assert dist_dir.is_dir()
    assert (dist_dir / "index.html").exists()


def test_no_cdn_references_in_source_or_built_html():
    """Cross-role check: Yuktha's real privacy principle (privacy/
    privacy_architecture_principles.md) requires 'no CDN-hosted fonts,
    scripts, or chart libraries' in the frontend. Confirms Sheng's scaffold
    (built independently by a different AI pass, before Yuktha's real
    branch existed) doesn't violate it — checked against both the source
    index.html and, when available, the built dist/index.html."""
    forbidden_substrings = ["cdn.", "unpkg.com", "jsdelivr.net", "googleapis.com/ajax"]

    source_html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8").lower()
    for forbidden in forbidden_substrings:
        assert forbidden not in source_html, f"source index.html references a CDN: {forbidden}"

    built_html_path = FRONTEND_DIR / "dist" / "index.html"
    if built_html_path.exists():
        built_html = built_html_path.read_text(encoding="utf-8").lower()
        for forbidden in forbidden_substrings:
            assert forbidden not in built_html, f"built dist/index.html references a CDN: {forbidden}"
