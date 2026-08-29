# Generated API types

Per `build-reference.md` Section 8 and `skills/frontend-react.md`: this
folder holds TypeScript types generated from the backend's OpenAPI export
(`scripts/export_openapi.py`, not yet built) plus a thin fetch wrapper.

Do not hand-write request/response types here — regenerate from the OpenAPI
schema once `backend/api/` exists, and check for drift in CI.
