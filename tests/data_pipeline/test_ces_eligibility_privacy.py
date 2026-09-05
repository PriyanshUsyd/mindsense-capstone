"""
Regression test for the 2026-09-05 privacy fix: ces_eligibility.py must
never print a raw CES uid, in its stdout or in any structured output it
returns/writes. See backend/data_pipeline/ces_eligibility.py's module
docstring and privacy/ces-uid-fix.md.

Uses a small synthetic sensing/EMA frame so this test does not depend on
the real (gitignored) CES dataset being present locally.
"""

from __future__ import annotations

import json
import re

import pandas as pd

from backend.data_pipeline.ces_eligibility import compute_eligibility, make_pseudonymizer, summarize

RAW_UIDS = [
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "cccccccccccccccccccccccccccccccc"[:32],
]


def _synthetic_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Participant "a": ineligible (too few valid GPS days, no PHQ-4).
    # Participant "b": ineligible (has PHQ-4, but too few unlock days).
    # Participant "c": eligible (>=20 valid days on both, has PHQ-4).
    rows = []
    for day in range(25):
        rows.append({"uid": RAW_UIDS[0], "is_ios": 1, "loc_dist_ep_0": None, "unlock_num_ep_0": 5.0})
        rows.append({"uid": RAW_UIDS[1], "is_ios": 0, "loc_dist_ep_0": 100.0, "unlock_num_ep_0": None if day > 3 else 1.0})
        rows.append({"uid": RAW_UIDS[2], "is_ios": 1, "loc_dist_ep_0": 200.0, "unlock_num_ep_0": 3.0})
    sensing = pd.DataFrame(rows)
    ema = pd.DataFrame({"uid": [RAW_UIDS[1], RAW_UIDS[2]], "phq4_score": [4, 2]})
    return sensing, ema


def test_summarize_output_contains_no_raw_uid():
    sensing, ema = _synthetic_inputs()
    per_participant = compute_eligibility(sensing, ema)
    result = summarize(per_participant, pseudonymize=make_pseudonymizer())

    dumped = json.dumps(result)
    for raw_uid in RAW_UIDS:
        assert raw_uid not in dumped, f"raw uid {raw_uid!r} leaked into eligibility output"

    # The ineligible participants (a and b) must still be represented, just
    # not by their raw id.
    assert len(result["ineligible_participant_pseudonyms"]) == 2
    assert set(result["ineligible_reasons"].keys()) == set(result["ineligible_participant_pseudonyms"])


def test_pseudonyms_are_not_the_raw_uid_and_dont_trivially_embed_it():
    sensing, ema = _synthetic_inputs()
    per_participant = compute_eligibility(sensing, ema)
    pseudonymize = make_pseudonymizer()
    result = summarize(per_participant, pseudonymize=pseudonymize)

    for pseudonym in result["ineligible_participant_pseudonyms"]:
        assert pseudonym.startswith("p_")
        assert re.fullmatch(r"p_[0-9a-f]{12}", pseudonym)
        for raw_uid in RAW_UIDS:
            assert raw_uid not in pseudonym
            assert raw_uid[:8] not in pseudonym


def test_pseudonyms_differ_across_runs_with_different_salts():
    """Non-reversible AND not correlatable across runs: two independent
    pseudonymizers (as main() creates fresh per invocation) must not agree,
    so a pseudonym from one run can't be matched to a pseudonym from
    another run to re-identify the same participant."""
    sensing, ema = _synthetic_inputs()
    per_participant = compute_eligibility(sensing, ema)

    result_1 = summarize(per_participant, pseudonymize=make_pseudonymizer())
    result_2 = summarize(per_participant, pseudonymize=make_pseudonymizer())

    assert set(result_1["ineligible_participant_pseudonyms"]).isdisjoint(
        result_2["ineligible_participant_pseudonyms"]
    )


def test_same_salt_is_deterministic():
    """A fixed salt (e.g. for a test needing a stable mapping) must produce
    the same pseudonym for the same uid — confirms this is a real function
    of the uid, not randomness masquerading as one."""
    sensing, ema = _synthetic_inputs()
    per_participant = compute_eligibility(sensing, ema)
    fixed_salt = b"0" * 16

    result_1 = summarize(per_participant, pseudonymize=make_pseudonymizer(salt=fixed_salt))
    result_2 = summarize(per_participant, pseudonymize=make_pseudonymizer(salt=fixed_salt))

    assert result_1["ineligible_reasons"] == result_2["ineligible_reasons"]


def test_main_stdout_contains_no_raw_uid(capsys, monkeypatch):
    """End-to-end: run the actual main() entrypoint (the one a human would
    run from the command line) against synthetic data and check real
    captured stdout, not just the returned dict."""
    import backend.data_pipeline.ces_eligibility as mod

    sensing, ema = _synthetic_inputs()
    monkeypatch.setattr(mod, "load_eligibility_inputs", lambda: (sensing, ema))

    mod.main()
    captured = capsys.readouterr()

    for raw_uid in RAW_UIDS:
        assert raw_uid not in captured.out
