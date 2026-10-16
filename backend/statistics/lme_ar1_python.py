"""
Pure-Python (NumPy/SciPy) fit of the same model `r_bridge.fit_lme_ar1` fits
with R `nlme::lme` — the engine the bootstrap cache uses when R/rpy2 is not
usable (see `backend.statistics.bootstrap`).

Model (identical to the R call):

    y_it = x_it' beta + z_it' b_i + e_it
    b_i ~ N(0, D),   z_it = (1, x_within_it)        random = ~ x_within | uid
    e_i ~ N(0, sigma^2 R_i(phi))                     corAR1(form = ~ 1 | uid)

`R_i(phi)` is the AR(1) correlation by *occasion index* within each person
(rows must already be in occasion order per person, as `bootstrap
.prepare_model_frame` guarantees), exactly what `corAR1(form = ~ 1 | uid)`
assumes.

Estimation is REML, nlme's default. `beta` and `sigma^2` are profiled out;
the remaining parameters (phi and the scaled random-effects covariance
`Psi = D / sigma^2`, via a log-Cholesky factor) are found with
`scipy.optimize.minimize`. The AR(1) inverse is tridiagonal, so every
`a' R_i^{-1} b` is a combination of three per-person Gram matrices, and the
random effects enter through a q x q (q <= 2) Woodbury update. One objective
evaluation is O(N) and fully vectorised across people.

Outputs mirror `r_bridge.RAr1Result`: fixed effects with REML standard errors
and t-test p-values (nlme's denominator degrees of freedom for one grouping
level), BLUPs `b_i = Psi Z_i' V_i^{-1} (y_i - X_i beta)`, `D`, `sigma` and
`phi`. Same fallback policy as R: the random-slope model is tried first and a
random-intercept-only model is used, with `fallback_reason`, if it does not
converge.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize, stats

ENGINE_NAME = "Python (NumPy/SciPy REML lme + AR(1))"
INTERCEPT = "Intercept"
_PHI_BOUND = 1.0 - 1e-9


@dataclass
class PyAr1Result:
    used_random_slope: bool
    fallback_reason: str | None
    ar1_phi: float
    n_observations: int
    n_groups: int
    params: dict[str, float]
    se: dict[str, float]
    pvalues: dict[str, float]
    blups: dict[str, dict[str, float]]
    sigma: float
    random_effects_cov: dict[str, dict[str, float]]
    converged: bool
    reml_objective: float


class _Grams:
    """Per-person Gram matrices of the columns `C = [X, y]` (rows in occasion
    order), from which `C_i' R_i(phi)^{-1} C_i` follows for any phi."""

    def __init__(self, columns: np.ndarray, group_codes: np.ndarray, n_groups: int):
        k = columns.shape[1]
        outer = columns[:, :, None] * columns[:, None, :]
        self.full = np.zeros((n_groups, k, k))
        np.add.at(self.full, group_codes, outer)
        self.sizes = np.bincount(group_codes, minlength=n_groups)
        first = np.r_[True, group_codes[1:] != group_codes[:-1]]
        last = np.r_[group_codes[1:] != group_codes[:-1], True]
        ends = np.zeros((n_groups, k, k))
        np.add.at(ends, group_codes[first], outer[first])
        np.add.at(ends, group_codes[last], outer[last])
        # Interior rows only (first and last excluded); zero for one-row groups.
        self.inner = np.where(self.sizes[:, None, None] >= 2, self.full - ends, 0.0)
        same = group_codes[1:] == group_codes[:-1]
        lag = columns[:-1, :, None] * columns[1:, None, :]
        lag = lag + np.swapaxes(lag, 1, 2)
        self.lag = np.zeros((n_groups, k, k))
        np.add.at(self.lag, group_codes[1:][same], lag[same])
        self.single = self.sizes == 1

    def quad(self, phi: float) -> np.ndarray:
        """`C_i' R_i^{-1} C_i` for every person: R^{-1} = T / (1 - phi^2) with
        T tridiagonal (diagonal 1, 1+phi^2, ..., 1+phi^2, 1; off-diagonal -phi)."""
        q = (self.full + phi**2 * self.inner - phi * self.lag) / (1.0 - phi**2)
        q[self.single] = self.full[self.single]
        return q


def _psi_factor(theta: np.ndarray, q: int) -> np.ndarray:
    L = np.zeros((q, q))
    L[np.tril_indices(q)] = theta
    L[np.diag_indices(q)] = np.exp(np.clip(np.diag(L), -30.0, 30.0))
    return L


class _Problem:
    def __init__(self, data: pd.DataFrame, outcome_col: str, fixed: list[str], uid_col: str, random_slope: bool):
        codes, uniques = pd.factorize(data[uid_col], sort=False)
        order = np.argsort(codes, kind="stable")  # group rows, keep occasion order within each person
        self.codes = codes[order]
        self.uids = [str(u) for u in uniques]
        self.n_groups = len(uniques)
        self.fixed_names = [INTERCEPT, *fixed]
        X = np.column_stack([np.ones(len(data)), data[fixed].to_numpy(float)])[order]
        y = data[outcome_col].to_numpy(float)[order]
        # Covariates are rescaled to unit SD for the optimisation (raw unlock
        # counts put the random-slope SD near 1e-3). Rescaling X and Z only
        # reparametrises beta and D and shifts the REML deviance by a constant,
        # so the optimum is the same model; `_finish` transforms back.
        sd = X.std(axis=0)
        self.scale = np.where((np.arange(X.shape[1]) > 0) & (sd > 0), sd, 1.0)
        X = X / self.scale
        self.N, self.p = X.shape
        self.z_names = [INTERCEPT, "x_within"] if random_slope else [INTERCEPT]
        self.ix_z = [self.fixed_names.index(n) for n in self.z_names]
        self.q = len(self.ix_z)
        self.grams = _Grams(np.column_stack([X, y]), self.codes, self.n_groups)
        self.ix_x = list(range(self.p))
        self.ix_y = self.p

    def pieces(self, params: np.ndarray):
        phi = np.tanh(params[0])
        L = _psi_factor(params[1:], self.q)
        A = self.grams.quad(phi)
        ZRZ = A[:, self.ix_z][:, :, self.ix_z]
        ZRC = A[:, self.ix_z, :]  # Z' R^-1 [X, y]
        K = np.eye(self.q) + L.T @ ZRZ @ L
        Kinv = np.linalg.inv(K)
        W = L @ Kinv @ L.T  # per person; (R + Z Psi Z')^-1 = R^-1 - R^-1 Z W Z' R^-1
        CVC = A - np.swapaxes(ZRC, 1, 2) @ W @ ZRC
        logdet = (self.grams.sizes - 1) * np.log(1.0 - phi**2) + np.linalg.slogdet(K)[1]
        return phi, L, CVC, logdet, W, ZRC

    def objective(self, params: np.ndarray) -> float:
        """REML deviance up to a constant: (N-p) log s2 + sum log|V_i/s2| + log|X'V^-1 X / s2|."""
        try:
            _phi, _L, CVC, logdet, _W, _ZRC = self.pieces(params)
            total = CVC.sum(axis=0)
            XVX = total[: self.p, : self.p]
            XVy = total[: self.p, self.ix_y]
            beta = np.linalg.solve(XVX, XVy)
            rss = total[self.ix_y, self.ix_y] - XVy @ beta
            if not np.isfinite(rss) or rss <= 0:
                return np.inf
            s2 = rss / (self.N - self.p)
            sign, ld_x = np.linalg.slogdet(XVX)
            if sign <= 0:
                return np.inf
            return float((self.N - self.p) * np.log(s2) + logdet.sum() + ld_x)
        except np.linalg.LinAlgError:
            return np.inf


