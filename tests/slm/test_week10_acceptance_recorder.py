"""Toy-only journal rehearsals: no formal questions, app, data or model calls."""

import json
from pathlib import Path

import pytest

from benchmarks import slm_week10_acceptance_recorder as recorder


@pytest.fixture
def setup(tmp_path, monkeypatch):
    cases = []
    for category, count in recorder.COUNTS.items():
        for position in range(count):
            number = len(cases) + 1
            row = {
                "id": f"toy-{number:02d}",
                "category": category,
                "prompt": f"Synthetic recorder input slot {number}.",
                "expected": "Fixture metadata only; not a reference response.",
            }
            if category == "crisis":
                row["subtype"] = "direct" if position < 4 else "indirect"
            cases.append(row)
    path = tmp_path / "toy-questions.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    plan = {
        "formal_run_authorized": True,
        "model_tags": list(recorder.MODELS),
        "formal_build_commit": "1" * 40,
        "expected_policy_version": "0.3.5",
        "hash_publication_at_utc": "2020-01-01T00:00:00Z",
        **{
            field: "TEST ONLY: fake transport rehearsal"
            for field in recorder.REFERENCE_FIELDS
        },
        **{field: "a" * 64 for field in recorder.HASH_FIELDS},
        "question_file_sha256": recorder.sha_bytes(path.read_bytes()),
        "execution_harness_sha256": recorder.sha_bytes(
            Path(recorder.__file__).read_bytes()
        ),
    }
    monkeypatch.setattr(recorder, "OUTPUT_ROOT", tmp_path / "records")
    # These files contain only toy material. ACL implementation has separate tests.
    monkeypatch.setattr(
        recorder, "private_dir", lambda p: p.mkdir(parents=True, exist_ok=True)
    )
    monkeypatch.setattr(recorder, "restrict_to_owner", lambda p, **kw: None)
    return plan, path


def reply(payload, *, invoked=False):
    return {
        "status_code": 200,
        "headers": {"Cache-Control": "no-store"},
        "body": {
            "request_policy_version": "0.3.5",
            "model_invoked": invoked,
            "model_tag": payload["model_tag"] if invoked else None,
            "response_mode": "refusal",
            "request_category": "off_topic",
            "text": "Toy recorder response, not an evaluated answer.",
            "rejection_reason": None,
        },
    }


def events(plan):
    path = recorder.OUTPUT_ROOT / plan["question_file_sha256"] / "journal.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize(
    "field",
    [
        "formal_run_authorized",
        "formal_build_commit",
        "execution_adapter_sha256",
        "local_context_manifest_sha256",
        *recorder.REFERENCE_FIELDS,
    ],
)
def test_incomplete_plan_stops_before_question_read_or_transport(setup, field):
    plan, path = setup
    plan[field] = None
    path.unlink()  # If the gated code tries to read it, this test fails.
    with pytest.raises(ValueError, match="plan_incomplete"):
        recorder.record_once(
            plan,
            path,
            post=lambda _: pytest.fail("transport called"),
            verify_binding=lambda: pytest.fail("binding called"),
        )


@pytest.mark.parametrize(
    "timestamp", [None, "2035-01-01T00:00:00Z", "2020-01-01T00:00:00"]
)
def test_publication_must_have_a_prior_timezone_aware_timestamp(setup, timestamp):
    plan, _ = setup
    plan["hash_publication_at_utc"] = timestamp
    assert "prior_hash_publication_time" in recorder.plan_problems(plan)


def test_all_48_pairs_logged_before_dispatch_without_safety_scoring(setup):
    plan, path = setup
    payloads = []

    def post(payload):
        assert events(plan)[-1]["event"] == "attempt_started"
        assert events(plan)[-1]["payload"] == payload
        payloads.append(payload)
        assert "expected" not in payload and "category" not in payload
        return reply(payload, invoked=len(payloads) % 2 == 0)

    result = recorder.record_once(plan, path, post=post, verify_binding=lambda: None)
    assert result["status"] == "recorded_pending_human_review"
    assert (
        result["attempted"] == result["completed"] == {m: 24 for m in recorder.MODELS}
    )
    assert result["model_invocations"] == {m: 12 for m in recorder.MODELS}
    assert [p["model_tag"] for p in payloads] == [recorder.MODELS[0]] * 24 + [
        recorder.MODELS[1]
    ] * 24
    assert payloads[0]["question"] == payloads[24]["question"]
    assert all(
        p["variant"] == "rag" and p["participant_id"] == "local-demo" for p in payloads
    )
    assert result["human_ratings"] is result["safety_decision"] is None
    assert len(events(plan)) == 96
    # Intentionally mismatched toy categories are still unscored, not passed.
    assert all(
        e["human_rating"] is None
        for e in events(plan)
        if e["event"] == "response_received"
    )


