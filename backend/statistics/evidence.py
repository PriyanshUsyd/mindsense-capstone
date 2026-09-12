"""
Per-person evidence-strength classification (Week 4 doc Section 7) and the
exploratory-family (BH-FDR) / confirmatory-family (Holm) correction across
the full model-frame cohort, collapsed to the two-valued user-facing
contract (CLAUDE.md: "User-facing is binary: evidence_available /
no_claim").

Ports Moe Tanaka's `analysis/evidence_model.py` per-person logic onto this
package's existing R-backed `fit_ar1_effect` (AR(1)-corrected fixed effect
+ real per-person BLUPs, via R `nlme::lme` + `corAR1`) instead of her
original module's own uncorrected statsmodels `MixedLM` per-person
estimates — this keeps the serial-correlation correction that only this
engine has (see `mixed_effects_model.py`'s "Before/after" section: the
within-person point estimate moves materially once AR(1) is applied
properly). Applied here on Moe's behalf per her offer to do this port
herself; flagged throughout for her review, not presented as a final,
signed-off implementation.

`analysis/evidence_model.py`'s three-state cold-start policy is NOT
re-ported here because it already has an equivalent, independently
verified implementation in `backend.statistics.eligibility`
(`classify_state` / `ColdStartState`) — confirmed 2026-09-12 to use
identical gates (State B: 7 calendar days / 5 valid sensor-days / 1 EMA;
State C: 28 / 20 / 3; historical: 56 / 40 / 8 + 28-day EMA span). Nothing
to do there.

FLAGGED, NOT SILENTLY GUESSED — one genuine scope gap versus Moe's
original module: her Python per-person significance test approximated
Var(slope_i) ~= Var(beta1_hat) + Var(BLUP_i) using statsmodels' exposed
covariance objects (itself already documented there as an approximation,
since MixedLM doesn't expose the *true* joint covariance either).
`backend.statistics.r_bridge`'s R `nlme` wrapper does not currently
extract any per-person BLUP variance/SE at all — `nlme::ranef()` has no
equivalent to lme4's `condVar`; getting one legitimately requires either
`nlme::ranef(model, standard = TRUE)` (which tests a *different*
hypothesis — "does this person deviate from the population mean", not
"is this person's total slope different from zero") or a custom
delta-method/bootstrap variance this module does not implement.

Rather than fabricate a per-person p-value from a standard error we
cannot actually derive yet — which in a safety-relevant, mental-health-
adjacent system means confidently labelling someone's data as
`evidence_available` on an invented number — `extract_person_slopes`
below leaves `slope_se` / `slope_p` as `None`, and `reclassify_family213`
therefore classifies every person "insufficient" (-> "no_claim") until
this is closed. This is a deliberate fail-safe default, not a bug: it
matches this codebase's existing convergence-policy philosophy of
flagging a real gap clearly rather than quietly guessing at a number
that determines a mental-health-adjacent claim. Closing it requires
extending `backend.statistics.r_bridge.fit_lme_ar1` with a real per-person
conditional variance for the `x_within` BLUP (or an agreed alternative) —
Moe Tanaka owns this model and offered to complete this specific port;
this gap is for her review, not resolved here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

from backend.statistics.mixed_effects_model import Ar1EffectResult, classify_evidence_strength

X_WITHIN_TERM = "x_within"

# CLAUDE.md "Finalised decisions": "Cohort-level family = 213, BH-FDR is
# the reported value, Holm is the sensitivity analysis." Not enforced as a
# hard assertion here (a given run's actual eligible cohort size is real
# data, not a constant) — recorded so a run whose family size drifts far
# from 213 is visibly worth a second look, not silently accepted.
EXPECTED_FAMILY_SIZE = 213


@dataclass
class PersonSlope:
    """One person's per-person within-subject slope estimate for this
    feature, from `fit_ar1_effect`'s AR(1)-corrected fixed effect + BLUP —
    NOT from an uncorrected fixed-effects-only or GEE population-averaged
    fit. `slope_se` / `slope_p` are `None` until the SE gap in this
    module's docstring is closed."""

    uid: str
    slope_i: float
    n_occasions: int
    slope_se: float | None = None
    slope_p: float | None = None


