# Main-Evaluation Results Format

The main evaluation ran as **3 sessions (S1, S2, S3), all 8 team members
present at each**, rating every answer by **group consensus** (n = 8). See the
[roster](../../week8-main-evaluation-roster.md). Its results are in
`session-responses.csv`: **one row per session and question (12 rows)**. Do not
put teammate names in the CSV.

## How the consensus rows are recorded

The format below was written for individual per-category ratings. The team
rated by consensus instead, so each row records:

- `evaluator_code` = `group consensus, n = 8`;
- `category` = `overall_consensus` (one consensus verdict per answer, not one
  row per questionnaire dimension);
- `item_scores` = `consensus pass – no individual scores`;
- verdict, date, machine and any re-run note in `notes`.

Because there are no individual item scores, the per-item median/range output
of `scripts/summarize_session_responses.py` does not apply to these rows.
`architecture_variant` is `rag` because the Ollama runtime defaults to the RAG
variant and the UI does not send another (`backend/api/app.py`; release
checklist decision of 2026-10-08).

## Format for individual ratings (if used again)

Use one row per session, question and questionnaire category, with evaluator
codes such as `S1-E1` and `S1-E2`.

## Required conventions

- `question_id` is `Q1`, `Q2`, `Q3` or `Q4`. Use `SESSION` for the
  once-per-session usability category.
- `category` is one of `accuracy_faithfulness`, `comprehensibility`,
  `usefulness`, `personal_relevance`, `trust`, `uncertainty`,
  `correlation_causation`, `mental_health_inference`, `usability` or
  `privacy`.
- `item_scores` uses semicolon-separated item/value pairs, for example
  `A1=4;A2=5;A3=No`.
- Record an inapplicable item explicitly, for example
  `CC1=N/A;CC2=No`, and explain it in `na_reason`. Free text (`na_reason`,
  `notes`, `rejection_reason`) is never published: the public summary shows only
  the N/A count and any `critical_failure_type` outside the defined seven appears
  as "other"; the text is in the `--internal` output only.
- `critical_failure` is `Yes` or `No`; it cannot be left blank. Apply the
  [critical-failure map](critical-failure-map.md) to every Q1–Q4 response,
  not only Q4.
- `critical_failure_type` is `none` when the screen passes. When it fails, use
  the exact type or semicolon-separated types from `critical-failure-map.md`.
- Use the exact backend values for `response_mode` and `rejection_reason`.
- `architecture_variant` must identify the actual build as `base`, `rag`,
  `agentic` or `rag_agent`. Do not infer a variant from the wording alone.
- All rows in this round record rc-eval-2 (`ae849655e692d602b6ea00e0cb64f956d142b458`, policy 0.3.3), which replaced rc-eval-1. The 16 Oct S2/S3 re-runs did not record their checkout; the backend is identical to rc-eval-2 on every main commit through `1166938` (see the roster), and their `notes` say so.
- `evidence_path` points to the saved question directory under
  `docs/evaluation/evidence/main-evaluation/`.

Example only (do not copy it as a result):

```csv
S1,Q1,S1-E1,accuracy_faithfulness,A1=4;A2=5;A3=No,No,none,,uncertainty,,base,<rc-eval-2 SHA>,phi4-mini:3.8b,<recorded prompt version>,<recorded policy version>,docs/evaluation/evidence/main-evaluation/<session folder>/Q1/,Example format only
```

For individual ratings the evaluator is the unit (two `SESSION` rows per pair
session in the original [pair-session guide](../../pair-session-guide.md));
`--unit session` is kept for sensitivity only. The statistics summary reports
the valid denominator, median and range per item or dimension, excludes `N/A`
from the denominator, and reports critical failures separately. None of this
applies to the consensus rows of this round.

## Summary script build check

`scripts/summarize_session_responses.py` requires `--expected-commit <full SHA>` and
`--build-label <label>` (no defaults, so a new build cannot reuse an old label;
rc-eval-2: `--expected-commit ae849655e692d602b6ea00e0cb64f956d142b458
--build-label rc-eval-2`). If any row's
`commit_sha` is empty or differs, it prints the counts by kind and stops; it
never excludes rows. Fix the CSV. With `--internal`, the CSV line numbers
are also printed to stderr (no session IDs in either mode). The public report
states `Build: <label> (<SHA>)` right after the note.
