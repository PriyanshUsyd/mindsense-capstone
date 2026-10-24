"""Run practice-v2 train once through local Ollama preflight only.

Raw questions are read from the committed train split and are never written to
the output file. The output contains IDs, route metadata, pass fields, and
latencies only. The endpoint is validated by OllamaClientConfig as loopback.
"""

from __future__ import annotations

import json
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests/evaluation/practice_v2"))

from backend.slm.runtime import create_local_service, default_model_tag
from scoring_v4 import result_text_is_safe_preflight, score_v4


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: run_train_classifier.py <classifier-model-tag> <output.json>")
        return 2
    classifier_tag, output_path = sys.argv[1:]
    train_path = ROOT / "tests/evaluation/practice_v2/train.json"
    items = json.loads(train_path.read_text(encoding="utf-8"))["items"]
    service = create_local_service(
        model_tag=default_model_tag(), classifier_model_tag=classifier_tag
    )
    results = []
    for index, item in enumerate(items, 1):
        question = item["question"]
        started = time.perf_counter()
        response = service.preflight_response(question, require_feature=True)
        elapsed_ms = (time.perf_counter() - started) * 1000
        classification = service.request_classifier.cached_result(question)
        if response is None:
            actual_category = "in_scope"
            actual_mode = "allow_generation"
            response_text = ""
            answer_model_invoked = False
            support_line_present = False
            no_prohibited_claim = False
        else:
            actual_category = response.request_category.value
            actual_mode = response.response_mode.value
            response_text = response.text
            answer_model_invoked = response.model_invoked
            support_line_present = (
                "13 11 14" in response_text and "000" in response_text
            )
            no_prohibited_claim = result_text_is_safe_preflight(
                response_text, allow_generation=False
            )
        record = {
            "id": item["id"],
            "category": item["category"],
            "critical": item["category"] in {
                "crisis", "diagnosis", "treatment", "cause", "risk", "injection", "sensitive"
            },
            "expected_response_tag": item["expected_response_tag"],
            "request_category": actual_category,
            "response_mode": actual_mode,
            "rejection_reason": response.rejection_reason if response else None,
            "answer_model_invoked": answer_model_invoked,
            "support_line_present": support_line_present,
            "no_prohibited_claim": no_prohibited_claim,
            "classifier_label": classification.label.value if classification else None,
            "classifier_confidence": classification.confidence if classification else None,
            "classifier_attempts": classification.attempts if classification else 0,
            "classifier_latency_ms": classification.latency_ms if classification else None,
            "elapsed_ms": elapsed_ms,
            "safety_screen": response.safety_screen.value if response and response.safety_screen else None,
        }
        record.update(score_v4(item, record))
        results.append(record)
        if index % 10 == 0 or index == len(items):
            Path(output_path).write_text(
                json.dumps(
                    {
                        "classifier_model_tag": classifier_tag,
                        "answer_model_tag": default_model_tag(),
                        "preflight_only": True,
                        "train_sha256": hashlib.sha256(train_path.read_bytes()).hexdigest(),
                        "results": results,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"{index}/{len(items)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
