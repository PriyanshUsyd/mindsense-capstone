# Main-Evaluation Evidence

## Evaluation format

The main evaluation ran as **3 sessions involving all 8 team members** on
rc-eval-2 (`d31e05d`), not as the four pairs `ME-P01`–`ME-P04` originally
planned (recorded 2026-10-16; see the
[roster](../../week8-main-evaluation-roster.md#actual-evaluation-format-3-sessions-all-8-members)).
Session dates, attendance and IDs are TBC (team to confirm).

Evidence already saved keeps its original folder ID:

| Folder | Contents | Maps to session |
|---|---|---|
| `ME-P01/` | `ME-P01.pdf`: transcript with Details lines (username/hostname redacted 2026-10-16) | TBC (team to confirm) |
| `ME-P04/Q1/`–`Q4/` | `notes.md` per question with Details lines | TBC (team to confirm) |
| `ME-P01-attempt1-rc-eval-1/` | Superseded rc-eval-1 attempt | Not part of the rc-eval-2 results |

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
