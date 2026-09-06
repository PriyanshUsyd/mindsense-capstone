"""Baseline computation, sufficiency gates, and three-state cold-start policy
(Week 4 doc, sections 4-5). Chatbot-runtime view: trailing windows as of a
given report_date -- an EMA occasion date, evaluated per-occasion (see
run_week5_pipeline.run_cold_start_snapshot) -- distinct from the one-time
full-history mean used for the LMM research fit (predictors.py).

Week 4 open item #4 ("keep the 7-day user-facing recency window, or align it
to the 14-day model window") is resolved here: DECIDED to unify to 14 days.
The recency window now reuses ALIGN_WINDOW_DAYS / ALIGN_WINDOW_LAG_DAYS from
predictors.py instead of a separate RECENCY_WINDOW_DAYS=7. This is a design
decision closing a previously-open item, not a bug fix -- the old 7-day
window was a valid, deliberate Week 4 choice, just not the one the team has
since settled on. Window constants are imported from predictors.py, not
redefined here, so the two can't drift apart.
"""
import numpy as np
import pandas as pd

from predictors import ALIGN_WINDOW_DAYS, ALIGN_WINDOW_LAG_DAYS, OCCASION_MIN_VALID_DAYS

BASELINE_MIN_DAYS = 28
BASELINE_TARGET_DAYS = 56
MEANINGFUL_Z = 1.0

# Sufficiency gates: (min calendar days, min valid sensor-days in window, min EMAs in window)
GATE_DESCRIPTIVE = dict(calendar_days=7, valid_sensor_days=5, ema_count=1)
GATE_COMPARATIVE = dict(calendar_days=28, valid_sensor_days=20, ema_count=3)
GATE_HISTORICAL = dict(calendar_days=56, valid_sensor_days=40, ema_count=8)


def _count_in_window(dates: pd.DatetimeIndex, end_date, window_days: int) -> int:
    start_date = end_date - pd.Timedelta(days=window_days - 1)
    return int(((dates >= start_date) & (dates <= end_date)).sum())


def evaluate_person_feature(
    daily_dates_valid: pd.DatetimeIndex,
    daily_values_clean: pd.Series,
    ema_dates: pd.DatetimeIndex,
    first_history_date,
    report_date,
) -> dict:
    """Evaluate cold-start state A/B/C for one participant x one feature x one
    EMA occasion (report_date = that occasion's date -- called once per
    occasion, not once per participant; see run_cold_start_snapshot).

    daily_dates_valid: dates where the cleaned feature is non-null (post cleaning.py gates)
    daily_values_clean: Series indexed by date of the cleaned (pre-transform) value, for
        computing baseline_mean/SD and the recency deviation
    """
    calendar_days = (report_date - first_history_date).days + 1
    total_ema = int((ema_dates <= report_date).sum())

    if calendar_days < 7 or total_ema == 0:
        return {"state": "A", "reason": "below no-data threshold", "calendar_days": calendar_days,
                "ema_count_total": total_ema}

    # Recency window = the 14-day model alignment window (Week 4 open item #4,
    # resolved: unify rather than keep a separate 7-day user-facing window).
    # Ends ALIGN_WINDOW_LAG_DAYS before report_date, same construction as
    # predictors._window_stats.
    recency_end = report_date - pd.Timedelta(days=ALIGN_WINDOW_LAG_DAYS)
    recency_start = recency_end - pd.Timedelta(days=ALIGN_WINDOW_DAYS - 1)
    recency_vals = daily_values_clean.loc[recency_start:recency_end].dropna()
    recency_n_valid = len(recency_vals)

    # Baseline window ends exactly where the recency window's day before
    # start would be -- adjacent, never overlapping, by construction.
    baseline_end = report_date - pd.Timedelta(days=ALIGN_WINDOW_DAYS + ALIGN_WINDOW_LAG_DAYS)

    def window_gate(window_days: int):
        start = baseline_end - pd.Timedelta(days=window_days - 1)
        vals = daily_values_clean.loc[start:baseline_end].dropna()
        ema_n = _count_in_window(ema_dates, baseline_end, window_days)
        span_days = (baseline_end - first_history_date).days + 1
        return vals, ema_n, span_days

    base28_vals, base28_ema, span28 = window_gate(BASELINE_MIN_DAYS)
    base56_vals, base56_ema, span56 = window_gate(BASELINE_TARGET_DAYS)

    comparative_ok = (
        span28 >= GATE_COMPARATIVE["calendar_days"]
        and len(base28_vals) >= GATE_COMPARATIVE["valid_sensor_days"]
        and base28_ema >= GATE_COMPARATIVE["ema_count"]
    )
    historical_ok = (
        span56 >= GATE_HISTORICAL["calendar_days"]
        and len(base56_vals) >= GATE_HISTORICAL["valid_sensor_days"]
        and base56_ema >= GATE_HISTORICAL["ema_count"]
    )

    descriptive_ok = (
        calendar_days >= GATE_DESCRIPTIVE["calendar_days"]
        and len(daily_values_clean.dropna()) >= GATE_DESCRIPTIVE["valid_sensor_days"]
        and total_ema >= GATE_DESCRIPTIVE["ema_count"]
    )

    if not descriptive_ok:
        return {"state": "A", "reason": "below descriptive sufficiency gate",
                "calendar_days": calendar_days, "ema_count_total": total_ema}

    result = {
        "calendar_days": calendar_days,
        "ema_count_total": total_ema,
        "recency_n_valid_days": recency_n_valid,
        "recency_mean": float(recency_vals.mean()) if recency_n_valid else np.nan,
        "baseline28_n_valid_days": len(base28_vals),
        "baseline28_ema_count": base28_ema,
        "baseline56_n_valid_days": len(base56_vals),
        "baseline56_ema_count": base56_ema,
        "historical_gate_met": historical_ok,
    }

    if not comparative_ok:
        result["state"] = "B"
        result["reason"] = "partial history: below 28-day comparative gate"
        return result

    baseline_mean = float(base28_vals.mean())
    baseline_sd = float(base28_vals.std(ddof=1)) if len(base28_vals) > 1 else np.nan
    result["state"] = "C"
    result["baseline_mean"] = baseline_mean
    result["baseline_sd"] = baseline_sd

    # Recency sufficiency gate: 14-day window needs >= OCCASION_MIN_VALID_DAYS
    # valid days, same threshold predictors.py uses for occasion validity.
    if recency_n_valid >= OCCASION_MIN_VALID_DAYS and baseline_sd and not np.isnan(baseline_sd) and baseline_sd > 0:
        z = (result["recency_mean"] - baseline_mean) / baseline_sd
        pct = 100 * (result["recency_mean"] - baseline_mean) / baseline_mean if baseline_mean else np.nan
        result["deviation_z"] = z
        result["deviation_pct"] = pct
        result["meaningful_change"] = abs(z) >= MEANINGFUL_Z
    else:
        result["deviation_z"] = np.nan
        result["meaningful_change"] = None
        result["reason"] = f"insufficient recent data (<{OCCASION_MIN_VALID_DAYS} days) for deviation statement"

    return result