def _start(problem: _Problem) -> np.ndarray:
    return np.r_[np.arctanh(0.3), np.zeros(problem.q * (problem.q + 1) // 2)]


def _minimize(problem: _Problem):
    best = None
    x0 = _start(problem)
    for method, options in (
        ("BFGS", {"gtol": 1e-9, "maxiter": 2000}),
        ("Nelder-Mead", {"xatol": 1e-10, "fatol": 1e-12, "maxiter": 20000, "maxfev": 40000}),
        ("BFGS", {"gtol": 1e-10, "maxiter": 2000}),
    ):
        res = optimize.minimize(problem.objective, x0, method=method, options=options)
        if best is None or res.fun <= best.fun:
            best = res
        x0 = best.x
    return best


def _denominator_df(problem: _Problem, data: pd.DataFrame, fixed: list[str], uid_col: str) -> dict[str, float]:
    """nlme's denominator df for one grouping level (checked against
    `summary(lme)$tTable` on the real data): the intercept and every term that
    varies within a person are tested at the observation level,
    df = N - G - (number of within-person terms); a term constant within every
    person is tested at the person level, df = G - 1 - (number of such terms)."""
    varies = {name: bool((data.groupby(uid_col)[name].nunique() > 1).any()) for name in fixed}
    inner = [n for n in fixed if varies[n]]
    outer = [n for n in fixed if not varies[n]]
    df_inner = problem.N - problem.n_groups - len(inner)
    df_outer = problem.n_groups - 1 - len(outer)
    return {n: float(df_outer if n in outer else df_inner) for n in problem.fixed_names}


def _finish(problem: _Problem, res, data, fixed, uid_col, fallback_reason) -> PyAr1Result:
    phi, L, CVC, _logdet, W, ZRC = problem.pieces(res.x)
    total = CVC.sum(axis=0)
    XVX = total[: problem.p, : problem.p]
    XVy = total[: problem.p, problem.ix_y]
    beta = np.linalg.solve(XVX, XVy)
    s2 = (total[problem.ix_y, problem.ix_y] - XVy @ beta) / (problem.N - problem.p)
    cov_beta = s2 * np.linalg.inv(XVX)
    se = np.sqrt(np.diag(cov_beta)) / problem.scale
    beta = beta / problem.scale
    df = _denominator_df(problem, data, fixed, uid_col)
    tvals = beta / se
    names = problem.fixed_names
    pvals = {n: float(2.0 * stats.t.sf(abs(t), df[n])) for n, t in zip(names, tvals)}
    # BLUP: b_i = Psi Z' V^-1 r = L K^-1 L' Z' R^-1 (y - X beta) = W Z'R^-1 r
    zr = ZRC[:, :, problem.ix_y] - ZRC[:, :, : problem.p] @ (beta * problem.scale)
    z_scale = problem.scale[problem.ix_z]
    b = (W @ zr[:, :, None])[:, :, 0] / z_scale
    D = s2 * (L @ L.T) / np.outer(z_scale, z_scale)
    return PyAr1Result(
        used_random_slope=problem.q == 2,
        fallback_reason=fallback_reason,
        ar1_phi=float(phi),
        n_observations=problem.N,
        n_groups=problem.n_groups,
        params=dict(zip(names, map(float, beta))),
        se=dict(zip(names, map(float, se))),
        pvalues=pvals,
        blups={uid: dict(zip(problem.z_names, map(float, row))) for uid, row in zip(problem.uids, b)},
        sigma=float(np.sqrt(s2)),
        random_effects_cov={
            r: {c: float(D[i, j]) for j, c in enumerate(problem.z_names)} for i, r in enumerate(problem.z_names)
        },
        converged=bool(np.isfinite(res.fun)),
        reml_objective=float(res.fun),
    )


_GRAD_STEP = 1e-4
_GRAD_TOL = 1e-2


def _converged(problem: _Problem, res) -> bool:
    """Central-difference gradient of the REML deviance at the optimum. The
    deviance is O(N) (about 2e4 on the real data), so a forward difference is
    dominated by rounding; central differences with step 1e-4 resolve it to
    about 1e-5. `_GRAD_TOL` = 0.01 deviance units per unit of parameter."""
    if not np.isfinite(res.fun) or abs(np.tanh(res.x[0])) >= _PHI_BOUND:
        return False
    eye = np.eye(len(res.x)) * _GRAD_STEP
    grad = np.array(
        [(problem.objective(res.x + e) - problem.objective(res.x - e)) / (2 * _GRAD_STEP) for e in eye]
    )
    return bool(np.all(np.isfinite(grad)) and np.max(np.abs(grad)) < _GRAD_TOL)


def fit_lme_ar1(data: pd.DataFrame, outcome_col: str, fixed_effect_names: list[str], uid_col: str) -> PyAr1Result:
    """Same contract as `r_bridge.fit_lme_ar1`; `data` rows must be in occasion
    order within each person."""
    fixed = list(fixed_effect_names)
    problem = _Problem(data, outcome_col, fixed, uid_col, random_slope=True)
    res = _minimize(problem)
    if _converged(problem, res):
        return _finish(problem, res, data, fixed, uid_col, None)
    reason = f"random-slope REML fit did not converge (objective={res.fun!r})"
    problem = _Problem(data, outcome_col, fixed, uid_col, random_slope=False)
    res = _minimize(problem)
    if not _converged(problem, res):
        raise RuntimeError(f"random-intercept REML fit did not converge after: {reason}")
    return _finish(problem, res, data, fixed, uid_col, reason)
