# MindSense Master Test Register

Owner: Yuktha Naveen, Privacy and Security Lead  
Coverage: Week 4 onward  
Last updated: 6 September 2026  
Status: authoritative index of executed project checks; update this file every week

## Purpose

This register records what was tested, why it was necessary, what the result
proved, and what it did not prove. It separates Privacy Lead checks from tests
authored by other project roles. A passing result supports the stated scope; it
is not approval for clinical use or participant deployment.

## Results at a Glance

| Week | Check | Result | Meaning |
| --- | --- | --- | --- |
| 4 | Privacy network gate | 3/3 passed | Python test traffic was blocked from public addresses while loopback remained available. |
| 4 | Complete Python suite | 124/124 passed | The repository worked under the loopback-only socket policy at that commit. |
| 4 | Frontend lint and production build | Passed | The starter frontend compiled without requiring remote runtime assets. |
| 4 | Dependency health | `pip check` passed; npm reported 0 vulnerabilities | No broken Python requirements or known npm advisories were detected at that time. |
| 4 | Phi-4 Mini latency baseline | 5/5 requests completed; mean 2.22 s; sample p95 3.28 s | Local Ollama inference was operational on Yuktha's Mac and a baseline was established. |
| 5 | Initial privacy and transport regression | 10/10 passed | The Python network gate and SLM loopback transport restrictions held after integration. |
| 5 | R privacy regression | 9/9 passed with real R active | Sensitive statistical inputs and model objects were cleaned up on success and error; R capabilities stayed within the allowlist. |
| 5 | Focused privacy/statistics/transport suite | 55/55 passed | The privacy controls, R integration, mixed-effects path, and SLM transport worked together. |
| 5 | Complete Python suite | 345/345 passed; 45 convergence warnings | No functional regression was detected across the current backend, pipeline, statistics, SLM, evaluation, integration, and privacy code. |
| 5 | Frontend tests | 6/6 passed | Idle, loading, success, error, and API-contract behaviour worked with synthetic data. |
| 5 | Frontend lint and production build | Passed | The tested UI met static checks and produced a deployable local build. |
| 5 | Dependency security and consistency | All checks passed; 0 known vulnerabilities | Declared Python, optional R bridge, installed Python, and npm dependencies had no advisories known to the scanners at test time. |
| 5 | Phi-4 Mini latency confirmation | 5/5 requests completed; mean 2.57 s; sample p95 3.88 s | The Week 4 local model remained operational after the merged changes. |

The Week 5 latency sample was about 15.7% slower on mean latency than Week 4.
Five prompts are too small a sample to establish a performance regression or a
production service-level target.

## Week 4 Record

### Privacy and Network Verification

**Why necessary:** MindSense processes behavioural and wellbeing information,
so the local-first claim needed an enforceable network boundary rather than a
document-only promise.

**Assumptions before testing:** tests ran from the repository root with the
declared test dependencies installed; `pytest.ini` was active; loopback traffic
was required for local components; the RFC 5737 addresses represented external
traffic without targeting a real service; and raw CES data and credentials
remained outside Git.

**Conducted:** `tests/privacy/test_no_network_egress.py` exercised two public
documentation addresses and one loopback address. `pytest.ini` applied the
same deny-by-default socket policy to the complete Python suite. Source,
manifests, Git exclusions, frontend assets, telemetry, logging, credentials,
and the local Ollama listener were also reviewed.

**Result:** 3/3 privacy tests and 124/124 complete Python tests passed. No
automatic cloud model, analytics, telemetry, crash upload, CDN, or public
frontend runtime call was detected. Ollama was observed listening on
`127.0.0.1:11434`, with no established non-loopback connection in the process
snapshot.

**What it proved:** the tested Python paths enforce loopback-only sockets and
the reviewed application code did not contain an automatic public-data path.

**Limit:** `pytest-socket` controls Python sockets only. A process snapshot is
not a packet capture and does not prove that a native runtime can never make a
connection. A whole-device or OS-level public-network-blocked integrated run
remains required before participant use.

