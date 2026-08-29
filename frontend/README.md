# MindSense — Frontend (Conversational Interface)

React + TypeScript, built with Vite. Owned by the Conversational Interface
Lead (Sheng Wang) — see `skills/frontend-react.md` and
`docs/ui/chat-states-design.md`.

**Status:** Week 4 scaffold only, built to fill a gap found on 2026-08-29
(no `frontend/` folder existed in the repo before this). Sheng Wang should
treat this as a starting point to review/adjust, not a finished setup.

## Rules (do not deviate — see skills/frontend-react.md and build-reference.md)

- Talks to the local FastAPI backend over HTTP only. Never reads SQLite
  directly, never imports backend Python code, never calls Ollama directly.
- No CDN-hosted fonts, scripts, or chart libraries — package everything
  locally (`npm install`, no `<script src="https://...">`). This is a hard
  privacy requirement, not a style preference.
- API types in `src/api/` are generated from the backend's OpenAPI export,
  never hand-written.
- No Redux / React Query / routing library unless a real requirement shows up.
- Charts: Apache ECharts (calendar-heatmap coordinate system), not yet added
  as a dependency — add it when the first chart component is actually built.

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
