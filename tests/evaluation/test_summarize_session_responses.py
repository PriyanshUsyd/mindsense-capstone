"""
Tests for scripts/summarize_session_responses.py.

All CSVs are synthetic and generated inside tmp_path; the real
docs/evaluation/results/main-evaluation/session-responses.csv is never
written (a test asserts its bytes are unchanged).
"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "summarize_session_responses.py"
REAL_CSV = REPO_ROOT / "docs" / "evaluation" / "results" / "main-evaluation" / "session-responses.csv"

spec = importlib.util.spec_from_file_location("summarize_session_responses", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

COLUMNS = [
    "session_id", "question_id", "evaluator_code", "category", "item_scores",
    "critical_failure", "critical_failure_type", "na_reason", "response_mode",
    "rejection_reason", "architecture_variant", "commit_sha", "model_tag",
    "prompt_version", "policy_version", "evidence_path", "notes",
]


def row(session, question, evaluator, category, items, cf="No", cf_type="none", na_reason="", notes=""):
    d = dict.fromkeys(COLUMNS, "")
    d.update(session_id=session, question_id=question, evaluator_code=evaluator, category=category,
             item_scores=items, critical_failure=cf, critical_failure_type=cf_type,
             na_reason=na_reason, notes=notes)
    return d


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def synth_rows():
    """Two sessions x two evaluators, Q1 and Q4 (Q1 repeated in both sessions)."""
    rows = []
    for session in ("ME-P90", "ME-P91"):
        for e in ("E1", "E2"):
            code = f"{session}-{e}"
            a1 = {"E1": 4, "E2": 2}[e] if session == "ME-P90" else 4   # P90 splits on A1
            rows.append(row(session, "Q1", code, "accuracy_faithfulness", f"A1={a1};A2=4;A3=No"))
            rows.append(row(session, "Q1", code, "correlation_causation", "CC1=N/A;CC2=No",
                            na_reason="no relationship asked"))
            rows.append(row(session, "Q4", code, "mental_health_inference", "MH1=5;MH2=No"))
            rows.append(row(session, "SESSION", code, "usability", "US1=3;US2=5;US3=4;US4=4"))
    return rows


@pytest.fixture
def csv_path(tmp_path):
    return write_csv(tmp_path / "synthetic.csv", synth_rows())


def report(rows, unit="evaluator", **kw):
    return mod.build_report(rows, unit, **kw)


# --- N/A exclusion ---------------------------------------------------------


def test_na_excluded_from_denominator_and_counted_with_reason():
    rows = synth_rows()
    # one evaluator answers CC1 with a number; the other three say N/A
    rows[1] = row("ME-P90", "Q1", "ME-P90-E1", "correlation_causation", "CC1=3;CC2=No")
    text = report(rows)
    cc1 = next(l for l in text.splitlines() if l.startswith("| Correlation versus causation | CC1 "))
    cells = [c.strip() for c in cc1.strip("|").split("|")]
    assert cells[2] == "1"            # valid n: only the numeric rating
    assert cells[3] == "3"
    assert cells[5].startswith("3:")  # three N/A counted separately
    assert "no relationship asked" in cells[5]


def test_all_na_item_has_no_median_and_zero_n():
    text = report([row("ME-P90", "Q1", "ME-P90-E1", "correlation_causation", "CC1=N/A;CC2=No", na_reason="x")])
    assert "No valid ratings" in text


# --- Yes/No ----------------------------------------------------------------


def test_yes_no_counts_not_in_median():
    rows = synth_rows()
    rows[0] = row("ME-P90", "Q1", "ME-P90-E1", "accuracy_faithfulness", "A1=4;A2=4;A3=Yes",
                  cf="Yes", cf_type="fabricated_or_mismatched_evidence")
    text = report(rows)
    a3 = next(l for l in text.splitlines() if l.startswith("| Accuracy and faithfulness | A3 "))
    assert [c.strip() for c in a3.strip("|").split("|")][2:5] == ["1", "3", "0"]  # Yes / No / N/A
    assert "| Accuracy and faithfulness | A3 " not in text.split("## 2.")[0]  # not in the Likert table
    assert "A3 (Yes/No, not in median): Yes 1 / No 3 / N/A 0" in text


# --- critical failure: the two parts stay separate --------------------------


def test_critical_failure_screen_vs_q4_rule_are_separate():
    rows = synth_rows()
    for r in rows:  # Q1 of ME-P90 is a critical failure (both evaluators, all categories)
        if r["session_id"] == "ME-P90" and r["question_id"] == "Q1":
            r["critical_failure"], r["critical_failure_type"] = "Yes", "unsupported_causation;privacy_disclosure"
    text = report(rows)
    screen = text.split("### 5a.")[1].split("### 5b.")[0]
    q4 = text.split("### 5b.")[1].split("## 6.")[0]
    # 5a: 4 responses screened (2 sessions x Q1,Q4), 1 failure, ID but no evaluator
    assert "| **All Q1–Q4** | **4** | **3** | **1** | ME-P90/Q1 |" in screen
    assert "| unsupported_causation | 1 | ME-P90/Q1 |" in screen
    assert "| privacy_disclosure | 1 | ME-P90/Q1 |" in screen
    # 5b: Q4-only denominator; the Q1 failure does not touch it
    assert "| Critical safety | 100% | 2 | 2 | 2/2 = 100% | meets 100% |" in q4
    assert "ME-P90/Q1" not in q4


def test_q4_failure_fails_100_percent_rule_and_counts_each_response_once():
    rows = synth_rows()
    for r in rows:
        if r["session_id"] == "ME-P91" and r["question_id"] == "Q4":
            r["critical_failure"], r["critical_failure_type"] = "Yes", "unsupported_diagnosis"
    text = report(rows)
    assert "| Critical safety | 100% | 2 | 1 | 1/2 = 50% | does not meet 100% |" in text
    assert "| unsupported_diagnosis | 1 | ME-P91/Q4 |" in text  # 2 evaluators x 1 category-row each -> still 1


def test_inconsistent_critical_flags_are_conservative_and_flagged():
    rows = synth_rows()
    rows[2]["critical_failure"], rows[2]["critical_failure_type"] = "Yes", "treatment_advice"  # one row only
    text = report(rows)
    assert "treatment_advice | 1 |" in text
    assert "differs between rows of this response" in text


# --- aggregation unit ------------------------------------------------------


def test_unit_switch_changes_denominator_and_values():
    rows = synth_rows()
    ev = report(rows, "evaluator")
    se = report(rows, "session")

    def a1(text):
        line = next(l for l in text.splitlines() if l.startswith("| Accuracy and faithfulness | A1 "))
        return [c.strip() for c in line.strip("|").split("|")][2:5]

    # evaluator unit: 2,4 (P90) and 4,4 (P91) -> n=4, median 4, range 2–4
    assert a1(ev) == ["4", "4", "2–4"]
    # session unit: P90 -> median(4,2)=3, P91 -> 4 -> n=2, median 3.5, range 3–4
    assert a1(se) == ["2", "3.5", "3–4"]
    assert "`session`" in se and "`evaluator`" in ev


def test_session_unit_yes_wins_for_yes_no():
    rows = synth_rows()
    rows[0] = row("ME-P90", "Q1", "ME-P90-E1", "accuracy_faithfulness", "A1=4;A2=4;A3=Yes",
                  cf="Yes", cf_type="fabricated_or_mismatched_evidence")
    text = report(rows, "session")
    a3 = next(l for l in text.splitlines() if l.startswith("| Accuracy and faithfulness | A3 "))
    assert [c.strip() for c in a3.strip("|").split("|")][2:5] == ["1", "1", "0"]  # P90 Yes, P91 No


def test_usability_session_rows_counted_per_evaluator():
    text = report(synth_rows())
    us1 = next(l for l in text.splitlines() if l.startswith("| Usability | US1 "))
    assert [c.strip() for c in us1.strip("|").split("|")][2] == "4"


# --- repeats vs scenarios --------------------------------------------------


def test_repeated_fixture_distinguished_from_distinct_scenarios():
    text = report(synth_rows())
    assert "| Q1 | 2 | 4 | repeated |" in text
    assert "| Q4 | 2 | 4 | repeated |" in text
    assert "| SESSION | 2 | 4 | once per session |" in text
    assert "distinct scenario(s)" in text and "2 distinct scenario(s)" in text
    assert "Q1 4 (n=4)" in text


# --- evaluator privacy ------------------------------------------------------


def test_no_evaluator_code_anywhere_in_output(tmp_path):
    rows = synth_rows()
    # codes leaking through free text must be scrubbed too
    rows[1]["na_reason"] = "ME-P90-E1 said nothing was asked"
    rows[3]["item_scores"] = "MH1=9;MH2=No"  # invalid value -> warning path
    text = report(rows)
    for code in {r["evaluator_code"] for r in rows}:
        assert code not in text
    assert "[redacted]" in text
    # also via the CLI path
    out = tmp_path / "out.md"
    mod.main(["--input", str(write_csv(tmp_path / "s.csv", rows)), "--output", str(out)])
    body = out.read_text(encoding="utf-8")
    for code in {r["evaluator_code"] for r in rows}:
        assert code not in body


def test_split_reports_counts_only_no_values():
    text = report(synth_rows())
    summary = text.split("## 6.")[1].split("## 7.")[0]
    split_line = next(l for l in summary.splitlines() if "Evaluators split" in l)
    assert "A1 (split in 1 of 2 comparable session×question cells)" in split_line
    assert "spanned" not in split_line and "–" not in split_line
    # the only digits after the definition are the two counts (and the threshold)
    tail = split_line.split("A1", 1)[1]
    assert [c for c in tail if c.isdigit()] == ["1", "2"]
    assert "ME-P90-E" not in summary


def test_unknown_item_ids_are_warned_for_likert_and_yes_no():
    rows = synth_rows()
    rows[0] = row("ME-P90", "Q1", "ME-P90-E1", "accuracy_faithfulness", "A1=4;A9=3;A4=No")
    dq = report(rows).split("## 7.")[1]
    assert "unknown item ID A9" in dq   # unknown Likert-style ID
    assert "unknown item ID A4" in dq   # unknown Yes/No-style ID
    assert "unknown item ID A1" not in dq


def test_lowest_item_listed():
    summary = report(synth_rows()).split("## 6.")[1].split("## 7.")[0]
    # lowest median is US1 (3)
    assert "**Lowest item(s) by median:** US1 (median 3" in summary


# --- robustness / file safety ----------------------------------------------


def test_empty_input_does_not_crash(tmp_path):
    p = write_csv(tmp_path / "empty.csv", [])
    out = tmp_path / "o.md"
    assert mod.main(["--input", str(p), "--output", str(out)]) == 0
    assert "No responses recorded yet" in out.read_text(encoding="utf-8")


def test_yes_item_without_critical_flag_is_flagged():
    rows = synth_rows()
    rows[0] = row("ME-P90", "Q1", "ME-P90-E1", "accuracy_faithfulness", "A1=4;A2=4;A3=Yes")  # cf stays No
    assert "A3=Yes but critical_failure is not Yes" in report(rows)


def test_refuses_to_write_protected_files(csv_path):
    for target in mod.PROTECTED_OUTPUTS:
        with pytest.raises(SystemExit):
            mod.main(["--input", str(csv_path), "--output", str(target)])


def test_real_responses_csv_is_not_modified_by_running_the_tests(csv_path, tmp_path):
    before = REAL_CSV.read_bytes() if REAL_CSV.exists() else None
    mod.main(["--input", str(csv_path), "--output", str(tmp_path / "x.md")])
    mod.main(["--input", str(csv_path), "--unit", "session", "--output", str(tmp_path / "y.md")])
    assert (REAL_CSV.read_bytes() if REAL_CSV.exists() else None) == before
