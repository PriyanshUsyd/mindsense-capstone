# Week 5 SLM Dependency Privacy Spot-Check

- Prepared by: Richard Zhao, SLM Integration
- Date: 4 September 2026 (Australia/Sydney)
- Status: developer checks completed within the scope below; peer and
  Integration/QA approval pending. Not participant-use approval.
- Scope: Week 5 changes after `7d33de4`, plus the inherited local inference
  boundary introduced in Week 4 PR #1. This document is added in Week 5;
  it does not modify or backdate Week 4 code, commits, or PR descriptions.

## Dependency and purpose

No new third-party Python or npm package is introduced by the Week 5 delta.
This does not exempt changed runtime/model usage from review. The checked
path uses Python's `urllib`, existing Pydantic/PyYAML, the local Ollama
runtime, and the already-installed comparison candidates.

| Component | Checked version or identity | Purpose |
|---|---|---|
| Python | 3.13.9 environment | Application and standard-library HTTP transport |
| Ollama | 0.33.2 from local `/api/version` | Local model serving |
| Phi baseline | `phi4-mini:3.8b`, Q4_K_M, digest `78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753` | Baseline explanation generation |
| Qwen challenger | `qwen3:4b`, Q4_K_M, digest `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7` | Controlled comparison, not final selection |

The model identities and embedded MIT/Apache licence indicators were checked
through local `/api/tags` and `/api/show`. No models were downloaded for this
review. Existing Python dependency licences are recorded in
`privacy/initial_dependency_audit.md`; this is not a new audit of every
transitive/native library. Final model selection remains `comparison_pending`.

## Privacy review

A tick means that the behaviour was examined with the evidence described
below. It does not mean that the component has no networking, no access to
data, or unconditional approval.

- [x] Checked default network calls in the application path and runtime docs.
- [x] Checked telemetry, analytics, crash reports, diagnostics, and usage
  metrics against application code and the documented runtime scope.
- [x] Checked install/download and automatic-update behaviour.
- [x] Checked access to participant data, prompts, responses, wellbeing
  labels, and dataset-derived features at the SLM boundary.
- [x] Checked upstream licence texts for the runtime and two model candidates
  for local university-prototype use; redistribution conditions remain relevant.
- [x] Considered standard-library and existing-dependency alternatives.

## Findings and mitigations

### Network behaviour

- `backend/slm/client.py` accepts only HTTP loopback `/api/chat` endpoints.
  Both configuration and transport entry validate the endpoint. Environment
  proxies and HTTP redirects are disabled; a local redirect cannot cause the
  client to follow a second URL.
- `tests/slm/test_transport_privacy.py` uses a synthetic loopback server to
  check redirect refusal, plus tests for external endpoint rejection and
  disabled proxy handlers. The suite's `pytest-socket` policy blocks external
  Python socket connections. These tests do not sandbox the native daemon.
- For the 4 September smoke run, the existing Ollama binary was started with
  `OLLAMA_HOST=127.0.0.1:11434` and `OLLAMA_NO_CLOUD=1`. A post-run connection
  snapshot found a listener at `127.0.0.1:11434` and zero established
  non-loopback connections among the observed Ollama processes. This is a
  point-in-time observation, not packet capture or proof about all future runs.
- Model pulls, runtime installation, and Windows/macOS application updates
  can contact the internet. The upstream FAQ documents this behaviour;
  cloud disablement does not by itself prove that updates are disabled.
  Do installations before testing, pre-download models, and use a controlled
  serving process with external networking blocked for participant sessions.

### Telemetry and logging

No new telemetry, analytics, crash-upload SDK, or remote log sink was added
in the SLM changes. Upstream distinguishes local inference from cloud
features; its local-data statement is not an exhaustive binary traffic audit.
Ollama can write local diagnostic logs. The shadow CLI and benchmark print or
save response text, so they are development tools for synthetic fixtures only.
Do not use them to collect real participant conversations without an approved
logging, retention, consent, and redaction design. Whole-device disconnected
verification remains an acceptance gate; no absolute "nothing ever leaves
this computer" claim is made.

### Data touched

The service consumes validated `EvidencePacket` objects and a question, not
CES files, raw coordinates, or raw PHQ-4 rows. Its intended inputs may contain
derived behavioural evidence, which remains sensitive if linked to a person.
The model receives the question and structured packet after the
`participant_ref` field is replaced with `redacted`. Other contract IDs and
free text are not automatically anonymised; callers must supply non-identifying
IDs and minimised inputs. Payload redaction is regression-tested and does not
mutate the upstream evidence packet.

All committed smoke fixtures/results are synthetic. The sealed Week 11
prompts were not supplied to a model or displayed during this review. Only
integrity/structure tests and byte-hash checks touched that existing file.
Raw datasets, weights, credentials, and private bilingual meeting notes are
not part of this delivery.

### Licences and alternatives

- Ollama and Phi upstream licence texts are MIT; Qwen3-4B is Apache-2.0.
  Preserve relevant notices/terms if distributing software or weights. This
  PR distributes neither runtime binaries nor model weights and does not
  establish clinical fitness or institutional approval.
- Existing `urllib` was retained instead of adding an HTTP SDK. Existing
  Pydantic/PyYAML provide schema validation and safe configuration loading.
  Deterministic templates replace model generation for missing-data and
  prohibited requests. No cloud-model SDK is needed.

Sources checked on 4 September 2026:

- [Ollama FAQ: local/cloud data, cloud disablement, updates, and binding](https://docs.ollama.com/faq)
- [Ollama MIT licence](https://github.com/ollama/ollama/blob/main/LICENSE)
- [Microsoft Phi-4-mini-instruct MIT licence](https://huggingface.co/microsoft/Phi-4-mini-instruct/blob/main/LICENSE)
- [Qwen3-4B Apache-2.0 licence](https://huggingface.co/Qwen/Qwen3-4B/blob/main/LICENSE)
- [Python urllib redirect handling](https://docs.python.org/3/library/urllib.request.html#urllib.request.HTTPRedirectHandler)

## Decision for reviewers

- [ ] Approved
- [x] Approved with mitigation
- [ ] Rejected

### Privacy Lead sign-off

- Reviewer: Yuktha Naveen, Privacy and Security Lead
- Review date: 5 September 2026 (Australia/Sydney)
- Reviewed commit: `1554ec6`
- Scope: the Week 5 SLM dependency and local-inference boundary documented
  above; this is not approval of every dependency added by other components.
- Verification: 10/10 focused privacy and transport tests passed; the complete
  current-main suite passed 308/308 tests with 14 `statsmodels` convergence
  warnings unrelated to the SLM transport boundary.
- Dependency checks: `pip check` reported no broken requirements, and both the
  declared-requirements and installed-environment `pip-audit` checks reported
  no known vulnerabilities.

The current FastAPI `0.141.1` and Starlette `1.6.0` test stack requires
`httpx2`; current main instead declares `httpx`. For verification,
`httpx2==2.12.0` was privacy-checked and installed only in the untracked local
`.venv`. The package can make outbound HTTP requests when explicitly used, but
the reviewed API tests use its in-process ASGI transport with synthetic
fixtures. Integration/QA must correct or pin the declared test dependency and
rerun the suite so a fresh environment is reproducible.

**Decision:** approved with mitigation for synthetic local development. This
sign-off does not authorise participant deployment. The disconnected
integrated-app check, controlled model/runtime installation, input
minimisation, logging and retention design, and separate Integration/QA and
peer review of safety-critical paths remain required.

AI assistance: command execution, dependency lookup, and sign-off drafting;
the review decision was authorised by Yuktha Naveen after the recorded results
were checked.
