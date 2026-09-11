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

None currently.

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
