# SLM Latency Benchmark (Week 4 — Yuktha Naveen's task)

**Status: NOT COMPLETABLE ON THIS MACHINE — flagged, not faked.**
Weekly_Plan.md requires "the real-machine SLM latency benchmark." This
machine (the one this Week 4 cross-check ran on) does not have Ollama
installed (`ollama` is not on PATH, confirmed 2026-08-29), so no real
phi4-mini:3.8b latency numbers can be produced here. **Do not treat any
latency figure as real unless it was produced by actually running
`scripts/benchmark_slm_latency.py` below on a machine with Ollama +
phi4-mini:3.8b installed** — this is exactly the kind of number that should
never be estimated or guessed, since it directly informs whether the local
SLM approach is even viable on typical hardware.

A runnable benchmark script is provided so Yuktha (or anyone with Ollama
installed) can produce the real number without having to write the
harness from scratch.

## Running it for real

```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Pull the pinned model tag from backend/slm/model_manifest.yaml:
ollama pull phi4-mini:3.8b
# 3. Run the benchmark:
python scripts/benchmark_slm_latency.py --n-runs 10
```

## What it measures

- Cold-start latency (first call after the daemon starts / model loads).
- Steady-state latency (median/p95 over N subsequent calls) for a
  representative schema-constrained JSON request matching the
  `AssistantDraft` shape (see `backend/contracts/evidence.py`).
- Runs at `temperature=0`, matching the actual production call pattern
  (`skills/slm-ollama.md`) — this is not a chat-completion benchmark.

## Why this matters for Week 4 specifically

The client's spec assumes a locally-deployed SLM is viable on normal
hardware. If steady-state latency is too high on a typical participant/pilot
laptop, that's a Week 4-level risk to surface now (per the Weekly_Plan.md
framing: "every foundational decision that gates later work gets made
concretely this week"), not something discovered during the Week 7 pilot.

**Action needed:** Yuktha runs this on her own machine (and ideally on
whatever machine will actually run the pilot/evaluation sessions) and
commits the real output here, replacing this placeholder section:

```
RESULTS: <pending — not yet run on real hardware>
```
