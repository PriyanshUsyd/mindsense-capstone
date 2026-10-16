# MindSense privacy documentation

Yuktha Naveen owns this area as Privacy and Security Lead. The operational policy and status sources remain in the repository's established top-level `privacy/` directory. This documentation directory stores the rendered weekly reports and provides a single index to the current evidence.

## Core privacy controls

- [Privacy architecture principles](../../privacy/privacy_architecture_principles.md): rules for network calls, telemetry, logs, dependencies, storage, model files, and sensitive outputs.
- [Dependency privacy checklist](../../privacy/dependency_privacy_checklist.md): the reusable review applied when a dependency is proposed or changed.
- [Initial dependency audit](../../privacy/initial_dependency_audit.md): the baseline dependency and network-behaviour review.
- [Pull request privacy gate](../../.github/pull_request_template.md): the standing requirement that every dependency change records a privacy spot-check in its PR description.
- [Network-egress tests](../../tests/privacy/test_no_network_egress.py): automated enforcement that permits loopback traffic and blocks public Python socket connections during tests.
- [R-bridge privacy tests](../../tests/privacy/test_r_bridge_privacy.py): enforce temporary-data cleanup, package allowlisting, and the absence of network, shell, install, logging, and file-write calls in the embedded-R bridge.
- [Privacy and Security CI](../../.github/workflows/privacy-security-ci.yml): runs four clearly separated Python, R, frontend, and privacy/security stages for pull requests and updates to `main`.
- [Four-stage CI pipeline guide](ci-pipeline-guide.md): defines each stage's scope, test ownership, automatic run record, and failure-explanation artifacts.

## Weekly verification evidence

- [Week 4 status](../../privacy/week4_privacy_status.md): initial principles, dependency gate, and real-machine Phi-4 Mini latency baseline.
- [Week 4 Privacy Lead Report](week4-privacy-lead-report.pdf): six-page rendered report covering the completed Week 4 assignment.
- [Week 5 Privacy and Security Report](week5-privacy-security-report.pdf): six-page rendered post-merge privacy, transport, telemetry, logging, dependency, safety, and latency review.
- [Week 5 post-merge dependency review](../../privacy/week5_post_merge_dependency_review.md): retrospective review of the frontend test stack and local R toolchain added by PRs #7 and #8.
- [Latency benchmark](../../benchmarks/slm_latency_benchmark.py), [latest measured results](../../benchmarks/slm_latency_results.json), and [run history](../../benchmarks/history/README.md): reproducible local benchmark, current Week 6 result, and immutable earlier evidence.

## Current assurance boundary

The GitHub workflow runs four stages on every push and pull request; the
latest `main` run (`38833421820`, on `95e3171`) passed all four, including
Stage 4, the privacy and security gates. On the final build the local suite
passed 1027 Python tests and 41 frontend tests with outbound network blocked
except loopback (`pytest.ini`), and frontend lint/build passed (release
checklist §11). The git history was scrubbed of personal data on 2026-10-16.
Approval for participant use is the Privacy & Security Lead's sign-off on the
final build, which includes the whole-device offline test and the review areas
in the [master test register](master-test-register.md#privacy-review-and-remaining-work)
(input minimisation, logging and retention, dependency locking, governance).
