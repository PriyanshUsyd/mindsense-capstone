"""
Per-person slope standard-error bootstrap — closes the gap flagged in
`backend.statistics.evidence`'s module docstring (`extract_person_slopes`
currently returns `slope_se=None`/`slope_p=None` for everyone because
`nlme::ranef()` has no per-person conditional-variance extraction, and a
delta-method check confirmed `nlme` cannot supply one — see that
investigation's conclusion).

Implements both bootstrap designs agreed for comparison:

  - **parametric**: resimulate `y` from the real fit's own generative
    parameters (`beta`, the random-effects covariance `D`, AR(1) `phi`,
    residual `sigma`), refit, collect the resimulated per-person slopes.
    `nlme::simulate.lme` cannot be used for this — confirmed directly by
    calling it on the real AR(1) fit: it raises `models with "corStruct"
    and/or "varFunc" objects not allowed`, and its actual purpose (null-
    vs-alternative likelihood-ratio simulation, per its own help page) is
    a different thing entirely. Simulation here is therefore hand-rolled
    in Python/NumPy, matching the fitted model's own stated simplification
    that `corAR1(form = ~ 1 | uid)` treats each person's occasions as
    equally spaced by *occasion index*, not by calendar-day gap (see
    `r_bridge.fit_lme_ar1`'s docstring) — this bootstrap's residual
    generator uses the same by-index AR(1) recursion, not a calendar-
    aware one, so it resamples from the same DGP the model actually
    assumes, not some idealised one it doesn't.
  - **cluster**: resample participants with replacement (case bootstrap).
    A participant selected more than once is relabelled with a synthetic
    uid per copy (`"{uid}__boot{k}"`) so `nlme::lme` treats repeated
    copies as distinct clusters — feeding duplicate rows under one real
    uid would instead just double that person's occasion count within a
    single cluster, collapsing exactly the between-cluster variability
    this design is meant to capture. `x_within`/`x_between` are NOT
    recomputed from the resampled sample; each resampled copy carries its
    source participant's real covariate values unchanged (the standard
    case-resampling bootstrap — resample clusters, not their covariates).

Both methods require the R `nlme` engine (`fit_ar1_effect`'s primary
path): there is no per-person BLUP to bootstrap from the GEE fallback.

Parallelisation is process-based (R/rpy2 is not thread-safe, and only one
R can be embedded safely per OS process — see `r_bridge.py`'s own
docstring). A persistent worker pool (`multiprocessing` with `spawn`,
Windows' only option anyway) amortises R/rpy2 + package-import startup
(measured ~5s cold) across many iterations per worker rather than paying
it per iteration (measured single-fit cost: ~14.55s on the real dataset,
so paying 5s per iteration would be a ~34% overhead multiplied across
every draw).

Every iteration is checkpointed to a JSON-Lines file as it completes, so
a run can be interrupted and resumed without redoing completed work.
Seeds are derived deterministically from `(master_seed, method,
iteration_index)` via `numpy.random.SeedSequence`, independent of
execution order or worker count — the same iteration always reproduces
the same draw.
"""

from __future__ import annotations

import ctypes
import json
import multiprocessing as mp
import os
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats

from backend.statistics import r_bridge
from backend.statistics.evidence import X_WITHIN_TERM, PersonSlope
from backend.statistics.mixed_effects_model import Ar1EffectResult, fit_ar1_effect

INTERCEPT_TERM = "Intercept"

BootstrapMethod = Literal["parametric", "cluster"]
_METHOD_IDS = {"parametric": 0, "cluster": 1}


