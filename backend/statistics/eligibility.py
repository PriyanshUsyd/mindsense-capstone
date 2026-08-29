"""
Eligibility rule — implements build-reference.md Section 4's "not just
statistical" safety rule and docs/statistics/model-and-coldstart-spec.md.

DRAFT — the two constants below are a proposed default, not yet signed off by
Moe Tanaka (Statistical Analysis Lead). See
docs/statistics/model-and-coldstart-spec.md Section 2 for the reasoning and
the explicit flag that this needs Moe's review before contract-v1.0.0.

This module intentionally contains nothing else — the eligibility check
belongs in Statistics's own code (skills/statistics-mixedlm.md: "This
eligibility check belongs in code, in your module — it is not something the
UI invents on its own with a hardcoded number").
"""

from __future__ import annotations

# See docs/statistics/model-and-coldstart-spec.md Section 2.
MIN_COVERAGE_RATIO = 10 / 14
MIN_BASELINE_WINDOWS = 4


def is_eligible(
    coverage_ratio: float, n_prior_baseline_windows: int
) -> tuple[bool, str | None]:
    """Returns (eligible, ineligible_reason). ineligible_reason matches the
    EligibilityStatus enum values in backend/contracts/evidence.py."""
    if coverage_ratio < MIN_COVERAGE_RATIO:
        return False, "ineligible_insufficient_window"
    if n_prior_baseline_windows < MIN_BASELINE_WINDOWS:
        return False, "ineligible_insufficient_baseline"
    return True, None
