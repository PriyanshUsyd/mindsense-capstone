"""Suite-wide fixtures."""

import json

import pytest

from backend.slm import safety_screen


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


@pytest.fixture(autouse=True, scope="session")
def _network_free_safety_screen():
    # Session scope so module-scoped fixtures that build a service also get it.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            safety_screen, "UrllibLoopbackTransport", _NetworkFreeScreenTransport
        )
        yield
