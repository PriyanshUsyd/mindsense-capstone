# Chat feature

Home for the 7 chat-state components described in
`docs/ui/chat-states-design.md`.

**`NormalResponse.tsx` filled in by Priyansh Khandelwal (Integration/QA) —
Sheng Wang did not deliver this, per Weekly_Plan.md Week 5: "Integrate the
UI against the real SLM stub; build the 'normal response' state fully."**
No commit from Sheng Wang exists anywhere in this repository as of
2026-09-05. Wired to the real backend at `backend/api/app.py`, which runs
requests through the actual `SLMService` (safety gate, output grounding,
request policy) via a deterministic demo client — not a hardcoded string,
and not the real Ollama model either (see `backend/api/app.py`'s own
docstring for how to switch to the real local model).

The remaining 6 states (insufficient-data/cold-start, uncertainty,
refusal, generic fallback, crisis-aware fallback, loading) are still
Week 6 scope per the original plan — rough sketches only, not required to
work yet.
