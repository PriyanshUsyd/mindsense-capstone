# CES Eligibility — 97.3% vs 98.2% Reconciled (2026-08-29)

## The discrepancy

On 2026-08-29, `backend/data_pipeline/verify_ces.py` was built as an
independent cross-check of Honghao Li's reported CES re-verification. It
initially returned **98.2% eligible (216/220)**, not Honghao's reported
**97.3%**. This note documents exactly why, and picks an official number
for now.

## The exact difference

Both numbers use the same numerator logic (participant has ≥1 PHQ-4 entry
AND has data on both locked Tier-1 features: `loc_dist_ep_0`,
`unlock_num_ep_0`) over the same denominator (220 sensing participants).
**They differ only in how much feature data counts as "has data":**

| Definition | Rule | Result |
|---|---|---|
| **"coarse"** (this script's original definition) | >0 observed days ever, across a participant's *entire* history | 216/220 = **98.2%** |
| **"gated"** (added 2026-08-29) | ≥20 valid sensor-days on *both* features | 214/220 = **97.27% → 97.3%** |

The 20-valid-sensor-day threshold is not arbitrary — it's the exact State C
comparative-eligibility gate from Moe Tanaka's real, locked Week 4
statistics spec (`weekly_update/week4/Week4_Statistical_Analysis_Deliverable.md`
Section 4.3: "Comparative statements (State C)... ≥20 valid sensor-days").
Once the "gated" definition uses that real threshold instead of an
arbitrary "any data at all" check, **the number matches Honghao's reported
97.3% exactly** (214/220 = 97.2727...%, which rounds to 97.3%).

The 4 participants who have a PHQ-4 entry and *some* data but fall below
the 20-valid-day gate on at least one locked feature:
`1badfae62cc1b76787d4f8beb68737bf`, `1e85c892d8f047ff621ad9134c4e6d8d`,
`ad15fc229da933fbf1fc0f92fc9b55a3`, `c7d47e96f38254e31508ca2c19b24d29`.

## Official number for now

**97.3% (214/220), using the "gated" ≥20-valid-sensor-day definition.**

Justification for picking this one now, rather than waiting:
1. It matches a real, statistically-justified sufficiency threshold (Moe's
   locked spec), not an arbitrary "any data ever" check.
2. It corroborates Honghao's independently-reported figure exactly, which
   is reassuring rather than coincidental — two independently-run checks,
   built from two different starting points, converge once the same real
   threshold is applied.

## Still pending — this is a default, not a final answer

**Honghao Li has not yet confirmed this is in fact his own methodology.**
His exact script/notebook that produced 97.3% still hasn't been committed
anywhere in the repo. It's entirely possible he used a different rule that
happens to produce the same number by coincidence (unlikely given the exact
match, but not provably ruled out without his actual code). Flagged to
Priyansh: get Honghao to commit his real script, or confirm this
reconstruction matches his intent, before treating 97.3% as anything more
than "very likely correct, independently corroborated twice."
