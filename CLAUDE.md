# CLAUDE.md — MindSense / DATA5702

Working repository for the Statistical Analysis Lead (Moe Tanaka). Not under git management.

## Documentation-implementation sync rule

When code under `analysis/` is changed, reflect the change in the following documents within the same session.
Changing the code without also updating the documentation is prohibited.

- `analysis/preregistration.md`
- `Week5_Statistical_Analysis_Deliverable.md`

If reflecting the change is difficult, append it to the "Unreflected changes" section below and hand it off to the next session.

## Unreflected changes

(Append here any item where code was changed but the documentation could not be updated.
Remove the line once it has been reflected. Record the date, the affected file, and the change made.)

- **2026-09-12** — `analysis/baseline.py`, `analysis/cleaning.py`,
  `analysis/evidence_model.py` moved to `analysis/archive/` (retired, not
  deleted — see `analysis/archive/README.md`) and their logic ported/
  reconciled into `backend/statistics/` (transform order fixed to
  `log(mean)`, trailing window fixed to end the day before assessment,
  quality gate fixed to 12h in `backend/statistics/mixed_effects_model.py`
  and `backend/data_pipeline/cleaning.py`; per-person evidence-strength +
  BH-FDR/Holm family-213 correction + binary collapse ported into new
  `backend/statistics/evidence.py`, wired to `fit_ar1_effect`'s R-backed
  BLUPs). **Could not update `analysis/preregistration.md`** — that file
  does not exist anywhere in this repository (checked: not on `main`, not
  on any branch); someone owning this doc needs to create it first, or
  confirm the Group Proposal / Week 5 deliverable is meant to serve as its
  replacement. **`Week5_Statistical_Analysis_Deliverable.md` not yet
  updated either** — pending Moe Tanaka's review of
  `backend/statistics/evidence.py` (she offered to do this specific port
  herself; one flagged gap remains — see that module's docstring on
  per-person standard errors — before its numbers should be written up as
  final).

## Finalised decisions (changes require Statistical Analysis Lead approval)

- Quality gate: **12h**
- Comparison window **`[-14, -1]`**, baseline window **`[-42, -15]`** / **`[-70, -15]`**
- Transform order: **`log(mean)`**. **`mean(log)` is prohibited**
- Recency window unified to **14 days**; `RECENCY_WINDOW_DAYS` is **deprecated**
- Cohort-level family = **213**, **BH-FDR is the reported value**, Holm is the sensitivity analysis
- User-facing is **binary** (`evidence_available` / `no_claim`)
- Cold-start applies **per evaluation opportunity**; **State C does not persist**

## Session-start check

This repository is worked on from multiple sessions.
Before starting work, check the update times of files under `analysis/` to confirm there is no code newer than the documentation.

```bash
find analysis -type f -not -path "*__pycache__*" -printf "%T+  %p\n" | sort | tail -20
ls -l --time-style=full-iso analysis/preregistration.md Week5_Statistical_Analysis_Deliverable.md
```

If there is code newer than the documentation's update time, it is likely an unreflected change.
