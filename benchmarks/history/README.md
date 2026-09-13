# Benchmark Run History

This directory preserves immutable copies of generated benchmark evidence. A
stable result path may continue to represent the latest run, but a rerun must
not erase its earlier machine-readable evidence.

## Retention Rule

1. Store every completed or blocked run under
   `benchmarks/history/<benchmark>/<date-time>.<extension>`.
2. Keep the existing non-history path as the latest-result location when code
   or documentation depends on that stable path.
3. Never edit a historical run to make it match a later decision. Add a new
   run or review record instead.
4. Record the short result and historical path in
   `docs/privacy/master-test-register.md`.
5. Clearly label a reconstruction when the original raw result is unavailable;
   never invent missing timestamps, prompts, outputs, or measurements.

## Recovered Replace-in-Place Results

### SLM latency

Six known attempts are retained under `slm_latency/`:

- two blocked setup attempts from 27 August 2026;
- the successful Week 4 run from 29 August 2026;
- the successful Week 5 confirmation from 5 September 2026;
- the Week 6 initial run as an explicitly labelled summary-only reconstruction;
- the successful Week 6 post-merge run from 12 September 2026.

`benchmarks/slm_latency_benchmark.py` now writes every future execution to both
`benchmarks/slm_latency_results.json` and a timestamped history file.

### Prompt 0.4.8 grounding evaluation

The original pre-joint-review result and scorecard, and the later joint-review
consensus versions, are retained under `slm_grounding_prompt048/`. The current
non-history files remain the accepted latest evidence.

## Inventory Decision

As of 13 September 2026, these were the only machine-readable benchmark results
that Git history showed had been replaced. Other benchmark outputs were added
under distinct filenames and therefore already preserve their runs. Revisions
to narrative reports and a whitespace-only scorecard edit were not duplicated;
their history remains available through Git.
