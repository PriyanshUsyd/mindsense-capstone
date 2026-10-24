"""Request-classifier contract, voting, precedence, and fail-closed tests."""

import json

import pytest

from backend.slm.client import OllamaClientConfig, SLMTimeoutError
from backend.slm.request_classifier import (
    DEFAULT_REQUEST_CLASSIFIER_TIMEOUT_SECONDS,
    ClassifierLabel,
    OllamaRequestClassifier,
    RequestClassification,
    load_request_classifier_prompt,
    parse_classification,
)
from backend.slm.request_policy import (
    RequestCategory,
    RequestDisposition,
    RequestPolicyDecision,
)
from backend.slm.safety_screen import SafetyScreenLabel
from backend.slm.service import SLMService

CONFIG = OllamaClientConfig(model_tag="phi4-mini:3.8b")


def _response(label, confidence=0.95):
    return {"message": {"content": json.dumps({"label": label, "confidence": confidence})}}


class ResponseTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post_json(self, endpoint, payload, timeout_seconds):
        self.calls.append((endpoint, payload, timeout_seconds))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_prompt_has_three_to_five_fresh_examples_for_each_label():
    prompt = load_request_classifier_prompt()

    assert prompt.manifest.prompt_version == "0.6.0"
    assert {label.name for label in prompt.manifest.labels} == set(ClassifierLabel)
    assert all(3 <= len(label.examples) <= 5 for label in prompt.manifest.labels)


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"label":"off_topic","confidence":0.9,"extra":true}',
        '{"label":"off_topic","confidence":0.9,"label":"crisis"}',
        '{"label":"unknown","confidence":0.9}',
        '{"label":"off_topic","confidence":true}',
        '{"label":"off_topic","confidence":1.1}',
        '{"label":"off_topic","confidence":NaN}',
    ],
)
def test_classifier_parser_rejects_invalid_or_non_strict_json(content):
    assert parse_classification({"message": {"content": content}}) is None


def test_classifier_uses_strict_schema_temperature_and_caches_high_confidence():
    transport = ResponseTransport([_response("cause")])
    classifier = OllamaRequestClassifier(CONFIG, transport=transport)

    first = classifier.classify("synthetic routing example")
    second = classifier.classify("synthetic routing example")

    assert first == second
    assert first.label == ClassifierLabel.CAUSE
    assert first.attempts == 1
    endpoint, payload, timeout = transport.calls[0]
    assert endpoint == CONFIG.endpoint
    assert timeout == DEFAULT_REQUEST_CLASSIFIER_TIMEOUT_SECONDS
    assert payload["options"]["temperature"] == 0
    assert payload["format"]["additionalProperties"] is False
    assert set(payload["format"]["properties"]) == {"label", "confidence"}
    assert len(transport.calls) == 1


def test_low_confidence_uses_two_shuffled_calls_and_majority_vote():
    transport = ResponseTransport(
        [_response("risk", 0.5), _response("cause", 0.6), _response("cause", 0.7)]
    )
    classifier = OllamaRequestClassifier(CONFIG, transport=transport)

    result = classifier.classify("synthetic uncertain classification")

    assert result.label == ClassifierLabel.CAUSE
    assert result.attempts == 3
    assert len(transport.calls) == 3
    orders = [
        tuple(call[1]["format"]["properties"]["label"]["enum"])
        for call in transport.calls
    ]
    assert orders[0] != orders[1]
    assert orders[1] != orders[2]


def test_low_confidence_disagreement_chooses_safest_refusal_vote():
    transport = ResponseTransport(
        [
            _response("in_scope_gps", 0.4),
            _response("cause", 0.4),
            _response("sensitive", 0.4),
        ]
    )
    classifier = OllamaRequestClassifier(CONFIG, transport=transport)

    result = classifier.classify("synthetic no-majority classification")

    assert result.label == ClassifierLabel.SENSITIVE
    assert result.attempts == 3


def test_invalid_followup_fails_closed_without_accepting_partial_vote():
    transport = ResponseTransport(
        [_response("cause", 0.4), SLMTimeoutError("local timeout")]
    )
    classifier = OllamaRequestClassifier(CONFIG, transport=transport)

    assert classifier.classify("synthetic timeout classification") is None
    assert len(transport.calls) == 2


class StubScreen:
    def __init__(self, label, events=None):
        self.label = label
        self.calls = 0
        self.events = events

    def screen(self, question):
        self.calls += 1
        if self.events is not None:
            self.events.append("screen")
        return self.label


class StubClassifier:
    def __init__(self, label, confidence=0.95, events=None):
        self.result = RequestClassification(
            label=label, confidence=confidence, latency_ms=1.0, attempts=1
        )
        self.calls = 0
        self.events = events

    def classify(self, question):
        self.calls += 1
        if self.events is not None:
            self.events.append("classifier")
        return self.result


