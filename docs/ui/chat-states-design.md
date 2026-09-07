# UI — Chat States Design and Week 6 Normal Conversation

**Filled in by Priyansh Khandelwal (Integration/QA) — Sheng Wang did not
deliver this, per Weekly_Plan.md Week 4: "Design (not build yet) the 7
required chat states ... Set up the Vite + React + TypeScript scaffold."**
No commit from Sheng Wang exists anywhere in this repository as of
2026-09-05.

**Status update (2026-09-07):** the Week 5 interface was merged in PR #10. The
Week 6 implementation turns the normal path into a continuing conversation and
adds an explicit FastAPI startup path for Richard's local Ollama service. The
earlier planning document and scaffold remain attributable to Priyansh in git
history.

Per `skills/frontend-react.md`, each state is its own component, sharing a
common visual language, and must be **visually distinct enough that a user
should never have to read carefully** to tell them apart.

## The 7 states

| # | State | Maps to `response_mode` (evidence contract) | Visual language (proposed) | Content source |
|---|---|---|---|---|
| 1 | **Normal response** | `normal` | Paper response card plus a labelled evidence summary and limitations | `SafeSLMResponse.text` + the submitted EvidencePacket |
| 2 | **Insufficient-data / cold-start** | `insufficient_data` | Amber information card; no comparison or chart | Backend response text |
| 3 | **Uncertainty** (evidence exists but weak) | `uncertainty` | Amber evidence-warning treatment with a non-diagnostic boundary | Backend response text |
| 4 | **Refusal** (out-of-scope request) | `refusal` | Muted rose boundary card; no chart | Backend response text |
| 5 | **Generic fallback** (model/validation failure) | `generic_fallback` | Same visual family as Refusal but with a small "something went wrong" icon, so it reads as a system-side issue, not a boundary decision | `backend/slm/prompts/generic_fallback.yaml` |
| 6 | **Crisis-aware fallback** | `crisis_aware_fallback` | Deliberately the most visually distinct: full-width, high-contrast, calm but serious color (not alarming red — avoid anything that could itself feel distressing), resource links rendered as tappable/clickable, never auto-dismissing | `backend/slm/prompts/crisis_aware.yaml` verbatim — **never** paraphrased or regenerated client-side |
| 7 | **Loading/processing** | n/a (transient, pre-response) | Skeleton/shimmer card describing only processing steps, with no result claim | Frontend transient state |

## Non-diagnostic boundary applies to the UI too

Per `skills/frontend-react.md`: never colour a calendar-heatmap cell as
"depressed," "anxious," or "high risk." Cells are labelled strictly as
above/below the person's own baseline, with a visible missing/low-coverage
state (matching `FeatureWindow.coverage_ratio` from the evidence contract).

## Implemented visual system

- Cream background and white paper cards keep the health context calm rather
  than clinical.
- Forest and sage identify normal/private/local states; amber indicates missing
  or uncertain evidence; muted rose identifies refusal; calm violet gives the
  crisis-aware route the strongest distinction without using alarming red.
- Loading is treated as the seventh visible state because users need an honest
  indication before the local model returns.
- All interactive controls have keyboard focus treatment, state changes use
  appropriate live regions, and reduced-motion preferences disable shimmer.

## Evidence and safety decisions

- The current EvidencePacket contains a single aggregate GPS feature window,
  not daily time-series data. The prototype therefore shows exact window,
  observed value, baseline, coverage, and evidence strength but no fabricated
  chart.
- The project outcome is PHQ-4, but this Week 5 packet does not contain a PHQ-4
  association. The normal card explicitly says the relationship is unavailable
  instead of inferring wellbeing from movement.
- Crisis-aware copy is displayed verbatim from the backend version-controlled
  safety route and never rewritten in React.
- The demonstration packet is labelled synthetic so it cannot be mistaken for
  participant data.

## Acceptance criteria

- Submitting a question produces a visible loading state and disables duplicate
  submission.
- A successful `normal` response shows the exact backend text and evidence
  provenance.
- Every backend `response_mode` selects the corresponding distinct component.
- A local API error becomes generic fallback with technical context and retry.
- The layout remains usable at phone and desktop widths without remote assets.
- A second normal question appends a new turn without removing the first
  question or validated response.
- Enter submits, Shift+Enter creates a new line, and duplicate submissions are
  blocked while a response is pending.
- The header shows the returned local `model_tag` when generation succeeds.
- `MINDSENSE_SLM_RUNTIME=ollama` routes `/respond` through Richard's pinned
  Ollama client; the default remains deterministic for tests.
