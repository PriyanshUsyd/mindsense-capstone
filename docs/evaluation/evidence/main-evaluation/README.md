# Main-Evaluation Evidence

## Evaluation format

The main evaluation ran as **3 sessions (S1–S3), all 8 team members present at
each**, the same 4 questions in each, rated by group consensus (n = 8), on
rc-eval-2's response behaviour (see the
[roster](../../week8-main-evaluation-roster.md)). Folders:

| Session | Folder | Contents |
|---|---|---|
| S1 (13 Oct, `phi4-mini:3.8b`) | `ME-P01/` | `ME-P01.pdf`: transcript with Details lines (username/hostname redacted 2026-10-16; per-person values redacted 2026-10-17) |
| S2 (16 Oct re-run, `phi4-mini:3.8b`) | `S2/Q1/`–`Q4/` | `notes.md` per question |
| S3 (16 Oct re-run, `phi4-mini:3.8b`) | `ME-P04/Q1/`–`Q4/` | `notes.md` per question, including the superseded 13 Oct `demo-stub:1.0` run |
| — | `ME-P01-attempt1-rc-eval-1/` | Superseded rc-eval-1 attempt; not part of the results |

New evidence goes in one directory per session and question, using the
session ID the team confirms:

```text
<session_id>/Q1/
<session_id>/Q2/
<session_id>/Q3/
<session_id>/Q4/
```

## What is committed and what stays local

Committed to the repository, per question directory:

- `notes.md` — date/time, operator/evaluator codes, the exact question, the
  visible badge and response text, the **Details line** exactly as shown
  (`response_mode`, `rejection_reason`, `model_tag`, `policy`), any observed
  failure or retry, and anything else not captured elsewhere.

Kept **local only, never committed** (matching the
[progress-report evidence register](../../../progress-report/evidence-register.md)
and the [pair-session guide](../../pair-session-guide.md)):

- `ui.png` — screenshot of the exact question and complete visible response;
- `response.json` — the full `/respond` API response.

Do not store teammate names, usernames or machine hostnames, raw participant
identifiers, coordinates, personal disclosures or held-out Week 11 content.
A failed first attempt stays in the evidence; do not replace it silently with
a successful retry.

The matching questionnaire-category rows go in
`docs/evaluation/results/main-evaluation/session-responses.csv` and reference
the question directory through `evidence_path`.
