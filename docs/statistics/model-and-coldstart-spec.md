# Statistics — Week 4 Spec (Moe Tanaka's role)

**Status: DRAFT, built to fill a Week 4 gap found on 2026-08-29 (no prior repo
artifact existed for this task).** The exact statistical model itself was
already locked in `build-reference.md` Section 4 and `skills/statistics-mixedlm.md`
before this document — this file exists to (1) point at that lock explicitly,
and (2) propose the two things Week 4 still required that were genuinely
undecided: a specific baseline-window day count, and the three-state
cold-start policy text. **Moe still needs to review and sign off on the two
numeric choices below — they are defensible engineering defaults, not a
statistical judgment call that should be finalised by anyone other than the
Statistical Analysis Lead.**

## 1. The exact statistical model (already locked, restated here for Week 4 record-keeping)

Linear mixed-effects model, participant random intercept, person-mean-centred predictors:

```
PHQ4_it = B0 + Bw(x_it - x_mean_i) + Bb * x_mean_i + Bt * time_it + b0_i + e_it
```

- Library: `statsmodels.MixedLM` only. No scikit-learn anywhere (build-reference.md decisions log).
- `Bw` is the only coefficient allowed to back a "you vs. your own baseline" statement.
- Locked to the 2-feature Tier 1 set (GPS distance, unlock count/duration).
- Versioned via `model_spec_id` in the evidence contract (`backend/contracts/evidence.py`).

## 2. Minimum baseline window — proposed: 14 trailing days, 4 prior eligible windows

**Proposed values (DRAFT pending Moe's sign-off):**

- **Observation window per feature reading:** 14 trailing days ending immediately
  before the PHQ-4 timestamp it explains (build-reference.md Section 2, "Time
  alignment"). CES's weekly PHQ-4 cadence means a 14-day trailing window covers
  two PHQ-4 cycles, giving the aggregate more days to average over than a
  single 7-day window while still being "recent" relative to a person's
  current state.
- **Coverage threshold within that window:** at least 10 of the 14 days must
  have observed sensing data (`coverage_ratio >= 10/14 ≈ 0.71`) for the window
  to count at all.
- **Minimum prior eligible windows to compute a personal baseline:** 4. Below
  4 prior eligible windows, there isn't enough history to call something a
  stable personal baseline rather than noise — this is what gates
  `insufficient_data` in the eligibility rule below.

**Why these numbers, specifically:** CES has median ~170 PHQ-4 entries per
participant over up to 5 years, so requiring 4 prior weekly windows (~1 month
of history) before showing comparative evidence is a small fraction of a
typical participant's full history — it should not make most eligible
participants wait unreasonably long, while still ruling out a first-week
"here's your trend" claim built on one data point.

**This is the one field in the evidence contract that most needs Moe's own
judgment before contract-v1.0.0 is tagged** — these are reasonable defaults, not
a statistically-derived choice (e.g. via power analysis on CES's actual
within-person variance). Flagged explicitly to Priyansh for follow-up with Moe.

## 3. Eligibility rule (implements build-reference.md Section 4's "not just statistical" safety rule)

```python
def is_eligible(coverage_ratio: float, n_prior_baseline_windows: int) -> tuple[bool, str | None]:
    """See docs/statistics/model-and-coldstart-spec.md Section 2 for the constants."""
    MIN_COVERAGE_RATIO = 10 / 14
    MIN_BASELINE_WINDOWS = 4

    if coverage_ratio < MIN_COVERAGE_RATIO:
        return False, "ineligible_insufficient_window"
    if n_prior_baseline_windows < MIN_BASELINE_WINDOWS:
        return False, "ineligible_insufficient_baseline"
    return True, None
```

This must live in `backend/statistics/eligibility.py` (see stub committed
alongside this doc) — not hardcoded in the UI or the SLM layer.

## 4. Three-state cold-start policy (Week 4 required deliverable)

| State | Trigger | What the system is allowed to say |
|---|---|---|
| **Below-window** (`insufficient_data`) | `is_eligible()` returns `False` for either reason | Templated "not enough data" only. Uses claim id `not_enough_data`. No feature value, no direction, no comparison of any kind is shown — showing a number without a valid baseline invites a false comparison. |
| **Partial history** (`uncertainty`) | Eligible, but `evidence_strength == weak` (wide CI / small effective n even though the minimum thresholds are technically met) | A descriptive summary of the observed value only, with explicit "too early to compare confidently" language. Claim ids limited to `observation_of_deviation` + `uncertainty_disclosure` + `non_diagnostic_boundary` — `within_person_association` and `trend_description` are NOT allowed yet, since the association claim needs a confident estimate, not just a passed threshold. |
| **Full history** (`normal`) | Eligible AND `evidence_strength` is `moderate` or `strong` | Comparative statements allowed, using the full approved claim set (`observation_of_deviation`, `within_person_association`, `trend_description`, `uncertainty_disclosure`, `non_diagnostic_boundary`). Still never `diagnosis`/`causal_explanation`/`treatment_or_crisis_advice`/`risk_prediction`. |

This maps directly onto `ResponseMode` and `EligibilityStatus` /
`EvidenceStrength` already defined in `backend/contracts/evidence.py` — no new
enum values were needed to express it.

## What still needs a live human decision (not something to silently finalize)

1. Moe confirms or revises the 14-day / 4-window / 0.71-coverage constants above.
2. Moe confirms the `evidence_strength` banding rule (what CI width / p-value
   range counts as `weak` vs `moderate` vs `strong`) — not yet specified
   anywhere; the contract has the field, but the banding logic itself is
   Moe's to define per skills/statistics-mixedlm.md ("not a made-up confidence
   score — base it on actual model output").
