# Privacy docs — see the real ones at the repo root

**2026-08-29:** the AI-drafted placeholder docs that used to live in this
folder (`architecture-principles.md`, `latency-benchmark.md`) have been
removed — Yuktha Naveen pushed real Week 4 privacy work that supersedes
them. Read these instead:

- [`privacy/privacy_architecture_principles.md`](../../privacy/privacy_architecture_principles.md)
- [`privacy/dependency_privacy_checklist.md`](../../privacy/dependency_privacy_checklist.md)
- [`privacy/initial_dependency_audit.md`](../../privacy/initial_dependency_audit.md)
- [`privacy/week4_privacy_status.md`](../../privacy/week4_privacy_status.md)
- [`benchmarks/slm_latency_benchmark.py`](../../benchmarks/slm_latency_benchmark.py) +
  [`benchmarks/slm_latency_results.json`](../../benchmarks/slm_latency_results.json)
  (she actually ran this — result is honestly "blocked, not measured", no
  Ollama installed on her machine either)

Note the structural mismatch: `build-reference.md` Section 8 says Privacy's
code should live under `backend/privacy/`, but Yuktha's real files are at
the repo root (`privacy/`, `benchmarks/`). Not moved/renamed here — that's
a real-file relocation that should be Yuktha's or Honglin's call, not
something to silently "fix" by relocating someone else's committed work.

`tests/privacy/test_no_network_egress.py` (AI-drafted, still in this repo)
has no equivalent in Yuktha's branch and doesn't overlap with anything she
built — kept as-is.
