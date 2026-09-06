# Week 5 Post-Merge Dependency Privacy Review

Owner: Yuktha Naveen, Privacy and Security Lead

Review date: 6 September 2026 (Australia/Sydney)

Reviewed baseline: `6a5e6b6`

Scope: dependencies introduced by merged PRs #7 and #8

## Decision

Approved with mitigation for local development using synthetic or
de-identified data. This review does not approve participant deployment.

The two merged PR descriptions did not contain the standing dependency privacy
spot-check required by `.github/pull_request_template.md`. This retrospective
review closes the evidence gap, but future dependency-changing PRs must include
the completed checklist before merge.

## Frontend Test Dependencies

| Dependency | Version in lockfile | Purpose | Licence |
| --- | --- | --- | --- |
| `@testing-library/jest-dom` | 7.0.1 | DOM assertions | MIT |
| `@testing-library/react` | 16.3.3 | React component testing | MIT |
| `@testing-library/user-event` | 14.6.7 | Simulated user interaction | MIT |
| `jsdom` | 30.0.1 | Local test DOM | MIT |
| `vitest` | 5.0.0 | Frontend test runner | MIT |

Findings:

- These packages are declared as development dependencies and are not bundled
  into the production frontend by the Vite build.
- Installation downloads packages from the configured npm registry. The
  application does not install packages while processing participant data.
- No project configuration enables analytics, crash uploads, remote reporting,
  or browser-mode cloud testing.
- `vitest` declares `@opentelemetry/api` as an optional peer dependency in the
  lockfile. MindSense does not declare, install, or configure that optional
  package.
- The tests use synthetic fixture-shaped values and do not read the CES dataset.
- `npm ci` reported that local Node `22.19.0` is below `jsdom@30.0.1`'s declared
  minimum of `22.22.2`. All checks passed, but this is an unsupported local
  combination. Integration/QA should align the documented Node version and
  rerun before release.

Decision: approved for development-only use. Keep them in `devDependencies`,
retain the lockfile, and rerun `npm audit`, tests, lint, and the production build
after dependency changes.

## R Statistics Dependencies

| Dependency | Verified version | Purpose | Licence |
| --- | --- | --- | --- |
| R | 4.6.1 | Local statistical runtime | GPL-2 or GPL-3 |
| `rpy2` | 3.6.7 | Embedded R bridge for Python | GPL-2.0-or-later |
| `lme4` | 2.0-6 | Mixed-effects fitting | GPL (>= 2) |
| `lmerTest` | 3.2-1 | Denominator degrees of freedom | GPL (>= 2) |
| `pbkrtest` | 0.5.5 | Kenward-Roger support | GPL (>= 2) |
| `nlme` | 3.1-169 | AR(1) mixed-effects fitting | GPL (>= 2) |

Findings:

- Homebrew and CRAN require public-network access during explicit installation.
  Runtime package installation and automatic updates are not present in the
  application path.
- The reviewed `r_bridge.py` contains no Python or R calls for public networking,
  shell execution, package installation, telemetry, logging, or file writes.
- The bridge processes a local statistical dataframe containing an identifier,
  derived behavioural features, and PHQ-4 values. This is sensitive even when
  the identifier is pseudonymous.
- The original bridge retained its dataframe and fitted model in R's global
  workspace. The reviewed fix uses project-specific temporary names and restores
  or removes them on successful and failed fits.
- R workspace access is serialised so concurrent fits cannot overwrite or read
  another fit's temporary dataframe or model.
- `pytest-socket` controls Python sockets but cannot prove that native R code is
  unable to create a connection. A disconnected or OS-level blocked-network
  integrated run remains a release condition.
- `rpy2` is now pinned in the optional `requirements-r.txt`. R package versions
  remain recorded rather than machine-locked, so reproducibility across future
  CRAN releases remains a limitation.
- On this Apple Silicon Mac, the `rpy2` wheel's API mode looked for a CRAN R
  framework that was not installed. Verification therefore set
  `RPY2_CFFI_MODE=ABI` and successfully loaded Homebrew R 4.6.1. This
  environment setting must be retained or resolved before reproducing the
  R-active run on the same toolchain.

Decision: approved with mitigation for local statistical development. Do not run
Homebrew, pip, npm, or CRAN installation commands while real participant data is
loaded. Use minimised, pseudonymous inputs and retain the workspace-cleanup and
capability-allowlist tests.

## Verification Evidence

- New R privacy regression tests: 9/9 passed with the real R backend active.
- Focused privacy, SLM transport, R bridge, and mixed-effects tests: 55/55
  passed.
- Complete Python suite: 345/345 passed with 45 documented `statsmodels`
  convergence warnings and no skipped R tests.
- Ruff checks pass for the modified Python files. A repository-wide Ruff run
  reports 22 pre-existing findings in unrelated files; they were not changed by
  this privacy review.
- Frontend: 6/6 tests passed; lint and production build passed.
- `npm audit`: zero known vulnerabilities.
- `pip check`: no broken requirements.
- `pip-audit -r requirements.txt`: no known vulnerabilities.
- `pip-audit -r requirements-r.txt`: no known vulnerabilities.
- Installed-environment `pip-audit`: no known vulnerabilities.

Evidence paths:

- `backend/statistics/r_bridge.py`
- `tests/privacy/test_r_bridge_privacy.py`
- `tests/privacy/test_no_network_egress.py`
- `requirements-r.txt`
- `frontend/package-lock.json`

References:

- [rpy2 documentation](https://rpy2.github.io/doc/latest/html/overview.html)
- [CRAN lme4 package](https://cran.r-project.org/package=lme4)
- [CRAN lmerTest package](https://cran.r-project.org/package=lmerTest)
- [CRAN pbkrtest package](https://cran.r-project.org/package=pbkrtest)
- [CRAN nlme package](https://cran.r-project.org/package=nlme)
- [Vitest documentation](https://vitest.dev/)
- [Testing Library documentation](https://testing-library.com/)
