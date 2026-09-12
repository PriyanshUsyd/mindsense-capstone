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
| Phone-unlock feature (`unlock_num_ep_0`) | **Updated 2026-09-12 — now real, end-to-end.** As of this date, `backend/data_pipeline/cleaning.py::clean_unlock_frequency` + `backend/data_pipeline/unlock_frequency_feature.py` clean it, and `backend/statistics/mixed_effects_model.py` fits it via the same `build_model_frame`/`fit_mixed_effects_model`/`fit_ar1_effect` path GPS uses (`backend/statistics/run_tier1_evidence.py` runs both together against the real dataset). **This closes the gap this document previously described** ("not implemented... only a named example"), which is now stale as of that fix — see the commit "Wire unlock_frequency into backend statistics, same as GPS distance." **Still flagged for Moe Tanaka's sign-off**, unlike GPS: unlock's cleaning thresholds (no quality gate available; `log(mean + 1)` transform) are a methodology port from the one prior standalone implementation, not a spec Week 4/5 ever locked concrete numbers for — see `clean_unlock_frequency`'s docstring. Per-person evidence classification (Section 7) for either feature still requires the R engine, which this sandbox does not have installed, so it has only been exercised via a dependency-injected fake in tests — see `backend/statistics/evidence.py::bootstrap_person_slopes`'s docstring. |
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
[the signed-off feature list] is Tier 2/stretch." This section originally
presented the team with a choice between freezing at one feature or
extending the freeze until `unlock_num_ep_0` was really wired in — as of
2026-09-12 that wiring exists (see the table above), so the "freeze at one
feature" option is moot. What is still genuinely open, and still not this
document's call to make:

1. **Statistical sign-off.** Unlike GPS, unlock's cleaning thresholds were
   never locked in the Week 4/5 deliverables — the implementation ported
   the one prior standalone version rather than inventing numbers, but
   Moe Tanaka still needs to confirm or override the specific choices
   (no quality gate available; the `log(mean + 1)` transform offset).
2. **Per-person evidence for either feature** still degrades safely to
   "insufficient" for everyone in an environment without R installed —
   this sandbox included — regardless of which Tier-1 feature is in
   question; that isn't specific to unlock.

Given both of the above, "frozen" should currently be read as "both
Tier-1 features are really wired into the same pipeline," not yet as
"both are statistically finalised and ready to report."

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