class MustNotGenerate:
    def generate_draft(self, packet, question):
        raise AssertionError("classification must not generate an answer")


def test_crisis_rules_run_before_safety_screen_and_classifier(monkeypatch):
    import backend.slm.service as service_module

    crisis = RequestPolicyDecision(
        disposition=RequestDisposition.CRISIS,
        category=RequestCategory.CRISIS_SELF_HARM,
        reason_code="crisis_language_detected",
    )
    monkeypatch.setattr(service_module, "classify_crisis_request", lambda question: crisis)
    screen = StubScreen(SafetyScreenLabel.NO)
    classifier = StubClassifier(ClassifierLabel.OFF_TOPIC)
    service = SLMService(
        MustNotGenerate(), safety_screen=screen, request_classifier=classifier
    )

    result = service.preflight_response("synthetic crisis ordering case")

    assert result.response_mode.value == "crisis_aware_fallback"
    assert result.safety_screen == SafetyScreenLabel.NOT_RUN
    assert screen.calls == 0
    assert classifier.calls == 0


def test_safety_screen_runs_before_classifier_and_stops_it_on_crisis():
    screen = StubScreen(SafetyScreenLabel.YES)
    classifier = StubClassifier(ClassifierLabel.OFF_TOPIC)
    service = SLMService(
        MustNotGenerate(), safety_screen=screen, request_classifier=classifier
    )

    result = service.preflight_response("A neutral-looking new question.")

    assert result.response_mode.value == "crisis_aware_fallback"
    assert screen.calls == 1
    assert classifier.calls == 0


def test_order_is_crisis_rules_then_screen_then_classifier_then_deterministic_guard(
    monkeypatch,
):
    import backend.slm.service as service_module

    events = []
    original_classify = service_module.classify_request

    def track_guard(question):
        events.append("deterministic_guard")
        return original_classify(question)

    monkeypatch.setattr(service_module, "classify_request", track_guard)
    screen = StubScreen(SafetyScreenLabel.NO, events)
    classifier = StubClassifier(ClassifierLabel.OFF_TOPIC, events=events)
    service = SLMService(
        MustNotGenerate(), safety_screen=screen, request_classifier=classifier
    )

    service.preflight_response("A wholly unrelated request.")

    assert events == ["screen", "classifier", "deterministic_guard"]


@pytest.mark.parametrize(
    ("category", "reason", "model_label"),
    [
        (RequestCategory.PROMPT_INJECTION, "prompt_injection_detected", ClassifierLabel.OFF_TOPIC),
        (RequestCategory.SENSITIVE_DATA_REQUEST, "sensitive_data_request_detected", ClassifierLabel.CAUSE),
    ],
)
def test_high_precision_injection_and_sensitive_guards_override_classifier(
    monkeypatch, category, reason, model_label
):
    import backend.slm.service as service_module

    deterministic = RequestPolicyDecision(
        disposition=RequestDisposition.REFUSE,
        category=category,
        reason_code=reason,
        support_line=True,
    )
    monkeypatch.setattr(service_module, "classify_request", lambda question: deterministic)
    service = SLMService(
        MustNotGenerate(), request_classifier=StubClassifier(model_label)
    )

    decision, _ = service._classify("synthetic high-precision guard")

    assert decision == deterministic


def test_deterministic_time_window_guard_overrides_classifier(monkeypatch):
    import backend.slm.service as service_module

    deterministic = RequestPolicyDecision(
        disposition=RequestDisposition.ALLOW,
        category=RequestCategory.IN_SCOPE,
    )
    monkeypatch.setattr(service_module, "classify_request", lambda question: deterministic)
    monkeypatch.setattr(
        service_module, "request_scope_rejection", lambda question: "unsupported_time_window"
    )
    service = SLMService(
        MustNotGenerate(),
        request_classifier=StubClassifier(ClassifierLabel.IN_SCOPE_GPS),
    )

    decision, _ = service._classify("synthetic explicit-period request")

    assert decision.reason_code == "unsupported_time_window"
    assert decision.category == RequestCategory.IN_SCOPE


def test_classifier_in_scope_label_cannot_answer_without_deterministic_feature(
    monkeypatch,
):
    import backend.slm.service as service_module

    deterministic = RequestPolicyDecision(
        disposition=RequestDisposition.REFUSE,
        category=RequestCategory.OFF_TOPIC,
        reason_code="off_topic_request_detected",
        support_line=True,
    )
    monkeypatch.setattr(service_module, "classify_request", lambda question: deterministic)
    monkeypatch.setattr(service_module, "infer_feature_from_question", lambda question: "gps_distance")
    service = SLMService(
        MustNotGenerate(),
        request_classifier=StubClassifier(ClassifierLabel.IN_SCOPE_GPS),
    )

    decision, _ = service._classify("untrusted question with model-only feature guess")

    assert decision == deterministic
    assert decision.disposition == RequestDisposition.REFUSE


