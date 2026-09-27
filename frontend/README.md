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

Create the project-local Python environment from the repository root first.
Do not start the backend from Anaconda `base` or another global environment:

```bash
./scripts/setup_local_python_env.sh
source .venv/bin/activate
```

The setup script installs `requirements.txt` using
`constraints-python312.txt`, then verifies that NumPy, SciPy, and statsmodels
can be imported together. In the activated environment, start the backend. For
a frontend-only demo:

```bash
python -m uvicorn backend.api.app:app --reload
```

For the real local model:

```bash
ollama pull phi4-mini:3.8b
MINDSENSE_SLM_RUNTIME=ollama python -m uvicorn backend.api.app:app --reload
```

Then start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

The backend's bounded local-model deadline defaults to 180 seconds. During a
slow first request, the UI remains in its loading state and changes its status
to **Local model warming up** after 12 seconds so the cold start is not mistaken
for a broken page. Pre-warming the model before a client demo is still
recommended.

The frontend posts `{ participant_id, question }` to
`http://127.0.0.1:8000/respond`. `feature_id` is an optional override; when it is
omitted, the backend infers the feature from the question. Evidence is built
from the approved local dataset by the backend and is never assembled in the
browser. Until the response contract returns a structured evidence summary,
the UI shows the validated response text without inventing numeric cards.