if sys.platform == "win32":
    from ctypes import wintypes

    class _ProcessMemoryCounters(ctypes.Structure):
        """Mirrors Win32's PROCESS_MEMORY_COUNTERS (psapi.h) — only the
        fields GetProcessMemoryInfo actually needs to fill in matter
        here."""

        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    # Explicit argtypes/restype are required, not cosmetic: GetCurrentProcess's
    # pseudo-handle is the 64-bit all-bits-set value (0xFFFFFFFF_FFFFFFFF).
    # ctypes' *default* marshalling for an undeclared return/argument treats
    # it as a plain (signed, 32-bit-range) int, and raises `OverflowError:
    # int too long to convert` trying to pass that value back in as an
    # argument — discovered the hard way testing this against the real
    # dataset (2026-09-13). Declaring both as wintypes.HANDLE makes ctypes
    # marshal the pointer-sized value correctly instead.
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _psapi = ctypes.WinDLL("psapi", use_last_error=True)
    _kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    _kernel32.GetCurrentProcess.argtypes = []
    _psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    _psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessMemoryCounters), wintypes.DWORD]

    class _MemoryStatusEx(ctypes.Structure):
        """Mirrors Win32's MEMORYSTATUSEX (sysinfoapi.h) — system-wide (not
        per-process) memory, for GlobalMemoryStatusEx."""

        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    _kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
    _kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MemoryStatusEx)]


def _current_process_rss_mb() -> float | None:
    """Current process's working-set size (RSS, MB) — a worker's R
    interpreter's heap shows up here since rpy2 embeds R in-process (no
    separate Rterm.exe to inspect). Windows-only, via the psapi
    `GetProcessMemoryInfo` Win32 API directly through `ctypes` — no extra
    dependency (e.g. `psutil`) added just for this one diagnostic. Added
    2026-09-13 after an 11-worker B=500 run was killed by the OS for
    system-wide low memory: recorded per iteration from here on so the
    next time this happens, the checkpoint itself shows the growth curve
    (how many iterations before a worker's RSS gets dangerous) instead of
    only "it died at some point." Returns `None` on any non-Windows
    platform or if the API call fails — never raises, since this is a
    diagnostic, not something that should fail an iteration."""
    if sys.platform != "win32":
        return None
    try:
        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
        handle = _kernel32.GetCurrentProcess()
        ok = _psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        if not ok:
            return None
        return counters.WorkingSetSize / (1024 * 1024)
    except Exception:  # noqa: BLE001 - diagnostic only, must never break an iteration
        return None


def _system_free_memory_mb() -> float | None:
    """System-wide available physical memory (MB), not this process's own
    RSS — `GlobalMemoryStatusEx`, same no-new-dependency rationale as
    `_current_process_rss_mb`. Added alongside it 2026-09-13: the 2026-09-13
    OOM kill was a *system-wide* low-memory condition (the OS killed every
    worker, not one process hitting its own limit), so a per-worker RSS
    curve alone doesn't show the thing that actually triggered the kill —
    this does. Recorded per iteration so a future run's checkpoint shows
    when headroom got tight, not just that a worker eventually died."""
    if sys.platform != "win32":
        return None
    try:
        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(_MemoryStatusEx)
        ok = _kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        if not ok:
            return None
        return status.ullAvailPhys / (1024 * 1024)
    except Exception:  # noqa: BLE001 - diagnostic only, must never break an iteration
        return None


