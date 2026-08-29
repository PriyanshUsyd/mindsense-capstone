# Repository Structure — Week 4 Confirmation (Honglin Lu's role)

> **Built due to Week 4 time constraints — Documentation Lead to review,
> revise, and take ownership.** No commit from Honglin exists anywhere for
> this task as of 2026-08-29 (his branch, `honglin/docs-week4`, turned out
> to be a byte-identical duplicate of Yuktha's privacy branch — not
> separate real work, see the branch-discovery section below). This
> document is a placeholder confirmation pass, not a substitute for
> Honglin's own review of the repo he's meant to own.

Weekly_Plan.md: "Set up the GitHub repo, branch protection, and skeleton per
the repository structure in `build-reference.md`."

## Confirmation checklist — build-reference.md Section 8 vs. what's actually on `main` (2026-08-29)

| Section 8 path | Owner | Present? | What's actually there |
|---|---|---|---|
| `docs/` | Documentation Lead | ✅ | Proposal outline, per-role Week 4 docs, this file |
| `backend/contracts/` | Shared, full sign-off required | ✅ | `evidence.py` (draft, pending contract-v1.0.0 freeze) |
| `backend/data_pipeline/` | Honghao Li | ✅ | `verify_ces.py` (Priyansh's cross-check) + `ces_eligibility.py` (Honghao's reconstructed real script, see docs/data-pipeline/) |
| `backend/statistics/` | Moe Tanaka | ✅ | `eligibility.py`, matching Moe's real, locked spec in `weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md` |
| `backend/slm/prompts/` | Richard Zhao | ✅ | `model_manifest.yaml`, `generic_fallback.yaml`, `crisis_aware.yaml` (crisis content still placeholder, flagged) |
| `backend/privacy/` | Yuktha Naveen | ⚠️ structural mismatch | Her real work landed at top-level `privacy/` and `benchmarks/`, not `backend/privacy/` — noted in `docs/privacy/README.md`, not silently relocated |
| `backend/evaluation/` | Chonghao Shen | ✅ | `evaluation_plan_v0.1.md` (his real Week 4 plan, provisional) |
| `backend/api/` | Priyansh Khandelwal | Empty by design | Merge boundary — populated once enough of the other roles' contracts exist |
| `backend/db.py` | Whoever needs sqlite | Not yet present | No code needs it yet; `tests/test_repo_structure_cross_references.py` checks nothing else imports `sqlite3` in the meantime |
| `frontend/` | Sheng Wang | ✅ | Real Vite+React+TS scaffold, builds clean (`npm run build`) |
| `tests/` | Mirrors `backend/` | ✅ | 91+ tests across contracts/statistics/slm/privacy/evaluation |
| `dataset/` | gitignored | ✅ (correctly excluded) | Confirmed not committed |
| `.pre-commit-config.yaml` | Ruff | ✅ | Present, not yet verified in CI (no CI workflow exists yet) |

**Still missing entirely:** a CI workflow file (referenced implicitly by
`skills/*.md` and the pre-commit config, but no `.github/workflows/*.yml`
exists) — flagged here since it's a real gap in the skeleton, not
something either AI pass built.

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

## GitHub branch-protection setup (for whoever has admin access)

Cannot be done from this environment — these are GitHub web UI settings,
not files (this Week 4 pass itself pushed directly to `main` twice, which
branch protection would have blocked and forced through a PR instead — a
concrete reason to set this up, not just a hygiene suggestion). Full
step-by-step: **[`docs/github-branch-protection-setup.md`](github-branch-protection-setup.md)**
— under 2 minutes to follow.

## Files added toward the skeleton

See the top-level Week 4 status report for the full list; the short version
is a `README.md` placeholder in each otherwise-empty folder explaining what
belongs there and who owns it, so an empty directory in git isn't just a
mystery to whoever opens the repo next.