### Dependency Verification

**Why necessary:** dependencies can add telemetry, install scripts, network
clients, file access, vulnerable code, or licence obligations.

**Assumptions before testing:** the tracked manifests represented the intended
stack; installed packages came from the configured registries; package metadata
and advisory databases were available and current at scan time; and no
untracked runtime plugin was part of the application.

**Conducted:** Python and frontend manifests and installed packages were
reviewed. `pip check`, npm installation audit output, frontend lint, and the
production build were checked. The pull-request template was updated so every
new dependency requires a privacy spot-check covering purpose, network,
telemetry/logging, data access, licence, and decision.

**Result:** `pip check` found no broken requirements; npm reported zero known
vulnerabilities; frontend lint and build passed.

**What it proved:** the tested dependency set was internally consistent and no
known advisory was reported by the scanners at that time.

**Limit:** an audit result only covers advisories known to the tool and registry
at the time. It does not prove that a dependency is vulnerability-free.

### SLM Latency Baseline

**Why necessary:** the selected small language model must run locally with
usable response time; otherwise the local-only architecture is not practical.

**Assumptions before testing:** Ollama and the exact `phi4-mini:3.8b` tag were
already installed; Ollama was bound to loopback; the five synthetic prompts
were representative enough for a preliminary timing baseline; and ordinary
machine-load variation was accepted.

**Conducted:** `benchmarks/slm_latency_benchmark.py` sent five synthetic prompts
to `phi4-mini:3.8b` through Ollama at
`http://127.0.0.1:11434/api/generate` on Yuktha's Apple arm64 Mac.

**Result:** all five requests completed. Minimum 911.82 ms, mean 2220.03 ms,
median 2344.50 ms, sample p95 3282.67 ms, and maximum 3463.26 ms.

**What it proved:** Phi-4 Mini could run locally and provided a reproducible
Week 4 speed baseline.

**Limit:** latency does not measure privacy, factual correctness, clinical
safety, or response quality. One raw response used causal-sounding wording,
showing why deterministic request and output safety gates are required. The
successful historical result is stored in Git commit `517ade3`; the current
JSON file contains the Week 5 replacement result. An earlier pre-installation
attempt failed with connection refused and was not treated as a benchmark.

## Week 5 Record

### Post-Merge Privacy and Dependency Review

**Why necessary:** merged frontend testing and R statistics dependencies
expanded the attack surface and the types of sensitive data held in memory.

**Assumptions before testing:** baseline commit `6a5e6b6` contained all merged
Week 5 changes under review; lockfiles and installed versions reflected those
changes; tests used synthetic or de-identified inputs; and package installation
was separate from sensitive-data processing.

**Conducted:** the new npm development packages, R 4.6.1, `rpy2`, `lme4`,
`lmerTest`, `pbkrtest`, and `nlme` were reviewed for network, telemetry,
logging, install/update behaviour, data access, licences, and alternatives.
The two merged PRs had omitted the required dependency privacy section, so a
retrospective check was necessary.

**Result:** approved with mitigation for local development using synthetic or
de-identified data. This is not participant-use approval. The npm packages
remain development-only. R and CRAN require public networking for explicit
installation, but no runtime installer, updater, telemetry, or public network
call was found in the project R bridge.

**What it proved:** the reviewed dependencies can support the local development
workflow under the documented controls.

**Limits:** local Node 22.19.0 is below `jsdom@30.0.1`'s declared minimum
22.22.2 even though the checks passed. R package versions are recorded but not
fully machine-locked. Installation and updates must not run while participant
data is loaded.

### R Bridge Privacy Regression

**Why necessary:** the original R bridge left the statistical dataframe and
fitted model in R's global workspace. These objects can contain pseudonymous
participant IDs, derived behavioural features, and PHQ-4 values.

**Assumptions before testing:** Homebrew R 4.6.1, `rpy2` 3.6.7, and the recorded
R packages were available; `RPY2_CFFI_MODE=ABI` selected the working macOS
bridge mode; synthetic frames represented the same sensitive fields as the
real statistical path; and project code must not rely on temporary R objects
remaining after a fit.

