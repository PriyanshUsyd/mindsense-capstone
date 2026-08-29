# Group Proposal Report — Outline (DRAFT)

**Status: DRAFT, built to fill a Week 4 gap on 2026-08-29** (Weekly_Plan.md:
"Begin the Proposal outline" — Honglin Lu, Docs & Report Lead). Due Week 5
(Sep 6). This is a skeleton to work from, not content — Honglin owns the
actual writing.

## Proposed sections

1. **Introduction & Problem Statement**
   - The client (Tianyi Zhang) and coordinators (Sara Mumtaz, Dr Muhammad
     Farhan) — see `Client_Specs.md`.
   - Why digital phenotyping + a local SLM, framed around the client's
     actual spec, not a generic pitch.

2. **Dataset**
   - CES, why it was chosen over the client's WHO-5 example (PHQ-4
     substitution — `build-reference.md` Section 2), platform split caveat,
     locked 2-feature Tier 1 set and why (`build-reference.md` Section 2).
   - Reference the independent re-verification:
     `docs/data-pipeline/ces-reverification.md`.

3. **System Architecture**
   - The 8-role structure and how contracts (not direct cross-role imports)
     keep the team's work independent — `build-reference.md` Section 8.
   - Evidence contract as the load-bearing interface between Statistics and
     SLM: `backend/contracts/evidence.py`.
   - Locked technology stack table — `build-reference.md` Section 3.

4. **Statistical Approach**
   - The mixed-effects model, person-mean-centring, eligibility rule,
     three-state cold-start policy —
     `docs/statistics/model-and-coldstart-spec.md`.

5. **SLM Integration & Safety**
   - Ollama + phi4-mini:3.8b, schema-constrained generation, the claim
     policy, the two fallback templates, the deterministic safety gate —
     `skills/slm-ollama.md`, `backend/slm/`.

6. **Privacy Architecture**
   - What "nothing leaves the device" means precisely —
     `docs/privacy/architecture-principles.md`.

7. **Evaluation Plan**
   - The client's 10 named criteria (`build-reference.md` Section 9), the
     adversarial taxonomy and pre-registered threshold, the held-out set
     discipline — `docs/evaluation/`.

8. **Timeline & Risk**
   - Weekly plan summary (Week 4 → Week 12), the specific risks already
     surfaced (fine-tuning/cloud-GPU conflict, PHQ-4 vs. WHO-5 substitution,
     platform feature availability) — see `build-reference.md`'s decisions
     log and Section 2.

9. **AI Acknowledgement Statement**
   - Required per Weekly_Plan.md Week 5 — describe where AI tools were used
     across the project (including, honestly, this Week 4 gap-fill pass).

## What's still open

- Actual prose for every section above is Honglin's Week 5 focus per
  Weekly_Plan.md ("Compile the Group Proposal Report — primary focus this
  week").
- Section 8 (Timeline & Risk) should be reviewed against whatever the real
  Week 4 cross-check found — see the top-level status report Priyansh
  produced on 2026-08-29 for the current per-person state.
