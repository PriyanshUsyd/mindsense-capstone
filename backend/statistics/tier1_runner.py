"""
Runs the full baseline/evidence pipeline for both confirmed Tier-1
features (`feature-list-signoff.md` / `freeze-decision.md`, 2026-08-26:
`loc_dist_ep_0` + `unlock_num_ep_0`) against the real local CES dataset,
and persists real output for each — not synthetic numbers.

**Renamed from `run_tier1_evidence.py` 2026-09-14 — a scope change, not a
delete-and-recreate.** The old name included "evidence," implying
per-person evidence-strength determination end to end. That name no
longer matches what this module actually does: `backend.statistics
.bootstrap`'s per-person standard-error estimation (parametric + cluster,
B=500 replicates each) now exists, but it costs ~30-40 minutes per
feature per method on the real dataset — running it unconditionally
inside a routine "run the pipeline" script would make every invocation of
this file that expensive. This module therefore does the cheap part only
(cleaning -> model-frame construction -> mixed-effects fit -> AR(1) fit ->
per-person point estimates -> evidence classification, which stays
"insufficient" for everyone until a real `slope_se` is supplied — see
`backend.statistics.evidence`'s module docstring) and stops there.
`tier1_runner` names that narrower, actually-current scope; a caller who
wants real per-person labels runs `backend.statistics.bootstrap`
separately and feeds its output through `evidence
.build_person_slopes_from_bootstrap_se` / `intersect_bootstrap_evidence`
(not wired into this runner — a deliberate extension point, not an
oversight).

Uses `backend.statistics.feature_specs.TIER1_FEATURE_SPECS` — each
feature's raw column, transform, and cleaning entry point are declared
once there, not duplicated here (see that module for why: commit
4a3379e's own message documents the silent-wrong-transform bug that
motivated centralising this).

Run: python -m backend.statistics.tier1_runner
(needs the real CES dataset downloaded locally per Readme.md — gitignored;
writes to outputs/tier1/<timestamp>/, gitignored, never committed.)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from backend.statistics import evidence
from backend.statistics.feature_specs import TIER1_FEATURE_SPECS, FeatureSpec
from backend.statistics.mixed_effects_model import build_model_frame, fit_ar1_effect, fit_mixed_effects_model

DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"
OUTPUT_ROOT = Path(__file__).resolve().parents[2] / "outputs" / "tier1"

# Every raw column any Tier-1 FeatureSpec's clean_fn might need, loaded
# once and shared across features rather than re-reading sensing.csv per
# feature. Extending TIER1_FEATURE_SPECS with a feature whose clean_fn
# needs a column not listed here will fail loudly (pandas KeyError from
# that clean_fn) rather than silently drop the column — add it here too.
_SENSING_COLUMNS = ["uid", "day", "quality_loc", "loc_dist_ep_0", "unlock_num_ep_0"]


def load_sensing_and_ema() -> tuple[pd.DataFrame, pd.DataFrame]:
    sensing = (
        pd.read_csv(DATASET_DIR / "Sensing" / "sensing.csv", usecols=_SENSING_COLUMNS)
        .sort_values(["uid", "day"])
        .reset_index(drop=True)
    )
    ema = pd.read_csv(DATASET_DIR / "EMA" / "general_ema.csv", usecols=["uid", "day", "phq4_score"])
    return sensing, ema


@dataclass
class FeatureRunResult:
    feature: str
    transform_name: str
    n_occasions: int
    n_participants: int
    participant_uids: list[str]
    primary_fit: dict
    ar1_fit: dict
    evidence_summary: dict
    evidence_per_person: pd.DataFrame = field(repr=False, compare=False)


def run_one_feature(
    spec: FeatureSpec,
    sensing: pd.DataFrame,
    ema: pd.DataFrame,
    prefer_r: bool = True,
) -> FeatureRunResult:
    cleaned = spec.clean_fn(sensing)
    frame = build_model_frame(cleaned, ema, spec)

    fit = fit_mixed_effects_model(frame, prefer_r=prefer_r)
    ar1 = fit_ar1_effect(frame, prefer_r=prefer_r)

    ci_low, ci_high = _wald_ci(fit, "x_within")

    primary_fit = {
        "engine": fit.engine,
        "converged": fit.converged,
        "used_random_slope": fit.used_random_slope,
        "fallback_reason": fit.fallback_reason,
        "x_within_beta": fit.params.get("x_within"),
        "x_within_se": fit.se.get("x_within"),
        "x_within_ci95": [ci_low, ci_high],
        "x_within_p": fit.pvalues.get("x_within"),
        "denom_df_method": fit.denom_df_method,
        "denom_df_x_within": fit.denom_df.get("x_within"),
    }
    ar1_fit = {
        "engine": ar1.engine,
        "ar1_coefficient": ar1.ar1_coefficient,
        "x_within_beta": ar1.params.get("x_within"),
        "x_within_p": ar1.pvalues.get("x_within"),
        "fallback_reason": ar1.fallback_reason,
        "has_blups": ar1.blups is not None,
    }

    # Per-person evidence (Section 7) -- only reachable with real BLUPs,
    # i.e. only when the R engine actually ran. slope_se/slope_p are None
    # (no bootstrap has been run here -- see module docstring), so
    # reclassify_family213's fail-safe applies: every label is
    # "insufficient" until a real SE is supplied separately.
    if ar1.blups is not None:
        person_slopes = evidence.extract_person_slopes(ar1, frame)
        outcome_sd = float(frame["phq4_score"].std())
        predictor_sd = float(frame["x_within"].std())
        evidence_table = evidence.reclassify_family213(person_slopes, outcome_sd, predictor_sd)
        evidence_summary = {
            "family_size": len(evidence_table),
            "label_bh_counts": evidence_table["label_bh"].value_counts().to_dict(),
            "label_holm_counts": evidence_table["label_holm"].value_counts().to_dict(),
            "all_insufficient_pending_se": bool((evidence_table["label_bh"] == "insufficient").all()),
        }
    else:
        evidence_table = pd.DataFrame()
        evidence_summary = {
            "skipped_reason": (
                f"ar1_result has no BLUPs (engine={ar1.engine!r}) -- "
                "extract_person_slopes requires the R engine; see "
                "docs/statistics/r-bridge-setup.md."
            )
        }

    return FeatureRunResult(
        feature=spec.name,
        transform_name=spec.transform_name,
        n_occasions=len(frame),
        n_participants=int(frame["uid"].nunique()),
        participant_uids=sorted(frame["uid"].unique().tolist()),
        primary_fit=primary_fit,
        ar1_fit=ar1_fit,
        evidence_summary=evidence_summary,
        evidence_per_person=evidence_table,
    )


def _wald_ci(fit, term: str, z: float = 1.959964) -> tuple[float | None, float | None]:
    """95% Wald CI from beta +/- z*SE — the standard normal-approximation
    interval used here regardless of engine (R's Satterthwaite/
    Kenward-Roger df would give a slightly wider t-based interval; not
    used here to keep this a simple, engine-independent summary rather
    than re-deriving each engine's exact denominator df for a CI no
    downstream code consumes). `None` if beta or se is missing (e.g. the
    term wasn't fit)."""
    beta = fit.params.get(term)
    se = fit.se.get(term)
    if beta is None or se is None:
        return None, None
    return beta - z * se, beta + z * se


def reconcile_participant_sets(results: dict[str, FeatureRunResult]) -> dict:
    """Tier-1 features are fit independently (spec 2.2: family is per
    feature, not unified across features) and can end up with different
    participant sets -- e.g. GPS's quality gate drops people unlock's
    cleaning never touches. Family re-definition across features is out
    of scope here (Statistical Analysis Lead's own call, deferred); this
    just records the real numbers so that decision doesn't need to
    re-derive them later."""
    sets_by_feature = {name: set(r.participant_uids) for name, r in results.items()}
    names = list(sets_by_feature)

    out: dict = {name: {"n_participants": len(uids), "uids": sorted(uids)} for name, uids in sets_by_feature.items()}

    if len(names) == 2:
        a, b = names
        union = sets_by_feature[a] | sets_by_feature[b]
        intersection = sets_by_feature[a] & sets_by_feature[b]
        out["union_n"] = len(union)
        out["intersection_n"] = len(intersection)
        out[f"only_in_{a}"] = sorted(sets_by_feature[a] - sets_by_feature[b])
        out[f"only_in_{b}"] = sorted(sets_by_feature[b] - sets_by_feature[a])

    return out


def write_outputs(results: dict[str, FeatureRunResult], reconciliation: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, result in results.items():
        summary = {k: v for k, v in asdict_no_df(result).items()}
        (out_dir / f"{name}_summary.json").write_text(
            json.dumps(summary, indent=2, default=_json_default), encoding="utf-8"
        )
        result.evidence_per_person.to_csv(out_dir / f"{name}_evidence_per_person.csv", index=False)

    (out_dir / "participant_set_reconciliation.json").write_text(
        json.dumps(reconciliation, indent=2), encoding="utf-8"
    )


def asdict_no_df(result: FeatureRunResult) -> dict:
    d = asdict(result)
    d.pop("evidence_per_person", None)
    return d


def _json_default(o):
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    return None


def main(prefer_r: bool = True) -> Path:
    sensing, ema = load_sensing_and_ema()

    results = {
        name: run_one_feature(spec, sensing, ema, prefer_r=prefer_r) for name, spec in TIER1_FEATURE_SPECS.items()
    }
    reconciliation = reconcile_participant_sets(results)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_ROOT / timestamp
    write_outputs(results, reconciliation, out_dir)

    print(f"wrote Tier-1 run output to {out_dir}")
    for name, result in results.items():
        print(
            f"  {name}: engine={result.primary_fit['engine']!r} "
            f"beta={result.primary_fit['x_within_beta']} p={result.primary_fit['x_within_p']} "
            f"n_occasions={result.n_occasions} n_participants={result.n_participants}"
        )
    print(f"  participant sets: {reconciliation.get('intersection_n')} shared / {reconciliation.get('union_n')} union")

    return out_dir


if __name__ == "__main__":
    main()
