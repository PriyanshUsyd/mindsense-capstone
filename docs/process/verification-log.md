# Verification Log — Work Confirmed Outside GitHub

Not every real, completed task leaves a commit, PR, or file trail — some things
are legitimately confirmed by WhatsApp, verbal approval, or in-person/live
review of a setting that GitHub itself won't show in a diff (e.g. branch
protection configuration). Historically, audits of this repo have had no way
to tell "never actually done" apart from "done, but only confirmed
out-of-band," and defaulted to flagging both as unconfirmed.

**Going forward, this is the team's actual process:** the moment a task is
confirmed by some means other than a commit/PR/CI check, it gets a row in this
log — at the time it's confirmed, not retroactively reconstructed months
later. An audit (automated or manual) should treat a logged row here as
confirmed evidence, on the same footing as a merged PR, and should not
re-flag it as missing just because `git log` doesn't show it. Entries here
are still expected to be honest and specific (who confirmed it, how, when) —
this log is not a way to mark something done without anyone actually having
checked it.

| Week | Person | Task | How Verified | Confirmed By | Date | Notes |
|---|---|---|---|---|---|---|
| Week 4 | Honglin Lu | Branch protection settings on the GitHub repo | Other (direct inspection of GitHub admin settings) | Priyansh Khandelwal | 2026-08-30 | Confirmed working directly in the repo's GitHub Settings > Branches admin panel, not via a commit — this doesn't show up in `git log`/`git ls-tree`, so a code-only audit can't see it independently. |
| Week 5 | Chonghao Shen | Joint-judgment review of baseline responses with Richard Zhao (2-3 cases where judgment differed) | WhatsApp | Priyansh Khandelwal (team lead) | 2026-09-06 | The written scorecards (`benchmarks/slm_evaluation_alignment_scorecard.md`) still show "NOT ASSESSED" placeholders in the file itself — the actual comparison discussion happened over WhatsApp and was never transcribed back into the scorecard. Logged here so the discussion isn't lost, but the scorecard file itself should still be updated with the real disagreement cases when someone has time. |
| Week 6 | Honglin Lu | Frozen-Tier-1 architecture doc (`docs/architecture/frozen-tier1-architecture.md`) | Meeting | Priyansh Khandelwal | 2026-09-12 | Reviewed and approved in person, despite the doc's own header still reading "not yet reviewed or approved" — that header should be updated to reflect this sign-off. |

## Notes on using this log

- Add a row as soon as the out-of-band confirmation happens — don't wait for
  the next audit to prompt it.
- "Confirmed By" should be a real person who actually did the verification,
  not just whoever is filing the row.
- If a doc or scorecard file still contains stale "pending"/"not assessed"
  language that this log's entry supersedes, note that explicitly (see the
  Week 5 row above) rather than leaving two contradictory records with no
  link between them — and update the source file when practical.
