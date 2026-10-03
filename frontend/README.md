# MindSense — Frontend (Conversational Interface)

React 19 + TypeScript 6, built with **Vite 8**. Owned by the Conversational
Interface Lead (Sheng Wang) — see `skills/frontend-react.md` and
`docs/ui/chat-states-design.md`.

**Status (2026-09-22):** The Week 8 UI hardening pass keeps the local end-to-end
chat flow, removes obsolete synthetic-evidence placeholders, distinguishes
transport failures from handled backend failures, and refreshes the visual
system without changing Richard's response text or safety decisions.

## Rules (do not deviate — see skills/frontend-react.md and build-reference.md)

- Talks to the local FastAPI backend over HTTP only. Never reads SQLite
  directly, never imports backend Python code, never calls Ollama directly.
- No CDN-hosted fonts, scripts, or chart libraries — package everything
  locally (`npm install`, no `<script src="https://...">`). This is a hard
  privacy requirement, not a style preference.
- API types in `src/api/` are currently provisional and hand-written because
  the planned OpenAPI export script does not exist yet. Replace them with
  generated types when that script lands.
- No Redux / React Query / routing library unless a real requirement shows up.
- Do not invent a trend chart from a single aggregated feature window. Add the
  planned local ECharts dependency only after the evidence contract exposes a
  real daily series.

## Structure

```
src/
  api/            generated OpenAPI types + fetch wrapper
  components/     shared, reusable, visually-consistent building blocks
  features/chat/  the 7 chat-state components (docs/ui/chat-states-design.md)
```

## Getting started

```
npm install
npm run dev
```

In another terminal, start the local backend from the repository root. For a
frontend-only demo:

```
uvicorn backend.api.app:app --reload
```

For the real local model:

```
ollama pull phi4-mini:3.8b
MINDSENSE_SLM_RUNTIME=ollama python -m uvicorn backend.api.app:app --reload
```

The frontend posts `{ participant_id, question }` to
`http://127.0.0.1:8000/respond`. `feature_id` is an optional override; when it is
omitted, the backend infers the feature from the question. Evidence is built
from the approved local dataset by the backend and is never assembled in the
browser. Until the response contract returns a structured evidence summary,
the UI shows the validated response text without inventing numeric cards.
