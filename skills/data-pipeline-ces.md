# Skill: Data Pipeline (CES Dataset)

Applies to: Data Pipeline Lead primarily.

## The locked feature set

Only two features are in scope: **GPS distance travelled** and **phone unlock count/duration**. These are the only two confirmed reliable across the full 220-person cohort regardless of iOS/Android. Do not add a third feature without it independently passing the same cross-platform + completeness check — see `build-reference.md` Section 2 for the full reasoning.

## The platform split — the single most important rule here

188 iOS / 32 Android participants. Some Sensing columns are platform-limited (e.g. physical activity reads as zero on Android — that's "unsupported," not "didn't happen"). Our two locked features (GPS distance, unlock events) are confirmed available on both platforms, so this specific risk doesn't apply to Tier 1 — but if a third feature is ever proposed, check its real per-platform non-null rate before trusting it, don't assume from the column name alone.

**Never impute a platform-unsupported feature as zero.** Always carry a `platform`, `expected_days`, `observed_days`, `coverage_ratio` set of fields alongside any feature value, so downstream code (Stats, SLM) can tell "no signal" apart from "not measured."

## Data location

Raw CES files live in `dataset/` (gitignored, never committed — only small synthetic fixtures go in git). Structure: `Demographics/`, `EMA/`, `Sensing/`, `Raw Sensing/`. The two locked features come from `Sensing/sensing.csv` (`loc_dist_ep_0`, `unlock_num_ep_0` and their epoch variants) — you do not need the 239 per-participant raw files in `Raw Sensing/unlock/` or `Raw Sensing/running_apps/` for the locked Tier 1 build.

## Building a FeatureWindow

Per `build-reference.md` Section 2 ("Time alignment" subsection): build one row per participant × PHQ-4 outcome window, using a **trailing aggregate** — never raw hourly rows joined directly to a weekly PHQ-4 value. The window is the trailing days immediately before each PHQ-4 timestamp; never use a sensing value that happened after the outcome it's supposed to explain.

Every `FeatureWindow` object must carry: `feature_id`, unit, trailing-window start/end, the aggregated value, `observed_days`, `expected_days`, `coverage_ratio`, `platform`, and quality flags. This is not optional metadata — it's what lets the Statistics lead's eligibility rule work correctly.

## Real, known data quirks (verified directly on this copy)

- Participant counts differ slightly across files (216 in demographics, 220 in sensing, 218 with PHQ-4 data) — the sets are not identical. Handle missing-participant cases explicitly, don't assume every uid appears everywhere.
- 14 uids show as both iOS and Android on different rows (likely a device switch or logging artifact) — decide explicitly how to treat these (exclude from platform-based logic, or pick the platform with more rows) rather than silently picking one.
- GPS distance has at least one extreme outlier (~1.21e9) — apply a sanity-bound filter before this reaches the statistical model.

## What NOT to do

- Don't search across CES's 200+ other columns looking for "better" features after Week 5 — the feature set is frozen once signed off.
- Don't build your own database layer — write through `backend/db.py` only.
- Don't add scikit-learn for preprocessing/scaling — pandas/NumPy handle everything this pipeline needs; see `build-reference.md`'s decisions log.
