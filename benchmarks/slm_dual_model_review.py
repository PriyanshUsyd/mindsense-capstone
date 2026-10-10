"""Run the public Qwen companion with explicit-path provenance only.

Preserves the original Phi run and implementation. No participant data, broad
Git status, prompting-method experiment, or human rating is performed here.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from unittest.mock import patch

from backend.slm.output_grounding import OUTPUT_GROUNDING_VERSION
from backend.slm.prompt_loader import load_evidence_prompt
from backend.slm.request_policy import REQUEST_POLICY_VERSION
from backend.slm.service import SLMService
from benchmarks import slm_evaluation_alignment as alignment
from benchmarks import slm_variant_quality as quality

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "benchmarks/fixtures/week9_dual_model_protocol.json"
BASELINE = "benchmarks/history/week9_variant_quality_phi_2026-10-06.json"
MODEL = "qwen3:4b"
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *alignment.SOURCE_FILES,
            *quality.EXTRA_SOURCES,
            PROTOCOL,
            "benchmarks/slm_dual_model_review.py",
            "tests/slm/test_dual_model_review.py",
        )
    )
)


def allowed_path(relative: str) -> Path:
    """Validate the fixed public path before any filesystem access."""
    if relative not in (*SOURCE_FILES, BASELINE):
        raise ValueError("path outside the public source allow-list")
    path = ROOT / relative
    if path.is_symlink() or path.resolve() != path.absolute():
        raise ValueError("public source paths must not redirect")
    return path


def source_fingerprints() -> dict[str, dict[str, str]]:
    """Keep raw provenance and a CRLF-only comparison from the same read."""
    hashes: dict[str, dict[str, str]] = {"raw": {}, "lf": {}}
    for name in SOURCE_FILES:
        raw = allowed_path(name).read_bytes()
        hashes["raw"][name] = hashlib.sha256(raw).hexdigest()
        hashes["lf"][name] = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    return hashes


def provenance() -> dict:
    """No whole-tree status: only the exact listed public source files."""

    def git(*args):
        return subprocess.run(
            ["git", "-c", "core.fsmonitor=false", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout.strip()

    state = git("status", "--porcelain", "--", *SOURCE_FILES)
    prompt = load_evidence_prompt()
    hashes = source_fingerprints()
    return {
        "git_head": git("rev-parse", "HEAD"),
        "source_scope_dirty": bool(state),
        "working_tree_dirty": None,
        "status_scope": "explicit public sources only; whole worktree not inspected",
        "sha256_raw_bytes": hashes["raw"],
        "sha256_crlf_to_lf": hashes["lf"],
        "request_policy_version": REQUEST_POLICY_VERSION,
        "output_grounding_version": OUTPUT_GROUNDING_VERSION,
        "prompt_version": prompt.manifest.prompt_version,
        "prompt_sha256": prompt.sha256,
    }


def validate_baseline(protocol: dict, hashes: dict[str, dict[str, str]]) -> dict:
    """Accept only original bytes or their independently verified LF equivalent."""
    reproduction = protocol["reproduction_metadata"]
    raw = allowed_path(BASELINE).read_bytes()
    if (
        hashlib.sha256(raw).hexdigest() != protocol["baseline_sha256"]
        and hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        != reproduction["baseline_sha256_lf"]
    ):
        raise ValueError("baseline snapshot changed")
    baseline = json.loads(raw)
    if baseline["requested_model_tag"] != protocol["baseline_model"]:
        raise ValueError("unexpected baseline model")
    expected = baseline["provenance"]["sha256_raw_bytes"]
    expected_lf = reproduction["baseline_source_sha256_lf"]
    if set(expected_lf) != set(expected) or not set(expected).issubset(SOURCE_FILES):
        raise ValueError("baseline source fingerprint scope changed")
    if any(
        hashes["raw"].get(name) != digest
        and hashes["lf"].get(name) != expected_lf[name]
        for name, digest in expected.items()
    ):
        raise ValueError("baseline source drift; comparable execution refused")
    if protocol["companion_model"] != MODEL or protocol["repetitions"] != 3:
        raise ValueError("unexpected companion protocol")
    return baseline


def run_companion(
    *,
    service: SLMService | None = None,
    on_checkpoint: Callable[[dict], None] | None = None,
) -> dict:
    protocol = json.loads(allowed_path(PROTOCOL).read_text(encoding="utf-8"))
    before = source_fingerprints()
    baseline = validate_baseline(protocol, before)
    if service is not None and service.client.config.model_tag != MODEL:
        raise ValueError("injected service must use the companion model")

    def annotate(result):
        result["protocol_version"] = protocol["protocol_version"]
        result["companion_protocol"] = copy.deepcopy(protocol)
        result["baseline_comparison"] = {
            "path": BASELINE,
            "sha256": protocol["baseline_sha256"],
            "baseline_source_count": len(baseline["provenance"]["sha256_raw_bytes"]),
            "all_baseline_sources_match": True,
            "source_match_policy": "original raw bytes or verified CRLF-to-LF equivalent",
            "raw_baseline_sources_matched": sum(
                before["raw"][name] == digest
                for name, digest in baseline["provenance"]["sha256_raw_bytes"].items()
            ),
            "reproduction_revision": protocol["reproduction_metadata"][
                "runner_revision"
            ],
            "timing_comparability": "different days; no controlled latency ranking",
        }
        return result

    def checkpoint(result):
        if on_checkpoint is not None:
            on_checkpoint(annotate(result))

    # Replace both imported aliases, including the alignment call in each block.
    # No product implementation, transport, safety gate or expected result changes.
    with (
        patch.object(quality, "provenance", provenance),
        patch.object(alignment, "provenance", provenance),
    ):
        result = quality.run_quality_comparison(
            model_tag=MODEL, service=service, on_checkpoint=checkpoint
        )
    annotate(result)
    after = source_fingerprints()
    result["source_verification"] = {
        "before": before["raw"],
        "after": after["raw"],
        "before_crlf_to_lf": before["lf"],
        "after_crlf_to_lf": after["lf"],
        "all_sources_unchanged": before == after,
    }
    if before != after:
        result["status"] = "source_drift_invalid_human_review_pending"
    if on_checkpoint is not None:
        on_checkpoint(result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    output = parser.parse_args(argv).out
    history = ROOT / "benchmarks/history"
    # Reject other destinations lexically before inspecting any filesystem path.
    if output.parent.absolute() != history.absolute() or output.suffix != ".json":
        parser.error(
            "output must be a new JSON in the existing benchmarks/history directory"
        )
    if history.is_symlink() or history.resolve() != history.absolute():
        parser.error("the history directory must not redirect")
    if output.is_symlink() or output.exists():
        parser.error("previous evidence must never be overwritten")
    with output.open("x", encoding="utf-8") as handle:

        def checkpoint(result):
            handle.seek(0)
            json.dump(result, handle, indent=2)
            handle.write("\n")
            handle.truncate()
            handle.flush()
            print(
                json.dumps(
                    {
                        "records_saved": len(result["records"]),
                        "status": result["status"],
                    }
                ),
                flush=True,
            )

        result = run_companion(on_checkpoint=checkpoint)
    return int(result["status"] != "development_checks_passed_human_review_pending")


if __name__ == "__main__":
    raise SystemExit(main())
