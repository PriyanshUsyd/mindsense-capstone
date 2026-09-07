# Chat feature

Home for the 7 chat-state components described in
`docs/ui/chat-states-design.md`.

`NormalResponse.tsx` retains the API wrapper established by Priyansh and the
Week 5 visual system merged in PR #10. The Week 6 flow keeps successful turns
visible, accepts subsequent questions, prevents duplicate in-flight requests,
supports Enter-to-send, and can reset to a new conversation.

Every turn posts the frozen-contract synthetic EvidencePacket to
`backend/api/app.py`. That route passes the question through Richard's
`SLMService` request policy, local generation, output grounding, and fail-closed
fallback path. Launching FastAPI with `MINDSENSE_SLM_RUNTIME=ollama` selects the
real manifest-pinned local client without changing frontend code.

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

The normal state is the fully interactive Week 6 flow. Other response states
remain intentionally simple, but Richard's response modes cannot fall into an
unstyled or misleading normal state.

The frozen HTTP request contains one question and one EvidencePacket, not prior
turns. The interface therefore preserves conversation history visually while
each follow-up is independently grounded against the same evidence. Contextual
memory would require an approved shared-contract change and is not claimed here.
