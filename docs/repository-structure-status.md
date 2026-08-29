# Repository Structure — Week 4 Status (Honglin Lu's role)

Weekly_Plan.md: "Set up the GitHub repo, branch protection, and skeleton per
the repository structure in `build-reference.md`."

**Status as found on 2026-08-29, before this Week 4 gap-fill pass:** only
`build-reference.md`, `Weekly_Plan.md`, `Client_Specs.md`, `Readme.md`,
`.gitignore`, and `skills/` existed — none of the actual folder skeleton
from `build-reference.md` Section 8 was present (no `docs/`, `backend/`,
`frontend/`, or `tests/`).

**What this Week 4 pass added:** the folder skeleton itself
(`docs/`, `backend/{contracts,data_pipeline,statistics,slm/prompts,privacy,
evaluation,api}`, `frontend/` with a real Vite+React+TS scaffold, `tests/`
mirroring `backend/`), plus a `.pre-commit-config.yaml` matching the locked
tool choice (Ruff — `build-reference.md` Section 3).

## What could NOT be done from here — needs Honglin (or whoever has GitHub admin) directly

- **Branch protection rules on `main`** — this is a GitHub repository
  setting (Settings → Branches), not a file in the repo. It cannot be set
  via a commit; it requires someone with admin access on
  github.com/PriyanshUsyd/mindsense-capstone to configure it (e.g. require
  PR review before merge, require the CI check to pass).
- **Confirming there are no other stray branches/PRs on GitHub itself:**
  `git branch -a` here only shows `main` (local and `origin/main`), and the
  `gh` CLI isn't installed on this machine, so PRs couldn't be queried
  directly via the GitHub API from here. Worth a direct check on
  github.com to be certain, especially if anyone has pushed a branch that
  hasn't been fetched for some reason.

## Files added toward the skeleton

See the top-level Week 4 status report for the full list; the short version
is a `README.md` placeholder in each otherwise-empty folder explaining what
belongs there and who owns it, so an empty directory in git isn't just a
mystery to whoever opens the repo next.
