# MindSense Privacy and Architecture Principles

Owner: Yuktha Naveen, Privacy and Security Lead  
Status: Week 4 draft  
Last updated: 2026-08-27

## Scope

These principles define the privacy baseline for MindSense. They apply to the app, data pipeline, SLM integration, evaluation scripts, demo setup, and any future dependency or service added to the project.

## Core Position

MindSense is a local-first, privacy-preserving student capstone prototype. The default architecture is:

- Raw participant data stays on the local machine used for processing and demonstration.
- SLM inference runs locally unless the team explicitly records and approves an exception.
- No analytics, telemetry, crash reporting, or remote logging is enabled by default.
- Network access is deny-by-default for runtime paths that handle user or dataset-derived data.
- Any privacy-impacting change must be visible in the PR description before review.

## Network Calls

Runtime network calls are prohibited unless they are explicitly required, documented, and approved.

Allowed without additional review:

- Localhost calls between app components, such as UI to local API server.
- Local model server calls on loopback addresses, such as `127.0.0.1` or `localhost`.
- Development-only dependency installation before participant or dataset data is present.

Requires privacy review before merge:

- Any request to a public internet endpoint.
- Any SDK that can send telemetry, analytics, crash reports, diagnostics, or usage metrics.
- Any cloud-hosted model API.
- Any remote asset loading in the app, including fonts, scripts, images, or CDN libraries.
- Any package post-install script that downloads model weights or binaries.

Project rule:

- Code handling participant data or dataset-derived features must not make outbound internet requests.
- If network access is necessary for a non-sensitive development task, it must be separated from data-processing and inference paths.

## Telemetry and Analytics

Telemetry is disabled by default.

Prohibited by default:

- Product analytics.
- Session replay.
- Crash-report uploads.
- Remote performance monitoring.
- Prompt, response, feature, or evaluation-result logging to third-party services.

If a dependency includes optional telemetry:

- Disable it through configuration or environment variables.
- Record the disablement method in the dependency audit.
- Verify it is not active during the privacy check.

## Logs

Logs must be useful for debugging without exposing sensitive content.

Do not log:

- Raw sensor records.
- Participant identifiers.
- Free-text user inputs.
- SLM prompts or responses from evaluation participants.
- Wellbeing labels, scores, or crisis-trigger content tied to a person.
- File paths that include participant names or identifiers.

Allowed logs:

- Component start and stop events.
- Local model name and version.
- Aggregate latency metrics.
- Non-identifying error classes.
- Counts of records processed, after suppressing small-cell or participant-identifying detail.

Retention rule:

- Local logs should be deleted or rotated after testing unless required as evidence for a report.
- Evidence logs must be redacted before being shared outside the development machine.

## Downloads and Model Files

Model weights and runtime binaries can introduce privacy and security risk.

Rules:

- Prefer models with clear license terms, local inference support, and no required cloud callback.
- Record model name, version, source, license, file size, and checksum where practical.
- Do not download model files during a participant session.
- Do not auto-update models, prompts, or runtime packages during evaluation.
- Week 9 onward must use a fixed, reproducible model and prompt version.

## Backups and Sync

Backups must not silently move sensitive data into cloud storage.

Rules:

- Store participant or dataset-derived local files outside cloud-synced folders where practical.
- Do not place raw data in shared drives, public repositories, or messaging apps.
- If evidence artifacts must be shared, share redacted summaries rather than raw data.
- Demo machines should be checked for automatic cloud sync before evaluation.

## Dependencies

Every dependency is treated as part of the privacy boundary.

Before adding a dependency, check:

- What network access it performs by default.
- Whether it includes telemetry, analytics, crash reporting, or auto-update behavior.
- Whether it runs install scripts or downloads binaries/model weights.
- Whether it processes prompts, responses, features, or participant data.
- Its license and maintenance status.
- Whether the same outcome can be achieved with the standard library or an existing dependency.

Standing PR rule:

- Every PR that adds a new dependency must include a 10-minute privacy spot-check in the PR description.
- The spot-check must list the dependency name, purpose, network behavior, telemetry/logging behavior, license, and decision.
- PRs missing this section should not be merged.

## Architecture Boundaries

Recommended component boundaries:

- Data ingestion: reads local dataset files and emits normalized local records.
- Feature extraction: transforms local records into minimal Tier 1 feature values.
- Evidence contract: passes only required feature and evidence-strength fields to downstream logic.
- Statistical logic: produces baseline comparison state and permitted/prohibited claim flags.
- SLM layer: receives only the minimum evidence contract needed to generate a response.
- UI layer: displays normal, cold-start, uncertainty, refusal, generic fallback, and crisis-aware fallback states.

Privacy principle:

- The SLM layer should not receive raw sensor streams when a minimal evidence contract is enough.
- The UI should not display or persist hidden diagnostic fields that identify a participant.

## Crisis and Safety Content

Crisis-aware fallback content is safety-critical and must be handled separately from generic failure content.

Rules:

- Crisis-trigger handling should not rely on cloud services.
- Crisis-aware templates must not log user text or crisis details.
- Helpline/support-resource content must be prepared in version-controlled text, not improvised during evaluation.
- Any safety-critical path requires Integration and QA Lead review plus one peer review.

## Verification Checklist

For Week 4 and later privacy checks, record:

- Local runtime and model selected.
- Whether SLM inference works with network disconnected or blocked.
- Whether runtime logs contain prompts, responses, identifiers, or raw data.
- Whether dependencies added since the previous check passed the spot-check rule.
- Whether app/runtime loads remote assets or calls remote endpoints.
- Whether participant/evaluation artifacts are stored outside public or synced locations.

## Open Decisions

- Final SLM and deployment stack are owned by the SLM Integration Lead.
- Cloud fine-tuning is not approved by default because it conflicts with the local-only privacy claim if any real dataset-derived examples are uploaded.
- If fine-tuning is ever attempted, use purely synthetic examples only and record the exception decision.
