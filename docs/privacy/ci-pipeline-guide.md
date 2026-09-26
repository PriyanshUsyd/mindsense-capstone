# Four-Stage CI Pipeline Guide

Owner: Yuktha Naveen, Privacy and Security Lead

Workflow: `.github/workflows/privacy-security-ci.yml`

## Purpose

The pipeline separates application correctness, the embedded-R runtime,
frontend quality, and privacy/security controls. A failure therefore identifies
the responsible technical area instead of appearing as one mixed test result.

## Stage 1 - Python Application and Integration

This stage installs `requirements.txt`, runs `pip check`, and exercises the
Python backend, contracts, data pipeline, evaluation, SLM logic, Python
statistics fallback, and general integration tests.

It deliberately excludes:

- `tests/privacy/` and the privacy-specific data/transport tests, owned by Stage 4;
- `tests/integration/test_frontend_builds.py`, owned by Stage 3; and
- the R bridge, mixed-effects, and bootstrap test modules, owned by Stage 2.

## Stage 2 - R Statistical Runtime

This stage installs R 4.6.1, the approved R packages, `rpy2`, and both Python
requirements files. It refuses to continue unless the real R bridge is usable.
It then runs:

- `tests/statistics/test_r_bridge.py`;
- `tests/statistics/test_mixed_effects_model.py`;
- `tests/statistics/test_bootstrap.py`; and
- `tests/privacy/test_r_bridge_privacy.py`.

The final file is assigned here because its real workspace-cleanup checks need
an operational embedded-R runtime. Its static privacy rules remain part of the
same R-specific test module.

## Stage 3 - Frontend Test, Lint, and Build

This stage installs the exact packages in `frontend/package-lock.json`, then
runs Vitest, Oxlint, and the Vite production build. Dependency advisory scanning
is not mixed into this stage; it belongs to Stage 4.

Week 8 adds two synthetic tests in
`frontend/src/features/chat/NormalResponse.test.tsx`: chat turns must not be
written through Web Storage or survive a component remount, and model text
must render as text rather than create remote HTML elements. These do not
inspect all browser persistence mechanisms or prove memory erasure.

## Stage 4 - Privacy and Security Gates

This stage waits for the first three stages so that its run artifact can report
all four outcomes. It runs only privacy/security-specific checks:

- tracked participant-output and raw-identifier controls;
- API error redaction, `Cache-Control: no-store`, restricted CORS preflight,
  and rejection before participant-data access
  (`tests/privacy/test_api_response_privacy.py`, added in Week 8);
- deny-by-default network-egress tests;
- CES eligibility output privacy checks;
- loopback-only SLM transport and redirect checks;
- strict advisory audits for `requirements.txt` and `requirements-r.txt`; and
- the high/critical npm dependency audit.

This stage always creates `privacy-security-ci-run-<run>-<attempt>`, a Markdown
artifact containing the four-stage result table and Stage 4 detail.

## Failure Explanation Artifacts

If a stage fails, that stage creates a separate Markdown artifact retained for
90 days:

- `ci-failure-python-<run>-<attempt>`;
- `ci-failure-r-<run>-<attempt>`;
- `ci-failure-frontend-<run>-<attempt>`; or
- `ci-failure-privacy-security-<run>-<attempt>`.

Each report states the failed or skipped setup/check steps, lists likely cause
categories, and includes up to the last 200 lines of available command output.
The causes are diagnostic prompts, not automatic proof of root cause; the
captured output and linked GitHub Actions run remain the primary evidence.

## Automatic Versus Local Checks

The four CI stages use repository code and synthetic fixtures. They do not have
the gitignored CES dataset or the locally installed Phi-4 Mini model. The
following checks still require the Privacy Lead's local machine:

- real CES dataset-backed tests;
- the Phi-4 Mini latency benchmark and immutable history record;
- live frontend-to-FastAPI-to-Ollama inspection;
- process/network inspection while the application is running; and
- an operating-system-level disconnected-network run.

CI is read-only and never commits its generated Markdown artifacts to a branch.

For local Week 8 verification, use `docs/privacy/local-demo-privacy-check.md`.
Its tested macOS commands combine `privacy/macos-loopback.sb`, cloud-off, and
`LLAMA_ARG_CORS_ORIGINS=http://127.0.0.1:8000` for the native runner. The initial
runner-origin finding was mitigated in that configuration and the full
unsealed suite passed under the OS process network block. These settings are
not supplied by CI or applied to already-running processes. The browser and
the whole computer were not made offline. Final real-user account/deployment
approval remains outside this local-demo verification.

## Manual validation when sealed content cannot be accessed

The `workflow_dispatch` input `validation_scope` provides two explicit modes:

- `full`: the existing four-stage scope, including sealed integrity checks and
  the tracked-text scan of sealed content. This requires authorisation to access
  that content.
- `sealed-excluded`: development validation without accessing the sealed
  held-out working-tree directory. This is the default for manual runs only;
  automatic pull-request/push runs retain `full` scope.

A missing manual input falls back to `sealed-excluded`. An unknown scope cannot
enable full checkout; Stage 1 rejects it before running pytest and Stage 4's
identifier scanner rejects it before inventorying files.

In `sealed-excluded` mode, all four jobs use non-cone sparse checkout to omit
`tests/evaluation/held_out/`. Stage 1 also excludes that directory and
`tests/evaluation/test_held_out_integrity.py` before collection. Stage 4 keeps the
identifier gate enabled for other tracked text, excluding the sealed directory
at both Git inventory and Python path-filtering boundaries, before file access.
Synthetic regressions cover exclusion-before-access and detection of identifier
leaks in the remaining scope. R, frontend, network-isolation and dependency-audit
checks retain their existing commands.

The run name and Markdown run record state the selected scope. A successful
restricted run establishes only that scope; its report explicitly says full CI
acceptance is not established. It cannot certify sealed integrity, sealed-text
privacy, participant readiness or owner approval. Priyansh, Yuktha and Chonghao
still decide the appropriate full-validation and merge-acceptance boundary.

For a branch whose automatic runs must remain blocked, keep the authorised
`[skip ci]` publication marker, then dispatch this existing workflow on that exact
branch with `validation_scope=sealed-excluded` after the reviewed change is
published. A skip marker does not block `workflow_dispatch`. Verify the resulting
run's commit and scope before recording its results. Never dispatch the current
unmodified workflow expecting this option: it runs the full scope. Do not remove
the skip marker or start `full` while the sealed-file access restriction applies.

GitHub may render the dispatch form from the default-branch workflow, where a
new branch-only input is not yet available. In that case use an authorised CLI/API
dispatch that explicitly supplies both the branch ref and input; do not fall back
to submitting the old input-less form. No repository protection rule is changed
by this proposal, and the workflow remains owned by the Privacy/Security Lead.

Local reproduction of the restricted identifier gate:

```powershell
$priorCiScope = $env:MINDSENSE_CI_SCOPE
$env:MINDSENSE_CI_SCOPE = 'sealed-excluded'
try {
    .venv/Scripts/python.exe -m pytest tests/privacy/test_analysis_output_privacy.py -q -p no:cacheprovider
} finally {
    if ($null -eq $priorCiScope) {
        Remove-Item Env:MINDSENSE_CI_SCOPE -ErrorAction SilentlyContinue
    } else {
        $env:MINDSENSE_CI_SCOPE = $priorCiScope
    }
}
```

The environment selection is scoped to this command session. Do not run the
unrestricted integrity test or broad `pytest` under an active no-access rule.
