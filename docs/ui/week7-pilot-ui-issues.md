# Week 7 UI Pilot and Local End-to-End Log

**Owner:** Sheng Wang, Conversational Interface Lead

**Branch:** `sheng-week7-ui-pilot`

**Branch base:** `main` at `470fe8c` (2026-09-16)
**Status:** Pilot blocked by missing approved local dataset; Week 8 fixes require
triage before implementation

## Scope and constraints

This log supports the Week 7 team-only pilot and records interface issues for
Week 8. It does not change the frozen application build.

- No held-out guardrail questions were opened or used.
- Only previously used development questions are recorded below.
- Testing described here ran locally on Sheng Wang's MacBook Air. Richard Zhao
  asked Sheng to complete the UI checks independently and is handling any
  demo-machine validation separately. This document does **not** claim that
  Sheng tested Richard's machine.
- Richard owns guardrails, fallback copy, local-model operation, and the
  Base/RAG/agentic/RAG+agent comparison. This log covers only UI behaviour and
  end-to-end observations relevant to the interface.
- Issues are logged during Week 7, not live-patched. Priyansh triages blocking
  issues; accepted UI fixes are scheduled for Week 8.

## Version boundary

The local exploratory session on 2026-09-12 used the then-current `main`, but
its exact commit SHA was not captured. It used the earlier client-supplied
synthetic EvidencePacket flow.

PR #22 (`7feeac1`, merged 2026-09-16) subsequently changed `/respond` to build
evidence server-side from `participant_id`. Results from 2026-09-12 are useful
reproduction evidence, but they are **not** represented as verification of the
current frozen build. Every item in the current-build checklist below must be
run again after recording the exact commit SHA.

## Repository gate verification on 2026-09-17

The following non-interactive checks passed on this branch at base commit
`470fe8c` in an isolated Linux workspace. These checks verify the repository
gates only; they do not replace the Mac/Ollama end-to-end pilot.

| Gate | Result |
|---|---|
| `python -m pytest tests/api/test_app.py -q` | Pass: 14 tests; 2 dependency deprecation warnings |
| `npm test -- --run` | Pass: 3 files, 22 tests |
| `npm run lint` | Pass: 0 errors |
| `npm run build` | Pass: Vite 8.2.2 production build |

## Local environment used on 2026-09-12

| Item | Recorded value |
|---|---|
| Machine | Apple MacBook Air |
| Operating system | macOS; exact version was not captured |
| Ollama | `0.33.3` |
| Model | `phi4-mini:3.8b` |
| Frontend | Vite `8.2.2`, React 19, TypeScript |
| Backend | Local FastAPI at `127.0.0.1:8000` |
| Model endpoint | Local Ollama loopback at `127.0.0.1:11434` |
| External participant recruitment | None |

## Current-build pilot environment on 2026-09-17

| Item | Recorded value |
|---|---|
| Machine | Apple MacBook Air |
| Operating system | macOS 14.4.1 |
| Git branch / commit | `sheng-week7-ui-pilot` / `717cdf0` |
| Ollama | `0.34.1` |
| Model | `phi4-mini:3.8b` (`78fad5d182a7`, 2.5 GB) |
| Python environment | Project-local `.venv` |
| Scientific stack | NumPy 2.5.3, SciPy 1.18.1, statsmodels 0.15.0 |
| External participant recruitment | None |

The first backend start used the Anaconda `base` environment and failed while
importing SciPy because its compiled extension targeted the NumPy 1.x ABI but
NumPy 2.2.6 was installed. Creating the gitignored project `.venv` and
installing `requirements.txt` resolved the import failure. The backend then
started successfully and `/health` returned `{"status":"ok"}`.

The first `/respond` request on the working backend reached FastAPI but returned
an unhandled 500. The traceback ended in `FileNotFoundError` for
`dataset/Sensing/sensing.csv`. That directory is intentionally gitignored and
was not provisioned on Sheng's machine. The browser displayed `Local API:
Failed to fetch`, which incorrectly suggested the local service was
unreachable even though FastAPI logged the POST and the actual failure was
missing server-side data.

## Executed exploratory checks

| Check | Input/action | Observed result | Status |
|---|---|---|---|
| Backend and frontend startup | Start FastAPI with `MINDSENSE_SLM_RUNTIME=ollama`; start Vite | Both local services started and the chat page loaded | Pass on the 2026-09-12 build |
| First normal request after cold start | `How was my movement different from my recent baseline?` | UI eventually showed generic fallback rather than a normal response | Issue observed |
| Direct local-model replay | Run `backend.slm.shadow_cli` with the known development GPS fixture and `--timeout 180` | Returned `normal`; model invoked; request policy `0.2.0`; no fallback | Pass on the 2026-09-12 build |
| Warm normal request | Retry the same normal question after the direct replay | UI displayed the grounded GPS response and evidence card | Pass on the 2026-09-12 build |
| Off-topic refusal | `Can you recommend a movie for tonight?` | UI displayed `Outside MindSense's scope` with the refusal treatment | Pass on the 2026-09-12 build |

