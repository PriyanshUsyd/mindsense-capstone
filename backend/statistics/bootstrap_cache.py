"""
Cache for the per-person bootstrap SE (`backend.statistics.bootstrap`) —
design: `docs/statistics/week7-calibration-concerns.md` item 2, decisions
a-d, plus the changes listed there under "Implementation status".

Layout, per feature, under `outputs/bootstrap_cache/<feature>/` (gitignored;
`docs/privacy/local-demo-privacy-check.md`: per-person bootstrap rows are
never committed):

  raw_checkpoint.jsonl    every iteration (heavy; contains per-person BLUPs)
  raw_fingerprint.json    the raw layer's fingerprint (hash AND key dict)
  aggregated_cache.json   per-person SE + the final intersection table,
                          stored with its own fingerprint

**Fingerprint = three layers, flattened into one `{key: scalar}` dict, hashed
with SHA-256, stored beside the dict** (the hash alone cannot say *which*
entry changed, and the error message must).

  A. input        content hash of the exact model frame the fit consumes
                  (`bootstrap.prepare_model_frame`). Catches changes to the
                  dataset, cleaning, windows, transform and
                  `build_model_frame` by what they *do*, not by which file
                  they live in.
  B. code         content hash of every source file on the estimation path
                  (`ESTIMATION_CODE_FILES`). Needed because layer A cannot
                  see the simulation, the R model formula or `lmeControl`.
  C. environment  Python/R/package versions, plus the run configuration
     and config   (feature, transform, master_seed, B, engine, ...).

The aggregated layer's key = every raw key (prefixed `raw.`) + the content
hash of `evidence.py` + the evidence-classification thresholds, so a change
that only affects classification invalidates the cheap aggregated layer
without discarding the 2+ hour raw checkpoint's validity.

**Missing vs. stale (decision c).** No aggregated cache -> `None` (caller
continues with `insufficient`; a bootstrap is never started implicitly).
Fingerprint mismatch -> `BootstrapCacheStale`, naming the changed keys.

**Writes refuse a dirty tree.** Creating a raw checkpoint or an aggregated
cache requires every file it is keyed on to be committed and unmodified
(`git status --porcelain`; untracked counts as dirty) — this is the
2026-09-13 problem (a run from an uncommitted working tree has no
reproducible provenance). **Reads compare content hashes only**: identical
content is identical code whether or not it is committed, and a read must
not need `.git`.

**Resume safety.** A raw checkpoint is only appended to when its sidecar
fingerprint equals the current one; the 2026-09-13 run was resumed twice
with nothing recording the code state of each leg.

Run (after committing; real dataset required):
  python -m backend.statistics.bootstrap_cache loc_dist_ep_0
"""

from __future__ import annotations

import getpass
import hashlib
import importlib.metadata
import inspect
import json
import os
import subprocess
import sys
import tempfile
import warnings
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from backend.statistics import bootstrap, evidence, r_bridge
from backend.statistics.feature_specs import FeatureSpec
from backend.statistics.mixed_effects_model import classify_evidence_strength

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_ROOT = REPO_ROOT / "outputs" / "bootstrap_cache"

RAW_CHECKPOINT_NAME = "raw_checkpoint.jsonl"
RAW_FINGERPRINT_NAME = "raw_fingerprint.json"
AGGREGATED_NAME = "aggregated_cache.json"

# The one real B=500 configuration (CLAUDE.md / week7 item 3). A cache built
# with any other seed or B is stored, but the runner will not accept it:
# `config.master_seed` / `config.n_iterations` are part of the fingerprint.
CANONICAL_MASTER_SEED = 20260913
CANONICAL_N_ITERATIONS = 500