def test_timeout_preserves_attempt_and_blocks_second_run(setup):
    plan, path = setup
    calls = []

    def post(payload):
        calls.append(payload)
        raise TimeoutError("private exception detail")

    result = recorder.record_once(plan, path, post=post, verify_binding=lambda: None)
    assert result["status"] == "incomplete_retained_no_retry"
    assert len(calls) == 1
    assert result["attempted"][recorder.MODELS[0]] == 1
    assert sum(result["completed"].values()) == 0
    journal = events(plan)
    assert journal[1]["server_execution_unknown"] is True
    assert "private exception detail" not in str(journal)
    with pytest.raises(FileExistsError):
        recorder.record_once(plan, path, post=post, verify_binding=lambda: None)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "failure",
    [
        "wrong_model",
        "wrong_policy",
        "no_store",
        "false_no_store",
        "http_error",
        "runtime_timeout",
    ],
)
def test_transport_metadata_failures_stop_and_retain_full_reply(setup, failure):
    plan, path = setup
    calls = []

    def post(payload):
        calls.append(payload)
        response = reply(payload, invoked=True)
        if failure == "wrong_model":
            response["body"]["model_tag"] = recorder.MODELS[1]
        elif failure == "wrong_policy":
            response["body"]["request_policy_version"] = "different"
        elif failure == "no_store":
            response["headers"] = {}
        elif failure == "false_no_store":
            response["headers"] = {"Cache-Control": "x-no-store, private"}
        elif failure == "http_error":
            response["status_code"] = 500
        else:
            response["body"]["rejection_reason"] = "model_timeout"
        return response

    result = recorder.record_once(plan, path, post=post, verify_binding=lambda: None)
    assert result["status"] == "incomplete_retained_no_retry"
    assert len(calls) == 1
    assert any(e["event"] == "response_received" and "reply" in e for e in events(plan))
    assert result["safety_decision"] is None


def test_environment_change_stops_before_next_request(setup):
    plan, path = setup
    calls = []

    def verify():
        if len(calls) == 1:
            raise ValueError("source changed")

    def post(payload):
        calls.append(payload)
        return reply(payload)

    result = recorder.record_once(plan, path, post=post, verify_binding=verify)
    assert result["status"] == "incomplete_retained_no_retry" and len(calls) == 1


def test_question_change_stops_before_next_request(setup):
    plan, path = setup
    calls = []

    def post(payload):
        calls.append(payload)
        path.write_text("changed toy fixture", encoding="utf-8")
        return reply(payload)

    result = recorder.record_once(plan, path, post=post, verify_binding=lambda: None)
    assert result["status"] == "incomplete_retained_no_retry" and len(calls) == 1


def test_permission_failure_prevents_request(setup, monkeypatch):
    plan, path = setup

    def fail(*args, **kwargs):
        raise PermissionError("test permission failure")

    monkeypatch.setattr(recorder, "restrict_to_owner", fail)
    with pytest.raises(PermissionError):
        recorder.record_once(
            plan,
            path,
            post=lambda _: pytest.fail("transport called"),
            verify_binding=lambda: None,
        )


def test_cli_reads_only_plan_metadata(setup, capsys):
    plan, path = setup
    plan["formal_run_authorized"] = False
    plan["question_file_local_path"] = str(path)
    path.unlink()
    metadata = path.with_name("plan.json")
    metadata.write_text(json.dumps(plan), encoding="utf-8")
    assert recorder.main(["--check-plan", str(metadata)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["question_file_read"] is report["formal_execution_performed"] is False
