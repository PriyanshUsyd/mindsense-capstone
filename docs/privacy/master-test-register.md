# MindSense Master Test Register

Owner: Yuktha Naveen, Privacy and Security Lead  
Coverage: Week 4 onward  
Last updated: 8 September 2026
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
| 6 | Pre-gate Python baseline | 345/345 passed; 45 convergence warnings | Existing tests still passed on the Week 6 branch before adding the new privacy gate. |
| 6 | Raw CES identifier gate | Failed: 370,120 raw-UID rows across 20 CSVs | Newly merged analysis outputs expose the original 220 CES identifiers and must not be approved for participant-data handling. |
| 6 | Pre-gate frontend baseline | 11/11 passed; lint and build passed | The expanded UI passed its existing component and build checks. |
| 6 | Frontend redirect privacy gate | Failed: redirect rejection is not configured | The loopback URL is fixed, but browser redirects could move a request away from the local service. |
| 6 | Dependency security and consistency | All checks passed; 0 known vulnerabilities | No dependency manifest changes or known advisories were found at test time. |
| 6 | Phi-4 Mini latency confirmation | 5/5 requests completed; mean 1.92 s; sample p95 3.03 s | The pinned local model remained available and was faster than the Week 5 sample on the same Mac. |
| 6 | Post-fast-forward Python suite | 390 passed, 1 privacy failure; 45 warnings | New functionality passed, but the raw-identifier output gate still blocks privacy approval. |
| 6 | Post-fast-forward focused suite | 56 passed, 1 privacy failure; 45 warnings | Privacy, transport, R, and statistical checks passed except the raw-identifier output gate. |
| 6 | Post-fast-forward frontend suite | 13 passed, 1 privacy failure; lint and build passed | New UI behaviour passed, but browser redirect rejection remains absent. |
| 6 | Post-fast-forward dependency scan | All checks passed; 0 known vulnerabilities | Python, R bridge, installed Python, and npm advisories remained clear on 12 September. |
| 6 | Post-fast-forward latency confirmation | 5/5 requests completed; mean 2.22 s; sample p95 3.80 s | Local Phi-4 Mini remained operational after all Week 6 merges. |
| 6 | Raw-identifier remediation | Passed; 0 sensitive CSVs tracked | Twenty participant-level CSVs remain local and are excluded from Git; aggregate outputs remain tracked. |
| 6 | Frontend redirect remediation | Passed | The browser transport now rejects redirects while retaining the fixed loopback destination. |
| 6 | Post-remediation Python suite | 391/391 passed; 45 warnings | Both privacy fixes integrate with the complete backend and test suite. |
| 6 | Post-remediation frontend suite | 14/14 passed; lint and build passed | The redirect control and expanded UI work together without frontend regressions. |

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

## Week 6 Initial Record - 8 September 2026

### Scope and Environment

**Branch and baseline:** `yuktha/privacy-week6`, created from `origin/main` at
commit `3423e43a302287f857e91ef7b19bd50190deec60`. The working tree was clean
before the audit. No Week 6 changes were committed or pushed during this run.

**Environment:** macOS 26.6.2 on Apple arm64; Python 3.14.0; R 4.6.1 with the
real `rpy2` ABI path active; Node 22.19.0; npm 10.9.3; Ollama 0.33.2; and local
`phi4-mini:3.8b` model id `78fad5d182a7`.

**Changes reviewed since the Week 5 baseline:** merged statistics analysis
code and generated outputs, the expanded frontend, and SLM/evaluation evidence
updates. `requirements.txt`, `requirements-r.txt`, `frontend/package.json`,
and `frontend/package-lock.json` had no changes in this comparison.

### Existing-Suite Baseline

**Why necessary:** the Week 5 register predated later merges into `main`, so a
fresh baseline was needed before adding new privacy checks.

**Assumptions before testing:** the checked-out commit was the latest fetched
`origin/main`; project dependencies were already installed; `pytest.ini`
enforced loopback-only Python sockets; real R was available; frontend packages
matched the lockfile; and test fixtures were synthetic unless a test explicitly
used the local CES dataset.

