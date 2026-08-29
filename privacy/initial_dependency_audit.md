# Dependency and Privacy Audit

Owner: Yuktha Naveen, Privacy and Security Lead
Date: 2026-08-29
Reviewed commit: `0c1bf0b`
Scope: `/Users/yukthanaveen/Documents/SEM4/Capstone/Work/mindsense-capstone`

## Method

- Reviewed all tracked source, dependency manifests, the frontend lockfile, and Git history.
- Scanned backend, frontend, benchmark, and test source for network-capable code and external URLs.
- Scanned tracked files for common API-token, credential, password, and private-key patterns.
- Confirmed whether local dataset or virtual-environment files are tracked.
- Inspected application output paths for participant identifiers and raw-data exposure.
- Installed the declared dependencies into `.venv/` and `frontend/node_modules/` after approval.
- Ran dependency, privacy, full-suite, lint, frontend build, and SLM benchmark checks.

## Dataset and Credentials

- The CES dataset remains local under the gitignored `dataset/` directory.
- No file under `dataset/` or `.venv/` is tracked.
- No dataset file appears in Git history.
- No tracked file matched the checked Kaggle-token, credential, password-assignment, access-token, or private-key patterns.

Result: pass for repository exclusion.

## Dependencies

Python dependencies installed into `.venv/`:

| Package | Installed version | Declared license |
|---|---:|---|
| FastAPI | 0.141.1 | MIT |
| Uvicorn | 0.52.4 | BSD-3-Clause |
| Pydantic | 2.13.5 | MIT |
| pandas | 3.0.5 | BSD-3-Clause |
| NumPy | 2.5.2 | Permissive compound license |
| statsmodels | 0.15.0 | BSD-3-Clause |
| PyYAML | 6.0.3 | MIT |
| sqlite-utils | 4.2.1 | Apache-2.0 |
| pytest | 9.1.1 | MIT |
| pytest-asyncio | 1.4.0 | Apache-2.0 |
| pytest-socket | 0.8.1 | MIT |
| Ruff | 0.16.5 | MIT |

`pip check` reported no broken requirements. The Python declarations are still mostly unpinned and there is no resolved lockfile, so a future installation may select different versions.

Frontend dependencies were restored from `package-lock.json` with `npm ci`. The nine direct packages resolved to the recorded versions, and npm reported zero known vulnerabilities at installation time. Direct licenses are MIT or Apache-2.0. The lockfile contains one optional transitive package with an install script: MIT-licensed `fsevents` 2.3.3 for macOS.

No cloud-model, telemetry, analytics, crash-reporting, or session-replay SDK is declared. Dependency downloads use public package registries during development installation and must not occur during participant sessions.

No GitHub pull requests currently exist for the repository. These dependencies were committed directly to `main`, so the standing dependency privacy spot-check was bypassed and needs retrospective review.

Result: conditional approval for local development. Add a resolved Python lockfile and enforce the PR spot-check for future changes.

## Network and Telemetry

- No backend application module currently imports an HTTP client.
- `backend/slm/client.py`, the planned sole Ollama client, does not exist yet.
- The benchmark harness uses Python `urllib` and targets only `127.0.0.1:11434` by default.
- No telemetry, analytics, crash reporting, cloud-model integration, or CDN asset was found in application source.
- Frontend assets are local and no automatic fetch, XHR, WebSocket, EventSource, or beacon call was found.
- The Vite starter screen still contains six clickable links to public websites. They must be removed or approved before participant-facing use.
- Ollama was observed listening only on `127.0.0.1:11434`.
- A live connection snapshot during synthetic local inference showed no public Ollama TCP connection.

The connection snapshot is evidence of local behavior during that run, but it is not a substitute for a final test with public networking disabled.

Result: pass for current automatic application calls, with UI link removal and a disconnected-network SLM test still required.

## Logs and Command Output

- `backend/data_pipeline/verify_ces.py` prints aggregate statistics without participant UIDs.
- `backend/data_pipeline/ces_eligibility.py` currently prints `ineligible_uids` and UID-keyed `ineligible_reasons`.

Result: fail for the eligibility script's current shared output. The Data Pipeline Lead must replace UID-level output with aggregate reason counts before logs, terminal output, or screenshots are shared.

## Automated Verification

- `pytest.ini` denies non-loopback Python socket connections across the full test suite and allows only `127.0.0.1` and `localhost`.
- Privacy tests: 3 passed.
- Full pytest suite under the socket policy: 124 passed.
- Frontend lint: passed.
- Frontend production build: passed.
- Combined milestone count: 124 pytest checks plus one frontend production build equals 125 automated checks.
- Privacy-owned benchmark and test files pass Ruff lint and formatting checks.
- Repository-wide Ruff check still reports 11 pre-existing lint errors and 13 unformatted files in other role-owned modules.

Result: pass for the current automated privacy gate. Extend it with a local Ollama client smoke test when `backend/slm/client.py` exists.

## SLM Benchmark

The locked Week 4 model is Ollama with exact tag `phi4-mini:3.8b`.

Five synthetic prompts were run locally on this Mac:

- Minimum: 911.82 ms
- Mean: 2220.03 ms
- Median: 2344.50 ms
- p95: 3282.67 ms
- Maximum: 3463.26 ms

The latency benchmark passed. It is not a safety evaluation. One raw response used causal-sounding wording, so product responses must continue through the deterministic claim and safety gate before display.

## Required Follow-Up

- Data Pipeline Lead: remove UID-level eligibility output.
- UI Lead: remove or explicitly approve the six starter links.
- Integration/QA Lead: require PRs and the dependency privacy spot-check for dependency changes.
- Dependency owners: create a resolved Python lockfile.
- SLM and Privacy Leads: verify local inference with public networking disabled and add a loopback-only client smoke test.

## Assessment

The repository preserves the local dataset boundary, contains no detected telemetry or automatic cloud integration, passes all 124 Python tests under loopback-only socket restrictions, and now has measured local SLM latency. Final end-to-end "nothing leaves the device" verification still requires the disconnected-network SLM test, removal of UID-level output, removal or approval of starter links, and the actual application SLM client.
