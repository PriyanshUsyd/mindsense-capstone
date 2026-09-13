# Automated Privacy and Security CI Run Register

**Owner:** Privacy and Security Lead

**Workflow:** `.github/workflows/privacy-security-ci.yml`
**Purpose:** keep automatic CI evidence separate from the manually maintained
`docs/privacy/master-test-register.md`.

## How Every Run Is Recorded

GitHub automatically retains the trigger, commit, timestamps, logs, and result
for every workflow run. The workflow also creates a concise Markdown record:

- it is displayed in that run's GitHub Actions summary;
- it is downloadable as
  `privacy-security-ci-run-<run-id>-<attempt>/privacy-security-ci-run.md`;
- it is retained as a GitHub Actions artifact for 90 days; and
- it contains status metadata only, never participant data, test fixtures,
  model output, repository contents, or credentials.

The workflow deliberately does not commit run records back into the repository.
That keeps CI read-only, prevents recursive workflow commits, and avoids giving
the runner write access to `main`.

## Runs Automatically

These checks run for every pull request targeting `main`, every push to `main`
including a merged pull request, and every manual workflow dispatch:

| Automatic gate | Included checks |
|---|---|
| Python, privacy, security, integration, and R | Full `pytest` suite using synthetic fixtures; socket egress policy; raw-identifier output gate; SLM request, response, transport, grounding, and safety checks; backend API and evidence contract tests; statistical tests; real R bridge availability and R-backed tests; `pip check`. |
| Frontend | Vitest tests, loopback and redirect privacy gate, Oxlint, production build, and high/critical npm advisory audit. |
| Python dependencies | Strict `pip-audit` checks for `requirements.txt` and `requirements-r.txt`. |
| Run evidence | Overall decision and each job result written to the GitHub run summary and a Markdown artifact. |

External actions are pinned to immutable commit hashes. The workflow has
`contents: read` permission, checkout does not retain Git credentials, and no
project secrets are supplied.

## Still Runs Locally

The following cannot be treated as ordinary GitHub-hosted CI checks:

| Local check | Why it remains local |
|---|---|
| CES dataset-backed tests | The participant dataset is intentionally gitignored and must not be uploaded to GitHub Actions. |
| Phi-4 Mini latency benchmark | It requires the approved local Ollama model and results depend on the actual target hardware. |
| Integrated offline verification | The complete frontend, FastAPI, R, and Ollama stack must be tested with public networking disabled at operating-system level. |
| Repository-wide Ruff baseline | The current tree has 36 pre-existing findings. Enabling it as a required gate now would block unrelated PRs; new Privacy Lead Python tests are checked locally until the baseline is cleaned. |
| Human privacy and safety review | Automated checks cannot establish clinical appropriateness, informed consent, retention decisions, or incident-response readiness. |

## Reviewed Run Index

The GitHub Actions history and per-run Markdown artifacts are the authoritative
automatic record. After reviewing a run, add one row here so important merge
decisions remain easy to find after the 90-day artifact period.

| Date | Run ID | Trigger | Commit | Automatic result | Local checks required | Reviewed by | Notes |
|---|---:|---|---|---|---|---|---|
| Pending first remote run | - | - | - | Not yet executed on GitHub | Dataset, latency, offline integration | Yuktha Naveen | Workflow currently exists only as an uncommitted Week 6 branch change. |

## Review Rule

1. Open the GitHub Actions run and inspect every failed or skipped check.
2. Download or view the generated Markdown run record.
3. Confirm expected skips are limited to tests needing the gitignored dataset.
4. Add the reviewed run to the index above.
5. Run the local-only checks when the changed files affect data processing,
   model runtime, network behaviour, or release readiness.
6. Record significant local results and the combined release decision in the
   master test register.

A green automatic run permits review to continue; it does not by itself approve
participant deployment.