**Result:** the valid full Python run passed 345/345 tests with 45 statistical
convergence warnings. The focused privacy, transport, R bridge, and mixed-model
run passed 55/55 with the same 45 warnings. The existing frontend suite passed
11/11; lint and production build passed. An initial sandboxed Python run had
five loopback-server permission failures; rerunning with normal local loopback
permission passed all five, confirming they were environment-only rather than
project failures.

**What it proved:** behaviour already covered by the Week 5 suites survived the
later merges. It did not prove that newly committed analysis outputs were safe
or that browser redirects were blocked because neither condition had an
existing regression test.

### New Raw-Identifier Output Gate

**Why necessary:** the merged `analysis/output/` tree added participant-level
CSV artefacts after the previous privacy baseline. Project policy requires an
opaque `participant_ref` and prohibits raw CES identifiers in shared output.

**Assumptions before testing:** a 32-character lowercase hexadecimal value in a
CSV `uid` column follows the raw CES identifier format; approved pseudonyms use
an explicitly distinguishable opaque format; and files under
`analysis/output/` are shared because Git tracks them.

**Conducted:** added
`tests/privacy/test_analysis_output_privacy.py`, which streams every generated
CSV with a `uid` column and rejects raw CES-format identifiers. One detected
identifier was independently matched to the local demographics, sensing,
unlock, and EMA source files.

**Result:** failed. The gate found 370,120 raw-UID rows in 20 tracked CSV files,
covering 220 distinct CES identifiers. Affected artefacts include
`analysis/output/latest/cold_start_states.csv`, `evidence_per_person.csv`,
`occasion_gate_keys.csv`, reconciliation files, and historical run outputs.

**Meaning and required action:** this is a real repository privacy failure, not
a laptop issue. Participant-level outputs must be removed from Git or regenerated
with an approved non-linkable identifier policy. Because the values already
exist in Git history, the team must also decide whether history remediation and
credential/access review are required. Privacy approval is withheld for these
artefacts until remediation and a passing rerun.

### New Frontend Redirect Gate

**Why necessary:** the expanded UI now sends an evidence packet and question
from the browser to the local API. A loopback destination alone is insufficient
if the browser is permitted to follow an HTTP redirect to another origin.

**Assumptions before testing:** the Fetch API follows redirects by default; a
redirect response from a compromised or misconfigured local service could move
sensitive request data away from loopback; and the intended policy is to fail
closed rather than follow redirects.

**Conducted:** added `frontend/src/api/client.test.ts` to verify the exact
`http://127.0.0.1:8000/respond` destination and require
`redirect: 'error'` in the fetch options.

**Result:** failed. The destination was correctly fixed to loopback, but
`redirect: 'error'` was absent. The complete frontend result with the new gate
was 11 passed and 1 failed. Frontend lint remained clean.

**Meaning and required action:** add explicit redirect rejection to the
frontend request and rerun the 12-test frontend suite. Privacy approval for the
browser transport remains conditional until this gate passes.

### Dependency and Local-Model Checks

**Assumptions before testing:** manifests accurately describe the intended
environment; the advisory services were current; zero known vulnerabilities
does not mean vulnerability-free; the five benchmark prompts remained
synthetic and unchanged; and Ollama was reached only at
`127.0.0.1:11434`.

**Result:** `pip check` found no broken requirements. Audits of
`requirements.txt`, `requirements-r.txt`, the installed Python environment,
and the npm graph reported zero known vulnerabilities. No dependency manifests
changed since the Week 5 privacy baseline. Phi-4 Mini completed 5/5 prompts:
minimum 743.83 ms, mean 1919.76 ms, median 1988.51 ms, sample p95 3031.99 ms,
and maximum 3268.65 ms. Mean latency was about 25.3% lower than Week 5, but the
five-prompt sample remains too small for a performance guarantee.

### Security/Privacy Lead Review References

No commit added after the Week 5 master-register commit (`c624a08`) explicitly
assigns a new review or approval to the Security/Privacy Lead. The unmerged
Honghao Tier-1 and Sheng Week 6 commit messages also contain no such request.

Existing governance references remain active:

- Commit `82d9c14` records Yuktha's Privacy Lead approval of the Week 5 SLM
  dependency review.
- `docs/slm/week5-dependency-privacy-review.md` contains the named Privacy Lead
  sign-off.
- `privacy/privacy_architecture_principles.md` requires privacy review before
  merging privacy-relevant changes.
