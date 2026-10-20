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

The production local-runtime deadline defaults to 180 seconds because the Week
7 UI pilot measured one cold Phi generation at approximately 134.7 seconds.
It can be changed locally with `MINDSENSE_OLLAMA_TIMEOUT_SECONDS`, restricted to
1-300 seconds. Timeouts, an unavailable daemon, invalid model output, and an
unavailable evidence source produce separate stable `rejection_reason` values
while using the same reviewed fallback copy.

Deterministic crisis/refusal/off-topic routing runs before participant data is
loaded. If the approved local dataset is missing or unreadable, an otherwise
allowed question receives HTTP 200 with `response_mode=generic_fallback`,
`rejection_reason=evidence_source_unavailable`, and `model_invoked=false`.
Filesystem paths and exception text are never returned. Unknown participant
and unknown feature requests remain explicit 404 and 422 responses.

`MINDSENSE_SLM_RUNTIME` accepts only `demo` or `ollama`. An unknown value stops
startup instead of silently choosing another runtime.

`MINDSENSE_DATASET_DIR` selects the dataset (default: the real `dataset/`).
The client-approved synthetic demo dataset is committed at `data/synthetic/`
(see its README; regenerate with `python scripts/make_synthetic_dataset.py`).
Build its cache once per machine with
`MINDSENSE_DATASET_DIR=data/synthetic .venv/Scripts/python -m backend.statistics.bootstrap_cache --all --engine python`
(the cache is not committed: its fingerprint records the exact Python, numpy,
pandas and scipy versions), and start the API with the same variable and the
same `.venv` interpreter. A `bootstrap_cache_unusable` warning in the server
log means the cache does not match and every answer will fall back to no claim. `/health` and `/models` report
`dataset: real | synthetic`; the UI shows "Demo mode: synthetic data" for
`synthetic`. The synthetic cache has its own folder and fingerprint, so it is
never read for the real dataset or the other way round.

## Bounded packet-summary variants

The optional `variant` field accepts `base_llm`, `rag`, `agent` or `rag_agent`.
Omission keeps the behaviour introduced by PR #39: Ollama uses RAG and demo
uses Base. Existing frontend requests remain valid. There is no frontend
variant control in this backend change.

```json
{
  "participant_id": "<approved local lookup value>",
  "question": "How was my movement different from my recent baseline?",
  "feature_id": "gps_distance",
  "model_tag": "phi4-mini:3.8b",
  "variant": "rag_agent"
}
```

Only the existing server-built packet's canonical descriptions are supported.
RAG calls the Data-owned source once. Agent deterministically selects the
registered `get_packet_summary` tool, which wraps that source. RAG+Agent runs
the tool and then retrieval, with distinct context IDs. This does not add a
database, autonomous planner, raw-data access or new statistics.

An allowed non-Base request requires an Ollama client; demo rejects it with 422
before participant lookup. Unknown variants and blank/over-2000-character
questions use the existing private 422 response. Crisis/prohibited preflight
still takes priority. `SafeSLMResponse`, `/models` and model-tag rules are
unchanged. Generated OpenAPI describes the optional enum directly.

Context bindings are constructed from the known source contract before
retrieval, never from returned source metadata. State A, unhealthy packets and
policy rejections skip context preparation. Source/tool errors return the
versioned generic fallback with `rejection_reason=approved_context_unavailable`
and `model_invoked=false`. Existing sanitised errors and `Cache-Control:
no-store` remain in place. No context or tool traces are added to HTTP responses.

## `answer_kind` (display tag only)

`SafeSLMResponse` carries one optional field, `answer_kind`, so the UI can say
why an answer has its form. `SLMService` sets it from the evidence packet and
the route, never from the answer text; it is preserved on the context-variant
path. It changes no answer, route, policy, threshold or statistic.

| Value | When |
|---|---|
| `comparison_shown` | Any generated answer on an `ELIGIBLE` packet, whatever its mode |
| `no_clear_difference` | Generated answer, `PARTIAL` packet, reason `state_c_history_sufficient_evidence_not_reportable` |
| `few_recent_days` | Generated answer, `PARTIAL` packet, reason `state_c_history_sufficient_too_few_recorded_days` |
| `building_baseline` | Generated answer, `PARTIAL` packet, any other reason (State B) |
| `not_enough_data` | Insufficient-data template (State A) |
| `general_limits` | General-uncertainty template |
| `null` | Everything else: refusals, crisis and fallbacks keep using `request_category` / `rejection_reason` |

The API retains PR #39's aggregated-summary configuration; configuration is not
Privacy sign-off. The new validation uses public synthetic packets only.
Personal-data enablement and joint acceptance still require owner review.
See [Week 8 integration and reproducible checks](../../docs/slm/week8-safety-context-integration.md).
