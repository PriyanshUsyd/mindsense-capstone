# Occasion reconciliation with Data Pipeline Lead (Week 5)

Three generations of `mine_keys*.csv` are kept side by side, in the order they
were produced, rather than only the final one:

- **`mine_keys_8h_lag0.csv`** (28,662 occasions) -- generated under the
  pre-Fix-2 config (`quality_min_hours=8h`, `window_lag=0`, i.e. the window
  ends ON the EMA date). Superseded once the Statistical Analysis pipeline
  locked to 12h/lag=1.
- **`mine_keys_12h_lag1_buggy.csv`** (28,326 occasions) -- regenerated with
  `reconcile_occasions.py`'s CONFIG updated to match the current pipeline
  (`quality_min_hours=12h`, `window_lag=1`), but before a bug fix to
  `valid_day_counts()`: its per-person reindex range stopped at that person's
  own sensing date range, so any EMA occasion dated more than `window_lag`
  days after their last sensing day got no row at all (silently defaulted to
  0 valid days via the later left-merge) even when its 14-day window actually
  had enough real sensing data. This under-counted by exactly 11 occasions,
  all clustered at participants whose last sensing day fell on one of the
  dataset's two cohort-wide end dates (2021-06-15 / 2022-06-15), with the EMA
  date landing 2-8 days later.
- **`mine_keys_12h_lag1.csv`** (28,337 occasions) -- **current, correct
  version**, after fixing `valid_day_counts()` to extend the per-person
  reindex range to also cover that person's EMA date range (both ends), not
  just their sensing date range. `diff` against the pipeline's own
  `analysis/output/latest/occasion_gate_keys.csv` (produced independently by
  `run_week5_pipeline.py`) now shows **0 occasions only on either side** --
  full agreement.

**28,337 is also the figure the Data Pipeline Lead's independent implementation
converged on** (500 km distance-implausibility rule: 28,337 occasions / 214
participants -- see `Week5_Statistical_Analysis_Deliverable.md`). The 11-file
gap between `_buggy` and the final version was a bug in this reconciliation
tool's own boundary handling, not an error in the production
`analysis/predictors.py` pipeline -- the production pipeline's occasion count
was correct throughout; the reconciliation tool needed to catch up to it.

None of the three files are deleted: the sequence itself is the record of how
the two independent implementations converged on the same number.