@contextmanager
def _sample_peak_rss(interval_seconds: float = 2.0):
    """Background-thread RSS sampler for the lifetime of a `with` block.
    Added 2026-09-13: `rss_mb` recorded at iteration completion (see
    `_finalize_iteration_record`) can only ever show the memory state
    *after* the fit already finished — a transient spike mid-fit that
    subsides before the iteration returns would never appear in that one
    snapshot, and a real OOM kill on the real dataset that day was never
    explained by the completion-time snapshots alone. This polls
    `_current_process_rss_mb()` every `interval_seconds` on a daemon
    thread and tracks the running max, so the checkpoint can show "this
    iteration peaked at X MB," not just "ended at Y MB."

    Yields a single-element list `[peak_mb]` — read it after the `with`
    block exits, not during (the thread keeps mutating it). `peak_mb` is
    `None` only if RSS could never be read even once (non-Windows, or the
    API call failed every time); it is never a stale/zero placeholder.

    Overhead is one extra thread plus a `GetProcessMemoryInfo` call every
    ~2s for the duration of one ~30-45s fit — a handful of syscalls, not a
    measurable fraction of the fit's own cost."""
    peak: list[float | None] = [None]
    stop_event = threading.Event()

    def _poll() -> None:
        while not stop_event.is_set():
            rss = _current_process_rss_mb()
            if rss is not None:
                peak[0] = rss if peak[0] is None else max(peak[0], rss)
            stop_event.wait(interval_seconds)

    thread = threading.Thread(target=_poll, daemon=True)
    thread.start()
    try:
        yield peak
    finally:
        stop_event.set()
        thread.join(timeout=interval_seconds + 1)


def derive_seed(master_seed: int, method: BootstrapMethod, iteration_index: int) -> int:
    """Deterministic, independent seed for one `(method, iteration_index)`
    draw, regardless of which worker process executes it or in what
    order. Uses `numpy.random.SeedSequence`'s documented support for
    arbitrary integer-sequence entropy (not `.spawn()`, which tracks a
    call-order-dependent internal counter — entropy keyed directly by the
    thing we want to vary is what makes this safe to call from any
    worker, any number of times, and on resume after a crash)."""
    ss = np.random.SeedSequence([int(master_seed), _METHOD_IDS[method], int(iteration_index)])
    return int(ss.generate_state(1, dtype=np.uint64)[0])


@dataclass
class RealFit:
    """The one-time real-data AR(1) fit, plus the exact (sorted, NaN-free)
    model frame it was fit on and the generative parameters a parametric
    bootstrap needs to resimulate from it."""

    ar1_result: Ar1EffectResult
    model_frame: pd.DataFrame
    outcome_col: str
    uid_col: str
    date_col: str
    fixed_effect_names: list[str]


def fit_real_model(
    model_frame: pd.DataFrame,
    outcome_col: str = "phq4_score",
    uid_col: str = "uid",
    date_col: str = "date",
    extra_fixed_effects: list[str] | None = None,
) -> RealFit:
    """Fits the real AR(1) model once (via `fit_ar1_effect`, R primary
    path required) and sorts the model frame by `[uid_col, date_col]` —
    every bootstrap replicate below assumes that row order already
    matches occasion order per person, since `corAR1(form = ~ 1 |
    uid_col)` itself has no explicit time covariate and relies on row
    order within each group."""
    extra_fixed_effects = extra_fixed_effects or []
    fixed_effect_names = ["x_within", "x_between", *extra_fixed_effects]

    data = model_frame.dropna(subset=[outcome_col, date_col, *fixed_effect_names]).copy()
    data = data.sort_values([uid_col, date_col]).reset_index(drop=True)

    ar1_result = fit_ar1_effect(
        data,
        outcome_col=outcome_col,
        uid_col=uid_col,
        date_col=date_col,
        extra_fixed_effects=extra_fixed_effects or None,
        prefer_r=True,
    )
    if ar1_result.blups is None or ar1_result.sigma is None or ar1_result.random_effects_cov is None:
        raise ValueError(
            "bootstrap requires the R nlme::lme engine's real BLUPs and variance "
            f"components (got engine={ar1_result.engine!r}); R/rpy2/nlme must be "
            "usable here — see docs/statistics/r-bridge-setup.md"
        )

    return RealFit(
        ar1_result=ar1_result,
        model_frame=data,
        outcome_col=outcome_col,
        uid_col=uid_col,
        date_col=date_col,
        fixed_effect_names=fixed_effect_names,
    )


