"""Read-only Week 10 preparation; no question input or generation command.

Writes a fresh private audit and blank planning records. A successful audit
never authorises formal execution. Existing caches/results are only read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs/week10-acceptance-preparation"
BASE = "90930308c00cf5edbc565bcd6bac7d7f44590372"
MODELS = {
    "phi4-mini:3.8b": "78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753",
    "qwen3:4b": "359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7",
}
PENDING = [
    "Reviewed, immutable final build and its successful required checks",
    "Fresh independent 24-question set, author/provenance and reviewer recorded",
    "Approved dual-model protocol, execution harness and local context frozen",
    "Exact-byte question hash published before execution, with separate push permission",
    "Applicable privacy review for this Windows build and both model selections",
    "Explicit permission to start the formal run after all prerequisites are verified",
]


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


class NoRedirects(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("metadata redirects are forbidden")


def get_runtime_metadata(path: str) -> dict:
    require(path in {"/api/version", "/api/tags"}, "metadata GET only")
    opener = request.build_opener(request.ProxyHandler({}), NoRedirects())
    req = request.Request("http://127.0.0.1:11434" + path, method="GET")
    with opener.open(req, timeout=10) as response:
        return json.load(response)


def source_check() -> dict:
    protocol_path = ROOT / "benchmarks/fixtures/week10_safety_repair_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    require(git("rev-parse", "HEAD") == BASE, "candidate base changed")
    expected = protocol["reviewed_tracked_changes"]
    changed = set(git("diff", "HEAD", "--name-only").splitlines())
    require(changed == set(expected), "tracked change scope differs from repair")
    require(not git("diff", "--cached", "--name-only"), "staged changes need review")
    for path, digest in expected.items():
        require(sha(ROOT / path) == digest, "repair source fingerprint differs")
    require(
        sha(ROOT / "benchmarks/fixtures/week10_safety_development.json")
        == protocol["fixture_sha256"],
        "development fixture changed",
    )
    require(
        sha(ROOT / "benchmarks/slm_week10_safety_development.py")
        == protocol["runner_sha256"],
        "development runner changed",
    )
    paths = git(
        "ls-files",
        "--",
        "backend",
        "frontend/src",
        "frontend/package*.json",
        "requirements*.txt",
        "constraints*.txt",
    ).splitlines()
    # The selected trees contain application sources, not the held-out test set.
    return {
        "branch": git("branch", "--show-current"),
        "base_sha": BASE,
        "working_tree_uncommitted": True,
        "repair_protocol_sha256": sha(protocol_path),
        "tracked_changes": sorted(changed),
        "source_hashes": {p: sha(ROOT / p) for p in paths},
    }


def runtime_check() -> dict:
    version = get_runtime_metadata("/api/version")["version"]
    tags = get_runtime_metadata("/api/tags")["models"]
    installed = {m["name"]: m["digest"] for m in tags}
    require(version == "0.33.2", "runtime version differs from development candidate")
    require(
        all(installed.get(t) == d for t, d in MODELS.items()), "model digest mismatch"
    )
    return {"ollama_version": version, "installed_model_digests": MODELS}


def api_check() -> dict:
    from fastapi.testclient import TestClient

    from backend.api.app import create_app
    from backend.slm.runtime import configured_timeout_seconds

    with TestClient(create_app(runtime_name="ollama")) as client:
        health = client.get("/health")
        catalog = client.get("/models")
    require(health.status_code == catalog.status_code == 200, "metadata route failure")
    models = catalog.json()
    require(models["runtime"] == "ollama", "incorrect runtime")
    require(models["selection_enabled"] is True, "model selection disabled")
    require(
        set(MODELS) <= set(models["available_model_tags"]), "missing model selection"
    )
    return {
        "catalog": models,
        "timeout_seconds": configured_timeout_seconds(),
        "path": "in-process metadata GETs only; no live-server or generation claim",
    }


def cache_check() -> dict:
    from backend.statistics import bootstrap, bootstrap_cache, tier1_runner
    from backend.statistics.feature_specs import TIER1_FEATURE_SPECS
    from backend.statistics.mixed_effects_model import build_model_frame
    from backend.statistics.private_files import is_owner_only

    require(
        bootstrap.resolve_engine("auto") == bootstrap.ENGINE_PYTHON,
        "default cache engine differs",
    )
    sensing, ema = tier1_runner.load_sensing_and_ema()
    records = []
    for feature, spec in sorted(TIER1_FEATURE_SPECS.items()):
        directory = bootstrap_cache.cache_dir(feature, engine=bootstrap.ENGINE_PYTHON)
        files = [
            directory / name
            for name in (
                bootstrap_cache.RAW_CHECKPOINT_NAME,
                bootstrap_cache.RAW_FINGERPRINT_NAME,
                bootstrap_cache.AGGREGATED_NAME,
            )
        ]
        # Check first so the existing cache loader has no ACL repair to perform.
        for path in (bootstrap_cache.CACHE_ROOT, directory.parent, directory, *files):
            require(
                is_owner_only(path, is_dir=path.is_dir()),
                "cache ACL needs owner review",
            )
        before = {p.name: sha(p) for p in files}
        frame = build_model_frame(spec.clean_fn(sensing), ema, spec)
        cache = bootstrap_cache.load_aggregated_cache(
            spec, frame, engine=bootstrap.ENGINE_PYTHON
        )
        require(cache is not None and cache.n_iterations == 500, "B=500 cache missing")
        require(
            set(cache.failure_summary) == {"parametric", "cluster"}, "method missing"
        )
        for summary in cache.failure_summary.values():
            require(
                summary["n_total"] == summary["n_usable"] == 500, "incomplete cache"
            )
            require(
                summary["n_error"] == summary["n_fallback_to_intercept_only"] == 0,
                "cache contains failed/fallback replicates",
            )
        with files[0].open(encoding="utf-8") as handle:
            count = sum(1 for _ in handle)
        require(count == 1000, "raw record count mismatch")
        require(before == {p.name: sha(p) for p in files}, "cache content changed")
        records.append(
            {
                "feature": feature,
                "iterations_per_method": 500,
                "raw_records": count,
                "family_size": len(cache.intersection),
                "fingerprint_sha256": cache.fingerprint_sha256,
                "file_hashes": before,
                "owner_only": True,
            }
        )
    return {
        "features": records,
        "environment": bootstrap_cache.environment_versions(bootstrap.ENGINE_PYTHON),
        "rebuilt": False,
    }


def evidence_check() -> dict:
    from backend.statistics.private_files import is_owner_only

    checks = {
        "safety-development-20261018/result.json": "6bac22d66a13aa6842390043a3ede3f6d07e4ae30a553084c1bee7fd788d2721",
        "safety-repair-20261018/result.json": "b5699c7a290080a2e50d6da22f34fbeb3b0d600b82fbb3bcc6e5ca331f870901",
    }
    for name, digest in checks.items():
        path = ROOT / "outputs/week10-development" / name
        require(is_owner_only(path, is_dir=False), "result ACL differs")
        require(sha(path) == digest, "preserved result differs")
    return {"preserved_result_hashes": checks, "results_rerun": False}


def blank_records() -> list[dict]:
    return [
        {
            "slot": slot,
            "selected_model_tag": model,
            "case_id": None,
            "category": None,
            "attempted_at_utc": None,
            "http_status": None,
            "model_invoked": None,
            "response_artifact": None,
            "critical_safety_review": None,
            "route_review": None,
            "false_refusal_review": None,
            "not_covered_reason": None,
            "human_reviewer": None,
            "human_rating": None,
        }
        for model in MODELS
        for slot in range(1, 25)
    ]


def collect() -> dict:
    checks = {}
    for name, check in (
        ("source", source_check),
        ("runtime", runtime_check),
        ("api", api_check),
        ("cache", cache_check),
        ("preserved_evidence", evidence_check),
    ):
        try:
            checks[name] = {"passed": True, "details": check()}
        except Exception as exc:  # noqa: BLE001 - do not expose participant-bearing exceptions
            checks[name] = {"passed": False, "error_type": type(exc).__name__}
    return {
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "technical_preparation_passed": all(v["passed"] for v in checks.values()),
        "ready_for_formal_run": False,
        "pending_human_decisions": PENDING,
        "formal_questions_read": 0,
        "respond_requests": 0,
        "generation_requests": 0,
        "human_ratings": None,
        "checks": checks,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-name", default=datetime.now(UTC).strftime("audit-%Y%m%dT%H%M%SZ")
    )
    args = parser.parse_args(argv)
    require(
        bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.output_name)),
        "output name must be a single local directory name",
    )
    from backend.statistics.private_files import private_dir, restrict_to_owner

    private_dir(OUTPUT_ROOT)
    directory = OUTPUT_ROOT / args.output_name
    directory.mkdir(exist_ok=False)
    private_dir(directory)
    require(
        subprocess.run(
            ["git", "check-ignore", "-q", str(directory)], cwd=ROOT, check=False
        ).returncode
        == 0,
        "output directory must be Git-ignored",
    )
    audit = collect()
    plan = {
        "status": "DRAFT_NOT_APPROVED_NOT_RUN",
        "formal_run_authorized": False,
        "model_tags": list(MODELS),
        "model_digests": MODELS,
        "questions_per_model": 24,
        "planned_application_requests": 48,
        "formal_build_commit": None,
        "protocol_approval_reference": None,
        "question_author": None,
        "author_exposure_declaration": None,
        "ai_assistance_declaration": None,
        "operator": None,
        "reviewer": None,
        "question_file_local_path": None,
        "question_file_sha256": None,
        "hash_publication_reference": None,
        "hash_publication_at_utc": None,
        "execution_harness_sha256": None,
        "local_context_manifest_sha256": None,
        "privacy_scope_review_reference": None,
        "formal_start_permission": None,
    }
    for name, value in (
        ("readiness.json", audit),
        ("freeze-plan-DRAFT.json", plan),
        ("review-records-BLANK.json", blank_records()),
    ):
        with (directory / name).open("x", encoding="utf-8", newline="\n") as handle:
            restrict_to_owner(directory / name, is_dir=False)
            json.dump(value, handle, indent=2)
            handle.write("\n")
    print(
        json.dumps(
            {
                "output": str(directory.relative_to(ROOT)),
                "technical_preparation_passed": audit["technical_preparation_passed"],
                "ready_for_formal_run": False,
                "checks": {k: v["passed"] for k, v in audit["checks"].items()},
                "formal_or_generation_requests": 0,
            }
        )
    )
    return 0 if audit["technical_preparation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
