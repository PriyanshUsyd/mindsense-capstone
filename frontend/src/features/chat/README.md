# Chat feature

Home for the 7 chat-state components described in
`docs/ui/chat-states-design.md`.

`NormalResponse.tsx` retains the API wrapper established by Priyansh and the
Week 5 visual system merged in PR #10. The Week 6 flow keeps successful turns
visible, accepts subsequent questions, prevents duplicate in-flight requests,
supports Enter-to-send, and can start a new chat.

Session chat memory: every conversation from one browser session is kept in
React state only. The sidebar lists them newest first, titled by the first
question with its time, and clicking one reopens all of its turns, badges and
Details lines. "New chat" starts a fresh conversation without discarding the
others. Chats are kept only while the app is open and are cleared on End
session (after a confirmation), closing or refreshing the tab. Nothing is
written to Web Storage, IndexedDB, cookies or a service-worker cache, and each
`/respond` call still sends only the current question: no history field, and
every call is independent. Below 900 px the sidebar (and so the session list)
is hidden, as before; "New chat" stays in the header.

Every turn posts a local participant alias and question to
`backend/api/app.py`. The backend selects the approved local evidence, then
passes the question through Richard's `SLMService` request policy, local
generation, output grounding, and fail-closed fallback path. Launching FastAPI
with `MINDSENSE_SLM_RUNTIME=ollama` selects the real manifest-pinned local
client without changing frontend code.

In Ollama mode, the page loads `GET /models`, defaults to the backend-selected
model, and lets the user choose another manifest-listed candidate for the next
answer. The exact selected tag is sent as `model_tag` in `POST /respond`.
Selection is locked while a request is running. A 422 response refreshes the
catalog rather than retaining a stale model choice. Demo mode and a failed
catalog request omit `model_tag`, preserving the backend's safe default.

Implemented required UI states:

1. loading/processing;
2. normal response grounded in local evidence;
3. insufficient data/cold start;
4. uncertainty;
5. refusal;
6. generic fallback;
7. crisis-aware fallback.

An additional welcome/ready view provides quick questions before the first
request; it is not counted as one of the seven required states.

`ChatStates.tsx` maps each server `response_mode` directly. The crisis-aware
message is rendered verbatim from `SafeSLMResponse.text`; client code never
paraphrases it. A transport failure and a handled backend error both map to a
recoverable generic fallback, but their status and guidance are intentionally
different so a received HTTP 500 is not described as an unreachable API.

The normal state is the fully interactive Week 6 flow. Other response states
remain intentionally simple, but Richard's response modes cannot fall into an
unstyled or misleading normal state.

The HTTP request contains one question and a local participant alias, not prior
turns or a browser-built EvidencePacket. The interface therefore preserves
conversation history visually while each follow-up is independently grounded
by the backend. Contextual memory would require an approved shared-contract
change and is not claimed here.
