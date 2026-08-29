# Privacy & Architecture Principles (Week 4 — Yuktha Naveen's role)

**Status: DRAFT, built to fill a Week 4 gap found on 2026-08-29** (no privacy
documentation existed anywhere in the repo). This restates and operationalizes
`build-reference.md` Section 7 and `skills/privacy-security.md` — Yuktha
should review, adjust, and own this going forward; it is not a substitute for
her running the actual checks.

## What "nothing leaves the device" means, precisely

1. **Network calls:** no runtime network requests of any kind except the
   local Ollama daemon, which must be bound to `127.0.0.1` only — never
   `0.0.0.0` or a LAN-visible address. No cloud API calls, ever, in either
   deterministic or (if ever enabled) planner mode.
2. **Telemetry:** no analytics SDKs, no crash-reporting services (e.g.
   Sentry, Bugsnag), no usage pings, anywhere in the frontend or backend.
3. **Logs:** must never contain raw prompt content that includes real
   behavioural data. Debugging uses synthetic fixtures only
   (`tests/` fixtures, not real CES rows).
4. **Frontend assets:** no CDN-hosted fonts, scripts, or chart libraries —
   everything (React, ECharts, fonts) is installed via npm and bundled
   locally.
5. **Identity:** the evidence contract and every downstream system use an
   opaque `participant_ref` (see `backend/contracts/evidence.py`) — the raw
   CES `uid` never flows past the data pipeline boundary.

## Enforcement, not just inspection

Per `skills/privacy-security.md`, inspection alone isn't enough — see
`tests/privacy/test_no_network_egress.py` (built alongside this doc) for a
`pytest-socket`-based automated check that fails the build on any
unexpected external socket attempt, with the one explicit exception being a
scoped local smoke test against the Ollama daemon on loopback.

## The standing dependency-check rule (applies to every role, every PR)

Every PR that adds a new Python or JS package must include, in its PR
description, a short (~10 minute) privacy spot-check answering:

1. Does this library make network calls on its own (telemetry, update
   checks, license pings)?
2. Does it phone home on import/init, not just when you'd expect it to?
3. Is there a lighter-weight alternative that doesn't need this check at all?

**This is not a one-off Week 4 task** — it applies for the rest of the
project. A PR template checklist item should be added
(`.github/pull_request_template.md`, not yet created — flagged as a small
follow-up for Honglin/Yuktha) so this isn't relying on memory.

## Per-PR automated gate (Week 6 joint task with Priyansh, noted here for continuity)

`skills/privacy-security.md` asks for an automated check on every PR: does
the diff introduce a new network-capable import (`httpx`, `requests`,
`urllib`, `socket`, `aiohttp`) outside `backend/slm/client.py`, the one file
allowed to talk to the loopback Ollama daemon? This is a Week 6 deliverable
per Weekly_Plan.md, not expected yet at Week 4 — noted here so it isn't lost.

## What's still Yuktha's to do (not filled by this doc)

- Actually run the checks above against a real backend once one exists
  (currently there's very little backend code to check).
- The real-machine SLM latency benchmark (see
  `docs/privacy/latency-benchmark.md` — a script exists, but this machine
  doesn't have Ollama installed, so no real numbers could be produced here).
