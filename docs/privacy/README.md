# MindSense privacy documentation

Yuktha Naveen owns this area as Privacy and Security Lead. The operational policy and status sources remain in the repository's established top-level `privacy/` directory. This documentation directory stores the rendered weekly reports and provides a single index to the current evidence.

## Core privacy controls

- [Privacy architecture principles](../../privacy/privacy_architecture_principles.md): rules for network calls, telemetry, logs, dependencies, storage, model files, and sensitive outputs.
- [Dependency privacy checklist](../../privacy/dependency_privacy_checklist.md): the reusable review applied when a dependency is proposed or changed.
- [Initial dependency audit](../../privacy/initial_dependency_audit.md): the baseline dependency and network-behaviour review.
- [Pull request privacy gate](../../.github/pull_request_template.md): the standing requirement that every dependency change records a privacy spot-check in its PR description.
- [Network-egress tests](../../tests/privacy/test_no_network_egress.py): automated enforcement that permits loopback traffic and blocks public Python socket connections during tests.
- [R-bridge privacy tests](../../tests/privacy/test_r_bridge_privacy.py): enforce temporary-data cleanup, package allowlisting, and the absence of network, shell, install, logging, and file-write calls in the embedded-R bridge.
- [Privacy and Security CI](../../.github/workflows/privacy-security-ci.yml): runs the reproducible Python/R, frontend, privacy, security, build, and dependency gates for pull requests and updates to `main`.
- [Automated CI run register](automated-ci-run-register.md): separates automatically recorded GitHub run evidence from local-only checks and the master test register.

## Weekly verification evidence

- [Week 4 status](../../privacy/week4_privacy_status.md): initial principles, dependency gate, and real-machine Phi-4 Mini latency baseline.
- [Week 4 Privacy Lead Report](week4-privacy-lead-report.pdf): six-page rendered report covering the completed Week 4 assignment.
- [Week 5 Privacy and Security Report](week5-privacy-security-report.pdf): six-page rendered post-merge privacy, transport, telemetry, logging, dependency, safety, and latency review.
- [Week 5 post-merge dependency review](../../privacy/week5_post_merge_dependency_review.md): retrospective review of the frontend test stack and local R toolchain added by PRs #7 and #8.
- [Latency benchmark](../../benchmarks/slm_latency_benchmark.py) and [latest measured results](../../benchmarks/slm_latency_results.json): reproducible local benchmark and the current Week 5 result.

## Current assurance boundary

The latest Week 6 local preflight passed 391 Python/R tests and 14 frontend
tests, together with frontend lint/build and dependency advisory checks. The
new GitHub workflow is locally validated but has not yet executed remotely.
Current evidence supports conditional approval for synthetic local development.
It does not approve participant use; disconnected integrated-app testing,
input minimisation, logging and retention rules, Git-history remediation,
dependency locking, and governance review remain required.
