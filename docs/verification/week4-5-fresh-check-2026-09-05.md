# Week 4/5 Fresh Verification Check — 2026-09-05

This is an audit record of a from-scratch verification of the team's Week 4 and
Week 5 work, checked against `Weekly_Plan.md`. It does not rely on any earlier
session's findings — every claim below was re-derived from `git fetch --all`,
branch/commit inspection, diffs, and a full test run on 2026-09-05.

This is **not** the Group Proposal Report (that stays on OneDrive). This is an
internal integrity record: who actually authored what, what's genuinely done,
and what's still outstanding, with commit hashes for anyone who wants to check
the claims themselves.

## Method

1. `git fetch --all` (never trust local branches alone — see the team's Friday
   push cadence convention).
2. `git branch -a`, `git log --oneline --graph --all`, and `git log <branch>
   --format='%an %s'` for every remote branch, to see who actually authored
   each commit — not just whether a branch with a person's name exists.
3. For every one of the 8 roles: does a personal branch exist, is its content
   genuinely self-authored, and is it already merged into `main`? Cross-checked
   against each person's exact Week 4 and Week 5 task line in `Weekly_Plan.md`.
4. `python -m pytest -q`, held-out set checksum, `git diff main origin/main`.

## Headline finding

Commit messages in this repo routinely assert real authorship for people who
never actually committed the work ("Honghao's now-real, working script",
"Moe's mixed-effects model fitting", Sheng Wang's UI states) when `git log
--format='%an'` shows the actual author is Priyansh. Three of eight roles have
**zero self-authored commits anywhere in this repository's history**, under
any name. One role (Honghao) turned out to have real work under a git
identity (`AllenLi845`) that doesn't match his name — worth noting so this
isn't mistaken for "no work" in a future check.

## Per-person, per-week findings

### Honghao Li — Data Pipeline Lead
Git identity: `AllenLi845 <nddjthd@gmail.com>` — no branch, pushed straight to
`main`, bypassing PR review (`f30fce5`, parent `7cd6db0`).

- **Week 4 — Done.** `scripts/validate_ces.py` (552 lines) and
  `docs/data-pipeline/dataset_validation_CES.md`, real CES re-verification
  work, self-authored (`f30fce5`, 2026-08-27; renamed in `3c720ca`). Priyansh
  only fixed a path bug so it would run against this repo's dataset layout
  (`d5406a3`).
- **Week 5 — Not done.** `backend/data_pipeline/gps_distance_feature.py` and
  `backend/data_pipeline/ces_eligibility.py` have no commit by
  Honghao/AllenLi845 anywhere — both are 100% Priyansh-authored (`634866c`,
  `67ec7ba`, `1e0bae8`), despite commit messages describing them as his. No
  real end-to-end GPS feature build from him this week.

### Moe Tanaka — Statistical Analysis Lead
Git identity: `tanaka <moe.tnk0402@gmail.com>`.

- **Week 4 — Done.** `origin/moet/week4_statistical_analysis` (`8eb4ca5`),
  self-authored, real 498-line deliverable naming the exact model (mixed
  effects, person-level random intercepts, person-mean-centred predictors),
  baseline window, and three-state cold-start policy.
- **Week 5 — Not done.** No Week 5 branch or commit from Moe exists anywhere.
  `backend/statistics/mixed_effects_model.py`, wired to the GPS feature, is
  entirely Priyansh-authored (`67ec7ba`, `634866c`), despite being described
  as "Moe's mixed-effects model fitting."

### Richard Zhao — SLM Integration Lead
Git identity: `T3MPOR4RY <rzha0623@uni.sydney.edu.au>` — same university
email pattern as his likely real account; `T3MPOR4RY` looks like a leftover
placeholder git username he never fixed, not a fake account.

- **Week 4 — Done.** `origin/Rz` (`be5ba89`..`7d33de4`), self-pushed, 26 files
  / 2498 lines including the safety gate, SLM client, prompts, and tests.
  Merged via `79a673d`.
- **Week 5 — Done.** `origin/Rz-week5` (`22b4616`..`49dc73e`), self-pushed, 60
  files / ~21.5k lines including output grounding, request policy, shadow
  build, benchmarks, and tests. Merged via `9c2d317`.
- Flag: the git username `T3MPOR4RY` should be fixed — it's currently
  indistinguishable from a bot/placeholder account in `git log`.

### Sheng Wang — Conversational Interface Lead
- **Week 4 — Not done.** No branch, no commit, ever, under any name.
- **Week 5 — Not done.** `frontend/src/features/chat/NormalResponse.tsx` and
  all of `frontend/` are 100% Priyansh-authored (`c28d05a`), whose own commit
  message is explicit: "Fill in Sheng Wang's missing Week 4/5 UI work (both
  weeks, still no commit from him)."

### Yuktha Naveen — Privacy & Security Lead
Git identities: `ynav0325@uni.sydney.edu.au`, `yukthanaveen2000@gmail.com`.

- **Week 4 — Done.** `origin/yuktha/privacy-week4`, self-pushed, real
  (privacy architecture principles, latency benchmark, dependency audit).
  Note: this content landed via a branch named `honglin/docs-week4`, not a
  branch of her own — mislabeled, but the content is genuinely hers.
- **Week 5 — Done.** `origin/yuktha/privacy-week5`, self-pushed, including
  the two most recent commits on `main` (`82d9c14` SLM dependency review
  sign-off, `67cda0e` AI-disclosure cleanup). The most complete and reliably
  self-authored contributor across both weeks.

### Chonghao Shen — Evaluation Design Lead
Git identity: `lostice0129 <cshe0343@uni.sydney.edu.au>`.

- **Week 4 — Mostly done.** `origin/chonghao/evaluation-week4` (`3c2f9ee`),
  self-authored `evaluation_plan_v0.1.md` genuinely covers the frozen
  taxonomy and points to the pass-threshold rule. The held-out set,
  participant information sheet, and crisis-response script that also
  satisfy this week's task are Priyansh fills (`40ccdf6`, `d24c55e`), not
  Chonghao's own commits.
- **Week 5 — Done.** `origin/chonghao/evaluation-week5` (`fd7765e`,
  `d45ce82`), self-authored: rubric v0.1, development review, proposal
  contribution, and a real test. Merged via `7cd6db0`.

### Honglin Lu — Documentation & Report Lead
- **Week 4 — Not done.** Zero commits under any name/handle across the
  entire repository history. The branch named `honglin/docs-week4` contains
  no docs-lead work at all — it is actually Yuktha's Week 4 privacy/latency
  deliverables, mislabeled. The repo skeleton, branch-protection doc, and
  proposal outline that exist on `main` are all Priyansh fills (`d24c55e`,
  `33247f4`).
- **Week 5 — Not done.** No compiled Group Proposal Report exists in this
  repository — only `docs/proposal/outline.md`, a Priyansh-authored scaffold
  (`d24c55e`), not the report itself. The report is tracked separately on
  OneDrive.

### Priyansh Khandelwal — Integration & QA Lead
Both weeks: Done (self-evident from authorship of essentially every fill-in
commit referenced above, plus the Integration/QA-specific tasks: evidence
contract freeze, Tier 1 feature-list sign-off, PR review/merge).

## Re-verification (2026-09-05)

- `python -m pytest -q` → **308 passed**, 0 failed (16 benign `statsmodels`
  convergence warnings, unrelated to correctness).
- Held-out set checksum (`tests/evaluation/held_out/held_out_prompts.sha256`)
  matches a freshly computed SHA-256 of `held_out_prompts.json` — unchanged.
- `git diff main origin/main` → empty after fast-forwarding local `main` to
  `origin/main` (two commits, `82d9c14` and `67cda0e`, had not yet been
  fetched locally).
- Branch protection on `main` and PR `merged:true` status could not be
  verified in this environment: no `gh` CLI and no `GITHUB_TOKEN` were
  available, and an unauthenticated call to the GitHub branch-protection API
  returned 401. This is a genuine tooling gap, not a "confirmed passing"
  result — treat branch protection as unverified until checked with
  authenticated access.

## What this means going forward

The false-authorship pattern in commit messages and docstrings (Honghao's
and Moe's Week 5 work, Sheng's UI) is addressed directly in
`backend/data_pipeline/gps_distance_feature.py`,
`backend/data_pipeline/ces_eligibility.py`,
`backend/statistics/mixed_effects_model.py`, and
`frontend/src/features/chat/NormalResponse.tsx` in the commit that
accompanies this report — those docstrings now describe what the code does
against `Weekly_Plan.md`, without asserting a specific person wrote it.

The functional gaps (Honghao's Week 5 GPS feature, Moe's Week 5
implementation, Sheng's UI in both weeks, Honglin's docs in both weeks,
Chonghao's Week 4 held-out set/info sheet/crisis script) are not fixed by
this change — they are attribution corrections only. Whether or how those
gaps get closed is a team decision, not something this record makes for them.
