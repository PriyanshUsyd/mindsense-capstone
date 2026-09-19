# Local FastAPI integration boundary

`app.py` exposes the shared `/respond` endpoint used by the frontend. Both
runtime modes pass every request through Richard's `SLMService`. In Ollama
mode the request may include a manifest-listed `model_tag`; `/models` reports
the default and available candidates without probing or downloading models.

## Runtime modes

The deterministic mode is the default. It is suitable for automated tests and
does not require Ollama:

```bash
python -m uvicorn backend.api.app:app --reload
```

For a real local-model run, install Ollama and pull the manifest-pinned baseline
before using participant or dataset-derived data:

```bash
ollama pull phi4-mini:3.8b
ollama pull qwen3:4b
MINDSENSE_SLM_RUNTIME=ollama python -m uvicorn backend.api.app:app --reload
```

The frontend integration sequence is:

1. `GET /models` and show a selector only when `selection_enabled` is true.
2. Send the selected exact tag as `model_tag` in `POST /respond`.
3. Treat HTTP 422 as a stale or unsupported selection and refresh `/models`.

Omitting `model_tag` selects the manifest default (`phi4-mini:3.8b` at the
time of writing). Demo mode rejects an explicit tag so the UI cannot claim a
model was used when it actually received deterministic stub output.

The Ollama client accepts only manifest-listed model tags and the loopback
`http://127.0.0.1:11434/api/chat` endpoint. If Ollama is unavailable or returns
an invalid draft, `SLMService` fails closed to the version-controlled generic
fallback; the frontend never receives an unvalidated model draft.

`MINDSENSE_SLM_RUNTIME` accepts only `demo` or `ollama`. An unknown value stops
startup instead of silently choosing another runtime.
