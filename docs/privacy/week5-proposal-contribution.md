# Privacy Proposal Contribution

Yuktha Naveen | Privacy and Security Lead | 5 September 2026

My component is the project's privacy assurance layer. It addresses the risk that sensitive wellbeing evidence, identifiers, prompts, model responses, or diagnostic-style content could leave the local device or be exposed through dependencies, logs, and unsafe model behaviour. I established the Week 4 local-first principles and, in Week 5, led the post-merge verification needed to turn those principles into evidence the team can defend.

I defined the privacy boundary and checked the merged workflow end to end. It minimises local CES data into a validated `EvidencePacket`, applies deterministic request-policy checks, sends eligible requests through a loopback-only Ollama client, and validates model output before display. The client restricts requests to `127.0.0.1` or `localhost`, disables environment proxies and redirects, and redacts `participant_ref`. I also retained the standing dependency privacy check in `.github/pull_request_template.md`, making privacy evidence a recurring merge requirement rather than a one-off document.

I completed source, credential-pattern, manifest, telemetry, logging, and network reviews and verified the full merged repository. Results were 10/10 focused privacy and transport tests, 276/276 pytest checks, 4/4 real Phi shadow paths, and 16/16 prohibited-request cases with zero unexpected model calls. Frontend and Ruff checks passed. I also found seven advisories affecting local development tool `pip 25.2`, upgraded the untracked environment to `pip 26.2`, and confirmed clean repeated Python and npm audits.

I repeated the five-prompt Phi-4 Mini benchmark on my Mac. Mean latency was 2.57 seconds and sample p95 was 3.88 seconds, compared with 2.22 and 3.28 seconds in Week 4. All requests succeeded, but the sample is not a safety or production guarantee.

My work gives the team a documented privacy release gate: conditional approval for synthetic local development, not participant use. Remaining actions include a public-network-blocked integrated-app test, aggregate-only CES output, a Python lockfile, broader redaction, and an approved logging and retention design. Evidence is in `docs/privacy/week5-privacy-security-report.pdf`, `benchmarks/slm_latency_results.json`, `tests/privacy/test_no_network_egress.py`, and `tests/slm/test_transport_privacy.py`. References: [Ollama FAQ](https://docs.ollama.com/faq) and [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).

AI assistance: contribution drafting and formatting; privacy decisions, repository evidence, local benchmark execution, and test outcomes were reviewed against the versioned project artifacts.
