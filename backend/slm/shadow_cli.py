"""Run one real Week 5 SLM response without waiting for the chat UI.

Example, from the repository root::

    python -m backend.slm.shadow_cli \
      --packet tests/slm/fixtures/week5_gps_eligible.json \
      --question "How was my movement different from my recent baseline?"

The packet must already satisfy the shared EvidencePacket contract.  The CLI
does not read CES files and sends requests only to the loopback Ollama daemon.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from backend.contracts.evidence import EvidencePacket
from backend.slm.runtime import create_local_service, listed_model_tags


def load_packet(path: Path) -> EvidencePacket:
    try:
        return EvidencePacket.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValidationError) as exc:
        raise ValueError("packet file is not a valid EvidencePacket") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one schema-constrained MindSense SLM shadow response."
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument(
        "--model",
        default="phi4-mini:3.8b",
        choices=listed_model_tags(),
        help="Pinned comparison candidate; Phi is a baseline, not a final choice.",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    try:
        packet = load_packet(args.packet)
        response = create_local_service(
            model_tag=args.model,
            timeout_seconds=args.timeout,
        ).respond(packet, args.question)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(response.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
