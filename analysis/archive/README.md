# Archived — retired 2026-09-12

The three modules in this folder (`cleaning.py`, `baseline.py`,
`evidence_model.py`) were Moe Tanaka's standalone Week 5 statistics
pipeline. They are archived, not deleted, for historical reference and
because `analysis/output/` (one level up) still holds run artifacts
produced by them.

**Do not run these as a live pipeline going forward.** Their logic has
been reconciled into `backend/statistics/`, which is now the single
canonical engine:

| This archived module | Ported into |
|---|---|
| `cleaning.py` (12h quality gate, log-of-mean order of operations) | `backend/data_pipeline/cleaning.py` — the 12h gate was applied there 2026-09-12 (it had drifted to 8h); the log-of-mean order was applied to `backend/statistics/mixed_effects_model.py::build_trailing_predictor` the same day |
| `baseline.py` (three-state cold-start policy) | Already independently implemented in `backend/statistics/eligibility.py` (`classify_state`) since 2026-08-29 — confirmed 2026-09-12 to use identical gates; no porting needed |
| `evidence_model.py` (per-person evidence-strength, BH-FDR/Holm family-213 correction, binary collapse) | Ported into `backend/statistics/evidence.py` 2026-09-12, wired to run on `fit_ar1_effect`'s R-backed (`nlme::lme` + `corAR1`) AR(1)-corrected fixed effect and real per-person BLUPs, instead of this module's own uncorrected statsmodels estimates |

**Why this module could not simply keep running in parallel:** it also
depended on a `predictors.py` module (imported by `baseline.py`) that was
never committed to this repository — `analysis/baseline.py` as checked in
is not actually runnable as-is. The `analysis/output/` artifacts already
in this repo were produced from a local, uncommitted copy.

See `backend/statistics/evidence.py`'s module docstring for one specific,
flagged gap in the port (per-person standard errors are not yet
extractable from the R `nlme` wrapper this codebase uses, so per-person
significance currently fails safe to "insufficient" for everyone rather
than guessing). Moe Tanaka offered to complete this port herself and
should review `backend/statistics/evidence.py` before it is relied on for
anything beyond the plumbing check it currently passes.
