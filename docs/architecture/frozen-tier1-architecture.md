# Week 6 — Frozen Tier 1 Architecture

> **DRAFT — prepared for Honglin Lu's review, not yet reviewed or approved by her.**
> This document was drafted on her behalf because no Week 6 deliverable of
> hers exists in the repository — the only related Week 6 activity found is
> edits Moe Tanaka made directly to the Week 5 proposal document (not new
> architecture documentation). It is based on the repository's real, current
> state as of 2026-09-12, not a generic template. Please correct, replace, or
> reject anything below.

**Weekly_Plan.md's Week 6 task (Documentation & Report Lead):** "Update
documentation to reflect the frozen Tier 1 architecture."

---

## 1. What "frozen" actually means here, honestly

Weekly_Plan.md's Week 6 goal was: both Tier 1 features built and fully
working, both fallback UI states built. Based on the real repository state,
**this is only partially true**, and this document says so plainly rather
than rounding it up:

| Component | Status |
|---|---|
| GPS distance feature (`gps_distance`) | **Real, end-to-end.** Cleaning (`backend/data_pipeline/cleaning.py`), trailing-window predictor and model fit (`backend/statistics/mixed_effects_model.py`), tested against the real CES dataset. |
| Phone-unlock feature (`unlock_count`) | **Not implemented.** It exists only as a *named example* in `backend/contracts/evidence.py`'s docstring and in SLM prompt templates (`backend/slm/prompts/evidence_explainer.yaml`) — there is no `backend/data_pipeline/` cleaning module or `backend/statistics/` model wiring for it anywhere in the repository. The "2-feature Tier 1 set" the plan describes is, in working code, a 1-feature set with a second feature's *name* wired into the contract and prompt layer ahead of the data actually existing. |
| Cold-start / three-state eligibility | **Real.** `backend/statistics/eligibility.py` implements State A/B/C per the locked Week 4 spec, wired to the evidence contract's `EligibilityStatus` enum. |
| Both fallback UI states | **Real.** `frontend/src/features/chat/` has distinct components for cold-start, insufficient-data, refusal, and generic/crisis fallback (built across Sheng Wang's Week 5 and Week 6 PRs). |
| Off-topic / out-of-scope request routing | **Real**, added Week 6: `backend/statistics` — actually `backend/slm/request_policy.py` — gained a real `RequestCategory.OFF_TOPIC` classifier (Richard Zhao, PR #15, merged 2026-09-12), not just a prompt-text change. |
| SLM response health-check | **Real**, added Week 6: `backend/slm/response_health.py`. |

## 2. System architecture as it actually runs today

```
CES sensing CSVs (dataset/, gitignored)
        |
        v
backend/data_pipeline/cleaning.py           <- quality gate (12h), implausibility
  clean_gps_distance()                          filter, per-person winsorisation
        |
        v
backend/statistics/mixed_effects_model.py    <- trailing 14-day window (ends the
  build_model_frame() / fit_mixed_effects_       day BEFORE assessment), log(mean)
  model() / fit_ar1_effect()                     transform, person-mean-centred
        |                                        within/between terms, R-backed
        |                                        Satterthwaite df + AR(1)+BLUPs
        v                                        (Python fallback if R unavailable)
backend/statistics/eligibility.py            <- three-state cold-start gate
  classify_state() -> ColdStartState             (State A/B/C, per Week 4 spec)
        |
        v
backend/contracts/evidence.py                <- EvidencePacket (frozen contract,
  EvidencePacket / PersonalBaseline /             v1.0.0, tag contract-v1.0.0)
  StatisticalEvidence
        |
        v
backend/slm/service.py + request_policy.py   <- off-topic/prohibited/crisis
  + safety_gate.py                                routing, schema-constrained
                                                    draft, second safety check
        |
        v
frontend/src/features/chat/                  <- normal / cold-start /
                                                    insufficient-data / refusal /
                                                    fallback / crisis UI states
```

This diagram reflects what is actually wired together in the current
codebase (confirmed by reading the files, not inferred from the plan or from
commit messages) — not an aspirational version.

## 3. What "frozen" should mean going forward

Per Weekly_Plan.md, Week 6 was meant to be a hard freeze: "Anything beyond
[the signed-off feature list] is Tier 2/stretch." Given the unlock_count gap
above, a literal reading of "frozen Tier 1 architecture" as two working
features is not yet accurate. Two honest options, for the team (not this
document) to decide:

1. **Freeze at one feature.** Treat `gps_distance` as the sole Tier 1
   feature actually delivered, and move `unlock_count` explicitly to Tier 2 /
   a documented stretch goal — updating `build-reference.md`'s "hard cap:
   maximum 2 cross-platform features" language and the evaluation criteria
   that assume two features accordingly.
2. **Extend the freeze.** Treat the freeze as not yet actually reached, and
   assign someone to build `unlock_count`'s cleaning + statistics wiring
   before calling Tier 1 frozen.

This document does not make that call — it surfaces the gap so the team can.

## 4. Per-role documentation this doc does NOT replace

This is an architecture summary, not a replacement for role-owned docs,
which should still be the source of truth for their own areas:

- `backend/statistics/mixed_effects_model.py`'s own module docstring (the
  fullest, most current account of the statistics engine, including its
  known approximations and the 2026-09-12 fixes).
- `docs/slm/week6-integration-report.md` (Richard Zhao's Week 6 SLM record).
- `analysis/archive/README.md` (what was retired from `analysis/` and why).
- `CLAUDE.md`'s "Finalised decisions" (the authoritative list of locked
  statistical parameters).

## 5. What's still needed

- The Tier 1 scope decision in Section 3.
- Honglin's own pass over this document's accuracy and tone before it is
  treated as the team's official Week 6 architecture record.
