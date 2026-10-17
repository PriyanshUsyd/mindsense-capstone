"""Append-only dual-model acceptance recording core, with no live-run CLI.

The CLI only inspects plan metadata. A separately reviewed execution adapter
must provide the actual application transport and environment verification.
Tests use toy questions and fake transport, never the sealed candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from backend.statistics.private_files import private_dir, restrict_to_owner

MODELS = ("phi4-mini:3.8b", "qwen3:4b")
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "outputs/week10-formal-acceptance"
COUNTS = {
    "crisis": 8,
    "diagnosis": 3,
    "cause": 2,
    "treatment": 2,
    "risk prediction": 2,
    "prompt-injection": 1,
    "role-play": 1,
    "off-topic": 2,
    "in-scope": 3,
}
REFERENCE_FIELDS = (
    "protocol_approval_reference",
    "question_author",
    "author_exposure_declaration",
    "ai_assistance_declaration",
    "operator",
    "reviewer",
    "hash_publication_reference",
    "privacy_scope_review_reference",
    "formal_start_permission",
)
HASH_FIELDS = (
    "question_file_sha256",
    "execution_harness_sha256",
    "execution_adapter_sha256",
    "local_context_manifest_sha256",
)
INFRASTRUCTURE_REASONS = {
    "model_timeout",
    "model_unavailable",
    "model_generation_failed",
    "evidence_source_unavailable",
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat()


def plan_problems(plan: dict) -> list[str]:
    """Check declarations, not the truth/authenticity of approvals themselves."""
    problems = []
    if plan.get("formal_run_authorized") is not True:
        problems.append("formal_run_authorized")
    if plan.get("model_tags") != list(MODELS):
        problems.append("model_tags_and_order")
    if (
        not isinstance(plan.get("expected_policy_version"), str)
        or not plan["expected_policy_version"]
    ):
        problems.append("expected_policy_version")
    if not re.fullmatch(r"[0-9a-f]{40}", str(plan.get("formal_build_commit", ""))):
        problems.append("formal_build_commit")
    for field in HASH_FIELDS:
        if not re.fullmatch(r"[0-9a-f]{64}", str(plan.get(field, ""))):
            problems.append(field)
    for field in REFERENCE_FIELDS:
        value = plan.get(field)
        if (
            not isinstance(value, str)
            or not value.strip()
            or value.strip().upper()
            in {
                "PENDING",
                "UNKNOWN",
                "DRAFT",
                "TBD",
            }
        ):
            problems.append(field)
    try:
        published = datetime.fromisoformat(plan["hash_publication_at_utc"])
        if published.tzinfo is None or published >= datetime.now(UTC):
            raise ValueError("publication must predate execution")
    except (KeyError, AttributeError, TypeError, ValueError):
        problems.append("prior_hash_publication_time")
    return problems


def load_cases(path: Path, expected_hash: str) -> list[dict]:
    raw = path.read_bytes()
    if sha_bytes(raw) != expected_hash:
        raise ValueError("question_hash_mismatch")
    cases = json.loads(raw.decode("utf-8"))
    if not isinstance(cases, list) or len(cases) != 24:
        raise ValueError("question_count")
    for case in cases:
        if not isinstance(case, dict) or not all(
            isinstance(case.get(k), str) and case[k].strip()
            for k in ("id", "category", "prompt", "expected")
        ):
            raise ValueError("question_fields")
        fields = {"id", "category", "prompt", "expected"}
        if case["category"] == "crisis":
            fields.add("subtype")
        if set(case) != fields or len(case["prompt"]) > 2000:
            raise ValueError("question_schema")
    if len({c["id"] for c in cases}) != 24:
        raise ValueError("question_ids")
    if Counter(c["category"] for c in cases) != COUNTS:
        raise ValueError("question_categories")
    if Counter(c["subtype"] for c in cases if c["category"] == "crisis") != {
        "direct": 4,
        "indirect": 4,
    }:
        raise ValueError("crisis_subtypes")
    if len({" ".join(c["prompt"].casefold().split()) for c in cases}) != 24:
        raise ValueError("duplicate_questions")
    return cases


def new_private_file(path: Path):
    handle = path.open("x", encoding="utf-8", newline="\n")
    try:
        restrict_to_owner(path, is_dir=False)
    except BaseException:
        handle.close()
        raise
    return handle


def append_event(handle, event: dict) -> None:
    handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


def response_problems(reply: dict, model: str, policy_version: str) -> list[str]:
    problems = []
    if reply.get("binding_issues"):
        problems.append("adapter_response_binding")
    if reply.get("status_code") != 200:
        problems.append("http_status")
    headers = {k.lower(): v for k, v in reply.get("headers", {}).items()}
    cache_directives = {
        part.strip().lower() for part in headers.get("cache-control", "").split(",")
    }
    if "no-store" not in cache_directives:
        problems.append("no_store")
    body = reply.get("body")
    if not isinstance(body, dict):
        return [*problems, "response_json"]
    if body.get("request_policy_version") != policy_version:
        problems.append("policy_version")
    if type(body.get("model_invoked")) is not bool:
        problems.append("model_invoked_type")
    if body.get("model_invoked") is True and body.get("model_tag") != model:
        problems.append("invoked_model_tag")
    if body.get("model_tag") not in (None, model):
        problems.append("returned_model_tag")
    if body.get("rejection_reason") in INFRASTRUCTURE_REASONS:
        problems.append("infrastructure_failure")
    # Category/wording/quality require review; no safety pass is inferred here.
    return problems


def record_once(
    plan: dict,
    question_path: Path,
    *,
    post: Callable[[dict], dict],
    verify_binding: Callable[[], None],
) -> dict:
    """One record per pair; consumes the set locally even on an interrupted run.

    verify_binding must raise on changed source/runtime/data/adapter bindings.
    This core does not verify approval authenticity or start a backend. The
    caller must independently establish real permission and reviewed bindings.
    """
    problems = plan_problems(plan)
    if problems:
        raise ValueError("plan_incomplete: " + ", ".join(problems))
    if plan["execution_harness_sha256"] != sha_bytes(Path(__file__).read_bytes()):
        raise ValueError("recorder_hash_mismatch")
    verify_binding()
    cases = load_cases(question_path, plan["question_file_sha256"])
    private_dir(OUTPUT_ROOT)
    run_dir = OUTPUT_ROOT / plan["question_file_sha256"]
    # Canonical root must be shared by all runs. No --resume, overwrite or retry.
    run_dir.mkdir(exist_ok=False)
    private_dir(run_dir)
    with new_private_file(run_dir / "before-run.json") as handle:
        append_event(
            handle,
            {
                "created_at_utc": now(),
                "plan": plan,
                "question_file_sha256": plan["question_file_sha256"],
            },
        )
    result = {
        "status": "recording",
        "planned_requests": 48,
        "attempted": {m: 0 for m in MODELS},
        "completed": {m: 0 for m in MODELS},
        "model_invocations": {m: 0 for m in MODELS},
        "human_ratings": None,
        "safety_decision": None,
    }
    with new_private_file(run_dir / "journal.jsonl") as journal:
        try:
            for model in MODELS:
                for case in cases:
                    verify_binding()
                    if (
                        sha_bytes(question_path.read_bytes())
                        != plan["question_file_sha256"]
                    ):
                        raise ValueError("question_changed_during_run")
                    key = {"case_id": case["id"], "selected_model_tag": model}
                    payload = {
                        "participant_id": "local-demo",
                        "question": case["prompt"],
                        "model_tag": model,
                        "variant": "rag",
                    }
                    # Persist intent BEFORE sending. A timeout may still be an invocation.
                    append_event(
                        journal,
                        {
                            "event": "attempt_started",
                            "at_utc": now(),
                            **key,
                            "payload": payload,
                        },
                    )
                    result["attempted"][model] += 1
                    try:
                        reply = post(payload)
                    except Exception as exc:  # Retain ambiguous attempt; no retry.
                        append_event(
                            journal,
                            {
                                "event": "transport_error",
                                "at_utc": now(),
                                **key,
                                "error_type": type(exc).__name__,
                                "server_execution_unknown": True,
                            },
                        )
                        raise
                    append_event(
                        journal,
                        {
                            "event": "response_received",
                            "at_utc": now(),
                            **key,
                            "reply": reply,
                            "human_rating": None,
                        },
                    )
                    result["completed"][model] += 1
                    if (
                        isinstance(reply.get("body"), dict)
                        and reply["body"].get("model_invoked") is True
                    ):
                        result["model_invocations"][model] += 1
                    issues = response_problems(
                        reply, model, plan["expected_policy_version"]
                    )
                    if issues:
                        append_event(
                            journal,
                            {"event": "recording_stopped", **key, "reasons": issues},
                        )
                        raise ValueError("response_integrity_failure")
            verify_binding()
            if sha_bytes(question_path.read_bytes()) != plan["question_file_sha256"]:
                raise ValueError("question_changed_during_run")
            result["status"] = "recorded_pending_human_review"
        except BaseException as exc:  # noqa: BLE001 - preserve interruptions, never resume
            result["status"] = "incomplete_retained_no_retry"
            result["error_type"] = type(exc).__name__
            append_event(
                journal,
                {
                    "event": "run_interrupted",
                    "at_utc": now(),
                    "error_type": type(exc).__name__,
                },
            )
        finally:
            with new_private_file(run_dir / "recording-summary.json") as handle:
                append_event(handle, result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-plan", type=Path, required=True)
    args = parser.parse_args(argv)
    plan = json.loads(args.check_plan.read_text(encoding="utf-8"))
    problems = plan_problems(plan)
    print(
        json.dumps(
            {
                "plan_metadata_only": True,
                "missing_or_invalid": problems,
                "formal_execution_performed": False,
                "approval_authenticity_checked": False,
                "question_file_read": False,
            }
        )
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
