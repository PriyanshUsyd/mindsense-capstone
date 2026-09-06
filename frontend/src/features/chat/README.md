# Chat feature

Home for the 7 chat-state components described in
`docs/ui/chat-states-design.md`.

`NormalResponse.tsx` retains the API wrapper established by Priyansh and now
provides the Week 5 conversational prototype. It posts a frozen-contract,
synthetic EvidencePacket to `backend/api/app.py`, which passes the request
through Richard's `SLMService` safety, request-policy, and output-grounding
path. The default backend uses its deterministic local demo client; switching
the backend to Ollama does not require a frontend contract change.

Implemented required UI states:

1. loading/processing;
2. normal response with evidence provenance;
3. insufficient data/cold start;
4. uncertainty;
5. refusal;
6. generic fallback;
7. crisis-aware fallback.

An additional welcome/ready view provides quick questions before the first
request; it is not counted as one of the seven required states.

`ChatStates.tsx` maps each server `response_mode` directly. The crisis-aware
message is rendered verbatim from `SafeSLMResponse.text`; client code never
paraphrases it. A transport failure maps to generic fallback and offers retry.

Only the normal state is the fully exercised Week 5 product flow. The other
response states are structurally implemented so Richard's backend responses
cannot fall into an unstyled or misleading normal state; richer Week 6
interactions can extend them without changing the response contract.
