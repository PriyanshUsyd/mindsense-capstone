# Week 9 Evaluation Frontend Support Log

**Owner:** Sheng Wang, Conversational Interface Lead

**Branch:** `sheng-week9-evaluation-ui-support`

**Status:** Prepared for the locked RC; evaluation sessions not yet logged

**Created:** 2026-10-07

## Scope

This log records frontend readiness checks and new UI issues observed while
supporting the Week 9 internal evaluation sessions. It does not change the
frozen response-quality prompts, model variants, statistical calibration,
guardrail thresholds, dataset contents, or backend-generated response text.

All evaluation support is performed against the fixed RC commit
`b60cb848237a2a2a2cbc726551267a275f1668d0`. This documentation branch is not
the evaluation build. No dependency, frontend, backend, model, or prompt change
is introduced into the locked RC during the sessions.

The session operator remains responsible for the evaluation procedure in
`docs/evaluation/team-session-runbook-v0.1.md`. Sheng supports the visible web
interface, records UI failures without hiding failed attempts, and routes
non-UI problems to the appropriate owner.

## Privacy and evaluation boundary

- GitHub receives only the aggregate frontend-support result and redacted UI
  issue descriptions with independently reproducible steps.
- Keep individual ratings, session codes, screenshots, and full `/respond`
  request or response JSON local. Session codes are not anonymous because the
  team roster identifies the members of each pair.
- Do not copy held-out prompts, expected answers, raw sensing rows, locations,
  questionnaire responses, participant identifiers, or participant-level
  output into this file.
- Describe visual evidence without committing the underlying screenshot. A
  minimal, non-sensitive crop may be shared only after Privacy approval.
- Record only the response metadata required to reproduce the UI symptom.
- If raw identifiers, locations, hidden instructions, unsupported clinical
  claims, or a missed crisis route appear, stop the session and notify the
  Evaluation and Privacy leads.

## Frontend readiness check

Complete this once on every evaluation machine before its first session.

- [x] Record the fixed RC commit:
      `b60cb848237a2a2a2cbc726551267a275f1668d0`.
- [ ] Confirm the approved dataset is locally available without opening raw
      participant data in the browser or terminal capture.
- [ ] Confirm the project-local Python environment passes `python -m pip check`.
- [ ] Confirm Ollama and the approved local model are available.
- [ ] Confirm FastAPI starts on `127.0.0.1:8000` and its health check succeeds.
- [ ] Confirm the Vite frontend starts and loads in the approved browser.
- [ ] Confirm the frontend reaches `/respond` without CORS or transport errors.
- [ ] Confirm an approved public smoke question renders the expected response
      state without exposing raw identifiers or hidden metadata.
- [ ] Confirm Enter submits, Shift+Enter adds a new line, duplicate submission
      is blocked, retry works, and New conversation resets the thread.
- [ ] Confirm the loading/warm-up state, response card, and composer remain
      readable at the evaluation window size.
- [ ] Record the result as Pass, Blocked, or Pass with issue; never silently
      restart and report only the successful attempt.

## Evaluation environment summary

Do not enter a machine owner, pair, session code, exact session timestamp, or
local evidence path in the committed table.

| RC commit | OS | Browser and version | Viewport | API/model status | Frontend result | Check date | Redacted evidence summary |
|---|---|---|---|---|---|---|---|
| `b60cb848237a2a2a2cbc726551267a275f1668d0` | Pending | Pending | Pending | Pending | Not yet checked | Pending | Pending |

## Aggregate session support record

Keep the detailed session-by-session worksheet outside the repository. Update
this table only with totals after the supported sessions are complete.

| RC commit | Sessions supported | Sessions blocked by UI | New UI issue IDs | Overall frontend outcome | Notes |
|---|---:|---:|---|---|---|
| `b60cb848237a2a2a2cbc726551267a275f1668d0` | Pending | Pending | None recorded | Not yet run | Awaiting evaluation sessions |

## UI issue register

No Week 9 UI issue has been observed yet. Assign IDs sequentially from
`W9-UI-001` only after reproducing a new issue on the frozen/RC build.

### Issue template

#### W9-UI-___ — Short symptom

- **First observed:** evaluation date only; no session code or exact time
- **RC commit:** full commit SHA
- **Environment:** OS, browser version, and viewport; no machine owner or code
- **Severity:** Blocker / High / Medium / Low
- **Frequency:** Always / Intermittent / Once; reproduced N of N attempts
- **Area:** startup / navigation / composer / loading / response rendering /
  retry / responsive layout / accessibility / other
- **Preconditions:** visible application state and approved test setup
- **Reproduction steps:**
  1. Start from a named visible state.
  2. Perform the exact UI action.
  3. Record the next UI action, if any.
  4. Observe the symptom without silently retrying.
- **Expected:** what the interface should visibly do
- **Actual:** what the interface visibly did
- **Evidence summary:** redacted visible symptom, console error class, or HTTP
  status required for reproduction; screenshots and full JSON remain local
- **Local evidence retained:** Yes / No; do not enter its identifying path
- **Workaround:** none, or the temporary operator action used
- **Suspected owner:** Frontend / Data Pipeline / Statistics / SLM / Evaluation
  / Integration
- **Status:** Open / Triaged / Fixed / Retested / Closed
- **Retest evidence:** commit, machine, date, and result

## Severity guide

- **Blocker:** prevents the session from continuing or risks displaying
  sensitive or unsafe content.
- **High:** produces a materially misleading state, loses a response, or makes
  a required evaluation action unusable.
- **Medium:** impairs the workflow but has a reliable, documented workaround.
- **Low:** cosmetic or minor usability issue that does not affect recorded
  evaluation results.

## End-of-week handoff

Before opening the Week 9 PR:

- [ ] Replace all Pending values with aggregate verified results or a clear
      reason that no session occurred.
- [ ] Confirm every observed issue includes exact reproduction steps.
- [ ] Confirm the aggregate count includes sessions with no UI issue.
- [ ] Confirm no individual ratings, session codes, screenshots, full JSON,
      held-out prompts, or raw data are tracked by Git.
- [ ] Link fixes and retest evidence; do not mark an issue Closed without both.
- [ ] Run frontend tests, lint, and production build if frontend code changed.
- [ ] Reply to the team with the PR link or final commit SHA.
