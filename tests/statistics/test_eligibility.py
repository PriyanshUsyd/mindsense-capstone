"""
Eligibility / cold-start state tests, rewritten 2026-08-29 to match Moe
Tanaka's real, locked Week 4 spec (merged into main) instead of the
superseded AI-guessed 14-day/4-window placeholder. Explicit boundary
coverage on every threshold in his Section 4.3 table.
"""

import pytest

from backend.statistics.eligibility import (
    HISTORICAL_MIN_CALENDAR_DAYS,
    HISTORICAL_MIN_EMA_SPAN_DAYS,
    HISTORICAL_MIN_EMAS,
    HISTORICAL_MIN_VALID_SENSOR_DAYS,
    STATE_B_MIN_CALENDAR_DAYS,
    STATE_B_MIN_EMAS,
    STATE_B_MIN_VALID_SENSOR_DAYS,
    STATE_C_MIN_CALENDAR_DAYS,
    STATE_C_MIN_EMAS,
    STATE_C_MIN_VALID_SENSOR_DAYS,
    ColdStartState,
    classify_state,
    is_eligible,
    is_historical_relationship_eligible,
)


# --- State A boundaries -------------------------------------------------------

def test_state_a_below_calendar_day_minimum():
    state = classify_state(calendar_days=STATE_B_MIN_CALENDAR_DAYS - 1, valid_sensor_days=100, ema_count=10)
    assert state == ColdStartState.A_INSUFFICIENT_DATA


def test_state_a_zero_emas():
    state = classify_state(calendar_days=100, valid_sensor_days=100, ema_count=0)
    assert state == ColdStartState.A_INSUFFICIENT_DATA


def test_state_a_below_valid_sensor_day_minimum():
    state = classify_state(calendar_days=100, valid_sensor_days=STATE_B_MIN_VALID_SENSOR_DAYS - 1, ema_count=10)
    assert state == ColdStartState.A_INSUFFICIENT_DATA


def test_state_a_all_zero():
    state = classify_state(calendar_days=0, valid_sensor_days=0, ema_count=0)
    assert state == ColdStartState.A_INSUFFICIENT_DATA


# --- State B boundaries (exactly at the floor, and just under the State C ceiling) --

def test_state_b_at_exact_floor():
    state = classify_state(
        calendar_days=STATE_B_MIN_CALENDAR_DAYS,
        valid_sensor_days=STATE_B_MIN_VALID_SENSOR_DAYS,
        ema_count=STATE_B_MIN_EMAS,
    )
    assert state == ColdStartState.B_PARTIAL_HISTORY


def test_state_b_just_below_state_c_calendar_days():
    state = classify_state(
        calendar_days=STATE_C_MIN_CALENDAR_DAYS - 1,
        valid_sensor_days=STATE_C_MIN_VALID_SENSOR_DAYS,
        ema_count=STATE_C_MIN_EMAS,
    )
    assert state == ColdStartState.B_PARTIAL_HISTORY


def test_state_b_just_below_state_c_valid_sensor_days():
    state = classify_state(
        calendar_days=STATE_C_MIN_CALENDAR_DAYS,
        valid_sensor_days=STATE_C_MIN_VALID_SENSOR_DAYS - 1,
        ema_count=STATE_C_MIN_EMAS,
    )
    assert state == ColdStartState.B_PARTIAL_HISTORY


def test_state_b_just_below_state_c_ema_count():
    state = classify_state(
        calendar_days=STATE_C_MIN_CALENDAR_DAYS,
        valid_sensor_days=STATE_C_MIN_VALID_SENSOR_DAYS,
        ema_count=STATE_C_MIN_EMAS - 1,
    )
    assert state == ColdStartState.B_PARTIAL_HISTORY


# --- State C boundaries (exactly at the floor, and well above) ---------------

def test_state_c_at_exact_floor():
    state = classify_state(
        calendar_days=STATE_C_MIN_CALENDAR_DAYS,
        valid_sensor_days=STATE_C_MIN_VALID_SENSOR_DAYS,
        ema_count=STATE_C_MIN_EMAS,
    )
    assert state == ColdStartState.C_FULL_HISTORY