- `.github/pull_request_template.md` requires a dependency privacy spot-check.
- `privacy/initial_dependency_audit.md` assigns the SLM and Privacy Leads an
  integrated public-network-disabled verification that remains outstanding.

### Week 6 Initial Decision

**Result: privacy release gate failed.** Existing functional, dependency, and
local-model checks passed, but the newly added tests exposed two genuine gaps:
raw CES identifiers in tracked analysis outputs and missing browser redirect
rejection. These are not environment failures and must not be converted into
passes by skipping or weakening the tests.

### Post-Fast-Forward Verification - 12 September 2026

**Why necessary:** `origin/main` advanced by 22 commits to
`fbf7cf2de619802caaa918b2bf8bfc3a90c78131` after the initial Week 6 audit.
Those commits changed the frontend client, backend API, SLM request and health
logic, statistical evidence code, data pipeline, and test suite. The earlier
result therefore could not be treated as evidence for the updated repository.

**Assumptions before testing:** the Week 6 branch was fast-forwarded without
conflicts; the four uncommitted Privacy Lead files were preserved; real R and
the local model remained available; `pytest.ini` enforced the intended socket
policy; frontend dependencies matched the lockfile; and advisory databases were
current at the time queried.

**Conducted:** reran the complete Python suite, focused privacy/transport/R/
statistics suite, complete frontend suite, frontend lint and production build,
`pip check`, all three Python dependency audits, npm audit, Ruff on the new
Python privacy test, and the five-prompt local Phi-4 Mini benchmark.

**Results:**

- Complete Python: 390 passed, 1 failed, 45 convergence warnings.
- Focused privacy/transport/R/statistics: 56 passed, 1 failed, 45 warnings.
- Frontend: 13 passed, 1 failed; lint and production build passed.
- Dependency consistency: no broken Python requirements.
- Dependency advisories: zero known vulnerabilities in `requirements.txt`,
  `requirements-r.txt`, the installed Python environment, and npm.
- Ruff: the new Python privacy test passed static checks.
- Phi-4 Mini: 5/5 completed; minimum 927.70 ms, mean 2224.58 ms, median
  2395.99 ms, sample p95 3802.87 ms, and maximum 4084.96 ms.

**Failure assessment:** both failures are unchanged product issues, not laptop
or sandbox problems. The raw-identifier gate still finds 370,120 raw CES UID
rows in 20 CSV files. The frontend still uses the loopback endpoint but does
not set `redirect: 'error'`. The incoming `.gitignore` change ignores only a
top-level `outputs/` directory and does not remove or ignore the tracked
`analysis/output/` files.

**Decision:** the updated code is functionally stable under existing tests, but
the privacy release gate remains failed. Do not approve participant-data use or
represent the repository as privacy-clean until both new gates pass.

### Remediation and Passing Rerun - 12 September 2026

**Changes made on `yuktha/privacy-week6` only:**

- Added narrow `.gitignore` rules for participant-level cold-start, evidence,
  occasion-key, and reconciliation CSVs under `analysis/output/`.
- Removed the 20 affected CSVs from Git tracking while preserving every file in
  the local working directory.
- Created a separate local-only backup of all 20 CSVs and verified every copy
  against a SHA-256 manifest before completing the removal from Git tracking.
- Added an aggregate-only reconciliation summary and updated the statistical
  output documentation so shared evidence contains no participant identifiers
  or dates.
- Updated `tests/privacy/test_analysis_output_privacy.py` to scan files that are
  tracked or would be shared by Git, while excluding deliberately ignored local
  analysis data.
- Added `redirect: 'error'` to `frontend/src/api/client.ts`; the request remains
  fixed to `http://127.0.0.1:8000/respond`.

**Assumptions before rerunning:** ignored participant-level outputs remain
available only in the local workspace; aggregate reports are safe to keep in
Git; the Git index accurately represents what a future branch commit would
share; browser Fetch honours `redirect: 'error'`; and the same Python, R, Node,
and frontend environments used in the post-fast-forward run remained active.

**Results:**

- Raw-identifier privacy gate: 1/1 passed; zero sensitive CSVs remain tracked.
- Local retention verification: 20/20 CSVs backed up with zero checksum
  mismatches; the manifest contains 20 entries.
