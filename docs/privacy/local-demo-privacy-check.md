# Local Demo Privacy Procedure

Owner: Yuktha Naveen. Scope confirmed on 26 September 2026: a trusted operator
on one Mac, using the existing local demo. This is not real-user account or
participant-deployment approval. See the dated master register for results.

## Start the Verified Configuration

Use three terminals in the repository root. Stop any existing demo services
you started first; do not kill another person's process or reuse an unknown
daemon. These commands apply temporary restrictions to the new processes and
their children, not to the entire computer. They do not change Wi-Fi or the
system firewall. The macOS profile permits ordinary filesystem access but
denies outbound networking except loopback; it is not a data-file sandbox.

Terminal 1, installed local Ollama:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 \
LLAMA_ARG_CORS_ORIGINS=http://127.0.0.1:8000 \
  /usr/bin/sandbox-exec -f privacy/macos-loopback.sb ollama serve
```

The second variable is for the bundled llama.cpp runner, not Ollama's outer
HTTP server. Ollama 0.33.2 on this Mac passed it to the child runner. Recheck
after runtime upgrades; do not assume other versions preserve this setting.
An untrusted Origin must not receive matching or wildcard
`Access-Control-Allow-Origin`. HTTP 200 alone does not mean CORS granted access.
This is browser-origin hardening, not authentication against local programs.

Terminal 2, backend and embedded R:

```bash
MINDSENSE_SLM_RUNTIME=ollama RPY2_CFFI_MODE=ABI PYTHONPATH=. \
  /usr/bin/sandbox-exec -f privacy/macos-loopback.sb \
  .venv/bin/python -m uvicorn backend.api.app:app \
  --host 127.0.0.1 --port 8000 --no-access-log
```

Terminal 3, frontend server:

```bash
/usr/bin/sandbox-exec -f privacy/macos-loopback.sb \
  npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173`. The browser is a separate process and is **not**
sandboxed by these commands. Browser verification covers the reviewed local
assets/fetch destination, the existing redirect control, UI operation, and
non-persistence regressions, not a browser-wide or whole-device offline test.
Use a dedicated demo tab, avoid unrelated/untrusted tabs, and keep the machine
under the operator's control. Do not use this setup as a multi-user service.

All model weights and dependencies must already be installed. Downloads and
advisory scans are setup/maintenance activities; do not disable the runtime
network boundary to make a missing dependency download succeed.

## Logging, Storage and Retention

- Do not enable request/prompt debug logging, remote telemetry, or shell
  tracing containing input. The tested backend command disables access logs.
- Handled API errors are generic and noncacheable. Unexpected exceptions
  caught at the API boundary emit only `event=local_api_unexpected_failure`,
  without request values, exception messages or traceback. This does not
  sanitise arbitrary logs printed independently by future libraries.
- Chat text is transient React state. Clear it with New conversation and
  close the tab after testing. No Web Storage writes occurred in the tested
  paths; this is not forensic erasure of browser or OS memory.
- The existing client requests a five-minute model keep-alive. Native prompt
  caching was observed in memory; it must not be described as immediate
  deletion. Unload the model and stop the demo daemon at session end.
- Keep CES in ignored `dataset/`. Its directory on Yuktha's Mac was restricted
  to the owner with `chmod go-rwx dataset`; contents were not edited. This does
  not protect against root or processes running as the same account.
- Do not commit per-person bootstrap rows, even if identifiers are renamed or
  hashed. Use the ignored `outputs/` tree only if that cache is implemented;
  create private directories with mode 700 and files with mode 600, or use
  `umask 077`. The current runtime does not yet enable this proposed cache.
- Retain only redacted result metadata in Git. Keep raw debugging material
  local, use synthetic input, and remove temporary debug logs after review.
  Never publish request bodies, raw CES IDs, person-level output tables or
  screenshots of participant summaries as test artifacts.
- Real personal-summary retrieval remains disabled/unapproved. Existing
  synthetic context validation is covered by tests; enabling real sources
  requires a separate schema, ownership, retention and deletion review.

## End the Demo

Clear/close the demo tab. With no requests in progress, unload the model:

```bash
curl --noproxy '*' http://127.0.0.1:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"phi4-mini:3.8b","keep_alive":0}'
curl --noproxy '*' http://127.0.0.1:11434/api/ps
```

The second response must list no loaded models for this single-model demo.
Then stop each of the three processes in its own terminal with Ctrl+C. Confirm
the runner is gone and the demo ports no longer listen. Unloading/stopping is
a lifecycle control, not a claim of cryptographic erasure of RAM or swap.

## Recheck

```bash
MINDSENSE_CI_SCOPE=sealed-excluded RPY2_CFFI_MODE=ABI PYTHONPATH=. \
  /usr/bin/sandbox-exec -f privacy/macos-loopback.sb \
  .venv/bin/python -m pytest -q \
  --ignore=tests/evaluation/held_out \
  --ignore=tests/evaluation/test_held_out_integrity.py
/usr/bin/sandbox-exec -f privacy/macos-loopback.sb npm --prefix frontend test
```

Do not alter the sealed-set exclusion before the Evaluation Lead's authorised
release. No test in this procedure is permission to deploy to real participants.