# Files whose content can change a bootstrap replicate or the model frame.
# When in doubt a file belongs here: a missing entry silently serves a stale
# estimate, an extra one only costs a rerun. Completeness against the real
# import graph is enforced by tests/statistics/test_bootstrap_cache.py.
ESTIMATION_CODE_FILES: tuple[str, ...] = (
    "backend/statistics/bootstrap.py",  # simulation, resampling, seeds
    "backend/statistics/mixed_effects_model.py",  # fit_ar1_effect, build_model_frame, windows
    "backend/statistics/r_bridge.py",  # nlme formula, lmeControl, BLUP/D extraction
    "backend/statistics/feature_specs.py",  # transform + clean_fn per feature
    "backend/data_pipeline/cleaning.py",  # quality gate, thresholds, offsets
    "backend/data_pipeline/gps_distance_feature.py",
    "backend/data_pipeline/unlock_frequency_feature.py",
)

# Extra files for the aggregated layer only.
AGGREGATION_CODE_FILES: tuple[str, ...] = ("backend/statistics/evidence.py",)

# Modules reachable from the estimation entry points that are deliberately
# NOT fingerprinted, each with the reason. (Exclusion list for the import
# graph test; keep reasons honest.)
EXCLUDED_MODULES: dict[str, str] = {
    "backend": "package marker, empty",
    "backend.statistics": "package marker, docstring only",
    "backend.data_pipeline": "package marker, docstring only",
    "backend.statistics.evidence": (
        "raw layer uses only PersonSlope / X_WITHIN_TERM for aggregation, never "
        "inside a replicate; covered by the aggregated layer (AGGREGATION_CODE_FILES)"
    ),
}


class BootstrapCacheError(RuntimeError):
    """Unreadable / inconsistent cache or sidecar."""


class BootstrapCacheStale(BootstrapCacheError):
    """Recorded fingerprint != current fingerprint. `changed` lists which."""

    def __init__(self, message: str, changed: list[str]):
        super().__init__(message)
        self.changed = changed


class BootstrapCacheWriteRefused(BootstrapCacheError):
    """A fingerprinted file is dirty/untracked (or git cannot say)."""


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------


def _sha256_source(path: Path) -> str:
    # CRLF -> LF so a Windows autocrlf checkout hashes like a Linux one.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def model_frame_digest(frame: pd.DataFrame) -> dict[str, object]:
    """Content hash of an already-canonical frame (`prepare_model_frame`):
    column names, dtypes and every cell's bytes, in row order."""
    cols = sorted(frame.columns)
    ordered = frame[cols]
    h = hashlib.sha256()
    h.update(json.dumps([[c, str(ordered[c].dtype)] for c in cols]).encode("utf-8"))
    h.update(pd.util.hash_pandas_object(ordered, index=False).to_numpy().tobytes())
    return {
        "model_frame_sha256": h.hexdigest(),
        "n_rows": int(len(ordered)),
        "n_columns": len(cols),
    }


def environment_versions() -> dict[str, str]:
    versions = {"python": sys.version.split()[0]}
    for dist in ("numpy", "scipy", "pandas", "statsmodels", "rpy2"):
        try:
            versions[dist] = importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            versions[dist] = "not-installed"
    try:
        with r_bridge._R_WORKSPACE_LOCK:
            ro = r_bridge._load_r()[0]
            versions["R"] = str(ro.r("R.version.string")[0])
            versions["nlme"] = str(ro.r("as.character(packageVersion('nlme'))")[0])
    except Exception as exc:  # noqa: BLE001 - recorded, so a later mismatch is visible
        versions["R"] = f"unavailable ({type(exc).__name__})"
        versions["nlme"] = "unavailable"
    return versions


