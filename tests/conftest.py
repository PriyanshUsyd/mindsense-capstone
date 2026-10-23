"""Suite-wide fixtures."""

import json

import pytest

from backend.slm import safety_screen
from backend.slm import category_router
from backend.slm.request_policy import (
    RequestCategory,
    classify_request,
    infer_feature_from_question,
    is_general_uncertainty_question,
)


class _NetworkFreeScreenTransport:
    """Answers the policy 0.3.5 safety screen with "no" and nothing else.

    Tests that build the Ollama runtime replace the generation transport with
    a fake, but the screen has its own loopback transport. Without this the
    screen would call a real local Ollama (or fail closed to the crisis route
    when none is running). Screen behaviour itself is tested with injected
    transports in tests/slm/test_safety_screen.py.
    """

    def post_json(self, endpoint, payload, timeout_seconds):
        assert payload["format"]["properties"]["answer"]["enum"] == ["yes", "no"]
        return {"message": {"content": json.dumps({"answer": "no"})}}


class _NetworkFreeCategoryRouterTransport:
    """Keeps local-runtime tests deterministic without calling Ollama."""

    def post_json(self, endpoint, payload, timeout_seconds):
        labels = payload["format"]["properties"]["category"]["enum"]
        assert set(labels) == {
            "crisis", "diagnosis", "treatment", "cause", "risk",
            "clinical_score", "injection", "sensitive", "app_info",
            "capability", "time_window", "feature_unclear", "untracked",
            "in_scope_gps", "in_scope_unlocks", "off_topic",
        }
        message = json.loads(payload["messages"][1]["content"])["message"]
        decision = classify_request(message)
        if decision.category == RequestCategory.OFF_TOPIC:
            label = "off_topic"
        elif (
            decision.category == RequestCategory.IN_SCOPE
            and infer_feature_from_question(message) is None
            and not is_general_uncertainty_question(message)
        ):
            label = "feature_unclear"
        else:
            label = "off_topic"
        return {"message": {"content": json.dumps({"category": label})}}


@pytest.fixture(autouse=True, scope="session")
def _network_free_safety_screen():
    # Session scope so module-scoped fixtures that build a service also get it.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            safety_screen, "UrllibLoopbackTransport", _NetworkFreeScreenTransport
        )
        patch.setattr(
            category_router,
            "UrllibLoopbackTransport",
            _NetworkFreeCategoryRouterTransport,
        )
        yield
