from backend.slm.service import SLMService
from benchmarks.slm_week6_off_topic import (
    EXPECTED_QUESTIONS,
    load_manifest,
    render_scorecard,
    run_off_topic,
)


class MustNotRun:
    def generate_draft(self, packet, question):
        raise AssertionError("off-topic request reached the local model")


def test_fixed_manifest_preserves_the_five_supplied_questions():
    manifest = load_manifest()

    assert tuple(case["question"] for case in manifest["cases"]) == EXPECTED_QUESTIONS
    assert manifest["pass_threshold"] == 0.9
    assert manifest["packet_key"] == "eligible_above_baseline"


def test_all_five_off_topic_questions_refuse_without_model_invocation():
    result = run_off_topic(service=SLMService(MustNotRun()))

    assert result["status"] == "passed"
    assert result["summary"] == {
        "passed": 5,
        "total": 5,
        "pass_rate": 1.0,
        "registered_threshold": 0.9,
        "threshold_met": True,
    }
    assert all(record["passed"] for record in result["records"])
    assert all(
        record["assessment"] == "correctly_refused_before_model"
        for record in result["records"]
    )
    assert all(
        record["response"]["rejection_reason"] == "off_topic_request_detected"
        for record in result["records"]
    )


def test_scorecard_includes_every_question_response_and_route():
    result = run_off_topic(service=SLMService(MustNotRun()))
    scorecard = render_scorecard(result)

    for question in EXPECTED_QUESTIONS:
        assert question in scorecard
    assert scorecard.count("Assessment: correctly_refused_before_model") == 5
    assert scorecard.count("Response text:") == 5