def raw_key_dict(
    prepared_frame: pd.DataFrame,
    spec: FeatureSpec,
    *,
    engine: str,
    master_seed: int = CANONICAL_MASTER_SEED,
    n_iterations: int = CANONICAL_N_ITERATIONS,
    outcome_col: str = "phq4_score",
    extra_fixed_effects: Sequence[str] = (),
    repo_root: Path = REPO_ROOT,
    environment: dict[str, str] | None = None,
) -> dict[str, object]:
    """Layers A + B + C as one flat dict. `prepared_frame` must come from
    `bootstrap.prepare_model_frame`."""
    keys: dict[str, object] = {}
    for k, v in model_frame_digest(prepared_frame).items():
        keys[f"input.{k}"] = v
    for rel in ESTIMATION_CODE_FILES:
        keys[f"code.{rel}"] = _sha256_source(repo_root / rel)
    for k, v in (environment if environment is not None else environment_versions()).items():
        keys[f"env.{k}"] = v
    keys.update(
        {
            "config.feature": spec.name,
            "config.transform_name": spec.transform_name,
            "config.master_seed": int(master_seed),
            "config.n_iterations": int(n_iterations),
            "config.engine": engine,
            "config.outcome_col": outcome_col,
            "config.extra_fixed_effects": ",".join(extra_fixed_effects),
        }
    )
    return keys


def aggregated_key_dict(raw_keys: dict[str, object], repo_root: Path = REPO_ROOT) -> dict[str, object]:
    keys: dict[str, object] = {f"raw.{k}": v for k, v in raw_keys.items()}
    for rel in AGGREGATION_CODE_FILES:
        keys[f"code.{rel}"] = _sha256_source(repo_root / rel)
    # classify_evidence_strength carries the q / effect / occasion thresholds.
    keys["thresholds.classify_evidence_strength_sha256"] = hashlib.sha256(
        inspect.getsource(classify_evidence_strength).replace("\r\n", "\n").encode("utf-8")
    ).hexdigest()
    # Per-feature since bf2fa82 (EXPECTED_FAMILY_SIZE became a dict keyed by
    # feature name); fingerprint the whole mapping.
    keys["thresholds.expected_family_size"] = {
        name: int(size) for name, size in evidence.EXPECTED_FAMILY_SIZE.items()
    }
    return keys


def fingerprint_hash(keys: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(keys, sort_keys=True).encode("utf-8")).hexdigest()


def make_fingerprint(keys: dict[str, object]) -> dict[str, object]:
    return {"sha256": fingerprint_hash(keys), "keys": keys}


def _short(value: object) -> str:
    s = str(value)
    return s[:12] + "…" if len(s) > 24 and all(c in "0123456789abcdef" for c in s) else s


def diff_keys(recorded: dict[str, object], current: dict[str, object]) -> list[str]:
    changed = []
    for k in sorted(set(recorded) | set(current)):
        if k not in current:
            changed.append(f"{k}: recorded {_short(recorded[k])}, no longer part of the fingerprint")
        elif k not in recorded:
            changed.append(f"{k}: new in the fingerprint (current {_short(current[k])})")
        elif recorded[k] != current[k]:
            changed.append(f"{k}: recorded {_short(recorded[k])} -> current {_short(current[k])}")
    return changed


def _stale(what: str, recorded: dict[str, object], current: dict[str, object]) -> BootstrapCacheStale:
    changed = diff_keys(recorded["keys"], current)  # type: ignore[arg-type]
    listing = "\n  - ".join(changed) if changed else "(hash differs but no key does — sidecar was edited?)"
    return BootstrapCacheStale(
        f"{what} is stale: its fingerprint no longer matches. Changed keys:\n  - {listing}\n"
        "Next step: `code.*` / `input.*` / `env.*` keys changed -> the cached result no longer "
        "describes this code/data; rebuild it with `python -m backend.statistics.bootstrap_cache "
        "<feature>` from a clean, committed tree (or move the old cache aside). A purely cosmetic "
        "edit (e.g. a comment) still invalidates: the fingerprint compares content, not meaning.",
        changed,
    )


def _check_recorded(recorded: object, where: Path) -> dict[str, object]:
    if (
        not isinstance(recorded, dict)
        or not isinstance(recorded.get("keys"), dict)
        or fingerprint_hash(recorded["keys"]) != recorded.get("sha256")
    ):
        raise BootstrapCacheError(f"{where}: fingerprint record is malformed or its hash does not match its keys")
    return recorded


