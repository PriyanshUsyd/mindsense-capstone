# Statistics — Week 4 Spec (Moe Tanaka's role)

**SUPERSEDED — 2026-08-29.** This file was originally an AI-drafted
placeholder (14-day alignment window, 4-window/coverage-ratio baseline
gate) written when no real Week 4 statistics artifact existed anywhere in
the repo or on any branch. **Moe Tanaka has since pushed real, locked work**
at [`weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md`](../../weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md)
(merged into `main` 2026-08-29) — treat that file as the authoritative
Week 4 statistics spec, not this one.

This file is kept only as a short operational summary for code (see
`backend/statistics/eligibility.py`, updated to match Moe's real numbers)
— for anything beyond the three gate thresholds below, read Moe's actual
document, not this page.

## What changed vs. the old AI placeholder

| | AI placeholder (superseded) | Moe's real spec (authoritative) |
|---|---|---|
| Predictor→outcome alignment window | 14 days (guessed) | **14 days** for PHQ-4 (matches the instrument's "last 2 weeks" recall period — same number, real justification) |
| Minimum baseline to unlock comparative statements | 4 prior windows, ~14 days coverage (guessed) | **28 calendar days**, with sufficiency gates: ≥20 valid sensor-days AND ≥3 completed EMAs in that window |
| Target/full baseline for historical-relationship claims | not distinguished | **56 calendar days**, ≥40 valid sensor-days, ≥8 EMAs spanning ≥28 days |
| Model | LMM, random intercept only | LMM, random intercept **+ random slope**, Mundlak within/between specification |
| Multiple-comparison control | not addressed | Holm-Bonferroni (confirmatory, ≤3 tests) + Benjamini-Hochberg FDR (exploratory) |
| Evidence-strength banding | left as an open question for Moe | Fully specified: q-value + standardised effect + occasion count + sign-consistency table (Moe's §7) |

## Three-state cold-start policy, per Moe's real spec (condensed for code)

Evaluated **per feature, per report** — the lowest qualifying state across a
turn's features governs that turn's framing (Moe's §5).

| State | Trigger | Allowed |
|---|---|---|
| **A — No/insufficient data** | <7 days of history, OR 0 completed EMAs, OR <5 valid sensor-days for every Tier-1 feature | Templated message only. No numbers, no comparisons. |
| **B — Partial history** | ≥7 calendar days, ≥1 EMA, but the feature hasn't met the 28-day comparative gate | Current 7-day description only, with mandatory "too early to compare" language. No baseline %, no z-score, no historical-relationship claim. |
| **C — Full history** | Feature meets the 28-day gate (≥20 valid sensor-days, ≥3 EMAs). Historical-relationship claims additionally need the 56-day gate + evidence-strength gate | Comparative statements allowed (`\|z\| >= 1.0` for "meaningful change"); historical-relationship claims only when evidence-strength clears Moe's §7 table. |

## Still open (Moe's own §9, not resettled here)

Final Tier-1 feature list (max 3, joint with Data Pipeline), whether PHQ-4
total is the sole primary outcome, GPS diagnostics from Data Pipeline, and
whether the user-facing 7-day recency window should align to 14 days. These
are Moe's Week 5 Wednesday Tier-1 meeting items, not something this doc
should pre-empt.
