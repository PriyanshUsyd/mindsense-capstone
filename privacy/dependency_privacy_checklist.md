# Dependency Privacy Checklist

Owner: Yuktha Naveen, Privacy and Security Lead  
Status: Standing rule from Week 4

Use this checklist for every PR that adds, removes, or materially changes a dependency.

## PR Spot-Check Template

Copy this section into the PR description when adding a dependency.

```md
## Dependency Privacy Spot-Check

Dependency:
Purpose:
Added by:
Date:

Privacy review:
- [ ] I checked whether this dependency makes network calls by default.
- [ ] I checked whether this dependency sends telemetry, analytics, crash reports, diagnostics, or usage metrics.
- [ ] I checked whether this dependency has install scripts, post-install downloads, auto-update behavior, or remote model/binary downloads.
- [ ] I checked whether this dependency can access or process raw participant data, prompts, SLM responses, wellbeing labels, or dataset-derived features.
- [ ] I checked the license is acceptable for a university capstone prototype.
- [ ] I checked whether an existing dependency or standard-library feature can do the job.

Findings:
- Network behavior:
- Telemetry/logging behavior:
- Install/download behavior:
- Data touched:
- License:
- Alternatives considered:

Decision:
- [ ] Approved
- [ ] Approved with mitigation
- [ ] Rejected

Mitigation or notes:
```

## Quick Review Method

Spend 10 minutes on:

- Package README and docs.
- Package repository issues for telemetry, analytics, tracking, phone-home, auto-update, or privacy.
- Install metadata for scripts or binary downloads.
- Import path and intended use in the PR.
- Runtime configuration for disabling telemetry or remote calls.

## Merge Rule

A PR adding a dependency should not be merged unless the PR description includes the completed privacy spot-check.

For safety-critical paths, Priyansh as Integration and QA Lead must review in addition to one peer reviewer.
