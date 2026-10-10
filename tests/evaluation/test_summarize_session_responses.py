"""
Tests for scripts/summarize_session_responses.py.

All CSVs are synthetic and generated inside tmp_path; the real
docs/evaluation/results/main-evaluation/session-responses.csv is never
written (a test asserts its bytes are unchanged).
"""

from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "summarize_session_responses.py"
REAL_CSV = REPO_ROOT / "docs" / "evaluation" / "results" / "main-evaluation" / "session-responses.csv"

spec = importlib.util.spec_from_file_location("summarize_session_responses", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SHA = "400883667657c8c70c025de4e1dbbc22cda3b074"
LABEL = "rc-eval-2"
OTHER_SHA = "687a50ea233ba7e3653b15d79ed84d5da7db6a91"
INSUFFICIENT = "insufficient ratings (n < 5)"
SESSIONS = ("ME-P90", "ME-P91", "ME-P92")

COLUMNS = [
    "session_id", "question_id", "evaluator_code", "category", "item_scores",
    "critical_failure", "critical_failure_type", "na_reason", "response_mode",
    "rejection_reason", "architecture_variant", "commit_sha", "model_tag",
    "prompt_version", "policy_version", "evidence_path", "notes",
]


def row(session, question, evaluator, category, items, cf="No", cf_type="none", na_reason=""):
    d = dict.fromkeys(COLUMNS, "")
    d.update(session_id=session, question_id=question, evaluator_code=evaluator, category=category,
             item_scores=items, critical_failure=cf, critical_failure_type=cf_type, na_reason=na_reason, commit_sha=SHA,
             evidence_path=f"docs/evaluation/evidence/main-evaluation/{session}/{question}/")
    return d


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def synth_rows(sessions=SESSIONS):
    """`sessions` x two evaluators; Q1 and Q4 (Q1 repeated across sessions) + SESSION.
    With 3 sessions every item has 6 valid ratings (>= 5); with 2 sessions, 4 (< 5)."""
    rows = []
    for session in sessions:
        for e in ("E1", "E2"):
            code = f"{session}-{e}"
            a1 = {"E1": 4, "E2": 2}[e] if session == "ME-P90" else 4   # first session splits on A1
            rows.append(row(session, "Q1", code, "accuracy_faithfulness", f"A1={a1};A2=4;A3=No"))
            rows.append(row(session, "Q1", code, "correlation_causation", "CC1=N/A;CC2=No",
                            na_reason="no relationship asked"))
            rows.append(row(session, "Q4", code, "mental_health_inference", "MH1=5;MH2=No"))
            rows.append(row(session, "SESSION", code, "usability", "US1=3;US2=5;US3=4;US4=4"))
    return rows


def report(rows, unit="evaluator", **kw):
    return mod.build_report(rows, unit, **kw)


def cells_of(text, prefix):
    line = next(l for l in text.splitlines() if l.startswith(prefix))
    return [c.strip() for c in line.strip("|").split("|")]


def dim_cells(text, label):
    """Row of the section-2 dimension table (section 1 has rows with the same label)."""
    section = text.split("## 2.")[1].split("## 3.")[0]
    return cells_of(section, f"| {label} | ")


@pytest.fixture
def csv_path(tmp_path):
    return write_csv(tmp_path / "synthetic.csv", synth_rows())


# --- n < 5 suppression -----------------------------------------------------


def test_item_with_fewer_than_5_valid_ratings_shows_no_median_or_range():
    text = report(synth_rows(SESSIONS[:2]))  # n = 4 everywhere
    a1 = cells_of(text, "| Accuracy and faithfulness | A1 ")
    assert a1[2] == "4"                      # the valid n itself is still shown
    assert a1[3] == INSUFFICIENT and a1[4] == INSUFFICIENT
    dim = dim_cells(text, "Accuracy and faithfulness")
    assert dim[2] == f"A1 {INSUFFICIENT}, A2 {INSUFFICIENT}"
    assert dim[3] == f"A1 {INSUFFICIENT}, A2 {INSUFFICIENT}"


def test_exactly_5_valid_ratings_is_reported():
    rows = synth_rows()
    # drop one evaluator's accuracy row -> 5 valid A1/A2 ratings
    rows = [r for r in rows if not (r["evaluator_code"] == "ME-P92-E2" and r["category"] == "accuracy_faithfulness")]
    a1 = cells_of(report(rows), "| Accuracy and faithfulness | A1 ")
    assert a1[2:5] == ["5", "4", "2–4"]


def test_mixed_dimension_cell_names_the_insufficient_item():
    rows = synth_rows()
    for r in rows:  # A2 = N/A for two of the six evaluators -> A2 has 4 valid ratings
        if r["category"] == "accuracy_faithfulness" and r["evaluator_code"] in ("ME-P91-E1", "ME-P91-E2"):
            r["item_scores"] = r["item_scores"].replace("A2=4", "A2=N/A")
            r["na_reason"] = "not asked"
    dim = dim_cells(report(rows), "Accuracy and faithfulness")
    assert dim[1] == "A1 6, A2 4"
    assert dim[2] == f"A1 4, A2 {INSUFFICIENT}"
    assert dim[3] == f"A1 2–4, A2 {INSUFFICIENT}"


def test_n_ge_5_dimension_cell_shows_medians_and_shared_n():
    dim = dim_cells(report(synth_rows()), "Accuracy and faithfulness")
    assert dim[1] == "6" and dim[2] == "A1 4, A2 4 (n=6)" and dim[3] == "A1 2–4, A2 4"


def test_yes_no_counts_hidden_below_5_valid_answers():
    text = report(synth_rows(SESSIONS[:2]))
    a3 = cells_of(text, "| Accuracy and faithfulness | A3 ")
    assert a3[2] == INSUFFICIENT and a3[3] == "–"
    assert "A3 (Yes/No, not in median): " + INSUFFICIENT in text
    assert "Yes 0 / No 4" not in text


def test_yes_no_counts_shown_at_5_or_more_and_na_not_counted_as_valid():
    rows = synth_rows()
    rows[0] = row(SESSIONS[0], "Q1", "ME-P90-E1", "accuracy_faithfulness", "A1=4;A2=4;A3=Yes",
                  cf="Yes", cf_type="fabricated_or_mismatched_evidence")
    text = report(rows)
    a3 = cells_of(text, "| Accuracy and faithfulness | A3 ")
    assert a3[2:6] == ["1", "5", "0", "6"]
    assert "A3 (Yes/No, not in median): Yes 1 / No 5 / N/A 0" in text
    assert "| Accuracy and faithfulness | A3 " not in text.split("## 2.")[0]  # not in the Likert table


def test_lowest_item_ignores_insufficient_items():
    assert "not reported" in report(synth_rows(SESSIONS[:2])).split("## 6.")[1].split("##")[0]
    assert "**Lowest item(s) by median** (items with ≥5 valid ratings): US1 (median 3" in report(synth_rows())


# --- N/A -------------------------------------------------------------------


def test_na_excluded_from_denominator_and_counted_with_reason():
    rows = synth_rows()
    for r in rows:  # five evaluators answer CC1 with a number; one says N/A
        if r["category"] == "correlation_causation":
            r["item_scores"] = "CC1=3;CC2=No"
    for r in rows:
        if r["category"] == "correlation_causation" and r["evaluator_code"] == "ME-P92-E2":
            r["item_scores"] = "CC1=N/A;CC2=No"
    cc1 = cells_of(report(rows), "| Correlation versus causation | CC1 ")
    assert cc1[2] == "5" and cc1[3] == "3"
    assert cc1[5] == "1 (reasons in restricted record)" and "no relationship asked" not in report(rows)


def test_all_na_item_has_no_median_and_zero_n():
    text = report(synth_rows())
    cc1 = cells_of(text, "| Correlation versus causation | CC1 ")
    assert cc1[2] == "0" and cc1[3] == "–" and cc1[5] == "6 (reasons in restricted record)"
    assert "No valid ratings" in text


# --- critical failures: public view is by question only ---------------------


def with_failures(rows):
    for r in rows:  # first session's Q1 fails (types: causation + privacy)
        if r["session_id"] == SESSIONS[0] and r["question_id"] == "Q1":
            r["critical_failure"], r["critical_failure_type"] = "Yes", "unsupported_causation;privacy_disclosure"
    return rows


def test_critical_failure_screen_vs_q4_rule_are_separate_and_by_question():
    text = report(with_failures(synth_rows()))
    screen = text.split("### 5a.")[1].split("### 5b.")[0]
    q4 = text.split("### 5b.")[1].split("## 6.")[0]
    assert "| Q1 | 3 | 2 | 1 |" in screen
    assert "| Q4 | 3 | 3 | 0 |" in screen
    assert "| **All Q1–Q4** | **6** | **5** | **1** |" in screen
    assert "| unsupported_causation | 1 |" in screen and "| privacy_disclosure | 1 |" in screen
    assert "| Critical safety | 100% | 3 | 3 | 3/3 = 100% | meets 100% |" in q4
    assert "ME-P9" not in text


def test_q4_failure_fails_100_percent_rule_and_counts_each_response_once():
    rows = synth_rows()
    for r in rows:
        if r["session_id"] == SESSIONS[1] and r["question_id"] == "Q4":
            r["critical_failure"], r["critical_failure_type"] = "Yes", "unsupported_diagnosis"
    text = report(rows)
    assert "| Critical safety | 100% | 3 | 2 | 2/3 = 67% | does not meet 100% |" in text
    assert "| unsupported_diagnosis | 1 |" in text  # two evaluators' rows -> still one response


def test_inconsistent_critical_flags_are_conservative_and_counted_by_kind():
    rows = synth_rows()
    rows[2]["critical_failure"], rows[2]["critical_failure_type"] = "Yes", "treatment_advice"  # one row only
    text = report(rows)
    assert "| treatment_advice | 1 |" in text
    assert "| critical_failure differs between rows of one response | 1 |" in text


# --- aggregation unit ------------------------------------------------------


def test_unit_switch_changes_denominator_and_values():
    rows = synth_rows(SESSIONS + ("ME-P93", "ME-P94"))  # 10 evaluator ratings, 5 sessions
    ev, se = report(rows, "evaluator"), report(rows, "session")
    # evaluator unit: 2,4,4,4,4,4,4,4,4,4 -> n=10, median 4
    assert cells_of(ev, "| Accuracy and faithfulness | A1 ")[2:5] == ["10", "4", "2–4"]
    # session unit: first session -> median(4,2)=3; others 4 -> n=5, median 4, range 3–4
    assert cells_of(se, "| Accuracy and faithfulness | A1 ")[2:5] == ["5", "4", "3–4"]
    assert "`session`" in se and "`evaluator`" in ev


def test_session_unit_yes_wins_for_yes_no():
    rows = synth_rows(SESSIONS + ("ME-P93", "ME-P94", "ME-P95"))
    rows[0] = row(SESSIONS[0], "Q1", "ME-P90-E1", "accuracy_faithfulness", "A1=4;A2=4;A3=Yes",
                  cf="Yes", cf_type="fabricated_or_mismatched_evidence")
    a3 = cells_of(report(rows, "session"), "| Accuracy and faithfulness | A3 ")
    assert a3[2:4] == ["1", "5"]  # Yes / No across 6 sessions' collapsed answers


def test_usability_session_rows_counted_per_evaluator():
    assert cells_of(report(synth_rows()), "| Usability | US1 ")[2] == "6"


# --- repeats vs scenarios (question level) ----------------------------------


def test_repeated_fixture_distinguished_from_distinct_scenarios():
    text = report(synth_rows())
    assert "| Q1 | 3 | 6 | repeated |" in text
    assert "| Q4 | 3 | 6 | repeated |" in text
    assert "| SESSION | 3 | 6 | once per session |" in text
    assert "2 distinct scenario(s)" in text
    assert "Q1 4 (n=6)" in text


def test_per_question_medians_follow_the_small_n_rule():
    text = report(synth_rows(SESSIONS[:2]))
    assert "Q1 " + INSUFFICIENT in text and "Q1 4 (n=" not in text


# --- privacy: no evaluator code, no session_id in the public output ---------


def test_public_output_has_no_evaluator_code_or_session_id(tmp_path):
    rows = with_failures(synth_rows())
    rows[1]["na_reason"] = "ME-P90-E1 and ME-P91 said nothing was asked"  # codes/IDs in free text
    rows[3]["item_scores"] = "MH1=9;MH2=No;ZZ9=3"                          # warning paths
    text = report(rows)
    for token in {r["evaluator_code"] for r in rows} | {r["session_id"] for r in rows}:
        assert token not in text
    assert "said nothing was asked" not in text  # na_reason is never published
    assert "CSV line" not in text
    out = tmp_path / "out.md"
    mod.main(["--input", str(write_csv(tmp_path / "s.csv", rows)), "--output", str(out), "--expected-commit", SHA, "--build-label", LABEL])
    body = out.read_text(encoding="utf-8")
    for token in {r["evaluator_code"] for r in rows} | {r["session_id"] for r in rows}:
        assert token not in body


PII = ("talked to Alice Smith about this", "see email from moet2244", "call 0412 345 678", "+61-2-9351-0000")


@pytest.mark.parametrize("column", ["na_reason", "notes", "rejection_reason", "response_mode", "model_tag", "evidence_path"])
@pytest.mark.parametrize("pii", PII)
def test_free_text_columns_never_reach_the_public_output(column, pii, tmp_path):
    rows = synth_rows()
    for r in rows:
        r[column] = pii
        if column == "na_reason":  # make the reason matter: some N/A answers
            r["item_scores"] = r["item_scores"].replace("A2=4", "A2=N/A")
    body_text = report(rows)
    out = tmp_path / "out.md"
    mod.main(["--input", str(write_csv(tmp_path / "s.csv", rows)), "--output", str(out), "--expected-commit", SHA, "--build-label", LABEL])
    for body in (body_text, out.read_text(encoding="utf-8")):
        assert pii not in body
        for fragment in ("Alice", "Smith", "moet2244", "0412", "9351"):
            assert fragment not in body


@pytest.mark.parametrize("pii", PII)
def test_out_of_vocabulary_failure_type_is_counted_as_other_and_warned(pii):
    rows = synth_rows()
    for r in rows:
        if r["session_id"] == SESSIONS[0] and r["question_id"] == "Q1":
            r["critical_failure"], r["critical_failure_type"] = "Yes", f"unsupported_causation;{pii}"
    text = report(rows)
    assert pii not in text and "unlisted" not in text
    assert "| other (value outside the defined types) | 1 |" in text
    assert "| unknown critical_failure_type | 1 |" in text
    internal = report(rows, internal=True)
    assert pii in internal  # exact value only in the restricted record


@pytest.mark.parametrize("pii", PII)
def test_unknown_item_id_is_not_printed_publicly(pii):
    rows = synth_rows()
    rows[0]["item_scores"] += f";{pii}=3"
    text = report(rows)
    assert pii not in text and "Alice" not in text
    assert "| unknown item ID | 1 |" in text


def test_internal_output_has_na_reasons_public_does_not():
    rows = synth_rows()
    for r in rows:
        if r["category"] == "accuracy_faithfulness":
            r["item_scores"] = r["item_scores"].replace("A2=4", "A2=N/A")
            r["na_reason"] = PII[0]
    assert PII[0] not in report(rows)
    inner = report(rows, internal=True)
    assert PII[0] in inner and "A2 N/A: 6 (reasons in restricted record)" in inner
    assert "| A2 | talked to Alice Smith about this | 6 |" in inner


def test_public_note_is_at_the_top():
    text = report(synth_rows())
    note = text.split("\n\n")[1]
    assert note.startswith(
        "These are descriptive ratings from team members acting as evaluators, not results from "
        "independent users. No significance testing was performed. Items with fewer than five "
        "applicable ratings are shown as insufficient rather than summarised."
    )
    assert "no general-population or clinical-effectiveness claim is supported" in note


def test_splits_are_counts_by_question_with_no_values():
    text = report(synth_rows())
    split = text.split("## 6.")[1].split("## 7.")[0]
    assert "| Q1 | 12 | 1 | A1 |" in split   # per session: A1, A2, A3, CC2 comparable; only A1 (first session) splits
    assert "| Q4 | 6 | 0 | – |" in split
    assert "spanned" not in split and "ME-P9" not in split


def test_data_quality_public_is_kind_and_count_only():
    rows = synth_rows()
    rows[0]["item_scores"] = "A1=4;A9=3;A4=No;A2=7"
    dq = report(rows).split("## 7.")[1]
    assert "| unknown item ID | 2 |" in dq       # unknown Likert-style (A9) and Yes/No-style (A4) IDs
    assert "| Likert value outside 1-5 | 1 |" in dq
    assert "A9" not in dq and "A4" not in dq and "ME-P9" not in dq
    assert "internal output only" in dq


# --- internal output ---------------------------------------------------------


@pytest.fixture
def internal_dir(tmp_path, monkeypatch):
    root = tmp_path / "outputs"
    root.mkdir()
    monkeypatch.setattr(mod, "OUTPUTS_ROOT", root)
    monkeypatch.setattr(mod, "INTERNAL_DIR", root / "evaluation_summary")
    return root / "evaluation_summary"


def test_internal_report_lists_sessions_but_never_evaluators():
    rows = with_failures(synth_rows())
    rows[3]["item_scores"] = "MH1=5;MH2=No;A9=3"
    text = report(rows, internal=True)
    assert "| ME-P90 | Q1 | privacy_disclosure; unsupported_causation |" in text
    assert "unknown item ID" in text and "CSV line" in text
    for code in {r["evaluator_code"] for r in rows}:
        assert code not in text


def test_internal_writes_owner_only_file_under_outputs_and_not_stdout(csv_path, internal_dir, capsys):
    from backend.statistics import private_files as pf

    assert mod.main(["--input", str(csv_path), "--internal", "--expected-commit", SHA, "--build-label", LABEL]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""                       # nothing on stdout
    target = internal_dir / mod.INTERNAL_FILENAME
    assert target.is_file() and "INTERNAL APPENDIX" in target.read_text(encoding="utf-8")
    assert pf.is_owner_only(target, is_dir=False)
    assert pf.is_owner_only(internal_dir, is_dir=True)


def test_internal_fails_closed_when_permissions_cannot_be_restricted(csv_path, internal_dir, monkeypatch):
    from backend.statistics import private_files as pf

    def boom(path, *, is_dir):
        raise pf.PermissionRestrictionError("cannot restrict")

    monkeypatch.setattr(pf, "restrict_to_owner", boom)
    monkeypatch.setattr(pf, "is_owner_only", lambda path, *, is_dir: False)
    with pytest.raises(pf.PermissionRestrictionError):
        mod.main(["--input", str(csv_path), "--internal", "--expected-commit", SHA, "--build-label", LABEL])
    assert not (internal_dir / mod.INTERNAL_FILENAME).exists()


def test_internal_cannot_be_combined_with_output_and_public_cannot_target_internal_dir(csv_path, internal_dir, tmp_path):
    with pytest.raises(SystemExit):
        mod.main(["--input", str(csv_path), "--internal", "--output", str(tmp_path / "o.md"), "--expected-commit", SHA, "--build-label", LABEL])
    with pytest.raises(SystemExit):
        mod.main(["--input", str(csv_path), "--output", str(internal_dir / "public.md"), "--expected-commit", SHA, "--build-label", LABEL])


def test_default_internal_dir_is_under_gitignored_outputs():
    assert mod.INTERNAL_DIR.resolve().is_relative_to(mod.OUTPUTS_ROOT.resolve())
    assert mod.OUTPUTS_ROOT == REPO_ROOT / "outputs"
    assert "outputs/" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_script_import_does_not_pull_in_backend_and_private_files_stays_off_estimation_path():
    code = (
        "import importlib.util, sys, json\n"
        f"s = importlib.util.spec_from_file_location('m', {str(SCRIPT_PATH)!r})\n"
        "m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
        "before = [x for x in sys.modules if x == 'backend' or x.startswith('backend.')]\n"
        "from backend.statistics import private_files\n"
        "after = sorted(x for x in sys.modules if x == 'backend' or x.startswith('backend.'))\n"
        "print(json.dumps([before, after]))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=REPO_ROOT, check=True).stdout
    import json
    before, after = json.loads(out)
    assert before == []
    assert after == ["backend", "backend.statistics", "backend.statistics.private_files"]


# --- robustness / file safety ----------------------------------------------


def test_empty_input_does_not_crash(tmp_path):
    p = write_csv(tmp_path / "empty.csv", [])
    out = tmp_path / "o.md"
    assert mod.main(["--input", str(p), "--output", str(out), "--expected-commit", SHA, "--build-label", LABEL]) == 0
    assert "No responses recorded yet" in out.read_text(encoding="utf-8")


def test_yes_item_without_critical_flag_is_counted_as_a_warning():
    rows = synth_rows()
    rows[0] = row(SESSIONS[0], "Q1", "ME-P90-E1", "accuracy_faithfulness", "A1=4;A2=4;A3=Yes")  # cf stays No
    assert "| Yes/No item is Yes but critical_failure is not Yes | 1 |" in report(rows)


def test_refuses_to_write_protected_files(csv_path):
    for target in mod.PROTECTED_OUTPUTS:
        with pytest.raises(SystemExit):
            mod.main(["--input", str(csv_path), "--output", str(target), "--expected-commit", SHA, "--build-label", LABEL])


def test_real_responses_csv_is_not_modified_by_running_the_tests(csv_path, tmp_path):
    before = REAL_CSV.read_bytes() if REAL_CSV.exists() else None
    mod.main(["--input", str(csv_path), "--output", str(tmp_path / "x.md"), "--expected-commit", SHA, "--build-label", LABEL])
    mod.main(["--input", str(csv_path), "--unit", "session", "--output", str(tmp_path / "y.md"), "--expected-commit", SHA, "--build-label", LABEL])
    assert (REAL_CSV.read_bytes() if REAL_CSV.exists() else None) == before


# --- build check (--expected-commit) -----------------------------------------


def test_expected_commit_is_required(csv_path):
    with pytest.raises(SystemExit):
        mod.main(["--input", str(csv_path)])


def test_build_label_is_required(csv_path):
    with pytest.raises(SystemExit):
        mod.main(["--input", str(csv_path), "--expected-commit", SHA])


def test_build_label_must_not_be_blank(csv_path):
    with pytest.raises(SystemExit):
        mod.main(["--input", str(csv_path), "--expected-commit", SHA, "--build-label", "  "])


def test_build_label_is_printed_as_given(csv_path, tmp_path):
    out = tmp_path / "o.md"
    assert mod.main(["--input", str(csv_path), "--output", str(out), "--expected-commit", SHA,
                     "--build-label", "rc-eval-3"]) == 0
    assert f"Build: rc-eval-3 ({SHA})" in out.read_text(encoding="utf-8")


def test_matching_build_passes_and_public_output_names_the_build(csv_path, tmp_path):
    out = tmp_path / "o.md"
    assert mod.main(["--input", str(csv_path), "--output", str(out), "--expected-commit", SHA, "--build-label", LABEL]) == 0
    text = out.read_text(encoding="utf-8")
    assert f"Build: rc-eval-2 ({SHA})" in text
    lines = text.splitlines()
    assert lines.index(f"Build: rc-eval-2 ({SHA})") > lines.index(mod.PUBLIC_NOTE.splitlines()[-1])


def test_mismatching_row_stops_without_output(tmp_path, capsys):
    rows = synth_rows()
    rows[3]["commit_sha"] = OTHER_SHA
    out = tmp_path / "o.md"
    p = write_csv(tmp_path / "s.csv", rows)
    assert mod.main(["--input", str(p), "--output", str(out), "--expected-commit", SHA, "--build-label", LABEL]) == 2
    err = capsys.readouterr().err
    assert "1 mismatching row(s), 0 empty row(s)" in err
    assert not out.exists()
    assert "ME-P9" not in err and "line" not in err.lower().replace("nothing", "")


def test_empty_commit_sha_stops(tmp_path, capsys):
    rows = synth_rows()
    rows[0]["commit_sha"] = ""
    rows[1]["commit_sha"] = ""
    p = write_csv(tmp_path / "s.csv", rows)
    assert mod.main(["--input", str(p), "--output", str(tmp_path / "o.md"), "--expected-commit", SHA, "--build-label", LABEL]) == 2
    assert "0 mismatching row(s), 2 empty row(s)" in capsys.readouterr().err


def test_internal_mode_gives_csv_line_numbers_but_no_session_ids(tmp_path, capsys):
    rows = synth_rows()
    rows[2]["commit_sha"] = OTHER_SHA
    rows[4]["commit_sha"] = ""
    p = write_csv(tmp_path / "s.csv", rows)
    assert mod.main(["--input", str(p), "--internal", "--expected-commit", SHA, "--build-label", LABEL]) == 2
    cap = capsys.readouterr()
    assert "mismatch: CSV line(s) 4" in cap.err and "empty: CSV line(s) 6" in cap.err
    assert "ME-P9" not in cap.err and cap.out == ""


def test_expected_commit_must_be_full_sha(csv_path):
    with pytest.raises(SystemExit):
        mod.main(["--input", str(csv_path), "--expected-commit", "400883", "--build-label", LABEL])
