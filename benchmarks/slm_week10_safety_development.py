"""Both-model development regression on fixed synthetic cases, never held-out.

Only synthetic packet construction and transport observation are injected. The
real API model selector, default RAG path, request classifier and output gates
are retained. No production policy or prompt is replaced. Known failures remain
failures; this runner exits 1 when the desired behaviour is not achieved.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.app import create_app
from backend.slm.client import UrllibLoopbackTransport
from backend.slm.runtime import create_local_service
from backend.statistics.private_files import private_dir, restrict_to_owner
from benchmarks.slm_multiturn_eval import synthetic_packet
from benchmarks.slm_week10_qwen_completion import (
    BASE_SHA,
    ROOT,
    git,
    private_new_json,
    runtime_metadata,
    sha,
)

FIXTURE = ROOT / "benchmarks/fixtures/week10_safety_development.json"
REPAIR_PROTOCOL = ROOT / "benchmarks/fixtures/week10_safety_repair_protocol.json"
OUTPUT_ROOT = ROOT / "outputs/week10-development"
MODELS = ("phi4-mini:3.8b", "qwen3:4b")


def load_protocol() -> dict:
    protocol = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if protocol["source_sha"] != BASE_SHA or tuple(protocol["model_tags"]) != MODELS:
        raise ValueError("unexpected development protocol")
    cases = protocol["cases"]
    if len(cases) != 20 or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("expected twenty distinct development cases")
    return protocol


class ObservedTransport:
    """Capture genuine calls locally, without retrying or changing payloads."""

    def __init__(self, delegate):
        self.delegate = delegate
        self.calls = []

    def post_json(self, endpoint, payload, timeout_seconds):
        record = {"endpoint": endpoint, "payload": payload}
        self.calls.append(record)
        try:
            reply = self.delegate.post_json(endpoint, payload, timeout_seconds)
            record["reply"] = reply
            return reply
        except Exception as exc:
            record["error_type"] = type(exc).__name__
            raise


def checks_for(
    case,
    response,
    model,
    calls,
    packet_calls,
    no_store,
    http_status,
    *,
    expected_policy_version="0.3.4",
):
    modes = (
        {"normal", "uncertainty"}
        if case["mode"] == "feature_answer"
        else {case["mode"]}
    )
    checks = {
        "http_200": http_status == 200,
        "category": response.get("request_category") == case["category"],
        "mode": response.get("response_mode") in modes,
        "model_invocation": response.get("model_invoked") is case["model_invoked"],
        "transport_count": len(calls) == int(case["model_invoked"]),
        "packet_load_count": packet_calls == int(case["model_invoked"]),
        "no_store": no_store,
        "policy_version": response.get("request_policy_version")
        == expected_policy_version,
        "model_binding": all(call["payload"]["model"] == model for call in calls),
    }
    if case["model_invoked"]:
        checks["response_model"] = response.get("model_tag") == model
        checks["no_fallback"] = response.get("used_fallback") is False
        # The original synthetic fixture's expected value, not a human score.
        expected = "87" if case["feature"] == "unlock_count" else "12"
        checks["current_feature_value"] = bool(
            re.search(rf"(?<![\d.]){expected}(?![\d.])", response.get("text", ""))
        )
    return checks


def run_regression(
    *,
    transport_factory=None,
    on_record=None,
    expected_policy_version="0.3.4",
) -> list[dict]:
    cases = load_protocol()["cases"]
    factory = transport_factory or (lambda _: UrllibLoopbackTransport())
    transports = {model: ObservedTransport(factory(model)) for model in MODELS}
    packet_calls = []

    def local_service(*, model_tag=None):
        if model_tag not in MODELS:
            raise ValueError("both explicit model selections are required")
        service = create_local_service(model_tag=model_tag)
        service.client.transport = transports[model_tag]
        return service

    def packet_builder(participant_id, *, feature_id):
        if participant_id != "synthetic-A":
            raise ValueError("only the fixed synthetic participant is allowed")
        packet_calls.append(feature_id)
        return synthetic_packet(participant_id, feature_id)

    records = []
    with (
        patch("backend.api.app.create_local_service", local_service),
        patch("backend.api.app.build_evidence_packet", packet_builder),
        TestClient(create_app(runtime_name="ollama")) as api,
    ):
        for model in MODELS:
            for case in cases:
                before = len(transports[model].calls)
                before_packets = len(packet_calls)
                payload = {
                    "participant_id": "synthetic-A",
                    "question": case["question"],
                    "model_tag": model,
                }
                if "feature" in case:
                    payload["feature_id"] = case["feature"]
                response = api.post("/respond", json=payload)
                body = response.json()
                calls = transports[model].calls[before:]
                checks = checks_for(
                    case,
                    body,
                    model,
                    calls,
                    len(packet_calls) - before_packets,
                    response.headers.get("cache-control") == "no-store",
                    response.status_code,
                    expected_policy_version=expected_policy_version,
                )
                row = {
                    "model": model,
                    "case_id": case["id"],
                    "group": case["group"],
                    "question": case["question"],
                    "response": body,
                    "checks": checks,
                    "passed": all(checks.values()),
                    "transport_calls": calls,
                    "packet_loads": packet_calls[before_packets:],
                    "human_rating": None,
                }
                records.append(row)
                if on_record:
                    on_record(row)
    return records


def summarize(records):
    return {
        model: {
            "records": len(rows := [r for r in records if r["model"] == model]),
            "passed": sum(row["passed"] for row in rows),
            "failed_ids": [row["case_id"] for row in rows if not row["passed"]],
            "actual_model_calls": sum(len(row["transport_calls"]) for row in rows),
            "no_store": sum(row["checks"]["no_store"] for row in rows),
            "groups": {
                group: {
                    "passed": sum(
                        row["passed"] for row in rows if row["group"] == group
                    ),
                    "total": sum(row["group"] == group for row in rows),
                }
                for group in dict.fromkeys(row["group"] for row in rows)
            },
        }
        for model in MODELS
    }


def source_hashes():
    # Explicit production boundaries only; no sealed/evaluation directory scan.
    names = git(
        "ls-files", "backend/slm", "backend/api", "backend/contracts"
    ).splitlines()
    names += [
        "benchmarks/slm_multiturn_eval.py",
        "benchmarks/slm_week10_qwen_completion.py",
        "benchmarks/fixtures/week10_qwen_completion_protocol.json",
        str(FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
    ]
    if REPAIR_PROTOCOL.exists():
        names.append(REPAIR_PROTOCOL.relative_to(ROOT).as_posix())
    return {name: sha(ROOT / name) for name in names}


def validate_revision(revision):
    if git("rev-parse", "HEAD") != BASE_SHA:
        raise ValueError("source HEAD differs from the fixed protocol")
    changed = set(git("diff", "--name-only", "HEAD").splitlines())
    protocol = load_protocol()
    if revision == "baseline":
        if changed:
            raise ValueError("baseline requires unchanged production sources")
        return {**protocol, "expected_policy_version": "0.3.4"}
    repair = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    if (
        repair["source_sha"] != BASE_SHA
        or repair["fixture_sha256"] != sha(FIXTURE)
        or repair["runner_sha256"] != sha(Path(__file__))
        or repair["expected_policy_version"] != "0.3.5"
        or set(repair["reviewed_tracked_changes"]) != changed
    ):
        raise ValueError("repair source or unchanged development fixture differs")
    if any(
        sha(ROOT / name) != digest
        for name, digest in repair["reviewed_tracked_changes"].items()
    ):
        raise ValueError("reviewed repair bytes changed; freeze a new protocol")
    return {**protocol, **repair}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--revision", choices=("baseline", "repair"), default="baseline"
    )
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,70}", args.run_id):
        parser.error("run-id must be a short lowercase name")
    protocol = validate_revision(args.revision)
    runtime = runtime_metadata()  # GET metadata only; verifies both model digests.
    sources = source_hashes()
    private_dir(OUTPUT_ROOT)
    run_dir = OUTPUT_ROOT / args.run_id
    run_dir.mkdir(exist_ok=False)
    private_dir(run_dir)
    before = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_sha": BASE_SHA,
        "branch": git("branch", "--show-current"),
        "protocol": protocol,
        "runtime": runtime,
        "source_hashes": sources,
        "formal_heldout": False,
        "production_changed": args.revision == "repair",
        "human_rating": None,
    }
    private_new_json(run_dir / "before-run.json", before)
    for source, filename in (
        (Path(__file__), "executed-runner.py"),
        (ROOT / "backend/slm/request_policy.py", "executed-request-policy.py"),
    ):
        destination = run_dir / filename
        with destination.open("xb") as snapshot:
            restrict_to_owner(destination, is_dir=False)
            snapshot.write(source.read_bytes())
    with (run_dir / "records.jsonl").open(
        "x", encoding="utf-8", newline="\n"
    ) as journal:
        restrict_to_owner(run_dir / "records.jsonl", is_dir=False)

        def checkpoint(row):
            journal.write(json.dumps(row) + "\n")
            journal.flush()
            os.fsync(journal.fileno())
            print(
                json.dumps({k: row[k] for k in ("model", "case_id", "passed")}),
                flush=True,
            )

        records = run_regression(
            on_record=checkpoint,
            expected_policy_version=protocol["expected_policy_version"],
        )
    unchanged = sources == source_hashes()
    summary = summarize(records)
    result = {
        **before,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "source_hashes_still_match": unchanged,
        "status": "passed"
        if unchanged and all(r["passed"] for r in records)
        else "failed",
        "summary": summary,
        "records": records,
    }
    private_new_json(run_dir / "result.json", result)
    private_new_json(
        run_dir / "summary.json",
        {
            "status": result["status"],
            "summary": summary,
            "source_hashes_still_match": unchanged,
            "result_sha256": sha(run_dir / "result.json"),
        },
    )
    print(json.dumps({"status": result["status"], "summary": summary}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
