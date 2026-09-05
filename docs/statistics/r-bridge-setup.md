# R bridge setup — how R got installed here, and a real gotcha

This documents exactly how R was installed for
`backend/statistics/r_bridge.py` (Satterthwaite/Kenward-Roger
denominator df and a true AR(1) mixed-effects fit, replacing the
between-within approximation and the GEE AR(1) robustness check as the
primary path in `backend/statistics/mixed_effects_model.py` when R is
available) on this Windows development machine, on 2026-09-05. Read this
before assuming "R isn't available" or "the R tests are broken" — the
most likely explanation for either is one of the two gotchas below, not
a real problem.

## What's installed

- **R 4.6.1**, installed **without admin rights** — `choco install
  r.project` failed outright (`Access to the path
  'C:\ProgramData\chocolatey\lib-bad' is denied`, confirming no
  write access to system-wide install locations). Worked around by
  downloading the official Windows installer directly from
  `https://cloud.r-project.org/bin/windows/base/R-4.6.1-win.exe` and
  running it with `/VERYSILENT /CURRENTUSER /DIR=<user-writable path>` —
  the CRAN Windows installer supports a fully per-user, no-admin install
  when pointed at a directory the current user can write to. Installed
  to `C:\Users\<you>\R-4.6.1-mindsense` (deliberately **outside** the
  repo — R itself is ~200MB+ with packages, and must never be committed).
- **R packages**: `lme4`, `lmerTest`, `pbkrtest`, `nlme` (the last ships
  with base R already). All four installed as precompiled Windows
  binaries from CRAN (`type="win.binary"`) — no compiler/Rtools needed.
- **rpy2** (Python side): `pip install rpy2` — installed clean from a
  prebuilt Windows wheel, no compilation needed either.

None of this is committed to the repo. `backend/statistics/r_bridge.py`
is written to degrade gracefully (see its own docstring and
`RBridgeUnavailable`) on any machine where R isn't installed at all —
this doc is about reproducing the R-available case, not a hard
dependency of the codebase.

## Required environment variables

Whoever wants the R-backed primary path (rather than the automatic
Python fallback) needs, in the process running Python:

```
R_HOME=<path to the R install, e.g. C:\Users\you\R-4.6.1-mindsense>
PATH must include <R_HOME>\bin\x64
```

Without these, `r_bridge.r_bridge_available()` returns `False` and
`fit_mixed_effects_model`/`fit_ar1_effect` silently use the Python
fallback — not an error, just not the primary path.

## Gotcha 1: git-bash/MSYS breaks rpy2's R detection on Windows

**Importing `rpy2.robjects` from a Python process launched from
git-bash (MSYS/MINGW64) fails**, even with `R_HOME`/`PATH` set correctly
and R genuinely installed and working (`Rscript -e
'R.version.string'` runs fine from the same shell). The failure:

```
C:\...\R-4.6.1-mindsense/bin/config.sh: line 184: make: command not found
...
R was not built as a library
IndexError: list index out of range
  (in rpy2.situation._get_r_cmd_config, called from rpy2.rinterface_lib.openrlib)
```

rpy2's R_HOME flag detection runs `R CMD config --ldflags`, which on
Windows R dispatches to a Unix-style `bin/config.sh` helper bundled for
MSYS2/Cygwin compatibility — that script needs `make`, which isn't part
of a plain R install, and running under git-bash apparently makes R
choose that script path instead of the native Windows one. This is not
about R or rpy2 being broken; it's specifically about invoking Python
from git-bash.

**Fix: run Python from a native Windows shell (PowerShell or cmd), not
git-bash, whenever you need the R-backed path to actually engage** —
either interactively, or via a subprocess PowerShell launched from
somewhere else. `pytest` runs from git-bash will still pass — the
R-dependent tests are all decorated to skip automatically
(`r_bridge_available()` returns `False` from that shell, same as R
genuinely not being installed) — but they'll be *skipped*, not
*exercised*. To actually run them, use PowerShell:

```powershell
$env:R_HOME = "C:\Users\you\R-4.6.1-mindsense"
$env:PATH = "C:\Users\you\R-4.6.1-mindsense\bin\x64;" + $env:PATH
python -m pytest tests/statistics/test_r_bridge.py tests/statistics/test_mixed_effects_model.py -q
```

The `'sh' is not recognized...` message that appears even in PowerShell
runs is a harmless rpy2 startup warning (it probes for an `sh` binary
that plain Windows doesn't have) — not an error, safe to ignore.

## Gotcha 2: `nlme::lme`'s `fixed=` argument needs an actual formula object

`nlme::lme(fixed = "y ~ x", ...)` fails with `no applicable method for
'lme' applied to an object of class "character"` — unlike
`lme4::lmer("y ~ x", ...)`, which accepts a formula given as a plain
string. `r_bridge.fit_lme_ar1` wraps the formula string in
`as.formula(...)` before passing it to `nlme::lme` for exactly this
reason.

## Why `converged` filters out "singular fit" messages specifically

`lme4`'s `model@optinfo$conv$lme4$messages` can contain the exact string
`"boundary (singular) fit: see help('isSingular')"` — which is a
*different* condition from genuine optimizer non-convergence
(`lme4::isSingular()` is the correct check for it, already captured
separately as `RSatterthwaiteResult.is_singular`). Treating "any message
present" as "did not converge" was an early bug here: it reported
`converged=False` on a random-intercept-only fallback model that had
converged (in the ordinary sense) but happened to sit at a singular
boundary — the same real, valid outcome the Python/statsmodels path
would report as `converged=True` with a separately-flagged degenerate
covariance. `fit_lmer_with_denominator_df` filters singular-fit messages
out of the genuine-convergence check accordingly.
