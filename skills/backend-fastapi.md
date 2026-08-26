# Skill: Backend (FastAPI)

Applies to: Data Pipeline, Statistics, SLM Integration, Privacy/Security, Integration/QA leads — anyone writing backend code.

## Structure

- One FastAPI app instance, created via an app-factory function in `backend/api/main.py` — this file is the Integration/QA lead's merge boundary. Do not add business logic here; it only wires routers together.
- Each domain gets its own router file under `backend/api/routers/` (`data.py`, `stats.py`, `chat.py`, `health.py`). A router only calls into its own domain module (`data_pipeline/`, `statistics/`, `slm/`) — it never reaches into another role's folder directly.
- Cross-role communication happens only through `backend/contracts/` (the shared Pydantic models). If your router needs something from another domain, import the contract type, not the other domain's internal function.

## Pydantic contracts

- Every shared model uses strict mode: `model_config = ConfigDict(extra="forbid", strict=True, frozen=True)`. This is non-negotiable — it's what catches a wrong type before it silently reaches another role's code.
- FastAPI auto-generates OpenAPI docs from these same models. Run the app locally and check `/docs` to see the exact JSON shape before writing code against it — don't guess the shape from memory.
- Export the OpenAPI spec deterministically with `scripts/export_openapi.py` so the frontend's generated TypeScript types stay in sync. If you change a contract field, re-run this and commit the regenerated `openapi.json` — don't hand-edit it.

## Error handling

- Return proper HTTP status codes, not 200 with an error string buried in the body. Validation errors from Pydantic already return 422 automatically — don't catch and reformat these unless there's a real reason.
- Never let a raw exception traceback reach the client. Catch known failure modes explicitly (e.g. `insufficient_data`, `model_unavailable`) and return a structured, contract-defined response instead.

## Testing

- Use `httpx`'s test client to exercise endpoints without a real network deployment — this is the standard pattern, not a workaround.
- Every router needs at least one test that actually calls the endpoint through the app, not just a unit test on the underlying function — the two catch different bugs.
- Tests must never make a real network call. If a test needs the Ollama daemon, mark it explicitly (`@pytest.mark.slow`) so it's excluded from the fast pre-push subset.

## What NOT to do

- Don't put SQL in a router — that belongs only in `backend/db.py`.
- Don't import `httpx`, `requests`, or `urllib` anywhere except `backend/slm/client.py` (the one file allowed to talk to the local Ollama daemon).
- Don't add scikit-learn, SQLAlchemy, or Gradio — see `build-reference.md`'s Key Decisions Log for why each was explicitly rejected.
