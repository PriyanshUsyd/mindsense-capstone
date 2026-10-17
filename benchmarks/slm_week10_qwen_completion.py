"""Fill missing Qwen development evidence; never execute held-out questions.

Reuses the existing public Z/F and synthetic multi-turn methods unchanged.
All responses and partial attempts stay under ignored outputs/week10-development.
The protocol is recorded before generation, and existing runs are never resumed
or overwritten. This is not a paired rerun of historical Phi evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

from backend.slm.runtime import create_local_service
from backend.statistics.private_files import private_dir, restrict_to_owner
from benchmarks import slm_multiturn_eval as mt
from benchmarks import slm_prompting_comparison as zf

ROOT = Path(__file__).resolve().parents[1]
MODEL = "qwen3:4b"
BASE_SHA = "90930308c00cf5edbc565bcd6bac7d7f44590372"
PROTOCOL_PATH = ROOT / "benchmarks/fixtures/week10_qwen_completion_protocol.json"
OUTPUT_ROOT = ROOT / "outputs/week10-development"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def read_protocol() -> dict:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["model_tag"] != MODEL or protocol["source_sha"] != BASE_SHA:
        raise ValueError("unexpected pinned development protocol")
    return protocol


def qwen_conditions(cases):
    # Validate every historical condition with its original Phi control first.
    # Only the recorded model factor changes for this new Qwen experiment.
    with patch.object(zf, "MODEL", "phi4-mini:3.8b"):
        original, prompts = ORIGINAL_CONDITIONS(cases)
    controls = dict(original)
    controls["model_tag"] = MODEL
    controls["protocol_version"] = read_protocol()["prompting_protocol_version"]
    return controls, prompts


ORIGINAL_CONDITIONS = zf.load_conditions


def runtime_metadata() -> dict:
    def get(path):
        with urlopen("http://127.0.0.1:11434" + path, timeout=10) as response:
            return json.load(response)

    protocol = read_protocol()
    installed = {m["name"]: m for m in get("/api/tags")["models"]}
    for tag, expected in protocol["installed_model_digests"].items():
        if installed.get(tag, {}).get("digest") != expected:
            raise ValueError(f"installed digest differs for {tag}")
    return {
        "ollama_version": get("/api/version")["version"],
        "installed_model_digests": protocol["installed_model_digests"],
        "models_loaded_before_run": [m["name"] for m in get("/api/ps")["models"]],
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }


def run_prompting(*, transport_factory=None, on_checkpoint=None) -> dict:
    with (
        patch.object(zf, "MODEL", MODEL),
        patch.object(zf, "load_conditions", qwen_conditions),
        patch.object(zf, "runtime_metadata", runtime_metadata),
    ):
        result = zf.run_comparison(
            transport_factory=transport_factory, on_checkpoint=on_checkpoint
        )
    result["week10_extension"] = {
        "protocol": read_protocol(),
        "protocol_sha256": sha(PROTOCOL_PATH),
        "adapter_sha256": sha(Path(__file__)),
        "adaptation": "Original condition validation retained; model and experiment ID changed in memory only.",
        "historical_phi_is_paired_comparator": False,
    }
    return result


def private_new_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        restrict_to_owner(path, is_dir=False)
        json.dump(value, handle, indent=2)
        handle.write("\n")


def summarize_result(kind: str, result: dict) -> dict:
    if kind == "prompting":
        return {k: result[k] for k in ("status", "summaries", "paired_comparison")}
    return {
        "summary": result["summary"],
        "model_calls": sum(r["model_invoked"] is True for r in result["records"]),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("preflight", "prompting", "multiturn"))
    args = parser.parse_args(argv)
    protocol = read_protocol()
    if git("rev-parse", "HEAD") != BASE_SHA:
        raise ValueError("source HEAD differs; review a new protocol before any run")
    if git("status", "--porcelain", "--", *zf.SOURCE_FILES, *mt.SOURCE_FILES):
        raise ValueError("existing application or benchmark sources were modified")
    runtime = runtime_metadata()
    # Structural checks only; this function makes no generation request.
    cases = zf.load_public_cases()
    qwen_conditions(cases)
    provenance = {
        "source_sha": BASE_SHA,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "protocol_sha256": sha(PROTOCOL_PATH),
        "adapter_sha256": sha(Path(__file__)),
        "original_source_hashes": zf.source_hashes(),
        "runtime": runtime,
        "protocol": protocol,
        "formal_heldout": False,
        "human_ratings": None,
    }
    if args.kind == "preflight":
        print(
            json.dumps(
                {
                    "preflight": "passed",
                    "runtime": runtime,
                    "source_sha": BASE_SHA,
                    "public_prompting_cases": len(cases),
                    "multiturn_scenarios": len(mt.SCENARIOS),
                }
            )
        )
        return 0
    private_dir(OUTPUT_ROOT)
    run_dir = OUTPUT_ROOT / ("qwen-" + args.kind + "-20261018")
    run_dir.mkdir(exist_ok=False)  # No selective resume or accidental rerun.
    private_dir(run_dir)
    private_new_json(run_dir / "before-run.json", provenance)
    journal_path = run_dir / "records.jsonl"
    journal = journal_path.open("x", encoding="utf-8", newline="\n")
    restrict_to_owner(journal_path, is_dir=False)
    try:
        if args.kind == "prompting":
            saved = 0

            def checkpoint(result):
                nonlocal saved
                for row in result["records"][saved:]:
                    journal.write(json.dumps(row) + "\n")
                saved = len(result["records"])
                journal.flush()
                os.fsync(journal.fileno())
                print(
                    json.dumps(
                        {
                            "kind": args.kind,
                            "records_saved": saved,
                            "status": result["status"],
                        }
                    ),
                    flush=True,
                )

            result = run_prompting(on_checkpoint=checkpoint)
        else:
            original_turn = mt.run_turn

            def logged_turn(*turn_args, **kwargs):
                row = original_turn(*turn_args, **kwargs)
                journal.write(json.dumps({**row.__dict__, "passed": row.passed}) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
                print(
                    json.dumps(
                        {
                            "kind": args.kind,
                            "scenario": row.scenario_id,
                            "condition": row.condition,
                            "turn": row.turn_index,
                        }
                    ),
                    flush=True,
                )
                return row

            with patch.object(mt, "run_turn", logged_turn):
                records = mt.run_evaluation(create_local_service(model_tag=MODEL))
            result = mt.build_result(records, MODEL)
            result["week10_extension"] = provenance
        if zf.source_hashes() != provenance["original_source_hashes"]:
            raise ValueError(
                "source changed during run; retain journal and report invalid provenance"
            )
        private_new_json(run_dir / "result.json", result)
        summary = summarize_result(args.kind, result)
        private_new_json(run_dir / "summary.json", summary)
        print(json.dumps(summary), flush=True)
    except BaseException as exc:
        private_new_json(
            run_dir / "interrupted.json",
            {
                "error_type": type(exc).__name__,
                "records_retained": True,
                "automatic_retry": False,
            },
        )
        raise
    finally:
        journal.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
