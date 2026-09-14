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
below leaves `slope_se` / `slope_p` as `None` by default, and
`reclassify_family213` therefore classifies every person "insufficient"
(-> "no_claim") unless a caller explicitly opts into a method that
populates them.

**Closed 2026-09-13, via bootstrap rather than delta method** — a
follow-up delta-method check (calling `nlme::simulate.lme` and
`nlme::ranef(model, standard = TRUE)` directly against the real fit)
confirmed the paragraph above: `nlme` genuinely has no per-person
conditional-variance extraction, and `simulate.lme` explicitly refuses
models with a `corStruct` (this one has `corAR1`). `backend.statistics
.bootstrap` implements two bootstrap SE estimators (parametric: resimulate
`y` from the fit's own generative parameters; cluster: case-resample
participants with replacement, run in a persistent process pool for a
real B=500-per-method production run) and `PersonSlope.slope_se`
/`.slope_p` can now be populated from either via
`bootstrap.build_person_slopes_from_bootstrap_se`. **Neither method is
used alone**: comparing both on the real dataset found they disagree not
just in scale but in what they are even sensitive to (see
`intersect_bootstrap_evidence`'s docstring for the full mechanism and
numbers) — so `intersect_bootstrap_evidence` combines
`reclassify_family213`'s output for each method, and only their
intersection (`label_intersection`) is used as the actual user-facing
value. This is a post-hoc decision, in the same register as the
cohort-level family size (213) and the binary user-facing collapse
(CLAUDE.md's "Finalised decisions") — Week 4's pre-registration did not
anticipate reconciling two different bootstrap estimators, only BH-FDR
over a single per-person test. Confirmed on the real dataset (B=500 both
methods): 23 of 214 participants are `evidence_available` under
intersection; see `docs/statistics/preregistration.md` section 4.1 and
`Week5_Statistical_Analysis_Deliverable.md` section 5.4 for the full
numbers (occasion-count correlation direction per method, SE-ratio range,
agreement table, split-half stability check).

**`bootstrap_person_slopes` below predates and is superseded by the above
— kept for reference, not deleted, not the function to call for a real
per-person SE.** It is an earlier, cluster-only implementation (2026-09-12,
Priyansh Khandelwal via an AI-assisted session) built and merged
independently, before the comparison above existed; its own docstring
still carries its original FLAGGED-for-sign-off status and a since-
superseded 2026-09-13 note about an `n_bootstrap=3` mechanism smoke test.
It was never reconciled with `backend.statistics.bootstrap`'s dual-method
design (a materially different cluster-bootstrap implementation exists in
both places now) — that reconciliation (retire one, or document why both
remain) is a call for whoever owns this module going forward, not resolved
by this merge.
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

    If every person's `slope_p` is `None` (i.e. `person_slopes` came
    straight from `extract_person_slopes`, before any SE estimate exists —
    see module docstring's flagged SE gap), `bh_q_213` / `holm_p_213` are
    NaN for everyone and `classify_evidence_strength` returns
    "insufficient" for the whole cohort — which maps through
    `to_user_facing_evidence` to "no_claim" for everyone. This is the
    correct, safe behaviour given an unknown per-person standard error,
    not a bug in this function: it fails toward under-claiming, never
    toward an unearned "evidence_available".

    `slope_se` / `slope_p` are carried through to the output unchanged
    (NaN where `person_slopes` didn't have them) purely for downstream
    transparency/auditing — e.g. `intersect_bootstrap_evidence` below,
    which calls this function once per bootstrap method and needs each
    method's own SE alongside its label to build a combined table.
    """
    uids = [p.uid for p in person_slopes]
    slope_i = np.array([p.slope_i for p in person_slopes], dtype=float)
    n_occasions = np.array([p.n_occasions for p in person_slopes], dtype=int)
    slope_se = np.array(
        [p.slope_se if p.slope_se is not None else np.nan for p in person_slopes],
        dtype=float,
    )
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
            "slope_se": slope_se,
            "slope_p": raw_p,
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


def intersect_bootstrap_evidence(
    parametric: pd.DataFrame,
    cluster: pd.DataFrame,
) -> pd.DataFrame:
    """[POST-HOC, 2026-09-13] Combines two independent
    `reclassify_family213` outputs — one per bootstrap SE estimator from
    `backend.statistics.bootstrap` (parametric: resimulate `y` from the
    fitted model's own generative parameters; cluster: case-resample
    participants with replacement) — into one per-person table, adding
    `label_intersection`: the **already user-facing, 2-valued**
    (`evidence_available` / `no_claim`) label, `evidence_available` only
    where *both* methods' own BH labels independently collapse to
    `evidence_available` via `to_user_facing_evidence`. Pass
    `label_intersection` straight to the user-facing contract — it is not
    a 4-tier label and must not be run back through
    `to_user_facing_evidence` (that raises on values outside
    strong/moderate/weak/insufficient).

    **Why an intersection, not either method alone (post-hoc, not
    pre-registered):** closing this module's per-person SE gap (module
    docstring) needs a real per-person standard error, which `nlme` has
    no direct way to supply (no `lme4::condVar` equivalent — confirmed by
    a delta-method check before bootstrapping was attempted at all).
    Comparing the two bootstrap designs on the real dataset (B=500 each)
    showed they are not just differently *scaled* but differently
    *sensitive*: parametric SE correlates **positively** with a person's
    occasion count (Spearman rho ~= +0.81) — more occasions means less
    BLUP shrinkage, so more of the true random-slope variance passes
    through into how much `slope_i` itself varies across resimulated
    draws — while cluster (case-resampling) SE correlates **negatively**
    with occasion count (rho ~= -0.33) — more of a person's own real,
    unchanging data makes their contribution more stable against which
    other participants get resampled alongside them, the ordinary "more
    data, smaller SE" pattern. Driven by the same variable in opposite
    directions, the two methods' per-person SE *rankings* end up
    negatively correlated with each other (rho ~= -0.397, not merely a
    constant rescaling — the SE ratio itself ranges ~1.05x-29.5x across
    people, mean ~7.85x). Neither is a defensible per-person SE on its
    own: cluster's SE is small specifically because it never re-draws a
    selected person's own observed trajectory, only who else is
    resampled alongside them — it does not encode the uncertainty from
    that person's data having come out differently, which is exactly
    what a person-level SE is supposed to capture, so it understates it;
    parametric's SE reflects genuine generative uncertainty but is
    dominated by a shrinkage-strength effect tied to occasion count, a
    different quantity from "how uncertain is this person's estimated
    slope." Requiring both to independently agree is the safe combination
    given that neither survives scrutiny alone — the same
    fail-toward-under-claiming stance `reclassify_family213` already
    takes when `slope_p` is entirely unknown, applied here to "SE is
    known but from two mutually-inconsistent estimators" instead.

    This is exactly the kind of decision CLAUDE.md's "Finalised
    decisions" section already contains post-hoc entries for (the
    cohort-level family size of 213; the binary user-facing collapse):
    Week 4's pre-registration defined BH-FDR correction over a single
    per-person test, not reconciliation across two different bootstrap SE
    estimators — this was not anticipated because the SE gap itself
    wasn't foreseen as needing a bootstrap in the first place.

    Confirmed on the real dataset (B=500 both methods, 2026-09-13): 23 of
    214 participants are `label_intersection == "evidence_available"`.
    The disagreement is **one-directional**: every participant parametric
    calls `evidence_available` is also called `evidence_available` by
    cluster (zero counter-examples); cluster additionally calls 28 more
    participants `evidence_available` that parametric does not — matching
    the expectation that cluster's smaller SE is the more permissive
    (and, per the mechanism above, less trustworthy on its own) side.
    Intersection therefore numerically equals parametric's own set here,
    though the *rule* is "both agree," not "defer to parametric" — a
    dataset where cluster's set were instead a strict subset of
    parametric's would produce a different intersection than either
    parent set alone.

    Parametric-only and cluster-only classifications (`label_bh` /
    `label_holm` per method, from `reclassify_family213` directly) are
    NOT superseded by this function — keep both DataFrames passed in here
    as standalone sensitivity analyses; nothing about adding an
    intersection view retires the single-method view.
    """
    shared_cols = ["uid", "slope_i", "n_occasions", "std_effect"]
    per_method_cols = ["slope_se", "slope_p", "bh_q_213", "holm_p_213", "label_bh", "label_holm"]

    combined = parametric[shared_cols + per_method_cols].merge(
        cluster[["uid", *per_method_cols]],
        on="uid",
        suffixes=("_parametric", "_cluster"),
    )
    combined = combined.rename(
        columns={"label_bh_parametric": "label_parametric", "label_bh_cluster": "label_cluster"}
    )

    user_facing_parametric = combined["label_parametric"].apply(to_user_facing_evidence)
    user_facing_cluster = combined["label_cluster"].apply(to_user_facing_evidence)
    combined["label_intersection"] = np.where(
        (user_facing_parametric == "evidence_available") & (user_facing_cluster == "evidence_available"),
        "evidence_available",
        "no_claim",
    )
    return combined