- Frontend loopback/redirect gate: 1/1 passed.
- Complete Python suite: 391/391 passed with 45 convergence warnings.
- Complete frontend suite: 14/14 passed.
- Ruff on the new privacy test, frontend lint, and frontend production build
  passed. A repository-wide Ruff baseline is not yet clean.

**What it proved:** the proposed branch state no longer shares the detected
participant-level CSVs, future files with those sensitive output names stay
local, a verified local copy exists for authorised analysis, aggregate evidence
remains available in the repository, the privacy test protects other shared
analysis CSVs, and the browser fails closed instead of following redirects away
from the local API.

**Residual limits:** these uncommitted branch changes do not alter `main`. The
raw identifiers also remain in existing Git history even after their staged
removal from the branch tip. Repository administrators and the project team
must decide whether history rewriting, access review, or notification is
required. This remediation supports a conditional pass for synthetic local
development; it does not approve participant deployment.

### Continuous Integration Automation - 12 September 2026

**Why necessary:** the privacy and security checks had been run manually after
merges. That leaves a window in which a later pull request can change network,
dependency, logging, model, or data-handling behaviour without repeating the
same controls.

**Implemented:** `.github/workflows/privacy-security-ci.yml` runs on pull
requests targeting `main`, on every push to `main` (including a merged pull
request), on `yuktha/**` branch pushes for pre-PR verification, and by manual
dispatch. It provides three independent jobs:

- the complete Python suite with the real R bridge required and `pip check`;
- frontend tests, lint, production build, and high/critical npm advisory gate;
- strict advisory audits of both Python requirements files.

Every run also publishes a status-only Markdown summary and a 90-day GitHub
Actions artifact. The separate operating register is
`docs/privacy/automated-ci-run-register.md`; CI does not write to the master
register or commit generated records to the repository.

**Security and privacy assumptions:** GitHub-hosted runners are acceptable for
synthetic test fixtures but not participant data; the CES dataset and local
Ollama model are absent; no repository secrets are supplied; checkout has
read-only permissions and does not retain credentials; network access during
setup is limited to downloading declared tools/packages and querying advisory
services; and pytest then enforces the project's loopback-only socket policy.
External actions are pinned to immutable commit hashes.

**CI dependency privacy spot-check:** `actions/checkout`,
`actions/setup-python`, and `actions/setup-node` are official GitHub actions;
`r-lib/actions/setup-r` is the established R setup action; and
`actions/upload-artifact` stores only the generated status record. Setup and
audit steps make expected public network calls for tools, packages, caches, and
advisory data. They receive no participant dataset or application secrets.
Checkout is read-only with credential persistence disabled. The uploaded file
contains run metadata and job outcomes only and is retained for 90 days.

**Expected omissions:** dataset-backed tests skip because `dataset/` remains
local and gitignored. The Phi-4 Mini latency benchmark remains a local-machine
check because a standard runner does not have the approved model or comparable
hardware. Repository-wide Ruff is not yet a required gate because the existing
tree has 36 pre-existing findings; the new privacy test itself passes Ruff.

**Local preflight result:** workflow YAML parsing and Git diff validation
passed. Using the workflow's Python/R environment settings, the complete suite
passed 391/391 with 45 statistical convergence warnings. Frontend tests passed
14/14; frontend lint and production build passed. Both Python requirements
audits and the npm high/critical audit reported zero known vulnerabilities.
Five localhost redirect cases initially failed only because the restricted
test sandbox denied binding a temporary loopback server; the permitted rerun
passed all five. No GitHub-hosted result exists until the workflow is pushed.

**Operational requirement:** after this workflow reaches `main`, repository
administrators should make all three jobs required branch-protection checks.
Without that setting, the workflow reports failures but GitHub may still allow
a pull request to merge.

**First remote pre-PR run:** GitHub Actions run `34729173377` on commit
`c572cd1` failed during environment setup. The frontend job passed completely,
including tests, lint, build, and npm audit. The Python suite did not start:
Python setup replaced R's shared-library path, so the R bridge check failed.
The separate `requirements-r.txt` audit also failed while resolving `rpy2`
without R or ABI mode. Remediation keeps both gates: Python is now configured
before R so R's library path remains active, and the standalone audit resolves
`rpy2` with `RPY2_CFFI_MODE=ABI`. The status-artifact action was also updated
to its current Node 24 release after the first run emitted a Node 20 deprecation
warning.

