"""
Tests for backend/statistics/participant_evidence.py — the module that
builds a REAL EvidencePacket for a participant from the actual CES pipeline
output, closing the gap where `/respond` used to accept a client-supplied
packet as-is (see backend/api/app.py's 2026-09-16 fix).

Real-dataset tests are skipped when the dataset isn't present locally
(gitignored), same convention as test_tier1_runner.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.contracts.evidence import EligibilityStatus, ResponseMode
from backend.statistics.participant_evidence import (
    UnknownFeature,
    UnknownParticipant,
    _round_user_facing,
    build_evidence_packet,
    select_local_demo_participant,
)

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"

requires_dataset = pytest.mark.skipif(
    not (DATASET_DIR / "Sensing" / "sensing.csv").exists(),
    reason="real CES dataset not present locally (gitignored) — cannot run end-to-end",
)

def _short_history_uid() -> str:
    if not (DATASET_DIR / "Sensing" / "sensing.csv").exists():
        return "dataset-not-present"
    sensing = pd.read_csv(DATASET_DIR / "Sensing" / "sensing.csv", usecols=["uid"])
    counts = sensing.groupby("uid").size()
    minimum = counts[counts == counts.min()]
    return str(min(minimum.index.astype(str)))


# Resolve real local participants at test time instead of publishing raw CES
# identifiers in the repository. The long-running participant is selected by
# the same private backend helper used by the browser's local demo alias.
LONG_HISTORY_UID = (
    select_local_demo_participant("gps_distance")
    if (DATASET_DIR / "Sensing" / "sensing.csv").exists()
    else "dataset-not-present"
)
SHORT_HISTORY_UID = _short_history_uid()


def test_round_user_facing_matches_pilot_flagged_value():
    """The exact excessive-precision case the Week 7 pilot report flagged
    (docs/evaluation/week7-rostered-pair-pilot-main.md, Q1)."""
    assert _round_user_facing(120.71428571428571) == 121


def test_round_user_facing_matches_reported_example():
    assert _round_user_facing(61.27214285714285) == 61


def test_round_user_facing_uses_half_up_not_bankers_rounding():
    """Week 8 rounding-rule decision (docs/statistics/preregistration.md
    section 5.2): ordinary half-up rounding, not Python's built-in `round`,
    which is round-half-to-even and would send 0.5 -> 0 and 2.5 -> 2."""
    assert _round_user_facing(0.5) == 1
    assert _round_user_facing(1.5) == 2
    assert _round_user_facing(2.5) == 3
    # Confirm this genuinely differs from Python's built-in round on ties.
    assert round(0.5) == 0
    assert round(2.5) == 2


def test_round_user_facing_returns_a_whole_number():
    result = _round_user_facing(83.191429)
    assert result == 83
    assert result == int(result)


def test_round_user_facing_handles_zero():
    assert _round_user_facing(0.0) == 0


@requires_dataset
def test_built_gps_packet_values_are_whole_numbers():
    packet = build_evidence_packet(LONG_HISTORY_UID, feature_id="gps_distance")
    assert packet.feature_window.value == int(packet.feature_window.value)
    if packet.baseline.value is not None:
        assert packet.baseline.value == int(packet.baseline.value)


@requires_dataset
def test_built_unlock_packet_values_are_whole_numbers():
    unlock_uid = select_local_demo_participant("unlock_count")
    packet = build_evidence_packet(unlock_uid, feature_id="unlock_count")
    assert packet.feature_window.value == int(packet.feature_window.value)
    if packet.baseline.value is not None:
        assert packet.baseline.value == int(packet.baseline.value)


@requires_dataset
def test_unknown_participant_raises():
    with pytest.raises(UnknownParticipant):
        build_evidence_packet("not-a-real-uid", feature_id="gps_distance")


@requires_dataset
def test_unknown_feature_raises():
    with pytest.raises(UnknownFeature):
        build_evidence_packet(LONG_HISTORY_UID, feature_id="not-a-real-feature")


@requires_dataset
def test_long_history_participant_is_comparison_eligible_by_history():
    """This participant has enough cumulative history to clear Moe's State C
    cold-start gate (28 calendar days / 20 valid sensor-days / 3 EMAs), but
    in THIS process (no R engine — see r_bridge.r_bridge_available()) no
    per-person evidence can be classified, so `response_health.py`'s
    ELIGIBLE-requires-evidence invariant means the packet is honestly
    reported as PARTIAL_DESCRIPTIVE_ONLY rather than an ELIGIBLE packet
    with no evidence attached (see build_evidence_packet's State C branch
    docstring for the discovery this test pins)."""
    packet = build_evidence_packet(LONG_HISTORY_UID, feature_id="gps_distance")

    assert packet.baseline.eligibility_status in (
        EligibilityStatus.ELIGIBLE,
        EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY,
    )
    assert packet.feature_window.feature_id == "gps_distance"
    assert packet.feature_window.observed_days > 0
    # Real per-request identity — never the raw CES uid (privacy rule).
    assert packet.identity.participant_ref != LONG_HISTORY_UID
    assert packet.identity.participant_ref.startswith("p_")


@requires_dataset
def test_short_history_participant_is_state_a_insufficient():
    packet = build_evidence_packet(SHORT_HISTORY_UID, feature_id="gps_distance")

    assert packet.baseline.eligibility_status == EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW
    assert packet.baseline.value is None
    assert packet.evidence is None
    assert packet.claim_policy.permitted_response_modes == (ResponseMode.INSUFFICIENT_DATA,)


@requires_dataset
def test_state_c_packet_never_fabricates_evidence_strength():
    """The core safety property this module must uphold: without the
    unreconciled bootstrap SE (evidence.py's flagged gap), evidence_strength
    must never be populated on a real participant's packet — no_claim/
    insufficient is the only honest outcome right now, per CLAUDE.md's
    finalised decisions and evidence.py's own module docstring."""
    packet = build_evidence_packet(LONG_HISTORY_UID, feature_id="gps_distance")

    if (
        packet.baseline.eligibility_status == EligibilityStatus.ELIGIBLE
        and packet.evidence is not None
    ):
        # Evidence may be None (no_claim) but must never silently assert a
        # strength value this codebase cannot yet defend.
        pytest.fail(
            "evidence_strength was populated without a real per-person "
            "standard error — this should be structurally impossible "
            "given evidence.py's current SE gap"
        )


@requires_dataset
def test_two_different_participants_yield_genuinely_different_packets():
    """Regression guard for the exact bug being fixed: two different
    participants must not produce the same packet."""
    eligible_packet = build_evidence_packet(LONG_HISTORY_UID, feature_id="gps_distance")
    insufficient_packet = build_evidence_packet(SHORT_HISTORY_UID, feature_id="gps_distance")

    assert (
        eligible_packet.baseline.eligibility_status
        != insufficient_packet.baseline.eligibility_status
    )
    assert eligible_packet.identity.participant_ref != insufficient_packet.identity.participant_ref


@requires_dataset
def test_as_of_recomputes_state_fresh_not_persisted():
    """CLAUDE.md: 'Cold-start applies per evaluation opportunity; State C
    does not persist.' An early `as_of` for the long-history participant
    (before they had accumulated enough history) must NOT be State C just
    because they eventually reach it."""
    sensing = pd.read_csv(
        DATASET_DIR / "Sensing" / "sensing.csv", usecols=["uid", "day"]
    )
    first_day = sensing.loc[sensing["uid"] == LONG_HISTORY_UID, "day"].min()
    early_as_of = pd.to_datetime(str(first_day), format="%Y%m%d").date()
    early_packet = build_evidence_packet(
        LONG_HISTORY_UID, feature_id="gps_distance", as_of=early_as_of
    )
    assert early_packet.baseline.eligibility_status != EligibilityStatus.ELIGIBLE
