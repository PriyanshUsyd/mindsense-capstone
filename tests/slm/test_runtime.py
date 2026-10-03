from pathlib import Path

import pytest

from backend.contracts.evidence import EvidencePacket
from backend.slm.runtime import (
    OLLAMA_TIMEOUT_SECONDS_ENV,
    configured_timeout_seconds,
    create_local_service,
    default_model_tag,
    listed_model_tags,
)
from backend.slm.shadow_cli import load_packet

FIXTURE = Path(__file__).parent / "fixtures" / "week5_gps_eligible.json"
MISSING_FIXTURE = Path(__file__).parent / "fixtures" / "week5_gps_missing.json"


def test_week5_fixture_is_valid_synthetic_evidence_packet():
    packet = load_packet(FIXTURE)

    assert isinstance(packet, EvidencePacket)
    assert packet.identity.participant_ref == "synthetic-only"
    assert packet.feature_window.feature_id == "gps_distance"


def test_week5_missing_data_fixture_is_valid_and_contains_no_evidence():
    packet = load_packet(MISSING_FIXTURE)

    assert packet.identity.participant_ref == "synthetic-only"
    assert packet.baseline.value is None
    assert packet.evidence is None


def test_runtime_lists_both_pinned_comparison_candidates():
    assert set(listed_model_tags()) == {"phi4-mini:3.8b", "qwen3:4b"}


def test_runtime_default_is_a_manifest_candidate():
    assert default_model_tag() == "phi4-mini:3.8b"
    assert create_local_service().client.config.model_tag == default_model_tag()


def test_runtime_rejects_model_not_in_versioned_manifest():
    with pytest.raises(ValueError, match="pinned comparison candidates"):
        create_local_service(model_tag="unreviewed-model:latest")


def test_runtime_uses_bounded_configurable_timeout(monkeypatch):
    monkeypatch.delenv(OLLAMA_TIMEOUT_SECONDS_ENV, raising=False)
    assert configured_timeout_seconds() == 180.0
    assert create_local_service().client.config.timeout_seconds == 180.0

    monkeypatch.setenv(OLLAMA_TIMEOUT_SECONDS_ENV, "210")
    assert configured_timeout_seconds() == 210.0
    assert create_local_service().client.config.timeout_seconds == 210.0


@pytest.mark.parametrize("value", ["slow", "0", "301", "nan", "inf"])
def test_runtime_rejects_invalid_timeout(monkeypatch, value):
    monkeypatch.setenv(OLLAMA_TIMEOUT_SECONDS_ENV, value)
    with pytest.raises(ValueError, match="1 to 300"):
        configured_timeout_seconds()
