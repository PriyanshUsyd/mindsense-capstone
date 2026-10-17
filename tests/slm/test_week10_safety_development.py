"""Runner accounting checks, not a claim that product safety passes."""

import json

import pytest

from benchmarks import slm_week10_safety_development as dev


class GroundedTransport:
    def post_json(self, endpoint, payload, timeout_seconds):
        user = json.loads(payload["messages"][1]["content"])
        return {
            "message": {
                "content": json.dumps(
                    {
                        "packet_id": user["evidence_packet"]["identity"]["packet_id"],
                        **user["allowed_response_options"][0],
                    }
                )
            }
        }


def test_diagnostic_miss_is_failure_even_when_output_is_grounded():
    case = next(c for c in dev.load_protocol()["cases"] if c["id"] == "diagnostic-1")
    checks = dev.checks_for(
        case,
        {
            "request_category": "in_scope",
            "response_mode": "uncertainty",
            "model_invoked": True,
            "request_policy_version": "0.3.4",
        },
        dev.MODELS[0],
        [{"payload": {"model": dev.MODELS[0]}}],
        1,
        True,
        200,
    )
    assert not checks["category"]
    assert not checks["model_invocation"]
    assert not checks["transport_count"]
    assert not checks["packet_load_count"]


def test_support_line_off_topic_is_not_counted_as_crisis_routing():
    case = dev.load_protocol()["cases"][0]
    checks = dev.checks_for(
        case,
        {
            "request_category": "off_topic",
            "response_mode": "refusal",
            "model_invoked": False,
            "request_policy_version": "0.3.4",
            "text": "Support resources are present.",
        },
        dev.MODELS[0],
        [],
        0,
        True,
        200,
    )
    assert not checks["category"]
    assert not checks["mode"]


def test_both_model_paths_record_attempts_and_keep_human_rating_blank():
    checkpoints = []
    records = dev.run_regression(
        transport_factory=lambda _: GroundedTransport(),
        on_record=checkpoints.append,
        expected_policy_version="0.3.5",
    )
    assert len(records) == len(checkpoints) == 40
    assert all(row["human_rating"] is None for row in records)
    assert all(row["passed"] for row in records)
    for model in dev.MODELS:
        rows = [row for row in records if row["model"] == model]
        assert len(rows) == 20
        calls = [call for row in rows for call in row["transport_calls"]]
        assert calls
        assert all(call["payload"]["model"] == model for call in calls)
        assert all(
            call["payload"]["options"] == {"temperature": 0, "seed": 42}
            for call in calls
        )
        assert all(row["passed"] == all(row["checks"].values()) for row in rows)


def test_transport_failure_is_recorded_without_retry():
    class Unavailable:
        calls = 0

        def post_json(self, *args):
            self.calls += 1
            raise RuntimeError("synthetic transport failure")

    delegate = Unavailable()
    observed = dev.ObservedTransport(delegate)
    with pytest.raises(RuntimeError):
        observed.post_json(
            "http://127.0.0.1:11434/api/chat", {"model": dev.MODELS[0]}, 180
        )
    assert delegate.calls == 1
    assert observed.calls[0]["error_type"] == "RuntimeError"


def test_baseline_run_rejects_modified_sources(monkeypatch):
    monkeypatch.setattr(
        dev,
        "git",
        lambda *args: (
            dev.BASE_SHA if args[0] == "rev-parse" else "backend/slm/request_policy.py"
        ),
    )
    with pytest.raises(ValueError, match="unchanged production"):
        dev.validate_revision("baseline")


def test_repair_rejects_wrong_base_before_any_model_call(monkeypatch):
    monkeypatch.setattr(dev, "git", lambda *args: "unexpected-head")
    with pytest.raises(ValueError, match="source HEAD"):
        dev.validate_revision("repair")
