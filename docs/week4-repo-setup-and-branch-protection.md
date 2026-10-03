# Week 4 — Repository Setup, Branch Protection & Skeleton

> **DRAFT — prepared for Honglin Lu's review, not yet reviewed or approved by her.**
> This document was drafted on her behalf because no Week 4 deliverable of hers
> exists in the repository (her Week 4 branch, `honglin/docs-week4`, was
> byte-identical to `yuktha/privacy-week4` — no separate content). It is based
> on the repository's real, current state, not a generic template. Please
> correct, replace, or reject anything below.

**Weekly_Plan.md's Week 4 task (Documentation & Report Lead):** "Set up the
GitHub repo, branch protection, and skeleton per the repository structure in
`build-reference.md`. Begin the Proposal outline."

---

## 1. Repository setup — what actually exists

The repository (`PriyanshUsyd/mindsense-capstone` on GitHub, public) exists
and is in active use — 22 branches at last count, 15 merged pull requests as
of Week 6. It is **owned by Priyansh Khandelwal's GitHub account**, not a
shared team or organisation account. If this wasn't a deliberate choice, it's
worth the team confirming who should hold admin rights on it (repo transfer,
or adding the team as explicit collaborators/an org), since whoever owns the
account controls branch-protection settings, secrets, and who can be added.

## 2. Skeleton — matches `build-reference.md` Section 8

The repository's actual current top-level layout matches the structure
`build-reference.md` specifies (Section 8, "Repository Structure"):

```
mindsense-capstone/
  docs/                       Documentation Lead
  backend/
    contracts/                Shared evidence contract
    data_pipeline/             Data Pipeline Lead
    statistics/                 Statistical Analysis Lead
    slm/                         SLM Integration Lead
      prompts/                    YAML prompt templates, versioned in git
    privacy/                     Privacy & Security Lead
    evaluation/                   Evaluation Design Lead
    api/                          Integration & QA Lead (merge boundary)
  frontend/
    src/
      api/                        generated types + fetch wrapper
      components/
      features/chat/
  tests/                      Mirrors backend/ structure
  analysis/                   Statistical Analysis Lead's own working pipeline
                                (partly archived 2026-09-12 — see
                                analysis/archive/README.md)
  dataset/                    CES CSVs — gitignored, never committed
  benchmarks/                 SLM/guardrail benchmark scripts + result JSONs
```

The `contracts/`-only cross-role communication rule from Section 8 (no role
edits another role's internal code directly) has held up in practice — every
merged PR so far respects that boundary.

## 3. Branch protection — could not be verified from the repository alone

**This is the one part of the Week 4 task this document cannot confirm.**
GitHub branch-protection rules (required reviews, status checks, no
force-push to `main`, etc.) are a repository *setting*, not something that
shows up in a commit or in the file tree — they can only be checked by
someone with admin access opening the repo's Settings → Branches page (or
via `gh api repos/.../branches/main/protection`, which needs an
authenticated `gh` session this environment does not have).

Given the number of direct-to-main commits visible in the git history
(`PriyanshUsyd` has pushed directly to `main` repeatedly, not always through
a PR), it seems unlikely that a "no direct pushes, PR + review required"
rule is currently active on `main` — but this is an inference from behaviour,
not a confirmed setting. **Whoever has admin access should check this
directly and record the actual answer here**, replacing this paragraph.

## 4. Proposal outline

A `docs/proposal/outline.md` already exists in the repository (added
2026-08-29, as part of an AI-assisted gap-fill when no team member had yet
pushed a Week 4 documentation deliverable — see
`docs/proposal/ai-acknowledgement.md`). It has not been superseded by a
version from Honglin. The full Group Proposal Report itself was later
compiled separately (see `docs/proposal/Group Proposal.md`, reconciled
2026-09-12 against the submitted PDF). Honglin should review whether
`outline.md` is still worth keeping as a standalone artifact now that the
full proposal exists, or whether it should be archived/removed to avoid two
documents describing the same plan.

## 5. What's still missing / needs a real owner

- Confirmation of actual branch-protection settings (Section 3 above).
- A decision on repository ownership/admin access (Section 1 above).
- Honglin's own review of whether `docs/proposal/outline.md` should stay,
  be updated, or be retired now that the full proposal is reconciled.