def test_feature_label_only_preserves_deterministic_in_scope_allow(monkeypatch):
    import backend.slm.service as service_module

    deterministic = RequestPolicyDecision(
        disposition=RequestDisposition.ALLOW,
        category=RequestCategory.IN_SCOPE,
    )
    monkeypatch.setattr(service_module, "classify_request", lambda question: deterministic)
    monkeypatch.setattr(service_module, "infer_feature_from_question", lambda question: "gps_distance")
    service = SLMService(
        MustNotGenerate(),
        request_classifier=StubClassifier(ClassifierLabel.IN_SCOPE_GPS),
    )

    decision, _ = service._classify("deterministic GPS feature match")

    assert decision == deterministic
    assert decision.disposition == RequestDisposition.ALLOW


def test_classifier_cannot_clarify_single_deterministic_feature_on_label_mismatch(
    monkeypatch,
):
    import backend.slm.service as service_module

    deterministic = RequestPolicyDecision(
        disposition=RequestDisposition.ALLOW,
        category=RequestCategory.IN_SCOPE,
        reason_code="deterministic_feature_route",
    )
    monkeypatch.setattr(service_module, "classify_request", lambda question: deterministic)
    monkeypatch.setattr(
        service_module, "infer_feature_from_question", lambda question: "unlock_count"
    )
    monkeypatch.setattr(service_module, "request_scope_rejection", lambda question: None)
    service = SLMService(
        MustNotGenerate(),
        request_classifier=StubClassifier(ClassifierLabel.IN_SCOPE_GPS),
    )

    decision, _ = service._classify("clear deterministic unlock-count request")

    assert decision == deterministic
    assert decision.reason_code != "feature_request_mismatch"


def test_classifier_feature_guess_without_feature_gets_clarification(monkeypatch):
    import backend.slm.service as service_module

    deterministic = RequestPolicyDecision(
        disposition=RequestDisposition.ALLOW,
        category=RequestCategory.IN_SCOPE,
    )
    monkeypatch.setattr(service_module, "classify_request", lambda question: deterministic)
    monkeypatch.setattr(service_module, "infer_feature_from_question", lambda question: None)
    monkeypatch.setattr(service_module, "request_scope_rejection", lambda question: None)
    service = SLMService(
        MustNotGenerate(),
        request_classifier=StubClassifier(ClassifierLabel.IN_SCOPE_GPS),
    )

    decision, _ = service._classify("model-only possible feature")

    assert decision.disposition == RequestDisposition.ALLOW
    assert decision.reason_code == "ambiguous_feature_request"


def test_feature_clarification_returns_before_answer_generation(monkeypatch):
    import backend.slm.service as service_module

    deterministic = RequestPolicyDecision(
        disposition=RequestDisposition.ALLOW,
        category=RequestCategory.IN_SCOPE,
    )
    monkeypatch.setattr(service_module, "classify_request", lambda question: deterministic)
    monkeypatch.setattr(service_module, "infer_feature_from_question", lambda question: None)
    monkeypatch.setattr(service_module, "request_scope_rejection", lambda question: None)
    service = SLMService(
        MustNotGenerate(),
        request_classifier=StubClassifier(ClassifierLabel.IN_SCOPE_GPS),
    )

    response = service.preflight_response("an ambiguous personal evidence request")

    assert response is not None
    assert response.response_mode.value == "generic_fallback"
    assert response.rejection_reason == "ambiguous_feature_request"
    assert response.model_invoked is False


def test_classifier_failure_uses_deterministic_refusal_or_off_topic(monkeypatch):
    import backend.slm.service as service_module

    matching = RequestPolicyDecision(
        disposition=RequestDisposition.REFUSE,
        category=RequestCategory.TREATMENT_ADVICE_SEEKING,
        reason_code="treatment_advice_request_detected",
        support_line=True,
    )
    monkeypatch.setattr(service_module, "request_scope_rejection", lambda question: None)
    service = SLMService(MustNotGenerate())

    assert service._classifier_failure_fallback("question", matching) == matching
    fallback = service._classifier_failure_fallback(
        "question",
        RequestPolicyDecision(
            disposition=RequestDisposition.ALLOW,
            category=RequestCategory.IN_SCOPE,
        ),
    )
    assert fallback.category == RequestCategory.OFF_TOPIC
    assert fallback.disposition == RequestDisposition.REFUSE
