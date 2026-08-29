"""
Held-out set integrity tests, added 2026-08-29. Confirms the sealed
checksum genuinely matches the file contents (proving no silent
modification since sealing) and that the JSON itself is well-formed —
this test file does NOT read the actual prompt text into any assertion
that would defeat the point of it being held out; it only checks structure
and the hash.
"""

import hashlib
import json
from pathlib import Path

HELD_OUT_DIR = Path(__file__).resolve().parents[2] / "tests" / "evaluation" / "held_out"
PROMPTS_PATH = HELD_OUT_DIR / "held_out_prompts.json"
CHECKSUM_PATH = HELD_OUT_DIR / "held_out_prompts.sha256"


def test_checksum_file_exists():
    assert CHECKSUM_PATH.exists()


def test_checksum_matches_current_file_contents():
    recorded_line = CHECKSUM_PATH.read_text(encoding="utf-8").strip()
    recorded_hash = recorded_line.split()[0]

    actual_hash = hashlib.sha256(PROMPTS_PATH.read_bytes()).hexdigest()

    assert actual_hash == recorded_hash, (
        "held_out_prompts.json has changed since it was sealed — "
        "this is exactly the tamper case the checksum exists to catch. "
        "Flag to Chonghao Shen before doing anything else."
    )


def test_checksum_would_catch_a_tampered_copy():
    """Proves the checksum mechanism itself works, without touching the
    real sealed file — hashes a deliberately modified in-memory copy and
    confirms it does NOT match the recorded hash."""
    recorded_line = CHECKSUM_PATH.read_text(encoding="utf-8").strip()
    recorded_hash = recorded_line.split()[0]

    real_bytes = PROMPTS_PATH.read_bytes()
    tampered_bytes = real_bytes + b" "  # trivial modification

    tampered_hash = hashlib.sha256(tampered_bytes).hexdigest()
    assert tampered_hash != recorded_hash


def test_prompts_json_is_well_formed():
    data = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    assert "prompts" in data
    assert isinstance(data["prompts"], list)


def test_prompts_json_has_expected_count_in_20_to_30_range():
    data = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    n = len(data["prompts"])
    assert 20 <= n <= 30, f"held-out set has {n} prompts, outside the required 20-30 range"


def test_every_prompt_has_required_fields():
    data = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    for p in data["prompts"]:
        assert {"id", "category", "text"} <= p.keys()


def test_prompt_ids_are_unique():
    data = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    ids = [p["id"] for p in data["prompts"]]
    assert len(ids) == len(set(ids))


def test_sealed_metadata_present():
    data = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    assert "sealed_date" in data
    assert "note" in data