# ---------------------------------------------------------------------------
# Write guard + permissions
# ---------------------------------------------------------------------------


def _git_porcelain(repo_root: Path, rel_files: Sequence[str]) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain", "--untracked-files=all", "--", *rel_files],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootstrapCacheWriteRefused(f"cannot verify the working tree is clean (git unavailable: {exc})") from exc
    if proc.returncode != 0:
        raise BootstrapCacheWriteRefused(f"cannot verify the working tree is clean: {proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line.strip()]


def assert_clean_for_write(
    rel_files: Sequence[str],
    repo_root: Path = REPO_ROOT,
    git_status: Callable[[Path, Sequence[str]], list[str]] = _git_porcelain,
) -> None:
    dirty = git_status(repo_root, rel_files)
    if dirty:
        raise BootstrapCacheWriteRefused(
            "refusing to write a bootstrap cache: files it is keyed on are modified or untracked "
            "(a cache from an uncommitted tree has no reproducible provenance):\n  "
            + "\n  ".join(dirty)
            + "\nCommit (or revert) them first."
        )


def _restrict_to_owner(path: Path, *, is_dir: bool) -> bool:
    """POSIX: mode 700 / 600. Windows: icacls, inheritance removed, current
    user only (best effort — `os.chmod` cannot express this on Windows).
    `docs/privacy/local-demo-privacy-check.md`. Never raises: a failure is
    a warning, the run continues."""
    try:
        if os.name == "posix":
            os.chmod(path, 0o700 if is_dir else 0o600)
            return True
        user = os.environ.get("USERNAME") or getpass.getuser()
        grant = f"{user}:(OI)(CI)F" if is_dir else f"{user}:F"
        proc = subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", grant],
            capture_output=True,
            text=True,
            encoding="mbcs",
            errors="replace",
            timeout=30,
        )
        if proc.returncode != 0:
            raise OSError(proc.stderr.strip() or proc.stdout.strip() or f"icacls exit {proc.returncode}")
        return True
    except Exception as exc:  # noqa: BLE001 - best effort by design
        warnings.warn(
            f"could not restrict permissions on {path} ({type(exc).__name__}: {exc}); "
            "the cache contains participant uids — restrict it manually.",
            stacklevel=2,
        )
        return False


def _private_dir(path: Path) -> None:
    created = not path.exists()
    path.mkdir(parents=True, exist_ok=True)
    if created:
        _restrict_to_owner(path, is_dir=True)


def _write_json_atomic(path: Path, payload: object) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, allow_nan=False)
        _restrict_to_owner(Path(tmp), is_dir=False)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def cache_dir(feature: str, cache_root: Path = CACHE_ROOT) -> Path:
    return cache_root / feature


# ---------------------------------------------------------------------------
# Raw checkpoint (decision a: raw separate from aggregated)
# ---------------------------------------------------------------------------


def prepare_raw_checkpoint(
    feature: str,
    raw_keys: dict[str, object],
    *,
    cache_root: Path = CACHE_ROOT,
    repo_root: Path = REPO_ROOT,
    git_status: Callable[[Path, Sequence[str]], list[str]] = _git_porcelain,
) -> Path:
    """Returns the checkpoint path to hand to `BootstrapRunConfig`.

    Existing sidecar: must match the current fingerprint exactly or
    `BootstrapCacheStale` (never mix legs of different code states).
    Checkpoint without a sidecar: refused (unknown provenance). Nothing
    there yet: requires a clean tree, then writes the sidecar first."""
    d = cache_dir(feature, cache_root)
    checkpoint = d / RAW_CHECKPOINT_NAME
    sidecar = d / RAW_FINGERPRINT_NAME
    current = make_fingerprint(raw_keys)

    if sidecar.exists():
        try:
            recorded = _check_recorded(json.loads(sidecar.read_text(encoding="utf-8")), sidecar)
        except json.JSONDecodeError as exc:
            raise BootstrapCacheError(f"{sidecar}: not valid JSON ({exc})") from exc
        if recorded["sha256"] != current["sha256"]:
            raise _stale(f"raw checkpoint for {feature!r} (resume refused)", recorded, raw_keys)
        return checkpoint

    if checkpoint.exists() and checkpoint.stat().st_size > 0:
        raise BootstrapCacheError(
            f"{checkpoint} has records but no {RAW_FINGERPRINT_NAME}: its code/data state is unknown, "
            "so resuming would mix an unknown leg into the result. Move it aside."
        )

    assert_clean_for_write(ESTIMATION_CODE_FILES, repo_root, git_status)
    _private_dir(cache_root)
    _private_dir(d)
    _write_json_atomic(sidecar, current)
    checkpoint.touch()
    _restrict_to_owner(checkpoint, is_dir=False)
    return checkpoint