**Second remote pre-PR run:** GitHub Actions run `34729354173` on commit
`3cb25bb` confirmed that the frontend and both Python dependency audits pass.
R 4.6.1 and the approved R packages also installed successfully, but `rpy2`
could not load `libR.so` because the runner still exposed only Python's shared
library directory. The workflow now obtains `R_HOME` from the installed R
executable and prepends its `lib` directory to `LD_LIBRARY_PATH` before Python
dependencies and tests run. The R gate remains mandatory.

## SLM Latency Run History

`benchmarks/slm_latency_results.json` remains the stable latest-result file.
Every available earlier run is preserved under
`benchmarks/history/slm_latency/`; future executions create a timestamped copy
automatically.

| Local time | Run | Status | Minimum | Mean | Median | Sample p95 | Maximum | Historical evidence |
|---|---|---|---:|---:|---:|---:|---:|---|
| 27 Aug 2026 19:13:40 AEST | Initial `llama3.2:3b` attempt | Blocked: Ollama unavailable | - | - | - | - | - | `2026-08-27T191340+1000_blocked-llama3-2.json` |
| 27 Aug 2026 19:42:25 AEST | Confirmed Phi-4 Mini attempt | Blocked: Ollama unavailable | - | - | - | - | - | `2026-08-27T194225+1000_blocked-phi4-mini-3-8b.json` |
| 29 Aug 2026 13:01:13 AEST | Week 4 baseline | Passed 5/5 | 911.82 ms | 2220.03 ms | 2344.50 ms | 3282.67 ms | 3463.26 ms | `2026-08-29T130113+1000_week4.json` |
| 5 Sep 2026 12:56:40 AEST | Week 5 confirmation | Passed 5/5 | 1261.09 ms | 2568.90 ms | 2988.77 ms | 3878.20 ms | 4061.79 ms | `2026-09-05T125640+1000_week5.json` |
| 12 Sep 2026, exact time unavailable | Week 6 initial | Passed 5/5 | 743.83 ms | 1919.76 ms | 1988.51 ms | 3031.99 ms | 3268.65 ms | `2026-09-12_week6-initial-summary-only.json` |
| 12 Sep 2026 21:17:08 AEST | Week 6 post-merge | Passed 5/5 | 927.70 ms | 2224.58 ms | 2395.99 ms | 3802.87 ms | 4084.96 ms | `2026-09-12T211708+1000_week6-post-merge.json` |

The Week 6 initial raw result was overwritten before commit. Its history entry
contains only the verified metrics previously recorded here and explicitly
marks unavailable prompt-level evidence. Two versions of the Prompt 0.4.8
grounding result and scorecard are also preserved under
`benchmarks/history/slm_grounding_prompt048/`: the 4 September pre-joint-review
run and the 6 September consensus update. No other machine-readable benchmark
result had been overwritten in Git history as of 13 September 2026.

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

### Week 6 Initial Audit

Week 6 confirmed that existing functionality remains stable and dependencies
have no currently known advisories, while identifying new privacy exposure
introduced after the Week 5 baseline. The current decision is **not approved
for participant-data use and not privacy-clean for merge** until raw identifiers
are removed from shared outputs and browser redirects are rejected. Synthetic
local development may continue without using the affected outputs.

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

The command updates the stable latest-result file and automatically creates a
new timestamped file under `benchmarks/history/slm_latency/`.

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
- `tests/privacy/test_analysis_output_privacy.py`
- `tests/slm/test_transport_privacy.py`
- `frontend/src/api/client.test.ts`
- `benchmarks/slm_latency_benchmark.py`
- `benchmarks/slm_latency_results.json`
- `benchmarks/history/README.md`
- `benchmarks/history/slm_latency/`
- `benchmarks/history/slm_grounding_prompt048/`
- `benchmarks/slm_prohibited_request_baseline_results.json`
- `benchmarks/slm_shadow_smoke_results.json`
- `benchmarks/slm_evaluation_alignment_results.json`
- `.github/pull_request_template.md`
- `.github/workflows/privacy-security-ci.yml`
- `docs/privacy/automated-ci-run-register.md`
