"""Cross-message isolation on `/respond`: nothing from one participant or turn reaches another.

`/respond` holds no conversation state: each request carries one participant id
and one question, and the evidence packet is rebuilt for that request only.
These tests interleave two synthetic participants and both features through
the real app (demo runtime) and check every answer against every other packet.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.app import create_app, create_runtime_service
from benchmarks.slm_multiturn_eval import (
    GPS_Q,
    SYNTHETIC_VALUES,
    UNLOCK_Q,
    foreign_numbers,
    numbers_in,
    synthetic_packet,
)

QUESTIONS = {"gps_distance": GPS_Q, "unlock_count": UNLOCK_Q}
# Interleaved: participant and feature both change between consecutive turns.
SEQUENCE = (
    ("synthetic-A", "gps_distance"),
    ("synthetic-B", "unlock_count"),
    ("synthetic-A", "unlock_count"),
    ("synthetic-B", "gps_distance"),
    ("synthetic-A", "gps_distance"),
)


@pytest.fixture
def api():
    with TestClient(create_app(create_runtime_service("demo"))) as client:
        yield client


def ask(api, participant, question, **extra):
    calls = []

    def packet_for(participant_id, feature_id):
        calls.append((participant_id, feature_id))
        return synthetic_packet(participant_id, feature_id)

    with patch("backend.api.app.build_evidence_packet", side_effect=packet_for):
        response = api.post("/respond", json={"participant_id": participant, "question": question, **extra})
    return response, calls


def test_interleaved_turns_quote_only_their_own_packet(api):
    for participant, feature in SEQUENCE:
        response, calls = ask(api, participant, QUESTIONS[feature])
        assert response.status_code == 200
        assert calls == [(participant, feature)]
        found = numbers_in(response.json()["text"])
        assert float(SYNTHETIC_VALUES[(participant, feature)][0]) in found
        assert not found & foreign_numbers(participant, feature)


def test_same_request_gives_the_same_answer_whatever_came_before(api):
    first, _ = ask(api, "synthetic-A", GPS_Q)
    for participant, feature in SEQUENCE:
        ask(api, participant, QUESTIONS[feature])
    again, _ = ask(api, "synthetic-A", GPS_Q)
    assert again.json()["text"] == first.json()["text"]


def test_an_earlier_crisis_turn_does_not_change_the_next_participant(api):
    crisis, _ = ask(api, "synthetic-A", "I've been feeling really hopeless and I don't see the point anymore.")
    assert crisis.json()["response_mode"] == "crisis_aware_fallback"
    response, calls = ask(api, "synthetic-B", GPS_Q)
    assert calls == [("synthetic-B", "gps_distance")]
    assert response.json()["response_mode"] in {"normal", "uncertainty"}


@pytest.mark.parametrize("field", ["history", "conversation_id", "previous_messages", "session_id"])
def test_request_cannot_carry_another_turn(api, field):
    response, calls = ask(api, "synthetic-A", GPS_Q, **{field: ["synthetic-B said 203 unlocks"]})
    assert response.status_code == 422
    assert calls == []
    assert "203" not in response.text


def test_responses_are_not_stored_by_the_browser_or_proxies(api):
    response, _ = ask(api, "synthetic-A", GPS_Q)
    assert response.headers["cache-control"] == "no-store"
