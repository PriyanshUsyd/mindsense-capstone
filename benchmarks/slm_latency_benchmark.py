#!/usr/bin/env python3
"""Local SLM latency benchmark for MindSense.

Supports:
- Ollama local HTTP API: python3 slm_latency_benchmark.py --provider ollama --model llama3.2:3b
- OpenAI-compatible local API: python3 slm_latency_benchmark.py --provider openai-compatible --model MODEL --url http://127.0.0.1:8000/v1/chat/completions
- CLI command: python3 slm_latency_benchmark.py --provider cli --cmd "llama-cli -m model.gguf -p {prompt} -n 128"
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import URLError


PROMPTS = [
    "Summarise this wellbeing evidence in one cautious sentence: sleep duration is lower than the user's baseline, activity is unchanged, and confidence is moderate.",
    "The user does not have enough baseline history. Write a brief response that avoids comparison claims.",
    "A user asks for a diagnosis based on sensor data. Refuse briefly and suggest seeking professional advice.",
    "Convert these evidence flags into a supportive non-clinical message: low confidence, missing activity data, sleep trend available.",
    "Write a generic fallback response for a local model failure without mentioning implementation details.",
]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = (len(ordered) - 1) * pct
    lower = int(idx)
    upper = min(lower + 1, len(ordered) - 1)
    weight = idx - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def run_ollama(model: str, prompt: str, timeout: int, url: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 128, "temperature": 0.2},
    }
    result = post_json(url, payload, timeout)
    return str(result.get("response", ""))


def run_openai_compatible(model: str, prompt: str, timeout: int, url: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 128,
        "temperature": 0.2,
    }
    result = post_json(url, payload, timeout)
    choices = result.get("choices", [])
    if not choices:
        return ""
    return str(choices[0].get("message", {}).get("content", ""))


def run_cli(cmd_template: str, prompt: str, timeout: int) -> str:
    command = cmd_template.format(prompt=prompt)
    completed = subprocess.run(
        command,
        shell=True,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return completed.stdout.strip()


def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    timings: list[float] = []
    outputs: list[dict[str, Any]] = []

    for idx, prompt in enumerate(PROMPTS, start=1):
        started = time.perf_counter()
        if args.provider == "ollama":
            output = run_ollama(args.model, prompt, args.timeout, args.url)
        elif args.provider == "openai-compatible":
            output = run_openai_compatible(args.model, prompt, args.timeout, args.url)
        elif args.provider == "cli":
            output = run_cli(args.cmd, prompt, args.timeout)
        else:
            raise ValueError(f"Unsupported provider: {args.provider}")
        elapsed_ms = (time.perf_counter() - started) * 1000
        timings.append(elapsed_ms)
        outputs.append(
            {
                "prompt_index": idx,
                "latency_ms": round(elapsed_ms, 2),
                "output_chars": len(output),
                "output_preview": output[:160],
            }
        )

    return {
        "provider": args.provider,
        "model": args.model,
        "url": args.url if args.provider != "cli" else None,
        "cmd": args.cmd if args.provider == "cli" else None,
        "runs": len(timings),
        "latency_ms": {
            "min": round(min(timings), 2),
            "mean": round(statistics.mean(timings), 2),
            "median": round(statistics.median(timings), 2),
            "p95": round(percentile(timings, 0.95), 2),
            "max": round(max(timings), 2),
        },
        "outputs": outputs,
    }


def environment() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "ollama_path": shutil.which("ollama"),
        "llama_cli_path": shutil.which("llama-cli"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local SLM latency benchmark.")
    parser.add_argument("--provider", choices=["ollama", "openai-compatible", "cli"], default="ollama")
    parser.add_argument("--model", default="llama3.2:3b")
    parser.add_argument("--url", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--cmd", default="")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--out", default="Work/benchmarks/slm_latency_results.json")
    args = parser.parse_args()

    if args.provider == "cli" and not args.cmd:
        parser.error("--cmd is required when --provider cli is used")

    result: dict[str, Any] = {
        "timestamp_local": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "environment": environment(),
        "status": "ok",
    }

    try:
        result["benchmark"] = benchmark(args)
    except (subprocess.SubprocessError, URLError, TimeoutError, OSError, ValueError) as exc:
        result["status"] = "blocked"
        result["error"] = type(exc).__name__
        result["message"] = str(exc)
        result["benchmark"] = {
            "provider": args.provider,
            "model": args.model,
            "url": args.url if args.provider != "cli" else None,
            "cmd": args.cmd if args.provider == "cli" else None,
        }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