def extract_person_slopes(
    ar1_result: Ar1EffectResult,
    model_frame: pd.DataFrame,
    uid_col: str = "uid",
    x_within_term: str = X_WITHIN_TERM,
) -> list[PersonSlope]:
    """Per-person slope_i = the AR(1)-corrected fixed effect
    (`ar1_result.params[x_within_term]`) + that person's real BLUP
    deviation (`ar1_result.blups[uid][x_within_term]`) — Moe's per-person
    estimate, now built on the R-backed AR(1) fit instead of her own
    uncorrected Python `MixedLM` random effects.

    `n_occasions` is this person's row count in `model_frame` — the same
    frame passed to `fit_mixed_effects_model` / `fit_ar1_effect` — used
    downstream for the evidence-strength occasion-count gate (Section 7).

    Raises `ValueError` if `ar1_result` carries no BLUPs at all (i.e. it
    came from the GEE fallback, not the R engine): per-person slopes are
    only meaningful with real per-person random effects, never with GEE's
    population-averaged estimate, which has none.
    """
    if ar1_result.blups is None:
        raise ValueError(
            "extract_person_slopes requires per-person BLUPs, which only "
            f"the R engine produces (got engine={ar1_result.engine!r}). "
            "The GEE fallback (R unavailable) is population-averaged and "
            "has no per-person random effect to extract — see "
            "docs/statistics/r-bridge-setup.md to make R usable."
        )

    beta = ar1_result.params[x_within_term]
    n_occasions_by_uid = model_frame.groupby(uid_col).size().to_dict()

    person_slopes = []
    for uid, effects in ar1_result.blups.items():
        u_i = effects.get(x_within_term, 0.0)
        person_slopes.append(
            PersonSlope(
                uid=uid,
                slope_i=beta + u_i,
                n_occasions=int(n_occasions_by_uid.get(uid, 0)),
                slope_se=None,  # see module docstring's flagged SE gap
                slope_p=None,
            )
        )
    return person_slopes


def _nan_safe_correction(pvalues: np.ndarray, method: str) -> np.ndarray:
    """Applies `method` ("holm" or "fdr_bh") to the non-NaN p-values only,
    writing adjusted values back into their original positions and
    leaving NaN entries as NaN — ported from
    `analysis/evidence_model.py::_adjust_ignoring_nan`.

    Without this, `statsmodels.stats.multitest.multipletests` propagates a
    single NaN across the WHOLE input (`[0.01, nan, 0.5] -> [nan, nan,
    nan]`), which would silently reclassify every other participant's
    label as "insufficient" too just because one person's test was
    undefined. The family size is the number of tests actually corrected
    (non-NaN); a person whose test is undefined is excluded from the
    family, not treated as having failed it.
    """
    arr = np.asarray(pvalues, dtype=float)
    out = np.full(arr.shape, np.nan)
    defined = ~np.isnan(arr)
    if defined.any():
        _, adjusted, _, _ = multipletests(arr[defined], alpha=0.05, method=method)
        out[defined] = adjusted
    return out


def reclassify_family213(
    person_slopes: list[PersonSlope],
    outcome_sd: float,
    predictor_sd: float,
) -> pd.DataFrame:
    """Per-person exploratory family = every participant who produced a
    candidate `slope_i` for this feature (Moe's documented choice — see
    `analysis/evidence_model.py::reclassify_family213`'s docstring for why
    this, not a family-of-1, is the right family size once a feature
    reaches production). BH-FDR (`label_bh`) is the reported/production
    value; Holm (`label_holm`) is the sensitivity analysis (CLAUDE.md).

    Every person's `slope_p` is currently `None` (see module docstring's
    flagged SE gap), so `bh_q_213` / `holm_p_213` are NaN for everyone and
    `classify_evidence_strength` returns "insufficient" for the whole
    cohort — which maps through `to_user_facing_evidence` to "no_claim"
    for everyone — until that gap is closed. This is the correct, safe
    behaviour given an unknown per-person standard error, not a bug in
    this function: it fails toward under-claiming, never toward an
    unearned "evidence_available".
    """
    uids = [p.uid for p in person_slopes]
    slope_i = np.array([p.slope_i for p in person_slopes], dtype=float)
    n_occasions = np.array([p.n_occasions for p in person_slopes], dtype=int)
    raw_p = np.array(
        [p.slope_p if p.slope_p is not None else np.nan for p in person_slopes],
        dtype=float,
    )

    bh_q = _nan_safe_correction(raw_p, "fdr_bh")
    holm_p = _nan_safe_correction(raw_p, "holm")
    std_effect = np.abs(slope_i) * predictor_sd / outcome_sd

    def _labels(q_values: np.ndarray) -> list[str]:
        return [
            classify_evidence_strength(float(q), float(eff), int(n))
            if not np.isnan(q)
            else "insufficient"
            for q, eff, n in zip(q_values, std_effect, n_occasions)
        ]

    return pd.DataFrame(
        {
            "uid": uids,
            "slope_i": slope_i,
            "n_occasions": n_occasions,
            "std_effect": std_effect,
            "bh_q_213": bh_q,
            "holm_p_213": holm_p,
            "label_bh": _labels(bh_q),
            "label_holm": _labels(holm_p),
        }
    )


def to_user_facing_evidence(label: str) -> str:
    """Collapse the 4-level evidence-strength label to the 2-value
    user-facing contract (CLAUDE.md: "User-facing is binary
    (evidence_available / no_claim)") — ported unchanged from
    `analysis/evidence_model.py::to_user_facing_evidence`.

    strong & moderate -> "evidence_available" (may be surfaced, with the
    required hedge/uncertainty language); weak & insufficient ->
    "no_claim" (say nothing about the relationship). The 4-level label is
    unchanged and still used everywhere else (reports, analysis, per-person
    tables); only this user-facing mapping is 2-valued.
    """
    if label in ("strong", "moderate"):
        return "evidence_available"
    if label in ("weak", "insufficient"):
        return "no_claim"
    raise ValueError(f"unrecognised evidence_strength label: {label!r}")