**Conducted:** `tests/privacy/test_r_bridge_privacy.py` contains nine checks:

1. No Python network, shell, subprocess, or logging imports.
2. No R network, shell, install, serialization, source, or file-write calls.
3. R package imports exactly match the approved allowlist.
4. New temporary objects are removed after success.
5. New temporary objects are removed after an exception.
6. Pre-existing R objects are restored rather than destroyed.
7. Concurrent R fits are serialized and cannot share temporary data.
8. A real R fit leaves no MindSense input or model object behind.
9. A failed real R fit still removes all MindSense temporary objects.

**Result:** 9/9 passed with Homebrew R and `rpy2` active.

**What it proved:** the bridge now minimises the lifetime of sensitive R data,
isolates concurrent calls, and stays within the reviewed capability and package
boundary.

**Limit:** source allowlists cannot prove the behaviour of every native R
dependency. macOS verification requires `RPY2_CFFI_MODE=ABI` with the current
Homebrew R setup.

### Focused Privacy, Transport, and Statistics Regression

**Why necessary:** the privacy fix had to be tested with the surrounding SLM
transport and statistical model code, not only as isolated helper functions.

**Assumptions before testing:** the repository root was on `PYTHONPATH`; the
real R backend was active; loopback binding was permitted; fixtures were
synthetic; and public sockets stayed blocked by the suite policy.

**Files and count:** network egress (3), R privacy (9), SLM transport (7), R
bridge statistics (6), and mixed-effects modelling (30), for 55 tests.

**Result:** 55/55 passed.

**What it proved:** the R cleanup and serialization controls did not change the
expected statistical interface, and SLM requests remained restricted to
validated loopback endpoints with proxies and redirects disabled.

### Complete Current Python Suite

All 345 tests below passed in the final Week 5 run. Shared assumptions were:
the tested commit and tracked configuration were the intended build; the
repository root was on `PYTHONPATH`; required Python/R/frontend dependencies
were installed; fixtures were synthetic unless a row says otherwise; and a
passing unit test represents only its encoded requirement.

Fresh verification on 6 September 2026 tested branch
`yuktha/privacy-week5` at commit `d15e3a3`. A restricted sandbox run reported
340 passes and five setup failures because the environment denied a temporary
HTTP server permission to bind to `127.0.0.1`. No project assertion failed.
The complete suite was rerun with local loopback binding permitted and produced
345/345 passes and 45 warnings. This confirms that loopback binding is a real
precondition for the redirect-privacy tests.

