# Week 4 Privacy and Security Status

Owner: Yuktha Naveen, Privacy and Security Lead
Date: 2026-08-29

## Completed

- Drafted the privacy and architecture principles for network calls, telemetry, logs, dependencies, downloads, storage, and safety handling.
- Established the standing rule that every dependency change needs a privacy spot-check in its PR description.
- Added the dependency spot-check to the repository PR template.
- Replaced the pre-application dependency audit with a complete audit of the current repository and installed stack.
- Installed and checked the declared Python and frontend dependencies.
- Enabled deny-by-default Python socket restrictions with loopback as the only exception.
- Ran the full Python and frontend checks.
- Installed the confirmed local model and measured real-machine SLM latency.

## Privacy Verification

Status: conditional pass.

Verified:

- CES and local credentials are excluded from Git and Git history.
- No telemetry, analytics, crash-reporting, cloud-model, CDN, or automatic public frontend call was detected.
- Ollama listens on `127.0.0.1:11434` only.
- No public Ollama TCP connection was observed during a synthetic inference snapshot.
- Privacy tests passed 3/3.
- The full pytest suite passed 124/124 under loopback-only socket restrictions.
- Frontend lint and production build passed.
- `pip check` found no broken requirements and npm reported zero known vulnerabilities during installation.

Open privacy findings:

- The eligibility script still emits raw ineligible CES UIDs.
- The starter frontend still contains six external links.
- Python requirements are mostly unpinned and have no resolved lockfile.
- Existing dependency additions bypassed the PR privacy spot-check because no PRs were used.
- A final SLM inference test with public networking disabled is still required.

## SLM Latency Benchmark

Status: measured successfully.

Environment:

- Provider: Ollama
- Model: `phi4-mini:3.8b`
- Endpoint: `http://127.0.0.1:11434/api/generate`
- Machine: Apple arm64 Mac
- Runs: 5 synthetic prompts

Results:

- Minimum: 911.82 ms
- Mean: 2220.03 ms
- Median: 2344.50 ms
- p95: 3282.67 ms
- Maximum: 3463.26 ms

Evidence: `benchmarks/slm_latency_results.json`

The benchmark measures latency, not clinical or safety quality. One raw response used causal-sounding wording, reinforcing that all product output must pass the deterministic claim and safety gate.

## Team Update

Week 4 privacy architecture, dependency rule, automated network gate, repository audit, and local SLM benchmark are complete. The current repository passes 124 pytest checks under loopback-only socket restrictions plus a clean frontend production build. Local Phi-4 Mini latency averaged 2.22 seconds across five synthetic prompts. Before participant-facing use, remove UID-level command output and external starter links, lock Python dependencies, enforce dependency PR reviews, and complete a disconnected-network Ollama test.
