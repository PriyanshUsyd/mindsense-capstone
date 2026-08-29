"""
Eligibility / cold-start state logic.

SUPERSEDED CONSTANTS, UPDATED 2026-08-29: this module originally
implemented an AI-guessed 14-day/4-window default. Moe Tanaka has since
pushed the real, locked Week 4 spec at
weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md (merged into
main 2026-08-29) — the constants and the three-state logic below now match
his §4.3 sufficiency-gate table and §5 cold-start policy exactly. Treat his
document as the source of truth if this module and that document ever
diverge again.

Per-feature, per-report evaluation. The lowest qualifying state across a
turn's features governs that turn's framing (Moe's §5).
"""

from __future__ import annotations

from enum import Enum

# Moe's real §4.3 sufficiency gates (calendar days, valid sensor-days, EMAs).
STATE_B_MIN_CALENDAR_DAYS = 7
STATE_B_MIN_VALID_SENSOR_DAYS = 5
STATE_B_MIN_EMAS = 1

STATE_C_MIN_CALENDAR_DAYS = 28
STATE_C_MIN_VALID_SENSOR_DAYS = 20
STATE_C_MIN_EMAS = 3

HISTORICAL_MIN_CALENDAR_DAYS = 56
HISTORICAL_MIN_VALID_SENSOR_DAYS = 40
HISTORICAL_MIN_EMAS = 8
HISTORICAL_MIN_EMA_SPAN_DAYS = 28


class ColdStartState(str, Enum):
    A_INSUFFICIENT_DATA = "A"
    B_PARTIAL_HISTORY = "B"
    C_FULL_HISTORY = "C"


def classify_state(
    calendar_days: int, valid_sensor_days: int, ema_count: int
) -> ColdStartState:
    """Per-feature cold-start state, per Moe's §4.3/§5.

    Note: this only decides State A vs B vs C (descriptive vs comparative
    eligibility). Whether a *historical-relationship* statement is further
    allowed within State C additionally requires the 56-day gate
    (see is_historical_relationship_eligible) AND the evidence-strength gate
    (Moe's §7, not implemented here — that's a statistical judgment on the
    fitted model's output, not a data-sufficiency check).
    """
    if (
        calendar_days < STATE_B_MIN_CALENDAR_DAYS
        or ema_count < 1
        or valid_sensor_days < STATE_B_MIN_VALID_SENSOR_DAYS
    ):
        return ColdStartState.A_INSUFFICIENT_DATA

    if (
        calendar_days >= STATE_C_MIN_CALENDAR_DAYS
        and valid_sensor_days >= STATE_C_MIN_VALID_SENSOR_DAYS
        and ema_count >= STATE_C_MIN_EMAS
    ):
        return ColdStartState.C_FULL_HISTORY

    return ColdStartState.B_PARTIAL_HISTORY


def is_historical_relationship_eligible(
    calendar_days: int, valid_sensor_days: int, ema_count: int, ema_span_days: int
) -> bool:
    """The stricter 56-day gate for historical-relationship ("your mood
    tends to...") statements, on top of already being in State C. Does NOT
    check the evidence-strength gate (Moe's §7) — that's a separate,
    model-output-dependent check."""
    return (
        calendar_days >= HISTORICAL_MIN_CALENDAR_DAYS
        and valid_sensor_days >= HISTORICAL_MIN_VALID_SENSOR_DAYS
        and ema_count >= HISTORICAL_MIN_EMAS
        and ema_span_days >= HISTORICAL_MIN_EMA_SPAN_DAYS
    )


def is_eligible(coverage_ratio: float, n_prior_baseline_windows: int) -> tuple[bool, str | None]:
    """DEPRECATED — kept only so any code/tests written against the old
    AI-guessed placeholder don't hard-crash on import. New code should use
    classify_state() instead, which implements Moe's real gates. Do not add
    new callers of this function."""
    if coverage_ratio < 10 / 14:
        return False, "ineligible_insufficient_window"
    if n_prior_baseline_windows < 4:
        return False, "ineligible_insufficient_baseline"
    return True, None
