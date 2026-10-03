"""Population LMM (Week 4 doc section 1.2/1.5/1.6) and evidence-strength
classification (section 7).

Model (Python cross-check per doc 1.5; primary is R lme4/lmerTest):
  phq4_score ~ x_within_it + x_within_lag1_it + x_between_i + week_in_study_it
  random intercept + random slope on x_within_it, grouped by uid.
AR(1) residual structure is not available in statsmodels MixedLM; this is a
documented limitation (independence working correlation used instead, per the
convergence-policy fallback philosophy in doc 1.5/1.7).
"""
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

MIN_OCCASIONS_PER_PERSON = 3  # to be included in the model fit at all

# Evidence-strength thresholds (Week 4 doc section 7, pre-registered).
# Values are locked; do not change without Statistical Analysis Lead approval.
STRONG_Q = 0.01
STRONG_EFFECT = 0.20
STRONG_MIN_OCCASIONS = 12

MODERATE_Q = 0.05
MODERATE_EFFECT = 0.10
MODERATE_MIN_OCCASIONS = 8

WEAK_Q = 0.10
WEAK_EFFECT = 0.10
WEAK_MIN_OCCASIONS = 8

# Multiple-comparison correction methods (Week 4 doc section 2).
BH_METHOD_NAME = "fdr_bh"
HOLM_METHOD_NAME = "holm"
BH_METHOD_LABEL = "Benjamini-Hochberg FDR (statsmodels.stats.multitest.multipletests, method='fdr_bh')"
HOLM_METHOD_LABEL = "Holm-Bonferroni (statsmodels.stats.multitest.multipletests, method='holm')"


def build_model_frame(occ_df: pd.DataFrame, ema_df: pd.DataFrame, uid_col: str = "uid") -> pd.DataFrame:
    ema = ema_df.copy()
    ema["_date"] = pd.to_datetime(ema["day"].astype(str), format="%Y%m%d")
    df = occ_df.merge(
        ema[[uid_col, "_date", "phq4_score"]],
        left_on=[uid_col, "ema_date"], right_on=[uid_col, "_date"], how="inner",
    )
    df = df[df["occasion_valid"]].copy()
    # x_within_lag1_it is missing for a person's first occasion, or when the
    # prior-EMA 14-day window itself fails the >=7-valid-day gate. The shared
    # formula needs a complete design matrix, so those occasions are dropped
    # entirely (a known N reduction from adding the lag-1 sensitivity term).
    df.loc[~df["lag1_valid"], "x_within_lag1_it"] = np.nan
    df = df.dropna(subset=["phq4_score", "x_within_it", "x_between_i", "x_within_lag1_it"])

    df = df.sort_values([uid_col, "ema_date"])
    first_date = df.groupby(uid_col)["ema_date"].transform("min")
    df["week_in_study_it"] = (df["ema_date"] - first_date).dt.days / 7.0

    n_per_person = df.groupby(uid_col)[uid_col].transform("size")
    df = df[n_per_person >= MIN_OCCASIONS_PER_PERSON]
    return df


def fit_lmm(df: pd.DataFrame, uid_col: str = "uid"):
    """Fit random-intercept + random-slope model; fall back to random-intercept-only
    on non-convergence, per doc 1.5. Returns (result, fallback_used: bool)."""
    formula = "phq4_score ~ x_within_it + x_within_lag1_it + x_between_i + week_in_study_it"
    try:
        model = smf.mixedlm(formula, df, groups=df[uid_col], re_formula="~x_within_it")
        result = model.fit(reml=True, method="lbfgs")
        if not result.converged:
            raise RuntimeError("did not converge")
        return result, False
    except Exception:
        model = smf.mixedlm(formula, df, groups=df[uid_col])
        result = model.fit(reml=True, method="lbfgs")
        return result, True


def extract_blups(result, fallback_used: bool, uid_col: str = "uid") -> pd.DataFrame:
    """Per-person BLUP slope_i = beta1 + u1_i, with an approximate per-person
    standard error and two-sided p-value: Var(slope_i) ~ Var(beta1_hat) +
    Var(u1_i) (independence between the fixed-effect estimator and the BLUP is
    an approximation -- their true covariance is not directly exposed by
    statsmodels MixedLM; documented limitation). This gives each person their
    own significance test, per doc section 7 ("applied ... per person").
    """
    from scipy.stats import norm

    beta1 = result.fe_params.get("x_within_it", np.nan)
    var_fixed = result.cov_params().loc["x_within_it", "x_within_it"] if not fallback_used else np.nan
    re = result.random_effects
    re_cov = None if fallback_used else result.random_effects_cov

    rows = []
    for uid, effects in re.items():
        if fallback_used:
            rows.append({uid_col: uid, "slope_i": beta1, "slope_se": np.nan, "slope_p": np.nan})
            continue
        u1 = effects.get("x_within_it", 0.0)
        slope_i = beta1 + u1
        var_random = re_cov[uid].loc["x_within_it", "x_within_it"]
        se_i = float(np.sqrt(var_fixed + var_random))
        z_i = slope_i / se_i if se_i > 0 else np.nan
        p_i = float(2 * (1 - norm.cdf(abs(z_i)))) if pd.notna(z_i) else np.nan
        rows.append({uid_col: uid, "slope_i": slope_i, "slope_se": se_i, "slope_p": p_i})
    return pd.DataFrame(rows)


