# Week 9 Evaluation Frontend Support Log

**Owner:** Sheng Wang, Conversational Interface Lead

**Branch:** `sheng-week9-evaluation-ui-support`

**Status:** Prepared; evaluation sessions not yet logged

**Created:** 2026-10-07

## Scope

This log records frontend readiness checks and new UI issues observed while
supporting the Week 9 internal evaluation sessions. It does not change the
frozen response-quality prompts, model variants, statistical calibration,
guardrail thresholds, dataset contents, or backend-generated response text.

The session operator remains responsible for the evaluation procedure in
`docs/evaluation/team-session-runbook-v0.1.md`. Sheng supports the visible web
interface, records UI failures without hiding failed attempts, and routes
non-UI problems to the appropriate owner.

## Privacy and evaluation boundary

- Record session codes, never teammate names or participant identifiers.
- Do not copy held-out prompts, expected answers, raw sensing rows, locations,
  questionnaire responses, or participant-level output into this file.
- Use only screenshots that contain approved synthetic or de-identified data.
- Record response metadata only when it is needed to reproduce a UI problem.
- If raw identifiers, locations, hidden instructions, unsupported clinical
  claims, or a missed crisis route appear, stop the session and notify the
  Evaluation and Privacy leads.

## Frontend readiness check

Complete this once on every evaluation machine before its first session.

- [ ] Record the exact frozen/RC commit below.
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

## Evaluation machine record

| Machine code | RC commit | OS | Browser and version | Viewport | API/model status | Frontend result | Checked at | Evidence |
|---|---|---|---|---|---|---|---|---|
| Pending | Pending | Pending | Pending | Pending | Pending | Not yet checked | Pending | Pending |

## Session support record

Add one row for every supported session, including sessions with no UI issue.

| Session code | Date/time | Machine code | RC commit | Frontend result | UI issue IDs | Notes |
|---|---|---|---|---|---|---|
| Pending | Pending | Pending | Pending | Not yet run | None recorded | Awaiting evaluation schedule |

## UI issue register

No Week 9 UI issue has been observed yet. Assign IDs sequentially from
`W9-UI-001` only after reproducing a new issue on the frozen/RC build.

### Issue template

#### W9-UI-___ — Short symptom

- **First observed:** YYYY-MM-DD HH:MM and session code
- **RC commit:** full commit SHA
- **Machine/browser/viewport:** machine code, OS, browser version, viewport
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
- **Evidence:** non-sensitive screenshot filename, console excerpt, HTTP status,
  and timestamp as applicable
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

- [ ] Replace all Pending rows with verified records or a clear reason that no
      session occurred.
- [ ] Confirm every observed issue includes exact reproduction steps.
- [ ] Confirm sessions with no UI issue are still recorded.
- [ ] Remove or redact sensitive screenshots and raw data.
- [ ] Link fixes and retest evidence; do not mark an issue Closed without both.
- [ ] Run frontend tests, lint, and production build if frontend code changed.
- [ ] Reply to the team with the PR link or final commit SHA.