| Test file | Count | Assumptions before running | Why necessary / what it proved |
| --- | ---: | --- | --- |
| `tests/api/test_app.py` | 5 | In-process ASGI behaviour represents the API; fixtures are synthetic. | API responses and failure handling follow the local application contract. |
| `tests/contracts/test_evidence_contract.py` | 5 | The versioned schema is the agreed component boundary. | Valid evidence packets are accepted and represented consistently. |
| `tests/contracts/test_evidence_contract_boundaries.py` | 24 | Encoded bounds and required fields match the current specification. | Invalid, excessive, or unsafe evidence is rejected at the boundary. |
| `tests/data_pipeline/test_ces_eligibility_privacy.py` | 5 | Local CES layout and eligibility policy are correct; output should be aggregate. | Eligibility output does not expose raw IDs and uses pseudonymised/aggregate results. |
| `tests/data_pipeline/test_cleaning.py` | 8 | Synthetic edge cases represent expected raw-data faults; cleaning rules are locked. | Cleaning, outlier handling, and transformations follow pipeline rules. |
| `tests/data_pipeline/test_gps_distance_feature.py` | 3 | Coordinates and timestamps are valid synthetic samples; daily distance is the agreed feature. | GPS records produce the intended daily distance feature locally. |
| `tests/data_pipeline/test_validate_ces_script.py` | 2 | The confirmed CES dataset exists at the documented local path. | The canonical script finds real local data and matches the independent check. |
| `tests/evaluation/test_held_out_integrity.py` | 8 | The committed checksum is the sealed reference and prompts should not be used for tuning. | The held-out set is structured correctly and tampering is detectable. |
| `tests/evaluation/test_week5_review.py` | 3 | The review document is the current evaluation record. | Results separate executed, uncovered, and unreviewed cases without overstating approval. |
| `tests/integration/test_ces_eligibility_scripts_agree.py` | 5 | Both scripts independently implement the same confirmed dataset rules. | They agree on 220 participants, 97.3% eligibility, and locked features. |
| `tests/integration/test_end_to_end_evidence_flow.py` | 13 | Synthetic packets represent component contracts; external services are not required. | Pipeline, contracts, statistics, policy, SLM service, and safety outputs interoperate. |
| `tests/integration/test_frontend_builds.py` | 3 | Node dependencies are installed from the lockfile. | The frontend builds and source/built HTML contain no CDN reference. |
| `tests/privacy/test_no_network_egress.py` | 3 | `pytest-socket` is active; RFC 5737 hosts represent public traffic; loopback is trusted. | Public Python sockets are blocked and loopback remains usable. |
| `tests/privacy/test_r_bridge_privacy.py` | 9 | Real R is available; temporary workspace retention is forbidden; the package allowlist is complete. | R data is cleaned and bridge capabilities remain restricted. |
| `tests/slm/test_client.py` | 6 | A mocked/local response represents Ollama protocol behaviour. | The Ollama client validates configuration and handles responses safely. |
| `tests/slm/test_evaluation_alignment.py` | 13 | Fixture labels and thresholds represent the approved development evaluation. | Evaluation cases and scoring align with current request/response rules. |
| `tests/slm/test_model_comparison.py` | 4 | Models receive equivalent prompts/settings and synthetic cases. | Comparison records remain controlled and comparable. |
| `tests/slm/test_output_grounding.py` | 65 | Evidence IDs and prohibited claim patterns cover the current safety specification. | Claims stay tied to supplied evidence; unsupported output triggers fallback. |
| `tests/slm/test_prohibited_request_baseline.py` | 2 | The 16-case fixture and 100% high-severity threshold are locked. | Prohibited requests meet threshold without unexpected model calls. |
| `tests/slm/test_prompt_loader.py` | 6 | Versioned YAML prompts are the trusted local source. | Prompt files load safely and all required templates exist. |
| `tests/slm/test_prompt_templates.py` | 21 | Required wording/checks encode the approved non-clinical behaviour. | Normal, insufficient-data, refusal, fallback, and crisis templates contain safeguards. |
| `tests/slm/test_request_policy.py` | 21 | Keyword/rule fixtures represent currently defined request classes. | Diagnosis, causation, treatment, crisis, privacy, and unrelated requests route deterministically. |
| `tests/slm/test_runtime.py` | 4 | The manifest is authoritative and Ollama is the selected local runtime. | Runtime selection and model configuration follow the pinned manifest. |
| `tests/slm/test_safety_gate.py` | 10 | Prohibited patterns and evidence references represent current output rules. | Unsafe, unsupported, identifying, or overconfident output is rejected. |
| `tests/slm/test_service.py` | 7 | Mocked model transport accurately isolates service orchestration. | Policy, invocation, redaction, grounding, and fallback work together. |
| `tests/slm/test_shadow_smoke.py` | 2 | Synthetic shadow records represent the intended model/template paths. | Shadow cases produce expected modes and machine-readable evidence. |
| `tests/slm/test_transport_privacy.py` | 7 | Loopback is trusted; a temporary local HTTP server can bind; redirects/proxies are untrusted. | External endpoints, proxies, and redirects are rejected; loopback is allowed. |
| `tests/statistics/test_eligibility.py` | 22 | The 28-day baseline and three-state cold-start policy are locked. | Baseline windows, cold-start states, and evidence eligibility follow specification. |
| `tests/statistics/test_mixed_effects_model.py` | 30 | Synthetic data reflects model structure; convergence warnings are acceptable test diagnostics. | Fitting, corrections, AR(1), evidence strength, and fallback meet the statistical contract. |
| `tests/statistics/test_r_bridge.py` | 6 | R packages/ABI mode are available and R is the primary reference implementation. | Satterthwaite/Kenward-Roger and AR(1) results cross the Python bridge correctly. |
| `tests/test_repo_structure_cross_references.py` | 23 | Tracked docs and paths are the intended governance source of truth. | Required files, ownership evidence, references, dependencies, and repository invariants remain consistent. |

