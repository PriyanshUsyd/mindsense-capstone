"""Train-only policy refinements: temporal routing and phone feature synonyms."""

import pytest

from backend.slm.request_policy import (
    RequestCategory,
    classify_request,
    infer_feature_from_question,
    request_scope_rejection,
)


@pytest.mark.parametrize(
    "question",
    [
        "How many steps did I take on the previous day?",
        "What is the capital of Iceland this Sunday?",
    ],
)
def test_untracked_and_unrelated_temporal_requests_are_not_feature_windows(question):
    assert request_scope_rejection(question) is None


@pytest.mark.parametrize(
    "question",
    [
        "How often did I open my device compared with my baseline?",
        "Compare my phone checking count with my usual level.",
        "Did my screen checking frequency change from my personal norm?",
        "Summarize my device interactions against my typical pattern.",
    ],
)
def test_everyday_phone_interaction_synonyms_require_the_unlock_evidence(question):
    assert infer_feature_from_question(question) == "unlock_count"


def test_supported_feature_with_an_unsupported_window_still_gets_boundary():
    assert (
        request_scope_rejection("How did my GPS movement change last winter?")
        == "unsupported_time_window"
    )


def test_choosing_treatment_from_an_app_report_remains_a_supported_refusal():
    decision = classify_request("Choose a treatment using my wellbeing report.")

    assert decision.category == RequestCategory.TREATMENT_ADVICE_SEEKING
    assert decision.support_line is True
