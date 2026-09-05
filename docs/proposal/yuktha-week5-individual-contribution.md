# Week 5 Individual Contribution — Privacy and Security Lead

**Contributor:** Yuktha Naveen

**Role:** Privacy and Security Lead

My component addresses the risk that sensitive wellbeing evidence, identifiers, prompts, model responses, or diagnostic-style content could leave the local device or be exposed through dependencies, logs, and unsafe model behaviour. In Week 5 I verified the merged implementation against the local-first privacy architecture established in Week 4, rather than relying only on written design principles.

The implemented workflow minimises local CES data into a validated `EvidencePacket`, applies deterministic request-policy checks, sends eligible requests through a loopback-only Ollama client, and validates model output before display. `backend/slm/client.py` permits only `127.0.0.1` or `localhost`, disables environment proxies and redirects, and replaces `participant_ref` with `redacted` before local inference. Missing-data, diagnosis-seeking, prohibited, and crisis cases can be handled locally without invoking the model. Every dependency PR must still complete the privacy spot-check in `.github/pull_request_template.md`.

I completed source, credential-pattern, manifest, telemetry, logging, and network reviews; reran the focused privacy suite; and verified the full merged repository. Results were 10/10 focused privacy and transport tests, 276/276 total pytest checks, 4/4 real Phi shadow paths, and 16/16 public prohibited-request cases with zero unexpected model calls. Frontend lint/build and relevant Ruff checks passed. `npm audit` found zero vulnerabilities. An installed-environment audit found advisories in local development tool `pip 25.2`; I upgraded the untracked virtual environment to `pip 26.2`, after which `pip-audit` and `pip check` were clean.

I also repeated the five-prompt Phi-4 Mini benchmark on my Mac. Mean latency was 2.57 seconds and sample p95 was 3.88 seconds, compared with 2.22 and 3.28 seconds in Week 4. All requests succeeded, but the small speed sample is not a safety or production guarantee.

The outcome is conditional approval for synthetic local development, not participant use. Remaining work includes a public-network-blocked integrated-app test, removal or approval of six frontend links, aggregate-only CES eligibility output, a resolved Python lockfile, broader redaction, and an approved logging/retention design. Evidence is in `privacy/week5_privacy_security_report.md`, `benchmarks/slm_latency_results.json`, `tests/privacy/test_no_network_egress.py`, and `tests/slm/test_transport_privacy.py`. References: [Ollama FAQ](https://docs.ollama.com/faq) and [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).
