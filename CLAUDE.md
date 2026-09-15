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

- **2026-09-14 — duplicate preregistration document, not yet reconciled.**
  A *separate* session independently created `analysis/preregistration.md`
  (249 lines, "compiled by session tooling" from already-locked decisions —
  its own header says so) — inside the archived `analysis/` directory, which
  this session's `docs/statistics/preregistration.md` migration note
  explicitly avoided for that reason. Discovered during a rebase of
  `moe-week6-tier1-extension` onto `origin/main`, which carried that file in
  independently of anything on this branch (no path conflict, since the two
  live at different locations). `docs/statistics/preregistration.md` is the
  more authoritative of the two (it is Moe Tanaka's actual original local
  file, with real provenance, not a reconstruction) but **no decision has
  been made yet on whether to delete/redirect `analysis/preregistration.md`,
  merge any content unique to it, or leave both in place** — flagged here
  rather than resolved unilaterally during the rebase.

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
