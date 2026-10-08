# Pilot Triage Summary — Consolidated Record Written in Week 9

**Written:** 2026-10-08 (Week 9) by Priyansh Khandelwal, Integration & QA Lead
**Status as of:** origin/main `a498b3f` (2026-10-08)

> **No triage artifact was produced in Week 7; triage decisions were recorded in Sheng's issue log. This file consolidates them.**

This is a retrospective consolidation, not a Week 7 document. It adds no new decisions. Each row is sourced from an existing record in the repository, and each "Fix" entry cites the commit or PR that made the change. Where a source record and the code on main differ, this file reports what main shows.

## Sources

| Source | Owner | Last change |
|---|---|---|
| `docs/ui/week7-pilot-ui-issues.md` (W7-UI-001…006) | Sheng Wang | `524a70b` (2026-09-27), merged via PR #46 |
| `docs/data-pipeline/week8_pilot_issue_log.md` (W7-UI-006 data side) | Honghao Li | `7262da0` (2026-10-05), PR #44 |
| `docs/evaluation/week7-rostered-pair-pilot-main.md` (pilot Q1–Q3) | Chonghao Shen | `35bb40d` (2026-09-20) |
| `docs/slm/week7-fallback-refinement.md` (cold-start deadline, missing-dataset 500) | Richard Zhao | `148ba02` (2026-09-20), PR #31 |

## A. UI / end-to-end issues from Sheng's log (W7-UI-001…006)

| ID | Severity | Issue (short) | Owner(s) per log | Decision | Fix (SHA / PR) | Status on main `a498b3f` |
|---|---|---|---|---|---|---|
| W7-UI-001 | High | Cold local-model generation exceeded the API timeout and appeared as a generic failure | Richard / Priyansh (timeout policy); Sheng (retest) | Bounded 180 s default deadline (configurable 1–300 s), plus an explicit warm-up UI state | Deadline: `148ba02`, PR #31 (`20b6b0d`). Warm-up UI: `df7bce9`, PR #46 (`3ec9cf3`) | **Closed** per log (cold Phi replay passed in 127.83 s on 2026-09-27). Fix reached main 2026-10-08 |
| W7-UI-002 | High | Normal card showed placeholder evidence and a contradictory "Synthetic demo data" label on the real-participant path | Sheng | Remove the obsolete synthetic panel; render only the validated backend response | `8b5a00e` (chat UI hardening), PR #33 (`f2e8a12`) | **Closed** (Week 8) per log |
| W7-UI-003 | Low | Frontend docs described the obsolete `{ evidence_packet, question }` request | Sheng | Document `{ participant_id, question, optional feature_id }` | `8b5a00e` (`frontend/src/features/chat/README.md`), PR #33. `frontend/README.md` updated in `df7bce9`, PR #46 | **Closed** (Week 8) per log |
| W7-UI-004 | Medium | Frontend `request_category` union missing `off_topic` | Sheng | Add `off_topic` to the provisional union, with test coverage | `8b5a00e` (`frontend/src/api/client.ts`, `client.test.ts`), PR #33 | **Closed** (Week 8) per log |
| W7-UI-005 | High | Documented backend command could use an incompatible global Python stack (NumPy 2 vs extensions built for 1.x) | Sheng (with Integration) | Require a project-local `.venv` with a constraints file | `df7bce9` + `524a70b`, PR #46 (`constraints-python312.txt`, `scripts/setup_local_python_env.sh`) | **Closed** per log (2026-09-27). Fix reached main 2026-10-08 |
| W7-UI-006 | Blocker | Real-participant path needed gitignored CES files that weren't provisioned; `/respond` 500, and the UI said "Failed to fetch" | Priyansh / Honghao (provisioning); Richard (API fail-closed); Sheng (retest) | (a) API fails closed with a handled response. (b) Documented local-only provisioning with a preflight check. No sanitised demo dataset | (a) `148ba02`, PR #31. (b) `7262da0`, PR #44 | **Partial.** Sheng's log: handled fallback and UI verified; provisioning remains with Data Pipeline/Integration. Honghao's log: end-to-end closure still needs integration verification. No per-machine preflight result recorded yet |

## B. Issues from the Week 7 rostered-pair pilot (Chonghao's record)

These have no W7-UI ID. They are listed by the pilot question that exposed them.

| Ref | Issue (short) | Owner | Decision | Fix (SHA / PR) | Status on main `a498b3f` |
|---|---|---|---|---|---|
| Pilot Q1 | Frontend always sent `gps_distance`, so a phone-unlock question was answered with GPS evidence | Priyansh (Integration) | Backend infers the feature from the question when `feature_id` is omitted | `e58012e`, PR #27 (`b524f33`) | **Fixed.** The pilot record shows Q1 passing on the retest build |
| Pilot Q2 | Requested time window ("last 3 days") was silently answered on the fixed window | Richard (request policy); Moe (statistical approval) | Explicit time-window requests are refused (`unsupported_time_window`) rather than answered on the fixed window | Detection and refusal: `db93d0a`, PR #34 (`32a0524`). Statistical record: `daff6e5`, PR #38 (`9abda9b`), preregistration §3.1 | **Fixed (by refusal).** Verified on `a498b3f`: the Q2 wording returns `unsupported_time_window`. Known detection gaps are recorded in `daff6e5` |
| Pilot Q1 (precision) | Participant-facing values shown with excessive precision (`120.71428571428571 unlocks per day`) | Moe | Round user-facing numeric values to integers | `bc9936b`, PR #38 (`9abda9b`) | **Fixed** per PR #38 |
| Pilot Q3 | "Do you think I'm depressed?" classified `off_topic` instead of `diagnosis_seeking` (the response was still safe) | Richard | Add diagnosis-seeking patterns to the request policy | `db93d0a`, PR #34 (`32a0524`) | **Fixed.** Verified on `a498b3f` (request policy 0.3.1): classified `diagnosis_seeking`, disposition `refuse` |

## C. Data-pipeline review (Honghao's record)

Honghao's log states that the Week 7 pilot found **no critical or blocking defect in the frozen Tier-1 data-pipeline feature logic**, so no Week 7 data-pipeline bug-fix branch was needed. The only data-pipeline item is the W7-UI-006 provisioning gap (Section A).

## Still open

| Item | Owner | Needed |
|---|---|---|
| W7-UI-006 end-to-end closure | Honghao Li (preflight), Sheng Wang (retest) | Run the preflight in `docs/data-pipeline/ces_local_provisioning.md` on each evaluation machine and record the result; Sheng to retest the UI path on the RC build |
| UI-001 / UI-005 fixes on the evaluation build | Priyansh Khandelwal | Make sure the tagged release candidate includes PR #46. The earlier proposed RC `b60cb84` does not |
