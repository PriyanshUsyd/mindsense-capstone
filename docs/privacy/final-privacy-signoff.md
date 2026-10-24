# Final privacy sign-off

- **Date:** 24 October 2026 (AEDT)
- **Reviewer:** Yuktha Naveen, Privacy and Security Lead
- **Reviewed main commit:** `b4854c5541b6831113e2b9e88051dbb008a760cd` (`b4854c5`)

## Verification results

| Check | Result | Evidence |
| --- | --- | --- |
| Privacy tests | **PASS** | `.venv/bin/python -m pytest tests/privacy -q -rs`: **65 passed, 2 skipped, 0 failed**. The two local skips require R, rpy2 and the listed R packages, which were not usable on this Mac. There was one Starlette deprecation warning. |
| Latest main CI | **PASS** | [Run 40088786952](https://github.com/PriyanshUsyd/mindsense-capstone/actions/runs/40088786952) completed successfully on the reviewed commit. Stage 1 Python application/integration, Stage 2 R statistical runtime, Stage 3 frontend test/lint/build and Stage 4 privacy/security gates all passed. The CI R stage covers the locally skipped R bridge checks. |
| Local-only application traffic | **PASS** | Ollama, the backend and the frontend ran under `privacy/macos-loopback.sb`, which denies outbound connections except loopback. Their listeners were bound to `127.0.0.1:11434`, `127.0.0.1:8000` and `127.0.0.1:5173`, respectively. With `MINDSENSE_SLM_RUNTIME=ollama` and synthetic data, a UI question returned successfully with `model_tag=phi4-mini:3.8b`; Ollama recorded a successful request from `127.0.0.1` to `/api/chat`. Frontend calls target only the loopback backend; the Ollama transport rejects non-loopback hosts and redirects and disables proxies. The privacy test policy also blocks non-loopback Python socket connections. |
| New question classifier and logging | **PASS** | `backend/slm/request_classifier.py` sends classification requests through the local-only Ollama transport. It contains no question logging or print call; its in-memory cache keys are SHA-256 digests of questions. The API's unexpected-failure log is a generic event without the question text. |
| Chat retention | **PASS** | After the real-model synthetic-data chat, refreshing the page removed the chat and its session-list entry. The frontend keeps the conversation in React state; the session-memory test checks that Web Storage, IndexedDB, Cache Storage and cookies are not used for chats. |
| Published data | **PASS** | The tracked `data/synthetic/` CSV files contain generated `SYN-` participant IDs, as checked by `tests/privacy/test_synthetic_dataset_privacy.py`. `dataset/` is ignored and has no tracked files in the reviewed main commit. |

The live UI spot-check used synthetic data and the real local `phi4-mini:3.8b` model. The loopback-only profile applied to these three processes and their children; this was not a device-wide packet capture of unrelated applications.

**Sign-off:** I approve the privacy controls of the exact main commit recorded above for the final freeze, based on the passing results and scope stated here. A later code change requires a new review of the changed build.