The 45 `statsmodels` convergence warnings came from small synthetic statistical
fixtures. They did not fail the suite, but they mean successful execution is
not the same as proof that every model fit is statistically stable on future
real data.

### Frontend Verification

**Conducted:** six Vitest/Testing Library checks covered idle state, loading and
button locking, successful response rendering, backend-unreachable error,
unknown error handling, and the exact evidence/question sent to the API. The
frontend lint and production build commands were also run.

**Assumptions before testing:** dependencies matched `package-lock.json`; jsdom
was sufficient to represent component behaviour; the mocked `respond` function
matched the backend contract; and these tests did not represent a live browser,
FastAPI process, or Ollama process.

**Result:** 6/6 tests passed; lint passed; production build passed.

**What it proved:** the current normal-response component handles its tested UI
states and synthetic API contract, and the frontend compiles locally.

**Limit:** the API module was mocked. This is not a browser test against a live
FastAPI and Ollama stack, and it does not test every planned UI state.

### Dependency Security Verification

| Check | Assumptions before running | Result | Meaning |
| --- | --- | --- | --- |
| `pip check` | Active environment is the intended project environment. | Passed | No broken requirements in the active Python environment. |
| `pip-audit -r requirements.txt` | Manifest is complete; advisory service is current. | 0 known vulnerabilities | No known advisory matched main Python requirements. |
| `pip-audit -r requirements-r.txt` | `rpy2` pin represents the Python R bridge; advisory service is current. | 0 known vulnerabilities | No known advisory matched pinned `rpy2`. |
| Installed-environment `pip-audit` | Installed environment contains only intended project tools; advisory service is current. | 0 known vulnerabilities | No known advisory matched installed Python packages. |
| `npm audit` | Lockfile is authoritative; npm advisory data is current. | 0 known vulnerabilities | No known advisory matched the frontend graph. |
| Ruff on modified Python files | Configured Ruff rules represent the agreed static standard. | Passed | Privacy-related Python changes met those rules. |
| Repository-wide Ruff | Existing findings were outside the privacy change. | 22 pre-existing findings | The repository is not globally Ruff-clean. |

### SLM Safety and Integration Evidence Relevant to Privacy

These artefacts were produced by the SLM/evaluation work and independently
checked during the privacy review. They were not authored as Yuktha's tests.

| Check | Assumptions before running | Result | Privacy/security meaning |
| --- | --- | --- | --- |
| Prohibited-request baseline | The 16 synthetic cases represent the currently known prohibited classes; threshold is 100%. | 16/16 passed; 0 unexpected model calls | Prohibited requests were stopped before model generation. |
| Shadow smoke | Four synthetic cases represent the required routing modes. | 4/4 passed | Normal, missing-data, refusal, and crisis/fallback paths produced expected modes. |
| Evaluation alignment | Labels and automated criteria are correct; human ratings are separate. | 6/6 executed source-plan, 14/14 high-severity, and 2/2 privacy cases passed | Automated checks met development rules; two source-plan cases remained uncovered. |
| Phi grounding regression | Exact local Phi model and prompt versions were available; three cases are a regression sample only. | 3/3 quality checks passed | References were redacted and tested responses respected evidence/uncertainty checks. |

Human quality ratings were not completed in these automated artefacts. Passing
them does not establish held-out performance, clinical safety, or joint team
approval.

### SLM Latency Confirmation

**Conducted:** the same five synthetic prompts were rerun with
`phi4-mini:3.8b` through loopback Ollama on Yuktha's Mac.