def test_state_c_well_above_floor():
    state = classify_state(calendar_days=365, valid_sensor_days=300, ema_count=50)
    assert state == ColdStartState.C_FULL_HISTORY


@pytest.mark.parametrize("calendar_days,valid_sensor_days,ema_count", [
    (28, 20, 3),
    (29, 21, 4),
    (56, 40, 8),
    (1000, 900, 200),
])
def test_state_c_various_qualifying_combinations(calendar_days, valid_sensor_days, ema_count):
    assert classify_state(calendar_days, valid_sensor_days, ema_count) == ColdStartState.C_FULL_HISTORY


# --- Historical-relationship gate (stricter 56-day gate on top of State C) --

def test_historical_relationship_at_exact_floor():
    assert is_historical_relationship_eligible(
        calendar_days=HISTORICAL_MIN_CALENDAR_DAYS,
        valid_sensor_days=HISTORICAL_MIN_VALID_SENSOR_DAYS,
        ema_count=HISTORICAL_MIN_EMAS,
        ema_span_days=HISTORICAL_MIN_EMA_SPAN_DAYS,
    ) is True


def test_historical_relationship_fails_just_under_calendar_days():
    assert is_historical_relationship_eligible(
        calendar_days=HISTORICAL_MIN_CALENDAR_DAYS - 1,
        valid_sensor_days=HISTORICAL_MIN_VALID_SENSOR_DAYS,
        ema_count=HISTORICAL_MIN_EMAS,
        ema_span_days=HISTORICAL_MIN_EMA_SPAN_DAYS,
    ) is False


def test_historical_relationship_fails_just_under_valid_sensor_days():
    assert is_historical_relationship_eligible(
        calendar_days=HISTORICAL_MIN_CALENDAR_DAYS,
        valid_sensor_days=HISTORICAL_MIN_VALID_SENSOR_DAYS - 1,
        ema_count=HISTORICAL_MIN_EMAS,
        ema_span_days=HISTORICAL_MIN_EMA_SPAN_DAYS,
    ) is False


def test_historical_relationship_fails_just_under_ema_count():
    assert is_historical_relationship_eligible(
        calendar_days=HISTORICAL_MIN_CALENDAR_DAYS,
        valid_sensor_days=HISTORICAL_MIN_VALID_SENSOR_DAYS,
        ema_count=HISTORICAL_MIN_EMAS - 1,
        ema_span_days=HISTORICAL_MIN_EMA_SPAN_DAYS,
    ) is False


def test_historical_relationship_fails_just_under_ema_span():
    assert is_historical_relationship_eligible(
        calendar_days=HISTORICAL_MIN_CALENDAR_DAYS,
        valid_sensor_days=HISTORICAL_MIN_VALID_SENSOR_DAYS,
        ema_count=HISTORICAL_MIN_EMAS,
        ema_span_days=HISTORICAL_MIN_EMA_SPAN_DAYS - 1,
    ) is False


def test_historical_relationship_eligible_does_not_imply_state_c_alone_is_checked():
    """is_historical_relationship_eligible does not itself re-check State C —
    a caller must confirm classify_state == C separately. Documents the
    current API shape rather than silently assuming it's checked internally."""
    # Passes the 56-day gate even though calendar_days alone would also
    # qualify for State C — this test exists to make the two-function split
    # explicit for future readers.
    assert is_historical_relationship_eligible(100, 100, 20, 100) is True
    assert classify_state(100, 100, 20) == ColdStartState.C_FULL_HISTORY


# --- Deprecated wrapper — kept working, not silently dropped -----------------

def test_deprecated_is_eligible_still_importable_and_callable():
    eligible, reason = is_eligible(coverage_ratio=1.0, n_prior_baseline_windows=10)
    assert eligible is True
    assert reason is None


def test_deprecated_is_eligible_insufficient_window():
    eligible, reason = is_eligible(coverage_ratio=0.1, n_prior_baseline_windows=10)
    assert eligible is False
    assert reason == "ineligible_insufficient_window"
