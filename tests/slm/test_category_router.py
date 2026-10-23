"""Strict local category-router contract and policy 0.5.0 handoff tests."""

import json

import pytest

from backend.slm.category_router import (
    DEFAULT_CATEGORY_ROUTER_TIMEOUT_SECONDS,
    OllamaCategoryRouter,
    RouterLabel,
)
from backend.slm.client import OllamaClientConfig, SLMTimeoutError
from backend.slm.request_policy import (
    RequestCategory,
    RequestDisposition,
    RequestPolicyDecision,
)
from backend.slm.safety_screen import SafetyScreenLabel
from backend.slm.service import SLMService

CONFIG = OllamaClientConfig(model_tag="phi4-mini:3.8b")


class RouterTransport:
    def __init__(self, content=None, failure=None):
        self.content = content
        self.failure = failure
        self.calls = []

    def post_json(self, endpoint, payload, timeout_seconds):
        self.calls.append((endpoint, payload, timeout_seconds))
        if self.failure:
            raise self.failure
        return {"message": {"content": self.content}}


class StubRouter:
    def __init__(self, label):
        self.label = label
        self.calls = 0

    def route(self, question):
        self.calls += 1
        return self.label


class StubSafetyScreen:
    def __init__(self, label):
        self.label = label
        self.calls = 0

    def screen(self, question):
        self.calls += 1
        return self.label


class MustNotGenerate:
    def generate_draft(self, packet, question):
        raise AssertionError("a routed non-answer must not generate a draft")


@pytest.mark.parametrize(
    ("category", "disposition", "feature"),
    [
        (RequestCategory.IN_SCOPE, RequestDisposition.ALLOW, "gps_distance"),
        (RequestCategory.DIAGNOSIS_SEEKING, RequestDisposition.REFUSE, None),
        (RequestCategory.PROMPT_INJECTION, RequestDisposition.REFUSE, None),
    ],
)
def test_router_never_overrides_a_confident_deterministic_route(
    monkeypatch, category, disposition, feature
):
    import backend.slm.service as service_module

    deterministic = RequestPolicyDecision(
        disposition=disposition,
        category=category,
        reason_code="deterministic_test_route",
        support_line=disposition == RequestDisposition.REFUSE,
    )
    monkeypatch.setattr(
        service_module, "classify_request", lambda question: deterministic
    )
    monkeypatch.setattr(
        service_module, "infer_feature_from_question", lambda question: feature
    )
    router = StubRouter(RouterLabel.RISK)
    service = SLMService(MustNotGenerate(), category_router=router)

    decision = service._route_uncertain_request(
        "synthetic deterministic route check", deterministic
    )

    assert decision == deterministic
    assert router.calls == 0


def test_in_scope_without_feature_gets_clarification_without_router(monkeypatch):
    import backend.slm.service as service_module

    deterministic = RequestPolicyDecision(
        disposition=RequestDisposition.ALLOW,
        category=RequestCategory.IN_SCOPE,
    )
    monkeypatch.setattr(
        service_module, "classify_request", lambda question: deterministic
    )
    monkeypatch.setattr(service_module, "infer_feature_from_question", lambda q: None)
    monkeypatch.setattr(
        service_module, "is_general_uncertainty_question", lambda q: False
    )
    router = StubRouter(RouterLabel.RISK)
    service = SLMService(MustNotGenerate(), category_router=router)

    response = service.preflight_response("Synthetic in-scope feature ambiguity")

    assert response is not None
    assert response.rejection_reason == "ambiguous_feature_request"
    assert response.request_disposition == RequestDisposition.ALLOW
    assert response.request_category == RequestCategory.IN_SCOPE
    assert response.model_invoked is False
    assert "13 11 14" in response.text and "000" in response.text
    assert router.calls == 0