**Assumptions before testing:** the model tag and prompt set were unchanged;
Ollama was bound to loopback and already warm/available; the Mac's current load
was accepted; and five samples were sufficient only for confirmation, not a
performance guarantee.

**Result:** 5/5 completed. Minimum 1261.09 ms, mean 2568.90 ms, median 2988.77
ms, sample p95 3878.20 ms, and maximum 4061.79 ms.

**What it proved:** the selected model and local endpoint still worked after
Week 5 integration, with a typical response in roughly 2.6 seconds in this
small sample.

**Limit:** benchmark prompts are synthetic and raw benchmark output bypasses
the product safety gate. Results vary with machine load and model warm-up.

## Meaning of the Combined Results

### Week 4

Week 4 established the privacy architecture, dependency review rule,
loopback-only Python test boundary, and first real-machine speed baseline. The
result was a **conditional pass for prototype development**, not proof that the
whole device or native Ollama runtime was permanently offline-safe.

### Week 5

Week 5 retested the expanded repository after integration, reviewed new npm
and R dependencies, added enforceable R-memory controls, and confirmed model
speed. The result is **conditional approval for local development with
synthetic or de-identified data**. It is not participant deployment approval.

Before participant-facing use, the project still needs:

- An integrated FastAPI, frontend, Ollama, and R run with public networking
  disconnected or blocked at the operating-system level.
- A documented logging, retention, deletion, and incident-response procedure.
- Verification that all IDs and free text reaching the SLM are minimised or
  redacted, not only `participant_ref`.
- A supported Node version and a reproducible locked Python/R environment.
- Human safety/quality review and independent review of safety-critical paths.
- Enforcement of the dependency privacy section before future PRs are merged.

## Reproduction Commands

Run from the repository root with `.venv` already created and dependencies
installed:

```bash
PYTHONPATH=. RPY2_CFFI_MODE=ABI .venv/bin/pytest -q
```

Focused privacy/statistics/transport suite:

```bash
PYTHONPATH=. RPY2_CFFI_MODE=ABI .venv/bin/pytest -q \
  tests/privacy \
  tests/slm/test_transport_privacy.py \
  tests/statistics/test_r_bridge.py \
  tests/statistics/test_mixed_effects_model.py
```

Frontend:

```bash
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend audit
```

Dependencies:

```bash
.venv/bin/pip check
.venv/bin/pip-audit -r requirements.txt
.venv/bin/pip-audit -r requirements-r.txt
.venv/bin/pip-audit
```

Latency benchmark, with local Ollama already serving the pinned model:

```bash
.venv/bin/python benchmarks/slm_latency_benchmark.py \
  --provider ollama \
  --model phi4-mini:3.8b \
  --out benchmarks/slm_latency_results.json
```

## Weekly Update Rule

At the end of each week, append one dated record containing:

1. Branch and tested commit hash.
2. Machine/runtime versions that affect the result.
3. Exact commands executed.
4. Assumptions made before each test or review.
5. Test counts, passes, failures, skips, and warnings.
6. Benchmark measurements and comparison with the previous week.
7. Dependencies added, changed, or removed and their privacy decisions.
8. New findings, fixes, unresolved limitations, and release decision.
9. Evidence file paths and the person who actually ran or authored each item.

Do not replace earlier weekly measurements. Historical results must remain in
this register even when machine-readable result files are updated.

## Evidence Index

- `privacy/privacy_architecture_principles.md`
- `privacy/initial_dependency_audit.md`
- `privacy/week4_privacy_status.md`
- `privacy/week5_post_merge_dependency_review.md`
- `tests/privacy/test_no_network_egress.py`
- `tests/privacy/test_r_bridge_privacy.py`
- `tests/slm/test_transport_privacy.py`
- `benchmarks/slm_latency_benchmark.py`
- `benchmarks/slm_latency_results.json`
- `benchmarks/slm_prohibited_request_baseline_results.json`
- `benchmarks/slm_shadow_smoke_results.json`
- `benchmarks/slm_evaluation_alignment_results.json`
- `.github/pull_request_template.md`
