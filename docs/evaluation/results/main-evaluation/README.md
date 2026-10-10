# Main-Evaluation Results Format

All `ME-P01`–`ME-P04` questionnaire ratings go in
`session-responses.csv`. Use one row per session, question and questionnaire
category. Do not put teammate names in the CSV; use evaluator codes such as
`ME-P01-E1` and `ME-P01-E2`.

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
  `CC1=N/A;CC2=No`, and explain it in `na_reason`.
- `critical_failure` is `Yes` or `No`; it cannot be left blank. Apply the
  [critical-failure map](critical-failure-map.md) to every Q1–Q4 response,
  not only Q4.
- `critical_failure_type` is `none` when the screen passes. When it fails, use
  the exact type or semicolon-separated types from `critical-failure-map.md`.
- Use the exact backend values for `response_mode` and `rejection_reason`.
- `architecture_variant` must identify the actual build as `base`, `rag`,
  `agentic` or `rag_agent`. Do not infer a variant from the wording alone.
- All rows in this round use the RC rc-eval-2 (`d31e05db5560d3cfe109642c4e5675be5d68cb3a`: merge commit of `priyansh-fix-50q`, policy 0.3.3), which replaced rc-eval-1 after ME-P01 attempt 1.
  Record its full SHA in `commit_sha`.
- `evidence_path` points to the saved question directory under
  `docs/evaluation/evidence/main-evaluation/`.

Example only (do not copy it as a result):

```csv
ME-P01,Q1,ME-P01-E1,accuracy_faithfulness,A1=4;A2=5;A3=No,No,none,,uncertainty,,base,<rc-eval-2 SHA>,phi4-mini:3.8b,<recorded prompt version>,<recorded policy version>,docs/evaluation/evidence/main-evaluation/ME-P01/Q1/,Example format only
```

The raw item values remain in the CSV. Moe's summary reports the valid
denominator, median and range per item or dimension, excludes `N/A` from the
denominator, and reports critical failures separately.

## Summary script build check

`scripts/summarize_session_responses.py` requires `--expected-commit <full SHA>` and
`--build-label <label>` (no defaults, so a new build cannot reuse an old label;
rc-eval-2: `--expected-commit d31e05db5560d3cfe109642c4e5675be5d68cb3a
--build-label rc-eval-2`). If any row's
`commit_sha` is empty or differs, it prints the counts by kind and stops; it
never excludes rows. Fix the CSV. With `--internal`, the CSV line numbers
are also printed to stderr (no session IDs in either mode). The public report
states `Build: <label> (<SHA>)` right after the note.