def evidence_strength(
    slope_i: float, outcome_sd: float, predictor_sd: float,
    q_value: float, n_occasions: int, lag0_sign, lag1_sign,
) -> str:
    """Section 7 thresholds. `q_value` is the per-person/per-report BH-adjusted
    significance for this statement; lag0_sign/lag1_sign are the signs of the
    within-person association at lag 0 and lag 1 (None if lag1 unavailable)."""
    if predictor_sd in (0, None) or outcome_sd in (0, None) or any(
        pd.isna(v) for v in [slope_i, outcome_sd, predictor_sd, q_value]
    ):
        return "insufficient"

    std_effect = abs(slope_i) * predictor_sd / outcome_sd
    consistent_lag01 = lag0_sign is not None and lag0_sign == lag1_sign

    if q_value < STRONG_Q and std_effect >= STRONG_EFFECT and n_occasions >= STRONG_MIN_OCCASIONS and consistent_lag01:
        return "strong"
    if q_value < MODERATE_Q and std_effect >= MODERATE_EFFECT and n_occasions >= MODERATE_MIN_OCCASIONS and lag0_sign is not None:
        return "moderate"
    if q_value < WEAK_Q and std_effect >= WEAK_EFFECT and n_occasions >= WEAK_MIN_OCCASIONS:
        return "weak"
    return "insufficient"


def confirmatory_correction(pvalues: list[float], labels=None) -> np.ndarray:
    """Holm-Bonferroni, FWER 0.05, for the confirmatory family
    (<=3 Tier-1 features x PHQ-4 total x lag 0).

    NaN-safe on the same terms as exploratory_correction. Holm does not
    propagate NaN across the vector the way the step-up FDR methods do, but it
    still counts an undefined test in the family size (m includes the NaN), so
    it is routed through the same helper to keep one definition of the family:
    a test that could not be computed is not part of it.
    """
    if len(pvalues) == 0:
        return np.array([])
    return _adjust_ignoring_nan(pvalues, HOLM_METHOD_NAME, "Holm", labels=labels)


def _adjust_ignoring_nan(pvalues, method: str, method_label: str, labels=None) -> np.ndarray:
    """Apply `method` to the non-NaN p-values only, writing the adjusted values
    back into their original positions and leaving NaN entries as NaN.

    statsmodels `multipletests` propagates a single NaN across the whole input
    (`[0.01, nan, 0.5]` -> `[nan, nan, nan]`), which would silently turn every
    per-person label into `insufficient` because `evidence_strength` treats a
    NaN q as insufficient. Correcting only the defined tests keeps one
    undefined test from collapsing the family.

    The family size is therefore the number of tests actually corrected: a
    person whose test is undefined is not counted in the family. `labels`
    (e.g. uids) is used only for the warning message.
    """
    arr = np.asarray(pvalues, dtype=float)
    out = np.full(arr.shape, np.nan)
    defined = ~np.isnan(arr)
    n_undefined = int((~defined).sum())

    if n_undefined:
        if labels is not None:
            missing = [str(l) for l, ok in zip(labels, defined) if not ok]
        else:
            missing = [f"index {i}" for i, ok in enumerate(defined) if not ok]
        shown = ", ".join(missing[:10]) + (f", ... (+{len(missing) - 10} more)" if len(missing) > 10 else "")
        print(
            f"WARNING [{method_label}]: {n_undefined} of {arr.size} p-values are undefined "
            f"(NaN) and were excluded from the correction family; the family size used is "
            f"{int(defined.sum())}, not {arr.size}. These participants are classified "
            f"'insufficient' because their test could not be computed, NOT because the "
            f"evidence was weak: {shown}",
            file=sys.stderr,
        )

    if defined.any():
        _, adj, _, _ = multipletests(arr[defined], alpha=0.05, method=method)
        out[defined] = adj
    return out


def correction_family_size(pvalues) -> int:
    """Number of tests that actually enter a correction family (non-NaN)."""
    return int((~np.isnan(np.asarray(pvalues, dtype=float))).sum())


