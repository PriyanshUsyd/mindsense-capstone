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
  UPDATE 2026-08-29 (second pass): `git fetch --all` found 4 real remote
  branches that a purely-local check had missed —
  `moet/week4_statistical_analysis`, `chonghao/evaluation-week4`,
  `honglin/docs-week4`, `yuktha/privacy-week4`. Three contained genuine,
  substantive teammate work and have been merged into `main` (see the Week
  4 status report for details). **`honglin/docs-week4` turned out to be an
  exact duplicate of `yuktha/privacy-week4`'s commits (identical hash
  `8dd9113`) — not separate real work from Honglin.** Honglin's actual Docs
  Week 4 task (repo skeleton + Proposal outline) still has no artifact
  authored by Honglin himself anywhere — flagged for direct follow-up.
  `gh` still isn't installed here, so open PRs (as opposed to branches)
  still couldn't be queried directly — worth a direct look on github.com.

## GitHub branch-protection setup steps (for whoever has admin access)

Cannot be done from this environment — these are GitHub web UI settings,
not files. Numbered steps for whoever has admin on
`github.com/PriyanshUsyd/mindsense-capstone`:

1. Go to the repo on github.com → **Settings** → **Branches**.
2. Under "Branch protection rules", click **Add branch protection rule** (or
   "Add rule").
3. Set **Branch name pattern** to `main`.
4. Enable **Require a pull request before merging** (so nobody, including
   admins, pushes straight to `main` again — this Week 4 pass itself pushed
   directly to `main` twice, which branch protection would have blocked and
   forced through a PR instead).
5. Under that, enable **Require approvals** and set it to at least 1.
6. Enable **Require status checks to pass before merging**, once CI exists
   (there's no CI workflow file yet — a follow-up item, not blocking this
   step).
7. Enable **Require branches to be up to date before merging**.
8. Consider enabling **Do not allow bypassing the above settings** so it
   applies to repo admins too, not just other contributors.
9. Save the rule.

## Files added toward the skeleton

See the top-level Week 4 status report for the full list; the short version
is a `README.md` placeholder in each otherwise-empty folder explaining what
belongs there and who owns it, so an empty directory in git isn't just a
mystery to whoever opens the repo next.
