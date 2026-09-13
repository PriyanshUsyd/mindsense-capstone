# Provenance note — `docs/proposal/CS62_Group_Proposal.pdf`

**Status:** committed to this repository (`2807f62`, "Add original
CS62_Group_Proposal.pdf alongside its markdown conversion"), authored under
`PriyanshUsyd`'s git identity, `Co-Authored-By: Claude Sonnet 5` — this file
was never falsely attributed to Honglin Lu at the git level. This note
records the real-world context behind it, which the commit message alone
didn't carry.

## What actually happened, per team communication

Per Priyansh's account of team coordination (OneDrive + WhatsApp, outside
GitHub — Honglin does her writing there, not in this repo): the final,
submitted Group Proposal was compiled and organized by Honglin Lu through
that out-of-GitHub process — she coordinated section reviews with the team
and produced the final formatted document. Priyansh added the resulting PDF
to this repository afterward, since she works outside GitHub and the repo
needed a copy of the actual submitted artifact. This note itself is not an
independent verification of that OneDrive/WhatsApp process (no access to
either from this environment) — it records what was reported, the same way
this repo already records other out-of-GitHub team coordination (e.g.
`freeze-decision.md`'s WhatsApp-agreement record).

**Byte-identity check performed 2026-09-13:** a separately-supplied copy of
this same PDF (placed at the repo root, described as sourced fresh from
Honglin's OneDrive) was compared against this committed file and found
**byte-for-byte identical** (SHA-256
`e0fd4c21e1e47c3cb795b3f7f532b7be1d397bd101594ebc3bc8c2a51ef2a6c4`). That
confirms this committed copy is the real, final submitted document — not a
stand-in or an earlier draft — but it is not new evidence beyond what
`2807f62` already established, since the two files are identical.

## Relationship to Honglin's real 704-line draft (`243d286`, unmerged)

`243d286` on branch `HonglinLu722-patch-1` (`docs/proposal/Group
Proposal.md`, 704 lines, genuine GitHub-web commit by Honglin) is **not**
an earlier or divergent version of this PDF — it is structurally a
different document entirely: 11 top-level sections (Introduction and
Problem Statement, Dataset and Data Preparation, Proposed System
Architecture, Statistical Approach, SLM Integration and Safety, Privacy and
Security Architecture, Evaluation Plan, Conversational Interface, Project
Timeline/Risks/Outcomes, AI Acknowledgement, References) versus the
submitted PDF's 8 (Introduction, Related Literature, Project Problems,
Methodologies, Resources, Expected Outcomes, Milestones/Schedule, AI
Acknowledgement), with different prose throughout.

Per team communication: `243d286` was Honglin's **early-stage draft**,
later reorganized into the final 8-section structure through the team's
OneDrive review process — not abandoned or ignored. This repository has no
independent way to verify the OneDrive review process itself; it can only
confirm what's stated here: the early draft exists (`243d286`), the final
structure exists (this PDF, and its markdown reconciliation at
`docs/proposal/Group Proposal.md` on `main`, commit `bc788fa3`), and the
two differ in exactly the way a substantial reorganization would produce.

## What's still unresolved

- `243d286` itself remains on an unmerged branch (`HonglinLu722-patch-1`),
  so it currently gets no visibility from `main` even as "superseded early
  draft" context — worth a pointer from `main` if anyone wants the history
  preserved.
- `dc620fb8` and `bc788fa3` remain in history as `Author: Honglin Lu`,
  actually written by Priyansh — a known, disclosed discrepancy (see
  `docs/proposal/ai-acknowledgement.md` and this repo's own audit trail),
  not resolved by this note and not rewritten, per the standing decision
  not to rewrite shared git history this late.