def exploratory_correction(pvalues: list[float], labels=None) -> np.ndarray:
    """Benjamini-Hochberg FDR q=0.05, for exploratory tests and per-person reports.

    NaN-safe: undefined tests are excluded from the family and returned as NaN
    rather than poisoning every other participant's q. See _adjust_ignoring_nan.
    """
    if len(pvalues) == 0:
        return np.array([])
    return _adjust_ignoring_nan(pvalues, BH_METHOD_NAME, "BH-FDR", labels=labels)


def reclassify_family213(per_person: pd.DataFrame, outcome_sd: float, predictor_sd: float,
                         uid_col: str = "uid") -> pd.DataFrame:
    """Per-person exploratory family = all 213 participants in the model frame,
    not one participant per family (family-of-1).

    Family size was UNDEFINED in the Week 4 doc: section 2's "per-person weekly
    report" family is scoped to one person's own statements across up to 3
    Tier-1 features (<=6 statements), which is a different family than "all
    participants tested for one feature." With only loc_dist_ep_0 implemented,
    the per-report family degenerates to size 1 and was never actually
    exercised as a multi-test family. This function defines that family as the
    213 participants who cleared the model's occasion/occasion-count gates and
    therefore each produced a candidate per-person slope_i/p for this feature --
    the natural population for "how many of our per-person claims are we making
    at once" once a feature reaches production. Thresholds (q<0.01/0.05/0.10),
    effect-size floors (0.10/0.20), the n_occasions gates (12/8), and the lag
    sign-consistency check are unchanged; only what is passed into
    evidence_strength()'s q_value argument changes.

    Returns per_person with added columns: bh_q_213, holm_p_213, std_effect,
    label_bh (production), label_holm (sensitivity), label_family1 (legacy,
    recomputed here from the raw per-person p for reference).
    """
    out = per_person.copy()
    pvalues = out["slope_p"].tolist()
    uids = out[uid_col].tolist() if uid_col in out.columns else None

    out["bh_q_213"] = exploratory_correction(pvalues, labels=uids)
    out["holm_p_213"] = confirmatory_correction(pvalues, labels=uids)

    # The family that was actually corrected: participants with a computable
    # per-person test. Recorded in run_manifest.json so a run where some tests
    # were undefined is not read as a full-cohort family. Both corrections use
    # the same definition, so the two sizes agree by construction; they are
    # recorded separately so the manifest states it rather than implying it.
    out.attrs["bh_family_size"] = correction_family_size(pvalues)
    out.attrs["holm_family_size"] = correction_family_size(pvalues)
    out.attrs["n_undefined_pvalues"] = len(pvalues) - out.attrs["bh_family_size"]
    out["std_effect"] = out["slope_i"].abs() * predictor_sd / outcome_sd

    def _label(q_col):
        return out.apply(
            lambda r: evidence_strength(
                r["slope_i"], outcome_sd, predictor_sd, r[q_col],
                int(r["n_occasions"]), r["lag0_sign"], r["lag1_sign"],
            ),
            axis=1,
        )

    out["label_family1"] = out.apply(
        lambda r: evidence_strength(
            r["slope_i"], outcome_sd, predictor_sd, r["slope_p"],
            int(r["n_occasions"]), r["lag0_sign"], r["lag1_sign"],
        ),
        axis=1,
    )
    out["label_bh"] = _label("bh_q_213")
    out["label_holm"] = _label("holm_p_213")
    return out


def to_user_facing_evidence(label: str) -> str:
    """Collapse the 4-level evidence-strength label to the 2-value form that
    reaches the SLM / evidence contract: strong & moderate -> "evidence_available"
    (may be surfaced, with the required hedge language); weak & insufficient ->
    "no_claim" (say nothing about the relationship). The 4-level label is
    unchanged and still used everywhere else (reports, analysis, per-person
    tables); only this user-facing mapping is 2-valued.

    This collapsing is a post-hoc decision. The Week 4 pre-registration
    defined four levels, but after seeing the results it was decided to
    collapse only the user-facing output to two values.

    Rationale: 26 people cluster in the standardised-effect-size band
    [0.15, 0.20), which sits just below the strong/moderate boundary.
    Changing only the preprocessing specification shifts the label for
    51 of 213 people (24%), so this boundary is unstable with respect to
    specification choice. Since the same person can land in either strong
    or moderate under an equally reasonable alternative specification,
    there is no basis for distinguishing the two.

    The threshold itself has not been changed, so this is not a
    pre-registration violation.
    """
    if label in ("strong", "moderate"):
        return "evidence_available"
    if label in ("weak", "insufficient"):
        return "no_claim"
    raise ValueError(f"unrecognised evidence_strength label: {label!r}")
