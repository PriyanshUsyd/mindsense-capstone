# AI Acknowledgement Statement

**STATUS: DRAFT for team review — not final.** Written 2026-09-05 from the
repository's actual git history and commit authorship (`git log --all`), not
from a generic template. Every specific claim below can be checked against
the commit hashes cited. Please read, correct anything inaccurate or
uncomfortable, and edit before this goes into the Group Proposal Report —
this is a first pass, not a statement anyone has signed off on.

## Summary

AI assistance (Claude, via Claude Code) was used extensively on this project
by Priyansh Khandelwal (Integration & QA Lead), across three distinct kinds
of work, and to a much smaller degree referenced in commit messages by other
teammates. This statement describes what the AI did, what it did not do, and
where its output was later replaced by a teammate's own real work.

## What the AI did

**1. Filling gaps left by missing teammate work (Week 4).** As of
2026-08-29, only two of eight roles (Yuktha Naveen, and partially Moe Tanaka)
had pushed any repository work. Commit `d24c55e` ("Fill Week 4 gaps for 6 of
8 roles") used AI assistance to draft placeholder deliverables for the other
six roles — data-pipeline verification scaffolding, statistics constants,
SLM prompt templates, a frontend design doc and scaffold, an evaluation
taxonomy/held-out set, and initial docs — so the team had something
functional to build on rather than an empty repository at the Week 4
deadline. These were always labelled as AI/placeholder work in the code and
commit history, not attributed to the named role owner.

**2. Reconciling AI placeholders with real teammate work as it arrived.**
As real branches were pushed, commits `40bbf00` (Moe's real statistics
work), `b5c0e13` (Yuktha's real privacy work), and `2e8e48c` (Chonghao's real
evaluation plan) used AI assistance to merge each person's actual
contribution in and remove or supersede the corresponding AI placeholder.
Commit `24809a1` did a further reconciliation pass. Two roles' work was
never received and their AI-authored placeholders were never replaced:
**Sheng Wang** (UI — no commit from Sheng exists anywhere in this
repository's history) and **Honglin Lu** (Documentation — no commit from
Honglin exists anywhere either; the `honglin/docs-week4` branch turned out
to be a duplicate of Yuktha's branch, not separate work). This is stated
here plainly because an AI Acknowledgement statement is exactly where that
kind of gap belongs, not somewhere it gets rounded up to "Complete."

**3. Independent cross-checks and verification (Weeks 4-5).** The CES
dataset re-verification script (`backend/data_pipeline/verify_ces.py`) was
built with AI assistance by Priyansh specifically as an independent
cross-check against Honghao's reported 97.3%-eligible figure — reported in
chat, with no supporting artifact in the repo at the time. `ces_eligibility.py`
was similarly AI-assisted, built to reproduce that figure from a real,
justified threshold rather than an arbitrary one. This week's privacy fix
(commit `0df66f6`), the GPS-distance feature builder and cleaning module
implementing Moe Tanaka's locked spec (commit `ffc9945`), and the
mixed-effects model fit wired to it (commit `6c9a8b8`) were built the same
way: AI-assisted implementation of a real teammate's own written
specification, run against the real dataset, not invented from scratch.

**4. Code scaffolding, testing, and verification passes more generally.**
Across Weeks 4-5, AI assistance was used for: writing test suites (the
majority of this repository's ~300 tests), running and re-verifying test
suites and dataset checksums, drafting documentation (including this
statement, and status docs — see the caveat below), and multi-branch
merge/verification work (checking real teammate branches against the
project's own technical skill files before merging them into `main`).

## What the AI did not do

- It did not fabricate the 97.3% eligibility figure, Chonghao's reported
  6/6 / 14/14 / 2/2 evaluation results, or any other numeric claim in this
  project — every such figure was either independently reproduced by
  running real code against real data, or is explicitly attributed to the
  teammate who reported it, with the AI's role limited to verification.
- It did not make the statistical, safety, or product decisions in this
  project — the named statistical model, the safety-gate rules, the
  pass-threshold lock, and the feature list were all decisions made (or, in
  the two flagged cases above, not yet made) by the named human role owner.
- It has not (as of this writing) resolved the specific gaps this statement
  names — Sheng Wang's and Honglin Lu's missing contributions remain
  missing; this document reports that fact rather than fixing it, since
  that is a team/process decision, not an AI one.

## A caveat about this document's own limits

Several earlier status documents in this repository (e.g.
`docs/week4-milestone-status.md`) were also AI-assisted and, on later
re-verification, were found to mark some tasks "Complete" in ways that
didn't hold up against the repository's own evidence — see Task 7 of the
2026-09-05 verification pass for the specific corrections made. This
statement should not be read as immune to the same risk: it is a best
current effort at an honest accounting, offered for the team to check, not
a final or infallible one.

## Attribution by teammate

Per real, verified git history (`git log --all --format='%an'`):

| Person | Real commits in this repo | AI-assisted work attributed to them |
|---|---:|---|
| Priyansh Khandelwal | 18 | All of Priyansh's own commits used AI assistance (Claude Code) as described above; explicitly disclosed in each commit message. |
| Richard Zhao | 13 | Real, independent commits (SLM Week 4 + Week 5). Several of his own commit messages/docs (e.g. `docs/slm/week5-integration-evaluation-handoff.md`) note his own use of AI tooling in places; not independently re-verified by this statement. |
| Chonghao Shen | 3 | Real, independent commits (evaluation plan, Week 5 review). |
| Yuktha Naveen | 3 | Real, independent commits (privacy architecture, benchmark). |
| Moe Tanaka | 1 | One real, independent commit (Week 4 statistics deliverable). |
| Honghao Li | 0 | No commit from Honghao exists anywhere in this repository. |
| Sheng Wang | 0 | No commit from Sheng exists anywhere in this repository. |
| Honglin Lu | 0 | No commit from Honglin exists anywhere in this repository. |

*Please review and edit this before it goes into the Group Proposal Report
— in particular, confirm this table is comfortable for everyone named in
it, and correct anything about your own AI usage that this document has
wrong or missed.*
