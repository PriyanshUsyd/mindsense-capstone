# Skill: Privacy & Security

Applies to: Privacy & Security Lead primarily, but the standing dependency-check rule applies to everyone.

## What "nothing leaves the device" actually means

This is defined precisely, not left as a vibe:
- No runtime network requests except the local Ollama daemon, and that daemon is bound to loopback (`127.0.0.1`) only.
- No telemetry, no analytics, no crash-reporting services, anywhere in the stack.
- No CDN-hosted fonts, scripts, or chart libraries in the frontend — everything is packaged and served locally.
- No cloud API calls of any kind at runtime, in either the deterministic or (if ever enabled) planner mode.

## The standing dependency rule

Every PR that adds a new package (Python or JS) includes a short privacy spot-check in its description: does this library make network calls on its own, phone home for telemetry, or otherwise reach outside the local machine? This is a 10-minute check, every time, not a one-off Week 4 task — new dependencies get added throughout the project and each one needs this.

## Enforcing it in tests, not just by inspection

Use `pytest-socket` (or equivalent) so that any test attempting an unexpected external socket connection **fails the build automatically** — don't rely on manual review alone to catch this. The one legitimate exception is a scoped, explicitly-allowed local smoke test against the Ollama daemon on loopback.

## Per-PR automated gate

Build a lightweight check that runs on every PR (not a heavy manual audit each time): does the diff introduce a new network-capable import (`httpx`, `requests`, `urllib`, `socket`, `aiohttp`) outside the one file that's allowed to have it (`backend/slm/client.py`)? Flag it automatically rather than relying on someone remembering to check by hand.

## Storage and data handling

- Real CES data lives only in the local, gitignored `dataset/` folder — never committed, never in logs, never in a screenshot shared publicly.
- Use an opaque `participant_ref` in the evidence contract and anywhere participant identity flows through the system — never the raw CES uid.
- Logs must never contain raw prompt content that includes real behavioural data — if you need to debug, use synthetic fixtures.

## What NOT to do

- Don't approve a PR that adds a new dependency without the privacy spot-check note in its description, even under time pressure.
- Don't assume a library is safe because it's popular — actually check what it does on import/init.
- Don't weaken the network-isolation test "just for now" to get something working faster — if something genuinely needs network access, that's a design conversation with the whole team, not a quiet workaround.
