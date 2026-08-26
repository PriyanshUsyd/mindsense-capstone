# Skill: Frontend (React + TypeScript + ECharts)

Applies to: Conversational Interface Lead primarily.

## Stack

React + TypeScript, built with Vite. No Gradio, no Streamlit, no plain server-rendered templates — see `build-reference.md`'s decisions log for why React specifically won for this project (7 mutually-exclusive chat states staying visually consistent as reusable typed components, while 6 other people build backend in parallel).

## Working against the contract, not against finished backend code

The backend exports its OpenAPI schema deterministically (`scripts/export_openapi.py`). Generate TypeScript types from it and commit the generated file — check it for drift in CI. This means you can build the entire UI against real, typed mock responses from Day 1, without waiting for the actual backend logic to be finished. If a contract field changes, your build should fail at compile time, not silently render `undefined` at runtime — that's the entire point of doing this through TypeScript rather than loose JSON.

The frontend must never read SQLite directly, import backend Python code, or call Ollama directly — it only ever talks to the local FastAPI backend over HTTP.

## The 7 required chat states

Build each as its own component, sharing a common visual language (see the design-token guidance if one exists in `docs/`):
1. Normal response
2. Insufficient-data / cold-start
3. Uncertainty (evidence exists but is weak)
4. Refusal (out-of-scope request)
5. Generic fallback (model/validation failure)
6. Crisis-aware fallback
7. (If applicable) loading/processing state while a response is being generated

Each state must be **visually distinct** from the others — a doctor or user should never have to read carefully to tell "normal answer" apart from "uncertain answer" apart from "refusal."

## Charts — Apache ECharts, calendar heatmap

Use ECharts' native calendar coordinate system for daily/weekly personal trend visualisation — this was chosen specifically because it has a built-in calendar-heatmap path, unlike Chart.js which would need an unmaintained plugin. Initialise the chart in an effect after the container mounts, update it when typed trend data changes, and call `dispose()` on cleanup to avoid memory leaks across chat sessions.

**Never colour a cell as "depressed," "anxious," or "high risk."** Label values as above/below the person's own baseline only, with a visible missing/low-coverage state — this directly reflects the non-diagnostic boundary from the evidence contract; the UI is not exempt from that rule just because it's presentation, not logic.

## What NOT to do

- Don't add Redux, React Query, a routing library, or global state management unless a specific, real requirement appears — this is a small app with a handful of screens, not a large platform.
- Don't hand-write API request/response types — always generate them from the OpenAPI export.
- Don't load fonts, scripts, or chart libraries from a CDN — package everything locally, consistent with the "nothing leaves the device" privacy requirement.