def _simulate_parametric_outcome(
    data: pd.DataFrame,
    uid_col: str,
    fixed_effect_names: list[str],
    beta: dict[str, float],
    random_effects_cov: dict[str, dict[str, float]],
    sigma: float,
    phi: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """y* = X*beta_hat + Z*u_i + e, u_i ~ MVN(0, D) per person, e an AR(1)
    residual generated by *occasion order within each person* (`data`
    must already be sorted `[uid_col, date]` — see `fit_real_model`),
    matching what the fitted `corAR1(form = ~ 1 | uid)` itself assumes."""
    re_terms = list(random_effects_cov.keys())
    cov_matrix = np.array([[random_effects_cov[r][c] for c in re_terms] for r in re_terms])

    y = np.full(len(data), beta.get(INTERCEPT_TERM, 0.0), dtype=float)
    for term in fixed_effect_names:
        y = y + beta[term] * data[term].to_numpy()

    innovation_sd = sigma * np.sqrt(max(1.0 - phi**2, 0.0))
    e = np.empty(len(data))

    for _uid, group in data.groupby(uid_col, sort=False):
        positions = group.index.to_numpy()
        n = len(positions)

        u_i = rng.multivariate_normal(np.zeros(len(re_terms)), cov_matrix)
        for i, term in enumerate(re_terms):
            if term == INTERCEPT_TERM:
                y[positions] += u_i[i]
            elif term in group.columns:
                y[positions] += u_i[i] * group[term].to_numpy()

        eps = rng.normal(0.0, 1.0, size=n)
        e_uid = np.empty(n)
        e_uid[0] = sigma * rng.normal(0.0, 1.0)
        for t in range(1, n):
            e_uid[t] = phi * e_uid[t - 1] + innovation_sd * eps[t]
        e[positions] = e_uid

    return y + e


def _fit_bootstrap_replicate(
    sim_frame: pd.DataFrame,
    outcome_col: str,
    uid_col: str,
    date_col: str,
    fixed_effect_names: list[str],
) -> dict:
    """Refits one bootstrap replicate and extracts exactly what's needed
    for the per-person slope draw. Never raises: any hard R/fit failure
    — including a random-intercept-only fallback that itself fails to
    converge, which `fit_ar1_effect` does not catch on its own (see
    `r_bridge._fit_lme_ar1`'s docstring) — is reported via `error` so the
    caller can exclude this replicate rather than the whole run dying."""
    extra_fixed_effects = [t for t in fixed_effect_names if t not in ("x_within", "x_between")]
    try:
        result = fit_ar1_effect(
            sim_frame,
            outcome_col=outcome_col,
            uid_col=uid_col,
            date_col=date_col,
            extra_fixed_effects=extra_fixed_effects or None,
            prefer_r=True,
        )
    except Exception as exc:  # noqa: BLE001 - isolate this one replicate's failure, see docstring
        return {"error": f"{type(exc).__name__}: {exc}"}

    if result.blups is None:
        return {"error": f"no BLUPs produced (engine={result.engine!r})"}

    return {
        "error": None,
        "used_random_slope": result.used_random_slope,
        "fallback_reason": result.fallback_reason,
        "ar1_phi": float(result.ar1_coefficient),
        "beta": {k: float(v) for k, v in result.params.items()},
        "blups": {str(uid): {k: float(v) for k, v in effects.items()} for uid, effects in result.blups.items()},
    }


def _finalize_iteration_record(
    method: BootstrapMethod,
    iteration_index: int,
    seed: int,
    fit_result: dict,
    elapsed_seconds: float,
    uid_map: dict[str, str] | None = None,
    selection_counts: dict[str, int] | None = None,
    peak_rss_mb: float | None = None,
) -> dict:
    """`usable` (for per-person SE aggregation) requires both a clean fit
    AND a random-slope model — a fallback to random-intercept-only has no
    `x_within` BLUP variation across people and would silently flatten
    every person's slope_i* to the same population value for that
    iteration, understating (not just missing) the true bootstrap
    variance if blended in uncritically. Recorded either way (for the
    failure/fallback-rate report), just excluded from the SE itself.

    `worker_pid` / `rss_mb` / `system_free_mb` / `peak_rss_mb` are
    diagnostic, not used by any aggregation function below — captured
    here (the process actually doing the fit, not the main process
    collecting results) so a per-worker memory-growth curve, the
    system-wide headroom, AND the in-flight peak during the fit itself
    (not just at completion) are all visible in the checkpoint after the
    fact. See `_current_process_rss_mb`'s, `_system_free_memory_mb`'s, and
    `_sample_peak_rss`'s docstrings for why each was added."""
    usable = fit_result.get("error") is None and fit_result.get("used_random_slope") is True
    return {
        "method": method,
        "iteration_index": iteration_index,
        "seed": seed,
        "elapsed_seconds": elapsed_seconds,
        "worker_pid": os.getpid(),
        "rss_mb": _current_process_rss_mb(),
        "peak_rss_mb": peak_rss_mb,
        "system_free_mb": _system_free_memory_mb(),
        "usable": usable,
        "error": fit_result.get("error"),
        "used_random_slope": fit_result.get("used_random_slope"),
        "fallback_reason": fit_result.get("fallback_reason"),
        "ar1_phi": fit_result.get("ar1_phi"),
        "beta": fit_result.get("beta"),
        "blups": fit_result.get("blups"),
        "uid_map": uid_map,
        "selection_counts": selection_counts,
    }


def _run_parametric_iteration(
    iteration_index: int,
    seed: int,
    data: pd.DataFrame,
    outcome_col: str,
    uid_col: str,
    date_col: str,
    fixed_effect_names: list[str],
    beta: dict[str, float],
    random_effects_cov: dict[str, dict[str, float]],
    sigma: float,
    phi: float,
) -> dict:
    t0 = time.time()
    rng = np.random.default_rng(seed)

    with _sample_peak_rss() as peak:
        sim_frame = data.copy()
        sim_frame[outcome_col] = _simulate_parametric_outcome(
            data, uid_col, fixed_effect_names, beta, random_effects_cov, sigma, phi, rng
        )
        fit_result = _fit_bootstrap_replicate(sim_frame, outcome_col, uid_col, date_col, fixed_effect_names)

    return _finalize_iteration_record(
        "parametric", iteration_index, seed, fit_result, time.time() - t0, peak_rss_mb=peak[0]
    )


def _run_cluster_iteration(
    iteration_index: int,
    seed: int,
    data: pd.DataFrame,
    outcome_col: str,
    uid_col: str,
    date_col: str,
    fixed_effect_names: list[str],
) -> dict:
    t0 = time.time()
    rng = np.random.default_rng(seed)

    with _sample_peak_rss() as peak:
        real_uids = data[uid_col].unique()
        draws = rng.choice(real_uids, size=len(real_uids), replace=True)
        groups_by_uid = {uid: group for uid, group in data.groupby(uid_col, sort=False)}

        parts = []
        uid_map: dict[str, str] = {}
        for copy_idx, real_uid in enumerate(draws):
            group = groups_by_uid[real_uid].copy()
            synthetic_uid = f"{real_uid}__boot{copy_idx}"
            group[uid_col] = synthetic_uid
            uid_map[synthetic_uid] = str(real_uid)
            parts.append(group)
        resampled = pd.concat(parts, ignore_index=True)

        fit_result = _fit_bootstrap_replicate(resampled, outcome_col, uid_col, date_col, fixed_effect_names)

    selection_counts = pd.Series(draws).value_counts().astype(int).to_dict()
    selection_counts = {str(k): int(v) for k, v in selection_counts.items()}

    return _finalize_iteration_record(
        "cluster", iteration_index, seed, fit_result, time.time() - t0,
        uid_map=uid_map, selection_counts=selection_counts, peak_rss_mb=peak[0],
    )


# ---------------------------------------------------------------------------
# Checkpointing (JSON Lines — append-only, resumable)
# ---------------------------------------------------------------------------


def load_completed_keys(path: Path) -> set[tuple[str, int]]:
    if not path.exists():
        return set()
    keys = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            keys.add((rec["method"], rec["iteration_index"]))
    return keys


def append_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Parallel execution (process pool, one persistent R interpreter per worker)
# ---------------------------------------------------------------------------

_WORKER_STATE: dict = {}


def _worker_init(
    model_frame: pd.DataFrame,
    outcome_col: str,
    uid_col: str,
    date_col: str,
    fixed_effect_names: list[str],
    beta: dict[str, float],
    random_effects_cov: dict[str, dict[str, float]],
    sigma: float,
    phi: float,
) -> None:
    """Pool(initializer=...): runs once per worker process before it
    takes any task. Warms up R/rpy2 + lme4/lmerTest/pbkrtest/nlme here
    (`r_bridge._load_r()` is itself `lru_cache`d, so this pays the ~5s
    import cost once per worker, not once per iteration) and stashes the
    (identical, otherwise-large) model frame and fit parameters as
    process-global state so each task only needs to ship a tiny
    `(method, iteration_index, seed)` tuple."""
    global _WORKER_STATE
    r_bridge.r_bridge_available()
    _WORKER_STATE = {
        "data": model_frame,
        "outcome_col": outcome_col,
        "uid_col": uid_col,
        "date_col": date_col,
        "fixed_effect_names": fixed_effect_names,
        "beta": beta,
        "random_effects_cov": random_effects_cov,
        "sigma": sigma,
        "phi": phi,
    }


def _worker_task(task: tuple[str, int, int]) -> dict:
    method, iteration_index, seed = task
    st = _WORKER_STATE
    if method == "parametric":
        return _run_parametric_iteration(
            iteration_index, seed, st["data"], st["outcome_col"], st["uid_col"], st["date_col"],
            st["fixed_effect_names"], st["beta"], st["random_effects_cov"], st["sigma"], st["phi"],
        )
    if method == "cluster":
        return _run_cluster_iteration(
            iteration_index, seed, st["data"], st["outcome_col"], st["uid_col"], st["date_col"],
            st["fixed_effect_names"],
        )
    raise ValueError(f"unknown bootstrap method: {method!r}")


@dataclass
class BootstrapRunConfig:
    master_seed: int
    n_iterations: int
    checkpoint_path: Path
    methods: tuple[BootstrapMethod, ...] = ("parametric", "cluster")
    n_workers: int = 11
    # A long-lived worker embeds one R interpreter and never restarts it
    # across iterations (see _worker_init) -- R's own heap is not reliably
    # released back to the OS between fits, so a worker's resident memory
    # grows with every iteration it processes. Observed on the real dataset
    # 2026-09-13: 11 workers with no recycling exhausted this machine's 12GB
    # and were killed by the OS for system-wide low memory after ~29
    # iterations/worker on average (323 of 970 pending tasks completed
    # before the kill -- see the checkpoint file from that run).
    #
    # maxtasksperchild forces the pool to kill and respawn a worker after
    # this many tasks, capping the growth at a fixed ceiling instead of
    # leaving it unbounded. Chosen as 20, not the ~29 observed failure
    # point, to leave a margin rather than recycle right at the edge: a
    # respawn re-pays R/rpy2 + package-import startup (measured ~5s cold,
    # see _worker_init's docstring) against a ~27s single-fit cost, i.e.
    # +5s / 20 iterations = +0.25s/iteration amortised, under 1% overhead
    # on top of the ~27s/iteration baseline -- cheap insurance against
    # repeating the 2026-09-13 OOM kill. n_workers is left at 11: the
    # OOM here was a per-worker memory-growth problem, not a
    # too-many-workers-at-once problem (reducing worker count would only
    # have delayed the same failure, not fixed its cause), and this
    # machine had no other obvious large-process pressure side of the 11
    # workers at the time.
    maxtasksperchild: int | None = 20


def _pending_tasks(config: BootstrapRunConfig) -> list[tuple[str, int, int]]:
    completed = load_completed_keys(config.checkpoint_path)
    tasks = []
    for method in config.methods:
        for i in range(config.n_iterations):
            if (method, i) in completed:
                continue
            tasks.append((method, i, derive_seed(config.master_seed, method, i)))
    return tasks


def run_bootstrap_serial(real_fit: RealFit, config: BootstrapRunConfig) -> list[dict]:
    """No multiprocessing — for quick sanity checks (small `n_iterations`)
    and for environments where spawning a worker pool is undesirable.
    Same checkpoint file format/semantics as `run_bootstrap_parallel`."""
    beta = {k: float(v) for k, v in real_fit.ar1_result.params.items()}
    random_effects_cov = real_fit.ar1_result.random_effects_cov
    sigma = real_fit.ar1_result.sigma
    phi = real_fit.ar1_result.ar1_coefficient

    for method, iteration_index, seed in _pending_tasks(config):
        if method == "parametric":
            record = _run_parametric_iteration(
                iteration_index, seed, real_fit.model_frame, real_fit.outcome_col, real_fit.uid_col,
                real_fit.date_col, real_fit.fixed_effect_names, beta, random_effects_cov, sigma, phi,
            )
        else:
            record = _run_cluster_iteration(
                iteration_index, seed, real_fit.model_frame, real_fit.outcome_col, real_fit.uid_col,
                real_fit.date_col, real_fit.fixed_effect_names,
            )
        append_record(config.checkpoint_path, record)

    return load_records(config.checkpoint_path)


def run_bootstrap_parallel(real_fit: RealFit, config: BootstrapRunConfig) -> list[dict]:
    """Process pool (spawn — Windows' only option, and the right choice
    anyway since each worker needs its own embedded R), one persistent R
    interpreter per worker, `imap_unordered` over pending `(method,
    iteration_index)` tasks not already in the checkpoint file.

    `config.maxtasksperchild` recycles a worker after that many tasks —
    see the long comment on that field for why (an OOM kill on the real
    dataset, 2026-09-13) and why 20, specifically, was chosen."""
    tasks = _pending_tasks(config)
    if not tasks:
        return load_records(config.checkpoint_path)

    beta = {k: float(v) for k, v in real_fit.ar1_result.params.items()}
    random_effects_cov = real_fit.ar1_result.random_effects_cov
    sigma = real_fit.ar1_result.sigma
    phi = real_fit.ar1_result.ar1_coefficient

    ctx = mp.get_context("spawn")
    with ctx.Pool(
        processes=config.n_workers,
        initializer=_worker_init,
        initargs=(
            real_fit.model_frame, real_fit.outcome_col, real_fit.uid_col, real_fit.date_col,
            real_fit.fixed_effect_names, beta, random_effects_cov, sigma, phi,
        ),
        maxtasksperchild=config.maxtasksperchild,
    ) as pool:
        for record in pool.imap_unordered(_worker_task, tasks):
            append_record(config.checkpoint_path, record)

    return load_records(config.checkpoint_path)


# ---------------------------------------------------------------------------
# Per-person / population-level aggregation
# ---------------------------------------------------------------------------


def collect_person_slope_draws(records: list[dict], method: BootstrapMethod, beta_term: str = X_WITHIN_TERM) -> dict[str, list[float]]:
    """real_uid -> [slope_i* across every usable iteration of `method`].
    For cluster bootstrap, pooled across every synthetic copy of that
    real person (0, 1, or more per iteration, via `uid_map`)."""
    draws: dict[str, list[float]] = {}
    for rec in records:
        if rec["method"] != method or not rec["usable"]:
            continue
        beta = rec["beta"][beta_term]
        uid_map = rec.get("uid_map")
        for uid, effects in rec["blups"].items():
            real_uid = uid_map[uid] if uid_map else uid
            draws.setdefault(real_uid, []).append(beta + effects.get(beta_term, 0.0))
    return draws


def per_person_se(draws: dict[str, list[float]], min_draws: int = 2) -> pd.DataFrame:
    rows = []
    for uid, values in draws.items():
        arr = np.asarray(values, dtype=float)
        se = float(np.std(arr, ddof=1)) if len(arr) >= min_draws else float("nan")
        rows.append({"uid": uid, "n_bootstrap_draws": len(arr), "slope_se": se})
    return pd.DataFrame(rows)


def population_beta_se(records: list[dict], method: BootstrapMethod, beta_term: str = X_WITHIN_TERM) -> float:
    values = [rec["beta"][beta_term] for rec in records if rec["method"] == method and rec["usable"]]
    return float(np.std(values, ddof=1)) if len(values) >= 2 else float("nan")


def failure_summary(records: list[dict], method: BootstrapMethod) -> dict:
    method_records = [r for r in records if r["method"] == method]
    n_total = len(method_records)
    n_usable = sum(1 for r in method_records if r["usable"])
    n_error = sum(1 for r in method_records if r["error"] is not None)
    n_fallback = sum(1 for r in method_records if r["error"] is None and r["used_random_slope"] is False)
    return {
        "n_total": n_total,
        "n_usable": n_usable,
        "n_error": n_error,
        "n_fallback_to_intercept_only": n_fallback,
        "failure_rate": (n_error + n_fallback) / n_total if n_total else float("nan"),
    }


def selection_count_distribution(records: list[dict]) -> pd.DataFrame:
    """Cluster bootstrap only: for every real participant, how many times
    they were drawn per iteration, pooled across all cluster iterations —
    the "missingness in practice" the cluster design trades off against
    the parametric design (a person drawn 0 times in an iteration
    contributes no slope_i* draw from that iteration)."""
    rows = []
    for rec in records:
        if rec["method"] != "cluster" or rec.get("selection_counts") is None:
            continue
        for real_uid, count in rec["selection_counts"].items():
            rows.append({"iteration_index": rec["iteration_index"], "uid": real_uid, "times_selected": count})
    return pd.DataFrame(rows)


def build_person_slopes_from_bootstrap_se(real_fit: RealFit, se_df: pd.DataFrame) -> list[PersonSlope]:
    """Combines the REAL (non-bootstrap) per-person point estimate
    (`beta_hat + BLUP_i`, exactly what `evidence.extract_person_slopes`
    computes) with a bootstrap-derived `slope_se`, via a normal-
    approximation Wald p-value — `p = 2 * (1 - Phi(|slope_i / se_i|))`.
    Only the SE comes from the bootstrap; the point estimate is not
    re-centred on the bootstrap mean (no bias correction is applied —
    not asked for, and bias-correcting here would need its own
    justification separate from just closing the SE gap)."""
    result = real_fit.ar1_result
    beta = result.params[X_WITHIN_TERM]
    n_by_uid = real_fit.model_frame.groupby(real_fit.uid_col).size().to_dict()
    se_by_uid = se_df.set_index("uid")["slope_se"].to_dict()

    person_slopes = []
    for uid, effects in result.blups.items():
        slope_i = beta + effects.get(X_WITHIN_TERM, 0.0)
        se = se_by_uid.get(uid, float("nan"))
        if se is not None and np.isfinite(se) and se > 0:
            z = slope_i / se
            p = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
            slope_se_value: float | None = float(se)
        else:
            p = None
            slope_se_value = None
        person_slopes.append(
            PersonSlope(
                uid=uid,
                slope_i=slope_i,
                n_occasions=int(n_by_uid.get(uid, 0)),
                slope_se=slope_se_value,
                slope_p=p,
            )
        )
    return person_slopes
