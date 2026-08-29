# Initial Dependency Audit

Owner: Yuktha Naveen, Privacy and Security Lead  
Date: 2026-08-27  
Scope: `/Users/yukthanaveen/Documents/SEM4/Capstone`

## Result

No application source tree or dependency manifest is currently present in the Capstone workspace.

Checked locations:

- `Work/`
- Top-level Capstone folder

Observed project content:

- Capstone planning documents, templates, PDFs, spreadsheets, and weekly meeting/build-plan files.
- No `package.json`, `requirements.txt`, `pyproject.toml`, `Pipfile`, `poetry.lock`, `environment.yml`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`, or comparable dependency manifest was present.
- No Git repository was present at the Capstone root.

## Current Dependency Baseline

Application dependencies added by the team: none visible in this workspace.

Privacy risk from dependencies at this point: low, because no runnable application dependency stack is present here yet.

## Standing Rule

From Week 4 onward, any PR adding a dependency must include the dependency privacy spot-check in its PR description.

Minimum required fields:

- Dependency name and purpose.
- Network behavior.
- Telemetry, analytics, crash reporting, diagnostics, or usage metrics.
- Install scripts, post-install downloads, auto-updates, model downloads, or binary downloads.
- Data touched.
- License.
- Alternatives considered.
- Decision and mitigation.

## Follow-Up Once Repository Exists

When the GitHub repository or app skeleton is available:

- Move `Work/.github/pull_request_template.md` into the repository `.github/` folder.
- Re-run this audit against actual dependency manifests and lockfiles.
- Record all runtime packages used by the data pipeline, SLM runtime, UI, and evaluation scripts.
- Confirm no dependency sends telemetry by default during local execution.
