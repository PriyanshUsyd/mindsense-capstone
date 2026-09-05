# MindSense privacy documentation

Yuktha Naveen owns this area as Privacy and Security Lead. The editable policy and verification sources remain in the repository's established top-level `privacy/` directory. This documentation directory stores the rendered technical reports and provides a single index to the current evidence.

## Core privacy controls

- [Privacy architecture principles](../../privacy/privacy_architecture_principles.md): rules for network calls, telemetry, logs, dependencies, storage, model files, and sensitive outputs.
- [Dependency privacy checklist](../../privacy/dependency_privacy_checklist.md): the reusable review applied when a dependency is proposed or changed.
- [Initial dependency audit](../../privacy/initial_dependency_audit.md): the baseline dependency and network-behaviour review.
- [Pull request privacy gate](../../.github/pull_request_template.md): the standing requirement that every dependency change records a privacy spot-check in its PR description.
- [Network-egress tests](../../tests/privacy/test_no_network_egress.py): automated enforcement that permits loopback traffic and blocks public Python socket connections during tests.

## Weekly verification evidence

- [Week 4 status](../../privacy/week4_privacy_status.md): initial principles, dependency gate, and real-machine Phi-4 Mini latency baseline.
- [Week 4 Privacy Lead Report](week4-privacy-lead-report.pdf): six-page rendered report covering the completed Week 4 assignment.
- [Week 5 verification source](../../privacy/week5_privacy_security_report.md): post-merge privacy, transport, telemetry, logging, dependency, safety, and latency review.
- [Week 5 Privacy and Security Report](week5-privacy-security-report.pdf): six-page rendered verification report.
- [Week 5 individual contribution](../proposal/yuktha-week5-individual-contribution.md) and [rendered PDF](../proposal/yuktha-week5-individual-contribution.pdf): concise personal contribution evidence for the Group Proposal Report.
- [Latency benchmark](../../benchmarks/slm_latency_benchmark.py) and [latest measured results](../../benchmarks/slm_latency_results.json): reproducible local benchmark and the current Week 5 result.

## Current assurance boundary

Week 5 verification passed 10 focused privacy and transport tests and 276 complete repository tests. The evidence supports conditional approval for synthetic local development. It does not approve participant use; disconnected integrated-app testing, input minimisation, logging and retention rules, aggregate-only CES output, dependency locking, and governance review remain required.
