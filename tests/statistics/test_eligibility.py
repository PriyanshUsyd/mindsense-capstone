from backend.statistics.eligibility import (
    MIN_BASELINE_WINDOWS,
    MIN_COVERAGE_RATIO,
    is_eligible,
)


def test_eligible_when_both_thresholds_met():
    eligible, reason = is_eligible(coverage_ratio=1.0, n_prior_baseline_windows=MIN_BASELINE_WINDOWS)
    assert eligible is True
    assert reason is None


def test_ineligible_insufficient_window():
    eligible, reason = is_eligible(coverage_ratio=MIN_COVERAGE_RATIO - 0.01, n_prior_baseline_windows=10)
    assert eligible is False
    assert reason == "ineligible_insufficient_window"


def test_ineligible_insufficient_baseline():
    eligible, reason = is_eligible(coverage_ratio=1.0, n_prior_baseline_windows=MIN_BASELINE_WINDOWS - 1)
    assert eligible is False
    assert reason == "ineligible_insufficient_baseline"