The successful direct replay reported `total_duration_ns=134666476457`
(approximately 134.7 seconds). The API's Ollama runtime uses the 120-second
default timeout, which is consistent with the cold request falling back before
the same generation could finish. This is a measured diagnosis, but the
failure must be reproduced on the current frozen build and target demo setup
before a final fix is selected.

## Current-build retest checklist

Run this checklist on the frozen build without using held-out prompts.

- [x] Record `git rev-parse --short HEAD`, macOS version, Ollama version, and
      `ollama list` output before the session.
- [x] Run the focused backend API tests and all frontend test, lint, and build
      gates.
- [ ] Start the real local runtime from a cold Ollama state and time the first
      normal response.
- [ ] Verify a normal GPS question uses the real server-built participant
      evidence introduced by PR #22.
- [ ] Verify the known development movie question maps to refusal without
      model generation.
- [ ] Simulate a local API/model failure and verify generic fallback plus retry.
- [ ] Verify uncertainty, insufficient-data, and generic-fallback cards are
      distinguishable by label, icon, and treatment rather than colour alone.
- [ ] Verify `New conversation`, prior-turn display, Enter/Shift+Enter, loading,
      duplicate-submit prevention, scrolling, and phone-width layout.
- [ ] Save only non-sensitive screenshots and record pass/fail evidence here.

## UI issues for Week 8 triage

| ID | Severity | State | Issue | Evidence / reproduction | Expected Week 8 direction | Status |
|---|---|---|---|---|---|---|
| W7-UI-001 | High | Loading / generic fallback | Cold local-model generation can exceed the API timeout and appear to the user as a generic failure. | On 2026-09-12 the first UI request fell back; the same request succeeded through the CLI with a 180-second timeout and took about 134.7 seconds. | Richard/Priyansh should choose preloading, a documented target-machine latency budget, or a configurable timeout. Sheng should retest the resulting loading and fallback behaviour. | Open; current-build reproduction required |
| W7-UI-002 | High | Normal evidence card | After PR #22, the backend uses a real participant id, but the normal card still renders generic `see response text` fields while `ChatStates.tsx` labels the card `Synthetic demo data` and mentions a Week 5 evidence packet. This creates contradictory provenance on the participant-data path. | `NormalResponse.tsx` uses placeholder evidence values because `SafeSLMResponse` does not return an evidence summary; `ChatStates.tsx` still contains the old fixture label and Week 5 copy. | Either return a safe evidence summary in the response contract or hide/replace the numeric panel until real values are available. Provenance labels must match the actual data path. | Open on `main` at `470fe8c` |
| W7-UI-003 | Low | Developer setup / documentation | Frontend documentation still says the browser posts `{ evidence_packet, question }`, while PR #22 changed the request to `{ participant_id, question, feature_id }`. | `frontend/README.md` and `frontend/src/features/chat/README.md` describe the obsolete synthetic-packet request. | Update startup and contract documentation after the shared contract is confirmed. | Open on `main` at `470fe8c` |
| W7-UI-004 | Medium | API contract | The frontend `request_category` union does not include Richard's Week 6 `off_topic` category. Runtime rendering currently relies on `response_mode`, so the known refusal still displays, but the hand-written TypeScript contract is incomplete. | `frontend/src/api/client.ts` lists safety categories but omits `off_topic`; the backend request policy `0.2.0` returns it for off-topic refusal. | Regenerate types from OpenAPI when available or update and test the provisional union in the shared contract change. | Open on `main` at `470fe8c` |
| W7-UI-005 | High | Local setup | The documented backend command can use an incompatible global Python stack. On Sheng's Anaconda `base`, NumPy 2.2.6 loaded SciPy/statsmodels extensions compiled for NumPy 1.x, so the API could not start. | Full import traceback reproduced on macOS 14.4.1. A project-local `.venv` with NumPy 2.5.3, SciPy 1.18.1, and statsmodels 0.15.0 started cleanly. | Document `.venv` setup as required and introduce a reproducible compatible dependency lock or constraints policy. | Workaround verified; permanent setup fix open |
| W7-UI-006 | Blocker | End-to-end / generic fallback | The real participant path requires gitignored dataset files that were not provisioned on the pilot machine. `/respond` raised `FileNotFoundError` for `dataset/Sensing/sensing.csv`; the UI misleadingly reported `Local API: Failed to fetch` even though the API received the request and returned 500. | `/health` passed; FastAPI logged `POST /respond` 500; traceback identified the missing file. | Priyansh/Honghao must provide an approved local-only data provisioning process or an approved sanitised demo dataset. The API should fail closed with a handled response, and the UI should distinguish server/data failure from an unreachable service. Sheng retests after provisioning. | Open; blocks current-build E2E on Sheng's Mac |

## Visual-state verification note

The current CSS now gives the three previously similar states different icons:
uncertainty uses `!`, insufficient data uses `○`, and generic fallback uses
`⚙`. This is a code-level improvement, not yet a completed runtime visual
review on the current frozen build. The checklist therefore keeps this item
open until the three rendered states are inspected at desktop and phone width.

## Handoff

At the end of Week 7, Sheng will give Priyansh and the relevant owners this log
for triage. Only accepted UI items move into Sheng's Week 8 implementation
branch. Test evidence must identify the exact build and machine used; local
results must not be described as demo-machine verification.
