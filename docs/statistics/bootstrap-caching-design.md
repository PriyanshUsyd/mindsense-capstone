# Bootstrap SE Caching — Week 7 Design Scope

**Decision author:** Moe Tanaka (Statistical Analysis Lead).
**Committed by:** Priyansh Khandelwal, on Moe's behalf.

**Provenance note:** these decisions were relayed by Moe Tanaka to Priyansh
Khandelwal over WhatsApp on 2026-09-20. They were not written directly to
GitHub by Moe herself, and this document is not a commit made by her — it
is Priyansh's transcription of what she said, committed so the scope has a
real record instead of living only in a chat thread. Any correction to
what's recorded here should come from Moe directly.

## Context: why this is entangled with the AR(1)/lme4 recalculation

The existing 23/214 cross-method intersection (see
`docs/statistics/preregistration.md`) was computed against the `lme4` fit,
from before AR(1) became the primary model. Per-person β_W (within-person
slope) differs by 34% between the `lme4` and AR(1) fits. Because per-person
BLUPs are derived from β_W, the classification of which of the 214-person
cohort clears the bootstrap SE gate shifts under AR(1) — Moe expects the
intersection to still land at fewer than 23, but says she doesn't know the
actual number without rerunning the bootstrap under the AR(1) fit.

Her point: caching and rerunning are one job, not two. There is no value in
designing a cache around bootstrap SE figures that are about to be replaced
by the AR(1) rerun — the cache should be built for the numbers Week 8
produces, not the current (lme4-era) ones.

## Week 7 scope: design only

Per the project plan, Week 7 is design-only for this piece — no rerun, no
cache implementation yet. Moe named four things to settle this week:

1. Where the cached bootstrap SE output lives.
2. How `tier1_runner` reads that cached output without triggering a live
   30–40 minute bootstrap run.
3. What invalidates a cached result.
4. Whether a stale cache fails closed or warns.

**Status: not yet answered.** Moe's message states *that* these four
things need deciding this week, but does not give the specific answers to
any of them. This document does **not** invent a file path, an
invalidation rule, or a fail-closed/warn choice on her behalf — those four
points are still open and need to be confirmed with her directly before
anything is implemented against them. Treat any specific technical answer
to (1)–(4) that appears elsewhere as unconfirmed until it traces back to
her.

## Week 8 plan (as she described it)

1. Rerun both bootstrap methods (parametric and cluster) on the AR(1) fit.
2. Recompute the cross-method intersection against the AR(1)-based
   per-person BLUPs.
3. Land the cache (per whatever the Week 7 design settles on).
4. Update `Week5_Statistical_Analysis_Deliverable.md` and
   `docs/statistics/preregistration.md` to reflect the AR(1)-based numbers.
