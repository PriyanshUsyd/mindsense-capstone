# Bootstrap SE Caching — Week 7 Design Scope

**Decision author:** Moe Tanaka (Statistical Analysis Lead).
**Committed by:** Priyansh Khandelwal, on Moe's behalf.

**Provenance note:** these decisions were relayed by Moe Tanaka to Priyansh
Khandelwal over WhatsApp on 2026-09-20. They were not written directly to
GitHub by Moe herself, and this document is not a commit made by her — it
is Priyansh's transcription of what she said, committed so the scope has a
real record instead of living only in a chat thread. Any correction to
what's recorded here should come from Moe directly.

> **Correction, 2026-10-07 (Moe Tanaka).** The "Context" section below and
> steps 1, 2 and 4 of the "Week 8 plan" were written on the premise that the
> existing 23/214 intersection came from the `lme4` fit and would shift under
> AR(1). **That premise is wrong.** `extract_person_slopes` builds each
> `slope_i` from `fit_ar1_effect`, so the per-person BLUPs behind 23/214 were
> `nlme::lme` + `corAR1` from the start, and both bootstrap estimators refit
> through the same `nlme` path (`lme4` is only the sensitivity fit). The B=500
> run was checked against the current primary specification on every point
> that matters and nothing differs (`docs/statistics/week7-calibration-concerns.md`
> item 3); commit `4af4d7a` ("AR(1) as primary") changed documents only. The
> text is left as originally relayed so the record of what was said is intact;
> read it with this correction applied. The rerun is still being done, but for
> a different reason: the 2026-09-13 run came from an uncommitted working tree,
> so no fingerprint can describe it, and the cache needs a run whose code state
> is known (week7 item 2, decision b and its implementation status). Decisions
> a–d of that item are the answers to the four open points below.

## Context: why this is entangled with the AR(1)/lme4 recalculation *(premise corrected — see above)*

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

## Week 8 plan (as she described it) *(steps 1, 2 and 4 superseded — see correction above)*

1. Rerun both bootstrap methods (parametric and cluster) on the AR(1) fit.
   *(Superseded: the existing run already is the AR(1) fit. Rerun instead on
   committed code, to obtain a result a fingerprint can describe, and compare
   it with the archived 2026-09-13 data as a reproducibility check.)*
2. Recompute the cross-method intersection against the AR(1)-based
   per-person BLUPs. *(Superseded: same reason; the intersection is
   recomputed from the rerun as part of building the cache, not because the
   classification is expected to shift.)*
3. Land the cache (per whatever the Week 7 design settles on).
4. Update `Week5_Statistical_Analysis_Deliverable.md` and
   `docs/statistics/preregistration.md` to reflect the AR(1)-based numbers.
   *(Superseded: there are no "AR(1)-based numbers" distinct from the
   current ones; documents change only if the rerun disagrees with 23/214.)*