# ---------------------------------------------------------------------------
# Aggregated cache (SE + intersection table)
# ---------------------------------------------------------------------------


@dataclass
class AggregatedCache:
    fingerprint_sha256: str
    n_iterations: int
    se: pd.DataFrame  # uid, method, slope_se, n_occasions, n_bootstrap_draws
    intersection: pd.DataFrame  # intersect_bootstrap_evidence output
    failure_summary: dict


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


def aggregate_checkpoint(real_fit: bootstrap.RealFit, records: list[dict], n_iterations: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    summaries = {m: bootstrap.failure_summary(records, m) for m in ("parametric", "cluster")}
    for method, summary in summaries.items():
        if summary["n_total"] != n_iterations:
            raise BootstrapCacheError(
                f"{method}: checkpoint holds {summary['n_total']} of {n_iterations} iterations; "
                "only a complete run is cached. Resume the run first."
            )
    frame = real_fit.model_frame
    n_by_uid = frame.groupby(real_fit.uid_col).size().to_dict()
    outcome_sd = float(frame[real_fit.outcome_col].std())
    predictor_sd = float(frame["x_within"].std())

    se_rows, tables = [], {}
    for method in ("parametric", "cluster"):
        se_df = bootstrap.per_person_se(bootstrap.collect_person_slope_draws(records, method))
        se_rows.append(
            se_df.assign(method=method, n_occasions=se_df["uid"].map(n_by_uid).astype(int))[
                ["uid", "method", "slope_se", "n_occasions", "n_bootstrap_draws"]
            ]
        )
        slopes = bootstrap.build_person_slopes_from_bootstrap_se(real_fit, se_df)
        tables[method] = evidence.reclassify_cohort_family(slopes, outcome_sd, predictor_sd)
    intersection = evidence.intersect_bootstrap_evidence(tables["parametric"], tables["cluster"])
    return pd.concat(se_rows, ignore_index=True), intersection, summaries


def write_aggregated_cache(
    feature: str,
    real_fit: bootstrap.RealFit,
    records: list[dict],
    raw_keys: dict[str, object],
    *,
    n_iterations: int,
    cache_root: Path = CACHE_ROOT,
    repo_root: Path = REPO_ROOT,
    git_status: Callable[[Path, Sequence[str]], list[str]] = _git_porcelain,
) -> Path:
    assert_clean_for_write((*ESTIMATION_CODE_FILES, *AGGREGATION_CODE_FILES), repo_root, git_status)
    se, intersection, summaries = aggregate_checkpoint(real_fit, records, n_iterations)
    d = cache_dir(feature, cache_root)
    _private_dir(cache_root)
    _private_dir(d)
    path = d / AGGREGATED_NAME
    _write_json_atomic(
        path,
        {
            "fingerprint": make_fingerprint(aggregated_key_dict(raw_keys, repo_root)),
            "n_iterations": n_iterations,
            "failure_summary": summaries,
            "se": _records(se),
            "intersection": _records(intersection),
        },
    )
    return path


def load_aggregated_cache(
    spec: FeatureSpec,
    model_frame: pd.DataFrame,
    *,
    engine: str,
    master_seed: int = CANONICAL_MASTER_SEED,
    n_iterations: int = CANONICAL_N_ITERATIONS,
    cache_root: Path = CACHE_ROOT,
    repo_root: Path = REPO_ROOT,
    environment: dict[str, str] | None = None,
) -> AggregatedCache | None:
    """`None` if no aggregated cache exists (decision c: carry on with
    `insufficient`). Raises `BootstrapCacheStale` on a fingerprint mismatch
    and `BootstrapCacheError` if the file is unreadable. Compares hashes
    only — no git involved."""
    path = cache_dir(spec.name, cache_root) / AGGREGATED_NAME
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        recorded = _check_recorded(payload["fingerprint"], path)
        se = pd.DataFrame(payload["se"])
        intersection = pd.DataFrame(payload["intersection"])
        summary = payload["failure_summary"]
        recorded_b = int(payload["n_iterations"])
    except BootstrapCacheError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BootstrapCacheError(f"{path}: unreadable bootstrap cache ({type(exc).__name__}: {exc})") from exc

    prepared = bootstrap.prepare_model_frame(model_frame)
    raw_keys = raw_key_dict(
        prepared,
        spec,
        engine=engine,
        master_seed=master_seed,
        n_iterations=n_iterations,
        repo_root=repo_root,
        environment=environment,
    )
    current = aggregated_key_dict(raw_keys, repo_root)
    if fingerprint_hash(current) != recorded["sha256"]:
        raise _stale(f"bootstrap cache for {spec.name!r}", recorded, current)
    return AggregatedCache(recorded["sha256"], recorded_b, se, intersection, summary)


# ---------------------------------------------------------------------------
# Orchestration / CLI
# ---------------------------------------------------------------------------


def run_and_cache(
    spec: FeatureSpec,
    prepared_source_frame: pd.DataFrame,
    *,
    master_seed: int = CANONICAL_MASTER_SEED,
    n_iterations: int = CANONICAL_N_ITERATIONS,
    n_workers: int = 6,
    maxtasksperchild: int | None = 20,
    cache_root: Path = CACHE_ROOT,
) -> Path:
    """Fit the real model, (resume and) run both bootstrap methods into the
    fingerprinted raw checkpoint, then write the aggregated cache."""
    real_fit = bootstrap.fit_real_model(prepared_source_frame)
    raw_keys = raw_key_dict(
        real_fit.model_frame,
        spec,
        engine=real_fit.ar1_result.engine,
        master_seed=master_seed,
        n_iterations=n_iterations,
    )
    checkpoint = prepare_raw_checkpoint(spec.name, raw_keys, cache_root=cache_root)
    config = bootstrap.BootstrapRunConfig(
        master_seed=master_seed,
        n_iterations=n_iterations,
        checkpoint_path=checkpoint,
        n_workers=n_workers,
        maxtasksperchild=maxtasksperchild,
    )
    records = bootstrap.run_bootstrap_parallel(real_fit, config)
    return write_aggregated_cache(
        spec.name, real_fit, records, raw_keys, n_iterations=n_iterations, cache_root=cache_root
    )


def main(argv: list[str] | None = None) -> None:
    import argparse

    from backend.statistics import tier1_runner
    from backend.statistics.feature_specs import TIER1_FEATURE_SPECS
    from backend.statistics.mixed_effects_model import build_model_frame

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("feature", choices=sorted(TIER1_FEATURE_SPECS))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--maxtasksperchild", type=int, default=20)
    args = parser.parse_args(argv)

    spec = TIER1_FEATURE_SPECS[args.feature]
    sensing, ema = tier1_runner.load_sensing_and_ema()
    frame = build_model_frame(spec.clean_fn(sensing), ema, spec)
    path = run_and_cache(spec, frame, n_workers=args.workers, maxtasksperchild=args.maxtasksperchild)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
