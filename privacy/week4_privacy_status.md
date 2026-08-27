# Week 4 Privacy and Security Status

Owner: Yuktha Naveen, Privacy and Security Lead  
Date: 2026-08-27

## Completed

- Drafted privacy and architecture principles covering network calls, telemetry, logs, analytics, downloads, backups, third-party libraries, architecture boundaries, and crisis/safety handling.
- Created the standing dependency privacy spot-check rule for PR descriptions.
- Created a PR template section that enforces the dependency spot-check.
- Completed the initial dependency audit for the local Capstone workspace.
- Created a reusable local SLM latency benchmark harness.
- Ran the SLM latency benchmark harness on this machine.

## SLM Latency Benchmark Result

Status: blocked, not measured.

Reason:

- No local SLM runtime is currently installed or running on this machine.
- `ollama` was not found on PATH.
- `llama-cli` was not found on PATH.
- The Ollama localhost endpoint `http://127.0.0.1:11434/api/generate` returned connection refused when run outside the sandbox.

Evidence file:

- `Work/benchmarks/slm_latency_results.json`

## Next Action Needed

Once the SLM runtime is installed or started on the benchmark machine, re-run the locked local model from `build-reference.md`:

```sh
python3 benchmarks/slm_latency_benchmark.py --provider ollama --model phi4-mini:3.8b
```

If the team uses a different local stack, use one of:

```sh
python3 benchmarks/slm_latency_benchmark.py --provider openai-compatible --model MODEL --url http://127.0.0.1:8000/v1/chat/completions
python3 benchmarks/slm_latency_benchmark.py --provider cli --cmd "llama-cli -m model.gguf -p {prompt} -n 128"
```

## Proposed Team Update

Privacy architecture draft and dependency PR rule are ready. Initial dependency audit found no app dependency stack in the workspace yet. CES was downloaded locally into the gitignored `dataset/` folder and was not committed. SLM latency benchmark harness is ready and was run locally, but latency could not be measured because no local SLM runtime is installed/running on this machine. Re-run after the locked Ollama `phi4-mini:3.8b` stack is available.
