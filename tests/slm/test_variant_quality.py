"""Regression checks for live-review evidence without starting a model."""

import json

import pytest

from backend.slm.client import SLMUnavailableError
from backend.slm.runtime import create_local_service
from backend.slm.variants import VariantExecutionError, VariantKind
from benchmarks import slm_variant_quality as quality
from benchmarks.slm_model_comparison import comparison_cases
from benchmarks.slm_packet_api_smoke import ObservedTransport


class GroundedTransport:
    def __init__(self):
        self.payloads = []

    def post_json(self, endpoint, payload, timeout_seconds):
        user = json.loads(payload["messages"][1]["content"])
        self.payloads.append(user)
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


def make_service(transport=None):
    service = create_local_service(model_tag="phi4-mini:3.8b")
    service.client.transport = transport or GroundedTransport()
    return service


@pytest.fixture(scope="module")
def result():
    service = make_service()
    original = service.client.transport
    result = quality.run_quality_comparison(service=service)
    assert service.client.transport is original
    assert len(original.payloads) == 36
    return result


def test_complete_mapping_runs_all_architectures_without_inflating_coverage(result):
    assert len(result["records"]) == 288
    assert result["status"] == "development_checks_passed_human_review_pending"
    assert result["execution_backend"] == "injected_transport_not_live"
    assert set(result["summaries"]) == {v.value for v in VariantKind}
    for summary in result["summaries"].values():
        source = summary["groups"]["source_plan"]
        assert source["executed_runs"] == source["automated_passed_runs"] == 18
        assert source["unique_executed_cases"] == 6
        assert source["cases_passing_all_repetitions"] == 6
        assert source["not_covered_case_ids"] == ["plan_q2", "plan_q8"]
        assert (
            summary["groups"]["guardrail_high_severity"]["unique_executed_cases"] == 14
        )
        assert (
            summary["groups"]["guardrail_privacy_extension"]["unique_executed_cases"]
            == 2
        )
        assert summary["model_invocations"] == 9
        assert summary["human_quality_pass_rate"] is None
    assert (
        sum(s["first_generation_ms"] is not None for s in result["summaries"].values())
        == 1
    )
    assert (
        sum(s["subsequent_generation_count"] for s in result["summaries"].values())
        == 35
    )


def test_trace_confirms_context_reaches_model_and_deterministic_cases_do_not(result):
    for record in result["records"]:
        if record["response"] is None:
            assert record["execution_status"] == "not_covered"
            assert record["automated_checks_passed"] is None
            continue
        expected = quality.EXPECTED_CONTEXT[VariantKind(record["variant"])]
        contexts = record["trace"]["model_call_context_ids"]
        assert contexts == ([expected] if record["response"]["model_invoked"] else [])
        assert (
            record["trace"]["packet_id"]
            == record["evidence_packet"]["identity"]["packet_id"]
        )
        if record["group"].startswith("guardrail_"):
            assert not record["response"]["model_invoked"]
            assert not record["trace"]["retrieval_attempted"]
            assert not record["trace"]["tool_selection_attempted"]


def test_export_preserves_evidence_and_human_review_is_not_fabricated(result):
    json.dumps(result)
    for record in result["records"]:
        assert all(v is None for v in record["human_review"].values())
        assert all(v is None for v in record["rubric_review"].values())
    review = quality.render_review(result)
    assert review.count("NOT COVERED:") == 2
    assert review.count("Joint decision / disagreement resolution: NOT ASSESSED") == 88
    assert result["response_comparison"]["plan_q1"] == 1
    assert len(result["provenance"]["sha256_raw_bytes"][quality.PROTOCOL]) == 64


def test_non_synthetic_packet_rejected_before_retrieval_or_transport():
    service = make_service()
    observer = ObservedTransport(service.client.transport)
    packet = comparison_cases()[0].packet
    packet = packet.model_copy(
        update={
            "identity": packet.identity.model_copy(
                update={"participant_ref": "not-synthetic"}
            )
        }
    )
    adapter = quality.PacketVariantReviewService(
        service, VariantKind.RAG_AGENT, observer
    )
    with pytest.raises(ValueError, match="synthetic"):
        adapter.respond(packet, "How has my phone unlock count changed?")
    assert observer.context_ids == []
    assert service.client.transport.payloads == []


def test_model_failure_remains_failed_with_complete_records_and_checkpoints(
    monkeypatch,
):
    class OfflineTransport:
        def post_json(self, *args):
            raise SLMUnavailableError("synthetic unavailable model")

    monkeypatch.setattr(quality, "REPETITIONS", 1)
    saved_counts = []
    result = quality.run_quality_comparison(
        service=make_service(OfflineTransport()),
        on_checkpoint=lambda result: saved_counts.append(len(result["records"])),
    )
    assert saved_counts == [24, 48, 72, 96]
    assert result["status"] == "development_checks_failed_human_review_pending"
    for summary in result["summaries"].values():
        assert summary["groups"]["source_plan"]["automated_passed_runs"] == 3
        assert (
            summary["groups"]["guardrail_high_severity"]["automated_passed_runs"] == 14
        )


def test_context_failure_is_recorded_and_never_counted_as_a_pass(monkeypatch):
    class FailingRunner:
        def run(self, request):
            raise VariantExecutionError("context_provider_failed")

    monkeypatch.setattr(
        quality, "create_packet_variant_runner", lambda *a, **kw: FailingRunner()
    )
    service = make_service()
    adapter = quality.PacketVariantReviewService(
        service, VariantKind.RAG, ObservedTransport(service.client.transport)
    )
    response = adapter.respond(
        comparison_cases()[0].packet, "How has my phone unlock count changed?"
    )
    assert response.used_fallback
    assert adapter.traces[0]["execution_error"] == "context_provider_failed"
    assert not service.client.transport.payloads


def test_transport_restored_after_unexpected_abort(monkeypatch):
    def abort(**kwargs):
        raise RuntimeError("synthetic interruption")

    service = make_service()
    original = service.client.transport
    monkeypatch.setattr(quality, "run_alignment", abort)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        quality.run_quality_comparison(service=service)
    assert service.client.transport is original


def test_existing_evidence_is_never_overwritten(tmp_path):
    output = tmp_path / "existing.json"
    output.write_text("historical evidence", encoding="utf-8")
    with pytest.raises(SystemExit):
        quality.main(["--out", str(output), "--scorecard", str(tmp_path / "new.md")])
    assert output.read_text(encoding="utf-8") == "historical evidence"
