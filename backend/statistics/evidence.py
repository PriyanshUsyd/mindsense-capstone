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
below still leaves `slope_se` / `slope_p` as `None` by default, and
`reclassify_family213` therefore still classifies every person
"insufficient" (-> "no_claim") unless a caller explicitly opts into the
method below.

**2026-09-12 — a candidate fix, NOT a finalised statistical decision,
implemented and FLAGGED FOR MOE TANAKA'S SIGN-OFF before any per-person
"evidence_available" is shown to a real user on the strength of it:**
`bootstrap_person_slopes` below estimates each person's `slope_se` via a
**cluster (case) bootstrap over participants** — resample participants
with replacement, refit the real R AR(1) model on each resample, and use
the empirical standard deviation of a person's `slope_i` across resamples
as `slope_se`. This is a standard, well-established technique for exactly
this situation (no analytical per-subject variance available from the
fitting package — Van der Leeden, Meijer & Busing 2008; Goldstein 2011,
on bootstrapping multilevel models) and does not require guessing a
number: it is a real, cited, defensible method. It is flagged rather than
treated as settled because (a) it is still a *methodology choice* among
more than one legitimate option (an alternative would be a parametric/
delta-method approximation combining `vcov(model)` with an approximation
of the random-effect posterior variance; that is not implemented here),
(b) the number of bootstrap replicates trades off directly against
compute cost and precision of the SE estimate, and (c) as of 2026-09-13 it
has been exercised exactly once against the real dataset in an environment
where R was genuinely available (`r_bridge.r_bridge_available()` returned
`True`), as a one-off diagnostic smoke test — `n_bootstrap=3` (far below
this function's own `n_bootstrap=200` default), 214 participants, 28,320
occasions. It completed without error in 107.5s, which is the useful
finding (the mechanism itself runs end-to-end against a genuine R
`nlme::lme` refit, not just the fake fits in
`tests/statistics/test_evidence.py`) — but at that deliberately tiny
replicate count, **45 of 214 participants (21%) received `slope_se=None`**
because they were never drawn in any of the 3 resamples, exactly the
failure mode already documented above and a concrete illustration of why a
real run needs far more than 3 replicates. This was a mechanism check
only, not a production run, not a validation of the method, and not Moe
Tanaka's sign-off. Moe Tanaka owns this model and offered to complete this
specific port; treat this as "implemented using a cluster bootstrap,
mechanism now confirmed to run against real R, still needs her sign-off on
method (parametric vs. cluster) and replicate count," not as a closed item.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
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


def _default_ar1_fit_fn(
    frame: pd.DataFrame,
    outcome_col: str,
    uid_col: str,
    extra_fixed_effects: list[str] | None,
) -> Ar1EffectResult:
    """The real fitting call `bootstrap_person_slopes` uses by default —
    forces the R engine (`prefer_r=True` is `fit_ar1_effect`'s default,
    made explicit here) because bootstrap SEs are only meaningful built on
    the same real per-person BLUPs `extract_person_slopes` requires."""
    from backend.statistics.mixed_effects_model import fit_ar1_effect

    return fit_ar1_effect(
        frame, outcome_col=outcome_col, uid_col=uid_col, extra_fixed_effects=extra_fixed_effects, prefer_r=True
    )


def bootstrap_person_slopes(
    model_frame: pd.DataFrame,
    outcome_col: str = "phq4_score",
    uid_col: str = "uid",
    x_within_term: str = X_WITHIN_TERM,
    extra_fixed_effects: list[str] | None = None,
    n_bootstrap: int = 200,
    seed: int = 0,
    fit_fn: Callable[[pd.DataFrame, str, str, list[str] | None], Ar1EffectResult] | None = None,
) -> list[PersonSlope]:
    """**Candidate fix for the SE gap above — FLAGGED FOR MOE TANAKA'S
    SIGN-OFF, not a finalised statistical decision** (see module
    docstring). Estimates each person's `slope_se` via a cluster (case)
    bootstrap over participants, then derives a two-sided normal-
    approximation `slope_p` from `slope_i / slope_se` — the same
    Var(slope_i)-based approach Moe's original
    `analysis/archive/evidence_model.py` used, just with the variance
    itself now coming from a bootstrap instead of an approximation this
    codebase cannot compute analytically for the R `nlme` engine.

    Procedure, one bootstrap replicate at a time:
      1. Resample participant `uid`s **with replacement**, same count as
         the original cohort (a case/cluster bootstrap: the unit of
         resampling is the *person*, not the occasion — resampling
         occasions directly would break each person's own within-person
         structure, which is the entire estimand here).
      2. Re-label a participant sampled more than once with a distinct
         suffix (e.g. `"u007__1"`) so the refit treats each copy as its
         own group — reusing the same `uid_col` value for both would
         silently collapse two independent bootstrap draws into one
         random-effect group.
      3. Refit via `fit_fn` (default: `fit_ar1_effect(..., prefer_r=True)`
         — requires the real R engine; raises if BLUPs aren't available,
         same fail-safe posture as `extract_person_slopes`).
      4. Map each relabelled group's `slope_i = beta + BLUP_i` back to its
         real `uid` and accumulate it across replicates.

    After all replicates, `slope_se` for a person is the sample standard
    deviation (`ddof=1`) of their accumulated bootstrap `slope_i` values.
    A person who was never drawn in any replicate (possible, though
    unlikely at `n_bootstrap=200` for a ~200-participant cohort) gets
    `slope_se=None` — reported honestly as "still insufficient," not
    silently defaulted to 0 or dropped.

    `n_bootstrap` (default 200): a real, disclosed tradeoff, not a hidden
    constant — more replicates narrow the bootstrap's own Monte Carlo
    error on the SE estimate, at directly proportional compute cost (each
    replicate is a full R `nlme::lme` AR(1) refit on ~28k occasions,
    which is not cheap; a smaller `n_bootstrap` is defensible for a quick
    check, a larger one for a number that will actually be reported).

    The returned `slope_i` point estimate is always the ORIGINAL fit's
    value (from `extract_person_slopes` on the non-bootstrapped
    `model_frame`), never the bootstrap mean — the bootstrap contributes
    only the standard error, not a re-estimated point.
    """
    from backend.statistics.mixed_effects_model import fit_ar1_effect

    fit_fn = fit_fn or _default_ar1_fit_fn
    rng = np.random.default_rng(seed)

    original_ar1 = fit_ar1_effect(model_frame, outcome_col=outcome_col, uid_col=uid_col, prefer_r=True)
    original_slopes = {
        p.uid: p for p in extract_person_slopes(original_ar1, model_frame, uid_col=uid_col, x_within_term=x_within_term)
    }

    uids = model_frame[uid_col].unique()
    bootstrap_slopes: dict[str, list[float]] = {uid: [] for uid in uids}

    for _ in range(n_bootstrap):
        sampled_uids = rng.choice(uids, size=len(uids), replace=True)

        parts = []
        relabel_to_original: dict[str, str] = {}
        draw_counts: dict[str, int] = {}
        for original_uid in sampled_uids:
            draw_counts[original_uid] = draw_counts.get(original_uid, 0) + 1
            relabelled_uid = f"{original_uid}__{draw_counts[original_uid]}"
            relabel_to_original[relabelled_uid] = original_uid

            person_rows = model_frame.loc[model_frame[uid_col] == original_uid].copy()
            person_rows[uid_col] = relabelled_uid
            parts.append(person_rows)

        bootstrap_frame = pd.concat(parts, ignore_index=True)

        boot_ar1 = fit_fn(bootstrap_frame, outcome_col, uid_col, extra_fixed_effects)
        if boot_ar1.blups is None:
            raise ValueError(
                "bootstrap_person_slopes requires per-person BLUPs on every "
                f"replicate, got engine={boot_ar1.engine!r} on one replicate — "
                "the R engine must be usable for the entire bootstrap run, "
                "not just the original fit."
            )

        beta_boot = boot_ar1.params[x_within_term]
        for relabelled_uid, effects in boot_ar1.blups.items():
            original_uid = relabel_to_original.get(relabelled_uid)
            if original_uid is None:
                continue  # shouldn't happen; defensive, not silently wrong
            u_i = effects.get(x_within_term, 0.0)
            bootstrap_slopes[original_uid].append(beta_boot + u_i)

    person_slopes = []
    for uid, original in original_slopes.items():
        draws = bootstrap_slopes.get(uid, [])
        if len(draws) >= 2:
            se = float(np.std(draws, ddof=1))
            z = original.slope_i / se if se > 0 else np.nan
            p = float(2 * scipy_stats.norm.sf(abs(z))) if np.isfinite(z) else None
        else:
            se = None
            p = None
        person_slopes.append(
            PersonSlope(
                uid=uid,
                slope_i=original.slope_i,
                n_occasions=original.n_occasions,
                slope_se=se,
                slope_p=p,
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