@pytest.mark.parametrize("label", list(RouterLabel))
def test_router_accepts_every_defined_label_as_strict_json(label):
    transport = RouterTransport(json.dumps({"category": label.value}))
    router = OllamaCategoryRouter(CONFIG, transport=transport)

    assert router.route("A new untrusted question") == label
    endpoint, payload, timeout = transport.calls[0]
    assert endpoint == CONFIG.endpoint
    assert timeout == DEFAULT_CATEGORY_ROUTER_TIMEOUT_SECONDS
    assert payload["options"]["temperature"] == 0
    assert payload["format"]["additionalProperties"] is False
    assert payload["format"]["required"] == ["category"]
    assert payload["format"]["properties"]["category"]["enum"] == [
        item.value for item in RouterLabel
    ]


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"category":"off_topic","extra":true}',
        '{"category":"off_topic","category":"crisis"}',
        '{"category":"not_a_route"}',
        "[]",
    ],
)
def test_bad_json_or_label_fails_closed_to_no_router_decision(content):
    router = OllamaCategoryRouter(CONFIG, transport=RouterTransport(content))
    assert router.route("A new untrusted question") is None


def test_timeout_fails_closed_and_is_cached_as_one_attempt():
    transport = RouterTransport(failure=SLMTimeoutError("deadline"))
    router = OllamaCategoryRouter(CONFIG, transport=transport)

    assert router.route("A new untrusted question") is None
    assert router.route("A new untrusted question") is None
    assert len(transport.calls) == 1


def test_router_cache_makes_only_one_call_for_a_question():
    transport = RouterTransport(json.dumps({"category": "off_topic"}))
    router = OllamaCategoryRouter(CONFIG, transport=transport)

    assert router.route("A new untrusted question") == RouterLabel.OFF_TOPIC
    assert router.route("A new untrusted question") == RouterLabel.OFF_TOPIC
    assert len(transport.calls) == 1


def test_model_in_scope_label_without_deterministic_feature_only_clarifies(monkeypatch):
    import backend.slm.service as service_module

    from backend.slm.request_policy import RequestPolicyDecision

    monkeypatch.setattr(
        service_module,
        "classify_request",
        lambda question: RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.OFF_TOPIC,
            reason_code="off_topic_request_detected",
            support_line=True,
        ),
    )
    monkeypatch.setattr(service_module, "infer_feature_from_question", lambda q: None)
    monkeypatch.setattr(service_module, "is_general_uncertainty_question", lambda q: False)
    router = StubRouter(RouterLabel.IN_SCOPE_GPS)
    service = SLMService(MustNotGenerate(), category_router=router)

    response = service.preflight_response("An unclear evidence question")

    assert response is not None
    assert response.rejection_reason == "ambiguous_feature_request"
    assert response.request_disposition == RequestDisposition.ALLOW
    assert response.request_category == RequestCategory.IN_SCOPE
    assert response.model_invoked is False
    assert "13 11 14" in response.text and "000" in response.text
    assert router.calls == 1


def test_router_crisis_label_uses_the_deterministic_crisis_template():
    router = StubRouter(RouterLabel.CRISIS)
    service = SLMService(MustNotGenerate(), category_router=router)

    response = service.preflight_response("What is the capital of Fiji?")

    assert response is not None
    assert response.response_mode.value == "crisis_aware_fallback"
    assert response.request_disposition == RequestDisposition.CRISIS
    assert response.rejection_reason == "category_router_crisis"
    assert response.model_invoked is False
    assert "1800 737 732" in response.text


def test_safety_screen_crisis_result_stops_before_category_router():
    router = StubRouter(RouterLabel.OFF_TOPIC)
    screen = StubSafetyScreen(SafetyScreenLabel.YES)
    service = SLMService(
        MustNotGenerate(), safety_screen=screen, category_router=router
    )

    response = service.preflight_response("What is the capital of Fiji?")

    assert response is not None
    assert response.response_mode.value == "crisis_aware_fallback"
    assert screen.calls == 1
    assert router.calls == 0


def test_refusal_disagreement_uses_the_configured_safety_priority():
    router = StubRouter(RouterLabel.INJECTION)
    service = SLMService(MustNotGenerate(), category_router=router)

    response = service.preflight_response("What is the capital of Fiji?")

    assert response is not None
    assert response.response_mode.value == "refusal"
    assert response.request_category == RequestCategory.PROMPT_INJECTION
    assert "13 11 14" in response.text and "000" in response.text
