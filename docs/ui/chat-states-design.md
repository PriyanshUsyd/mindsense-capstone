# UI — Chat States Design (Week 4, planning-level only)

**Filled in by Priyansh Khandelwal (Integration/QA) — Sheng Wang did not
deliver this, per Weekly_Plan.md Week 4: "Design (not build yet) the 7
required chat states ... Set up the Vite + React + TypeScript scaffold."**
No commit from Sheng Wang exists anywhere in this repository as of
2026-09-05.

**Status: DRAFT, built to fill a Week 4 gap found on 2026-08-29.** This is
planning-level design only, per Weekly_Plan.md ("Design (not build yet) the 7
required chat states") — no components are built here beyond the scaffold
(see `frontend/`). Sheng Wang should review and adjust before Week 6, when
these states get built for real.

Per `skills/frontend-react.md`, each state is its own component, sharing a
common visual language, and must be **visually distinct enough that a user
should never have to read carefully** to tell them apart.

## The 7 states

| # | State | Maps to `response_mode` (evidence contract) | Visual language (proposed) | Content source |
|---|---|---|---|---|
| 1 | **Normal response** | `normal` | Neutral card, primary accent color, includes the ECharts calendar-heatmap trend widget | `AssistantDraft.text` + evidence packet's approved claims |
| 2 | **Insufficient-data / cold-start** | `insufficient_data` | Muted/grey card, dashed border, no chart rendered at all (not a chart with zeros) | Templated `not_enough_data` copy only |
| 3 | **Uncertainty** (evidence exists but weak) | `uncertainty` | Same accent as Normal but with a visible "amber" uncertainty banner pinned above the text | Descriptive-only text, explicit "too early to compare confidently" language (see `docs/statistics/model-and-coldstart-spec.md` state 2) |
| 4 | **Refusal** (out-of-scope request) | `refusal` | Distinct neutral-dark card, no chart, short response | Static copy — "that's outside what this app can help with" |
| 5 | **Generic fallback** (model/validation failure) | `generic_fallback` | Same visual family as Refusal but with a small "something went wrong" icon, so it reads as a system-side issue, not a boundary decision | `backend/slm/prompts/generic_fallback.yaml` |
| 6 | **Crisis-aware fallback** | `crisis_aware_fallback` | Deliberately the most visually distinct: full-width, high-contrast, calm but serious color (not alarming red — avoid anything that could itself feel distressing), resource links rendered as tappable/clickable, never auto-dismissing | `backend/slm/prompts/crisis_aware.yaml` verbatim — **never** paraphrased or regenerated client-side |
| 7 | **Loading/processing** | n/a (transient, pre-response) | Skeleton/shimmer state, no content claims of any kind | n/a |

## Non-diagnostic boundary applies to the UI too

Per `skills/frontend-react.md`: never colour a calendar-heatmap cell as
"depressed," "anxious," or "high risk." Cells are labelled strictly as
above/below the person's own baseline, with a visible missing/low-coverage
state (matching `FeatureWindow.coverage_ratio` from the evidence contract).

## What's still open (for Sheng to decide, not finalized here)

- Exact color tokens / design system — none exists yet; this doc intentionally
  avoids inventing a full token set that isn't Sheng's call.
- Whether state 7 (loading) counts toward "7 required states" as a distinct
  component or a shared wrapper — Weekly_Plan.md text is ambiguous
  ("(If applicable) loading/processing state"); flagged, not resolved here.
