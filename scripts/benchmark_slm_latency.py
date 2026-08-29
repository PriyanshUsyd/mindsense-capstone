"""
SLM latency benchmark harness — Week 4 (Yuktha Naveen, Privacy & Security
Lead), per Weekly_Plan.md ("Run the real-machine SLM latency benchmark").

STATUS: this script has NOT been run on real hardware anywhere in this
verification pass — this machine has no Ollama install. See
docs/privacy/latency-benchmark.md. Do not fabricate or estimate results;
run this for real and record the actual numbers.

Usage:
    python scripts/benchmark_slm_latency.py --n-runs 10 [--model phi4-mini:3.8b]

Requires the `ollama` Python package (`pip install ollama`) and a running
local Ollama daemon with the model already pulled.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time

# Representative prompt shaped like a real EvidencePacket -> AssistantDraft
# call (see backend/contracts/evidence.py), kept intentionally small and
# synthetic — never real CES data (skills/privacy-security.md).
SAMPLE_PACKET = {
    "identity": {
        "contract_version": "1.0.0",
        "packet_id": "pkt_bench_0001",
        "model_spec_id": "mixedlm_v1",
        "participant_ref": "synthetic-ref-bench",
    },
    "feature_window": {
        "feature_id": "unlock_count",
        "value": 42.0,
        "coverage_ratio": 0.93,
        "platform": "ios",
    },
    "baseline": {"value": 38.5, "eligibility_status": "eligible"},
    "evidence": {
        "within_person_deviation_estimate": 3.5,
        "direction": "above_baseline",
        "evidence_strength": "moderate",
    },
}

SYSTEM_PROMPT = (
    "You are a non-diagnostic assistant. Given the evidence packet JSON, "
    "return an AssistantDraft JSON object. Never diagnose, never claim "
    "causation, never give treatment or crisis advice."
)


def run_once(model: str) -> float:
    import ollama

    start = time.perf_counter()
    ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(SAMPLE_PACKET)},
        ],
        options={"temperature": 0},
    )
    return time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="phi4-mini:3.8b")
    parser.add_argument("--n-runs", type=int, default=10)
    args = parser.parse_args()

    print(f"Cold-start run (model={args.model})...")
    cold_start_s = run_once(args.model)
    print(f"  cold-start latency: {cold_start_s:.2f}s")

    print(f"Steady-state runs (n={args.n_runs})...")
    latencies = [run_once(args.model) for _ in range(args.n_runs)]

    result = {
        "model": args.model,
        "cold_start_seconds": round(cold_start_s, 3),
        "steady_state_median_seconds": round(statistics.median(latencies), 3),
        "steady_state_p95_seconds": round(
            sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 3
        ),
        "raw_latencies_seconds": [round(latency, 3) for latency in latencies],
    }
    print(json.dumps(result, indent=2))
    print(
        "\nCopy this output into docs/privacy/latency-benchmark.md's "
        "RESULTS section — do not hand-edit numbers."
    )


if __name__ == "__main__":
    main()
