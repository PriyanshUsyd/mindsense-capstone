# CLAUDE.md — MindSense / DATA5702

Working repository for the Statistical Analysis Lead (Moe Tanaka). Not under git management.

## Documentation-implementation sync rule

When code under `analysis/` is changed, reflect the change in the following documents within the same session.
Changing the code without also updating the documentation is prohibited.

- `docs/statistics/preregistration.md` (the former `analysis/preregistration.md` duplicate was deleted 2026-10-06)
- `Week5_Statistical_Analysis_Deliverable.md`

If reflecting the change is difficult, append it to the "Unreflected changes" section below and hand it off to the next session.

## Unreflected changes

(Append here any item where code was changed but the documentation could not be updated.
Remove the line once it has been reflected. Record the date, the affected file, and the change made.)

The 2026-09-12/09-13 archival of `analysis/{baseline,cleaning,evidence_model}.py`
into `analysis/archive/`, the port of their logic into `backend/statistics/`,
bringing Moe Tanaka's real local `preregistration.md` into the repository at
`docs/statistics/preregistration.md`, correcting the Tier-1 feature list to
the 2 features actually signed off (both there and in
`Week5_Statistical_Analysis_Deliverable.md` §7), adding the
`unlock_num_ep_0` spec, and closing `backend/statistics/evidence.py`'s
per-person standard-error gap via bootstrap + cross-method intersection
(`docs/statistics/preregistration.md` §4.1;
`Week5_Statistical_Analysis_Deliverable.md` §5.4) are all reflected in their
respective documents as of 2026-09-13.

The 2026-09-14 duplicate `analysis/preregistration.md` was reconciled and
deleted 2026-10-06 (its one missing open item, the `term_phase` Dartmouth
calendar question, moved to `docs/statistics/preregistration.md` §9 item 6;
reflected in `Week5_Statistical_Analysis_Deliverable.md`).

## Finalised decisions (changes require Statistical Analysis Lead approval)

- Quality gate: **12h**
- Comparison window **`[-14, -1]`**, baseline window **`[-42, -15]`** / **`[-70, -15]`**
- Transform order: **`log(mean)`**. **`mean(log)` is prohibited**
- Recency window unified to **14 days**; `RECENCY_WINDOW_DAYS` is **deprecated**
- Cohort-level family = **the participants holding a per-person slope for that feature** (data-dependent, not a fixed constant — **214** for `loc_dist_ep_0` as of 2026-09-27). 213 was the retired `analysis/` pipeline's figure (origin suspected, not verified: its lag-1 term pushing one participant below the 3-occasion floor); the current primary has no lag-1 term and gives 214. `preregistration.md` §2.2 already defines the family this way. **BH-FDR is the reported value**, Holm is the sensitivity analysis
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
