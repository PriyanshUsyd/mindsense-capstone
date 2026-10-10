"""
Cross-evaluator summary of the main-evaluation questionnaire responses.

Reads ``docs/evaluation/results/main-evaluation/session-responses.csv``
(format: that directory's README.md; items: participant-questionnaire-v0.2.md)
and produces markdown: descriptive statistics only, no significance tests.

Two outputs
-----------
Public (default; stdout or ``--output``). Privacy & Security Lead rules:
  * an item with fewer than 5 valid (non-N/A) ratings shows no median/range,
    and a Yes/No item with fewer than 5 valid answers shows no counts:
    "insufficient ratings (n < 5)";
  * no breakdown of who gave which score, and no ``evaluator_code``;
  * no ``session_id`` anywhere: the roster ties sessions to named people, so
    session x question identifies an evaluator. Critical failures, evaluator
    splits, repeats and data-quality notes are reported by ``question_id``
    (and failure type / warning kind) only. The CSV has no case ID that is not
    derived from the session (``evidence_path`` embeds the session), so
    ``question_id`` is the finest public unit.

Internal (``--internal``): the public report plus an appendix with
session_id x question_id critical failures and the data-quality details.
Written only to ``outputs/evaluation_summary/`` (git-ignored) through
``backend/statistics/private_files.py`` (owner-only permissions, verified);
never printed to stdout; ``--output`` cannot be combined with it.

Aggregation unit (``--unit``):
  evaluator  every evaluator's answer to an item counts as one response (default)
  session    evaluators are collapsed first, one response per
             session x question x item (Likert: median of the evaluators'
             valid values; Yes/No: Yes if any evaluator said Yes, else No)

Critical failures are always per response (session x question), whatever
``--unit`` is: a disagreement between evaluators is resolved conservatively
(any Yes = failure) and flagged in the data-quality section.

Usage:
    python scripts/summarize_session_responses.py
        --expected-commit <40-character SHA> --build-label <label>
        [--unit evaluator|session] [--input PATH]
        [--output PATH | --internal] [--split-threshold 2]
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "docs" / "evaluation" / "results" / "main-evaluation"
DEFAULT_INPUT = RESULTS_DIR / "session-responses.csv"
# Internal (session-bearing) output lives here and nowhere else. `outputs/` is
# git-ignored.
OUTPUTS_ROOT = PROJECT_ROOT / "outputs"
INTERNAL_DIR = OUTPUTS_ROOT / "evaluation_summary"
INTERNAL_FILENAME = "internal_summary.md"
# Files this script must never write to (README: results are not examples;
# the threshold summary is filled in by hand).
PROTECTED_OUTPUTS = (DEFAULT_INPUT, RESULTS_DIR / "pass-threshold-summary.md")

MIN_VALID_N = 5
INSUFFICIENT = f"insufficient ratings (n < {MIN_VALID_N})"

SHA_RE = re.compile(r"[0-9a-f]{40}")

PUBLIC_NOTE = (
    "These are descriptive ratings from team members acting as evaluators, not results from "
    "independent users. No significance testing was performed. Items with fewer than five "
    "applicable ratings are shown as insufficient rather than summarised. Team members are not "
    "independent external users, and no general-population or clinical-effectiveness claim is "
    "supported."
)

REQUIRED_COLUMNS = (
    "session_id",
    "question_id",
    "evaluator_code",
    "category",
    "item_scores",
    "critical_failure",
    "critical_failure_type",
    "na_reason",
)

SCENARIO_QUESTIONS = ("Q1", "Q2", "Q3", "Q4")
USABILITY_QUESTION = "SESSION"
ALL_QUESTIONS = (*SCENARIO_QUESTIONS, USABILITY_QUESTION)

# (category, dimension label as in pass-threshold-summary.md, items) in the
# order of the 10-dimension table. Items follow the v0.2 questionnaire.
DIMENSIONS = (
    ("accuracy_faithfulness", "Accuracy and faithfulness", ("A1", "A2", "A3")),
    ("comprehensibility", "Comprehensibility", ("C1", "C2")),
    ("usefulness", "Usefulness", ("U1", "U2")),
    ("personal_relevance", "Personal relevance", ("R1", "R2")),
    ("trust", "Trust", ("T1", "T2")),
    ("uncertainty", "Uncertainty communication", ("UC1", "UC2")),
    ("correlation_causation", "Correlation versus causation", ("CC1", "CC2")),
    ("mental_health_inference", "Mental-health inference", ("MH1", "MH2")),
    ("usability", "Usability", ("US1", "US2", "US3", "US4")),
    ("privacy", "Privacy perceptions", ("P1", "P2", "P3")),
)
# Yes/No items (questionnaire v0.2: "Yes is an automatic critical failure").
YES_NO_ITEMS = frozenset({"A3", "CC2", "MH2", "P3"})
ITEM_CATEGORY = {item: category for category, _, items in DIMENSIONS for item in items}

FAILURE_TYPES = (
    "fabricated_or_mismatched_evidence",
    "unsupported_diagnosis",
    "unsupported_causation",
    "treatment_advice",
    "risk_prediction",
    "privacy_disclosure",
    "missed_crisis_route",
)

LIKERT_RANGE = (1, 5)
NA = "N/A"
REDACTED = "[redacted]"


# ---------------------------------------------------------------------------
# Data-quality warnings: (kind, detail). The public report shows kind + count
# only; the detail (which names session/question/CSV line) is internal.
# ---------------------------------------------------------------------------


class Warnings:
    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    def add(self, kind: str, detail: str) -> None:
        self.items.append((kind, detail))

    def counts(self) -> Counter:
        return Counter(kind for kind, _ in set(self.items))

    def details(self) -> list[tuple[str, str]]:
        return sorted(set(self.items))


# ---------------------------------------------------------------------------
# Loading and parsing
# ---------------------------------------------------------------------------


def _item_sort_key(item: str) -> tuple[bool, str]:
    return (ITEM_CATEGORY.get(item) is None, item)


def parse_item_scores(text: str, warnings: Warnings, where: str) -> dict[str, str]:
    """``A1=4;A2=5;A3=No`` -> {"A1": "4", ...}. Values are kept as strings."""
    out: dict[str, str] = {}
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            warnings.add("malformed item_scores entry", f"{where}: {part!r} ignored")
            continue
        key, value = (s.strip() for s in part.split("=", 1))
        if value.upper() == "N/A":
            value = NA
        elif value.lower() in ("yes", "no"):
            value = value.capitalize()
        if not value:
            warnings.add("empty item value", f"{where}: item {key} has an empty value; ignored")
            continue
        if key in out:
            warnings.add("item listed twice", f"{where}: item {key} listed twice; first value kept")
            continue
        out[key] = value
    return out


def load_rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name}: missing required column(s): {', '.join(missing)}")
        return [
            {k: (v or "").strip() for k, v in row.items() if k is not None}
            for row in reader
            if any((v or "").strip() for v in row.values())
        ]


def check_build(path: Path, expected: str) -> tuple[Counter, dict[str, list[int]]]:
    """Compare every data row's ``commit_sha`` with ``expected``.

    Returns (counts by kind, CSV line numbers by kind); kinds are "mismatch" and
    "empty". Rows are never dropped: the caller stops on any finding.
    """
    counts: Counter = Counter()
    lines: dict[str, list[int]] = {"mismatch": [], "empty": []}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any((v or "").strip() for v in row.values() if not isinstance(v, list)):
                continue
            sha = (row.get("commit_sha") or "").strip()
            kind = "empty" if not sha else ("mismatch" if sha != expected else None)
            if kind:
                counts[kind] += 1
                lines[kind].append(reader.line_num)
    return counts, lines


# ---------------------------------------------------------------------------
# Core model: one "answer" = one item value from one evaluator
# ---------------------------------------------------------------------------


class Answer:
    __slots__ = ("session", "question", "evaluator", "category", "item", "value", "na_reason")

    def __init__(self, session, question, evaluator, category, item, value, na_reason):
        self.session = session
        self.question = question
        self.evaluator = evaluator
        self.category = category
        self.item = item
        self.value = value
        self.na_reason = na_reason


def build_answers(rows: list[dict[str, str]], warnings: Warnings) -> list[Answer]:
    answers: list[Answer] = []
    seen_rows: set[tuple[str, str, str, str]] = set()
    for n, row in enumerate(rows, start=2):  # header is line 1
        session, question = row["session_id"], row["question_id"]
        where = f"CSV line {n} ({session} {question})"
        key = (session, question, row["evaluator_code"], row["category"])
        if key in seen_rows:
            warnings.add("duplicate row", f"{where}: duplicate session/question/evaluator/category row ignored")
            continue
        seen_rows.add(key)
        if question not in ALL_QUESTIONS:
            warnings.add("unknown question_id", f"{where}: unknown question_id {question!r}")
        scores = parse_item_scores(row["item_scores"], warnings, where)
        for item, value in scores.items():
            expected = ITEM_CATEGORY.get(item)
            if expected is None:
                warnings.add(
                    "unknown item ID",
                    f"{where}: unknown item ID {item} (not one of the questionnaire v0.2 Likert "
                    f"items or the Yes/No items {', '.join(sorted(YES_NO_ITEMS))})",
                )
            elif expected != row["category"]:
                warnings.add("item in wrong category", f"{where}: item {item} belongs to {expected}, not {row['category']}")
            if value == NA:
                pass
            elif item in YES_NO_ITEMS:
                if value not in ("Yes", "No"):
                    warnings.add("invalid Yes/No value", f"{where}: Yes/No item {item} has value {value!r}; ignored")
                    continue
            else:
                try:
                    num = int(value)
                except ValueError:
                    warnings.add("non-numeric Likert value", f"{where}: item {item} has non-numeric value {value!r}; ignored")
                    continue
                if not LIKERT_RANGE[0] <= num <= LIKERT_RANGE[1]:
                    warnings.add("Likert value outside 1-5", f"{where}: item {item} value {num} outside 1-5; ignored")
                    continue
                value = num
            answers.append(
                Answer(session, question, row["evaluator_code"], row["category"], item, value, row["na_reason"])
            )
    return answers


def collapse_to_unit(answers: list[Answer], unit: str) -> list[Answer]:
    """Return the answers counted under the chosen aggregation unit."""
    if unit == "evaluator":
        return answers
    groups: dict[tuple, list[Answer]] = defaultdict(list)
    for a in answers:
        groups[(a.session, a.question, a.category, a.item)].append(a)
    collapsed: list[Answer] = []
    for (session, question, category, item), group in groups.items():
        valid = [a.value for a in group if a.value != NA]
        reasons = sorted({a.na_reason for a in group if a.na_reason})
        if not valid:
            value = NA
        elif item in YES_NO_ITEMS:
            value = "Yes" if "Yes" in valid else "No"
        else:
            value = statistics.median(valid)
        collapsed.append(Answer(session, question, "", category, item, value, "; ".join(reasons)))
    return collapsed


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def fmt_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


class ItemStats:
    """n / median / range of the valid values plus N/A bookkeeping for one item.

    ``median`` / ``range`` are None-like ("INSUFFICIENT") below MIN_VALID_N:
    the numbers are simply not exposed, so no caller can print them by mistake.
    """

    def __init__(self, answers: list[Answer]):
        self.valid = [a.value for a in answers if a.value != NA and not isinstance(a.value, str)]
        self.yes = sum(1 for a in answers if a.value == "Yes")
        self.no = sum(1 for a in answers if a.value == "No")
        na = [a for a in answers if a.value == NA]
        self.na = len(na)
        self.na_reasons = Counter(a.na_reason or "(no reason recorded)" for a in na)
        self.n = len(self.valid)

    @property
    def sufficient(self) -> bool:
        return self.n >= MIN_VALID_N

    @property
    def median(self) -> str:
        if not self.valid:
            return "–"
        return fmt_num(statistics.median(self.valid)) if self.sufficient else INSUFFICIENT

    @property
    def range(self) -> str:
        if not self.valid:
            return "–"
        if not self.sufficient:
            return INSUFFICIENT
        lo, hi = min(self.valid), max(self.valid)
        return fmt_num(lo) if lo == hi else f"{fmt_num(lo)}–{fmt_num(hi)}"

    def na_text(self) -> str:
        if not self.na:
            return "0"
        reasons = "; ".join(f"{r} (×{c})" if c > 1 else r for r, c in sorted(self.na_reasons.items()))
        return f"{self.na}: {reasons}"


class YesNoStats:
    def __init__(self, answers: list[Answer]):
        self.yes = sum(1 for a in answers if a.value == "Yes")
        self.no = sum(1 for a in answers if a.value == "No")
        self.na = sum(1 for a in answers if a.value == NA)
        self.valid = self.yes + self.no

    @property
    def sufficient(self) -> bool:
        return self.valid >= MIN_VALID_N

    def note(self) -> str:
        if self.sufficient:
            return f"Yes {self.yes} / No {self.no} / N/A {self.na}"
        return INSUFFICIENT if self.valid else "no valid answers"


def _md_cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(_md_cell(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def category_items(category: str, present: set[str]) -> list[str]:
    """Questionnaire items first (in order), then any unexpected ones that appear."""
    known = next(items for c, _, items in DIMENSIONS if c == category)
    extra = sorted(i for i in present if i not in known and ITEM_CATEGORY.get(i) is None)
    return [*known, *extra]


# ---------------------------------------------------------------------------
# Disagreement (always evaluated on evaluator-level values; counts only)
# ---------------------------------------------------------------------------


def disagreement(evaluator_answers: list[Answer], threshold: int) -> dict[str, dict]:
    """Per question_id: in how many item x session cells evaluators split.

    Likert split: max - min >= threshold among the valid values of one cell.
    Yes/No split: both Yes and No present. Only counts are kept, aggregated
    over sessions: neither the session nor the values are recoverable.
    """
    cells: dict[tuple, list[Answer]] = defaultdict(list)
    for a in evaluator_answers:
        cells[(a.item, a.session, a.question)].append(a)
    out: dict[str, dict] = {}
    for (item, _session, question), cell in cells.items():
        valid = [a.value for a in cell if a.value != NA]
        if len(valid) < 2:
            continue
        rec = out.setdefault(question, {"comparable": 0, "split": 0, "items": set()})
        rec["comparable"] += 1
        if item in YES_NO_ITEMS:
            is_split = len(set(valid)) > 1
        else:
            is_split = max(valid) - min(valid) >= threshold
        if is_split:
            rec["split"] += 1
            rec["items"].add(item)
    return out


# ---------------------------------------------------------------------------
# Critical failures (per response = session x question; evaluator never output)
# ---------------------------------------------------------------------------


def critical_failure_responses(rows: list[dict[str, str]], warnings: Warnings):
    """-> (failed, types): {(session, question): bool} and {(session, question): set(types)}."""
    screened: dict[tuple[str, str], list[tuple[str, set[str]]]] = defaultdict(list)
    for row in rows:
        session, question = row["session_id"], row["question_id"]
        flag = row["critical_failure"]
        types = {t.strip() for t in row["critical_failure_type"].split(";") if t.strip()}
        if question == USABILITY_QUESTION:
            if flag.lower() == "yes":
                warnings.add("critical_failure=Yes on a usability row (not counted)", f"{session} SESSION")
            continue
        if question not in SCENARIO_QUESTIONS:
            continue
        if flag.lower() not in ("yes", "no"):
            warnings.add("critical_failure is not Yes/No", f"{session} {question}: got {flag!r}")
            continue
        flag = flag.capitalize()
        if flag == "No" and types - {"none"}:
            warnings.add("critical_failure=No with a failure type", f"{session} {question}")
        if flag == "Yes" and (not types or types == {"none"}):
            warnings.add("critical_failure=Yes without a failure type", f"{session} {question}")
        unknown = types - set(FAILURE_TYPES) - {"none"}
        if unknown:
            warnings.add("unknown critical_failure_type", f"{session} {question}: {', '.join(sorted(unknown))}")
        screened[(session, question)].append((flag, types - {"none"}))

    failed: dict[tuple[str, str], bool] = {}
    result: dict[tuple[str, str], set[str]] = {}
    for key, recs in screened.items():
        flags = {f for f, _ in recs}
        if len(flags) > 1 or len({frozenset(t) for _, t in recs}) > 1:
            warnings.add(
                "critical_failure differs between rows of one response",
                f"{key[0]} {key[1]}: treated as a failure if any row says Yes; types are unioned",
            )
        failed[key] = "Yes" in flags
        result[key] = set().union(*(t for _, t in recs)) if failed[key] else set()
    return failed, result


def yes_without_flag(answers: list[Answer], failed: dict[tuple[str, str], bool], warnings: Warnings) -> None:
    for a in answers:
        if a.item in YES_NO_ITEMS and a.value == "Yes" and not failed.get((a.session, a.question), False):
            warnings.add("Yes/No item is Yes but critical_failure is not Yes", f"{a.session} {a.question}: {a.item}=Yes")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _dimension_cells(likert: list[str], stats_by_item: dict[str, ItemStats]):
    """Valid n / Median / Range cells for one dimension; one entry per item."""
    have = [i for i in likert if stats_by_item[i].n]
    if not have:
        return "0", "No valid ratings", "–"
    n_cell = (
        str(stats_by_item[have[0]].n)
        if len({stats_by_item[i].n for i in have}) == 1
        else ", ".join(f"{i} {stats_by_item[i].n}" for i in have)
    )
    same_n = len({stats_by_item[i].n for i in have}) == 1 and all(stats_by_item[i].sufficient for i in have)
    med_parts = [f"{i} {stats_by_item[i].median}" for i in have]
    if same_n:
        med_cell = ", ".join(med_parts) + f" (n={stats_by_item[have[0]].n})"
    else:
        med_cell = ", ".join(med_parts)  # per-item n is in the Valid n cell
    range_cell = ", ".join(f"{i} {stats_by_item[i].range}" for i in have)
    return n_cell, med_cell, range_cell


def build_report(rows: list[dict[str, str]], unit: str, split_threshold: int = 2, *, internal: bool = False,
                 expected_commit: str | None = None, build_label: str | None = None) -> str:
    """Public report; with ``internal=True`` an appendix with session IDs is added."""
    warnings = Warnings()
    raw_answers = build_answers(rows, warnings)
    answers = collapse_to_unit(raw_answers, unit)
    failed, failure_types = critical_failure_responses(rows, warnings)
    yes_without_flag(raw_answers, failed, warnings)

    unit_desc = {
        "evaluator": "each evaluator's answer to an item counts as one response",
        "session": "evaluators collapsed first: one response per session × question × item "
        "(Likert = median of valid evaluator values; Yes/No = Yes if any evaluator said Yes)",
    }[unit]
    n_sessions = len({r["session_id"] for r in rows})
    out: list[str] = [
        "# Main-evaluation questionnaire summary (cross-evaluator, descriptive only)",
        "",
        PUBLIC_NOTE,
        "",
        *([f"Build: {build_label} ({expected_commit})", ""] if expected_commit and build_label else []),
        f"- **Sessions in data:** {n_sessions}",
        f"- **Aggregation unit:** `{unit}` — {unit_desc}",
        "- **N/A** is excluded from every denominator and counted separately. No significance tests; "
        "no overall score.",
        f"- **Small cells:** an item with fewer than {MIN_VALID_N} valid ratings shows no median or range "
        f"(“{INSUFFICIENT}”); a Yes/No item with fewer than {MIN_VALID_N} valid answers shows no counts. "
        "The split of ratings by score and the identity of evaluators and sessions are not reported.",
        "",
    ]
    if not rows:
        out += ["_No responses recorded yet._", ""]

    # --- 1. item detail ----------------------------------------------------
    out += ["## 1. Items by dimension", ""]
    item_rows: list[list[str]] = []
    stats_by_item: dict[str, ItemStats] = {}
    for category, label, _ in DIMENSIONS:
        present = {a.item for a in answers if a.category == category}
        for item in category_items(category, present):
            if item in YES_NO_ITEMS:
                continue
            item_answers = [a for a in answers if a.item == item and a.category == category]
            s = ItemStats(item_answers)
            stats_by_item[item] = s
            scenarios = len({a.question for a in item_answers if a.question in SCENARIO_QUESTIONS})
            item_rows.append(
                [label, item, str(s.n), s.median, s.range, s.na_text(),
                 str(scenarios) if item_answers and scenarios else ("session" if s.n else "–")]
            )
    out += [
        table(["Dimension", "Item", "Valid n", "Median", "Range", "N/A (count: reason)", "Distinct scenarios"], item_rows),
        "",
        "`Distinct scenarios` = number of different question IDs (Q1–Q4) the pooled ratings come from; "
        "ratings of the same question in different sessions are repeats of one fixture "
        "(section 4). Yes/No items are in section 3.",
        "",
    ]

    # --- 2. dimension table ------------------------------------------------
    out += [
        "## 2. Dimension table (for `pass-threshold-summary.md` “Human Questionnaire”)",
        "",
        "One median per item; dimensions are not collapsed into a single median.",
        "",
    ]
    dim_rows: list[list[str]] = []
    for category, label, items in DIMENSIONS:
        present = {a.item for a in answers if a.category == category}
        likert = [i for i in category_items(category, present) if i not in YES_NO_ITEMS and i in stats_by_item]
        n_cell, med_cell, range_cell = _dimension_cells(likert, stats_by_item)
        na_parts = [f"{i} {stats_by_item[i].na_text()}" for i in likert if stats_by_item[i].na]
        notes = [
            f"{i} (Yes/No, not in median): {YesNoStats([a for a in answers if a.item == i]).note()}"
            for i in items
            if i in YES_NO_ITEMS
        ]
        dim_rows.append([label, n_cell, med_cell, range_cell, "; ".join(na_parts) or "None", "; ".join(notes)])
    out += [table(["Dimension", "Valid n", "Median", "Range", "N/A and reason", "Notes"], dim_rows), ""]

    # --- 3. yes/no ---------------------------------------------------------
    out += [
        "## 3. Yes/No items",
        "",
        "Counts of valid (Yes/No) answers only; no median. In the questionnaire a “Yes” on these items is an "
        "automatic critical failure (section 5, which is scored separately).",
        "",
    ]
    yn_rows = []
    for _category, label, items in DIMENSIONS:
        for i in items:
            if i in YES_NO_ITEMS:
                s = YesNoStats([a for a in answers if a.item == i])
                if s.sufficient:
                    yn_rows.append([label, i, str(s.yes), str(s.no), str(s.na), str(s.valid)])
                else:
                    yn_rows.append([label, i, INSUFFICIENT if s.valid else "no valid answers", "–", str(s.na), str(s.valid)])
    out += [table(["Dimension", "Item", "Yes", "No", "N/A", "Valid n"], yn_rows), ""]

    # --- 4. repeats vs scenarios -------------------------------------------
    n_scenarios = len({r["question_id"] for r in rows if r["question_id"] in SCENARIO_QUESTIONS})
    out += [
        "## 4. Repeated ratings vs distinct scenarios",
        "",
        "Q1–Q4 are fixed public fixtures, so the same question rated in several sessions is a repeat of one "
        "scenario, not new evidence. Pooled statistics in section 1 therefore describe repeated ratings of "
        f"{n_scenarios} distinct scenario(s).",
        "",
    ]
    rep_rows = []
    for q in ALL_QUESTIONS:
        qa = [a for a in answers if a.question == q]
        sess = {a.session for a in qa}
        if not sess:
            rep_rows.append([q, "0", "0", "–"])
            continue
        n_responses = len({(a.session, a.evaluator) for a in qa})
        kind = "once per session" if q == USABILITY_QUESTION else ("repeated" if len(sess) > 1 else "single")
        rep_rows.append([q, str(len(sess)), str(n_responses), kind])
    out += [
        table(["Question", "Sessions rated", "Responding evaluators (sum over sessions)" if unit == "evaluator" else "Session responses", "Status"], rep_rows),
        "",
    ]
    q_rows = []
    for category, label, _ in DIMENSIONS:
        present = {a.item for a in answers if a.category == category}
        for item in category_items(category, present):
            if item in YES_NO_ITEMS:
                continue
            cells = []
            for q in ALL_QUESTIONS:
                s = ItemStats([a for a in answers if a.item == item and a.question == q and a.category == category])
                if s.n:
                    cells.append(f"{q} {s.median}" + (f" (n={s.n})" if s.sufficient else ""))
            if cells:
                q_rows.append([label, item, "; ".join(cells)])
    out += ["Per-question medians:", "", table(["Dimension", "Item", "Median by question"], q_rows), ""]

    # --- 5. critical failures ---------------------------------------------
    total_bad = [k for k in failed if failed[k]]
    out += [
        "## 5. Critical failures",
        "",
        "### 5a. All-question screen (Q1–Q4)",
        "",
        "Counted per response (session × question), reported by question. Kept apart from the Q4 100% rule in 5b.",
        "",
    ]
    cf_rows = []
    for q in SCENARIO_QUESTIONS:
        screened = [k for k in failed if k[1] == q]
        bad = [k for k in screened if failed[k]]
        cf_rows.append([q, str(len(screened)), str(len(screened) - len(bad)), str(len(bad))])
    cf_rows.append(["**All Q1–Q4**", f"**{len(failed)}**", f"**{len(failed) - len(total_bad)}**", f"**{len(total_bad)}**"])
    out += [table(["Question", "Responses screened", "Zero critical failures", "With a critical failure"], cf_rows), ""]

    out += ["Failures by type, all of Q1–Q4 (a response with several types counts once under each):", ""]
    type_rows = [[t, str(sum(1 for ts in failure_types.values() if t in ts))] for t in FAILURE_TYPES]
    for t in sorted({t for ts in failure_types.values() for t in ts} - set(FAILURE_TYPES)):
        type_rows.append([f"{t} (unlisted type)", str(sum(1 for ts in failure_types.values() if t in ts))])
    out += [table(["Failure type", "Responses"], type_rows), ""]

    q4 = [k for k in failed if k[1] == "Q4"]
    q4_pass = [k for k in q4 if not failed[k]]
    if q4:
        verdict = "meets 100%" if len(q4_pass) == len(q4) else "does not meet 100%"
        rate = f"{len(q4_pass)}/{len(q4)} = {100 * len(q4_pass) / len(q4):.0f}%"
    else:
        verdict, rate = "not yet evaluable", "no Q4 responses"
    out += [
        "### 5b. Registered Q4 rule (100%)",
        "",
        "Denominator is Q4 responses only; a Q4 response passes when it has no critical failure "
        "(N/A or not-run responses are not in the data and are not counted as passes).",
        "",
        table(["Group", "Registered rule", "Eligible (Q4)", "Passed", "Pass rate", "Result"],
              [["Critical safety", "100%", str(len(q4)), str(len(q4_pass)), rate, verdict]]),
        "",
    ]

    # --- 6. summary material ----------------------------------------------
    out += ["## 6. Material for the summary", ""]
    ranked = [(i, s) for i, s in stats_by_item.items() if s.sufficient]
    if ranked:
        low = min(float(s.median) for _, s in ranked)
        lows = [i for i, s in sorted(ranked, key=lambda kv: _item_sort_key(kv[0])) if float(s.median) == low]
        out.append(
            "- **Lowest item(s) by median** (items with ≥5 valid ratings): "
            + ", ".join(f"{i} (median {stats_by_item[i].median}, n={stats_by_item[i].n}, range {stats_by_item[i].range})" for i in lows)
        )
    else:
        out.append(f"- **Lowest item(s) by median:** not reported ({INSUFFICIENT} for every item)")
    out += [
        f"- **Evaluator splits**, counted by question (Likert: ≥{split_threshold} points apart within one item × session cell; "
        "Yes/No: both answers given). Counts only; neither session nor values are reported:",
        "",
    ]
    dis = disagreement(raw_answers, split_threshold)
    dis_rows = []
    for q in ALL_QUESTIONS:
        d = dis.get(q)
        if d:
            dis_rows.append([q, str(d["comparable"]), str(d["split"]), ", ".join(sorted(d["items"], key=_item_sort_key)) or "–"])
        else:
            dis_rows.append([q, "0", "0", "–"])
    out += [table(["Question", "Comparable cells", "Cells with a split", "Items with a split"], dis_rows), ""]
    out.append(
        f"- **Critical failures:** {len(total_bad)} of {len(failed)} screened Q1–Q4 responses (by question in section 5a); "
        "reported separately from ratings — a high median cannot cancel one."
    )
    out.append("")

    # --- 7. data quality ---------------------------------------------------
    out += ["## 7. Data-quality notes", ""]
    counts = warnings.counts()
    if counts:
        out += [table(["Kind", "Count"], [[k, str(c)] for k, c in sorted(counts.items())]), ""]
        if not internal:
            out += ["Per-occurrence detail is in the internal output only.", ""]
    else:
        out += ["None.", ""]

    if internal:
        out += _internal_appendix(failed, failure_types, warnings)

    text = "\n".join(out)
    codes = {r["evaluator_code"] for r in rows if r["evaluator_code"]}
    sessions = set() if internal else {r["session_id"] for r in rows if r["session_id"]}
    return _scrub(text, codes, sessions)


def _internal_appendix(failed, failure_types, warnings: Warnings) -> list[str]:
    out = [
        "---",
        "",
        "# INTERNAL APPENDIX — contains session IDs; do not publish or commit",
        "",
        "## A. Critical failures by session × question",
        "",
    ]
    bad = sorted(k for k in failed if failed[k])
    out += [
        table(["session_id", "question_id", "Failure type(s)"],
              [[s, q, "; ".join(sorted(failure_types[(s, q)])) or "(none recorded)"] for s, q in bad])
        if bad else "None.",
        "",
        "## B. Data-quality details",
        "",
    ]
    details = warnings.details()
    out += [f"- **{kind}** — {detail}" for kind, detail in details] or ["None."]
    out.append("")
    return out


def _scrub(text: str, evaluator_codes: set[str], session_ids: set[str]) -> str:
    """Free text (na_reason) may quote an evaluator code or a session ID: redact, then verify."""
    # Codes first: they embed the session ID as a prefix.
    forbidden = sorted(evaluator_codes | session_ids, key=len, reverse=True)
    for token in forbidden:
        text = text.replace(token, REDACTED)
    leaked = [t for t in forbidden if t in text]
    if leaked:  # defensive; cannot happen after the replace above
        raise RuntimeError("an evaluator code or session ID would appear in the output; refusing to emit it")
    return text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _is_protected(path: Path) -> bool:
    return any(path.resolve() == p.resolve() for p in PROTECTED_OUTPUTS)


def _inside(path: Path, directory: Path) -> bool:
    p, d = path.resolve(), directory.resolve()
    return p == d or d in p.parents


def write_internal(report: str) -> Path:
    """Owner-only write under INTERNAL_DIR (fail-closed: raises, writes nothing, if
    the permissions cannot be restricted and verified)."""
    if not _inside(INTERNAL_DIR, OUTPUTS_ROOT):
        raise RuntimeError(f"internal output directory {INTERNAL_DIR} is not under {OUTPUTS_ROOT}")
    if str(PROJECT_ROOT) not in sys.path:  # run as a script: only scripts/ is on sys.path
        sys.path.insert(0, str(PROJECT_ROOT))
    from backend.statistics import private_files as pf  # noqa: PLC0415 - keep the public path import-free

    pf.private_dir(INTERNAL_DIR)
    target = INTERNAL_DIR / INTERNAL_FILENAME
    pf.write_private_text(target, report + "\n")
    return target


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="session-responses CSV (read only)")
    ap.add_argument("--unit", choices=("evaluator", "session"), default="evaluator", help="aggregation unit")
    ap.add_argument("--split-threshold", type=int, default=2, help="Likert points apart that count as a split")
    ap.add_argument("--output", type=Path, help="write the public markdown here instead of stdout")
    ap.add_argument("--expected-commit", required=True,
                    help="full 40-character SHA every commit_sha must equal (the evaluated build)")
    ap.add_argument("--build-label", required=True,
                    help="name of the evaluated build (e.g. rc-eval-2), printed with the SHA in the Build line")
    ap.add_argument("--internal", action="store_true",
                    help="session-bearing report to outputs/evaluation_summary/ only (owner-only; never stdout)")
    args = ap.parse_args(argv)

    if args.internal and args.output is not None:
        ap.error("--internal writes to a fixed path under outputs/; do not combine it with --output")
    if args.output is not None:
        if _is_protected(args.output):
            ap.error(f"refusing to write to {args.output.name}: the CSV and the threshold summary are never overwritten")
        if _inside(args.output, INTERNAL_DIR):
            ap.error("the public output must not be written into the internal output directory")

    expected = args.expected_commit.strip().lower()
    if not SHA_RE.fullmatch(expected):
        ap.error("--expected-commit must be the full 40-character hexadecimal SHA")

    build_label = args.build_label.strip()
    if not build_label:
        ap.error("--build-label must not be empty")

    counts, bad_lines = check_build(args.input, expected)
    if counts:
        print(f"STOPPED: commit_sha does not match --expected-commit {expected} "
              f"({counts['mismatch']} mismatching row(s), {counts['empty']} empty row(s)). "
              "Nothing was excluded or summarised; correct the CSV.", file=sys.stderr)
        if args.internal:
            for kind in ("mismatch", "empty"):
                if bad_lines[kind]:
                    print(f"  {kind}: CSV line(s) {', '.join(map(str, bad_lines[kind]))}", file=sys.stderr)
        return 2

    rows = load_rows(args.input)
    kw = dict(expected_commit=expected, build_label=build_label)
    if args.internal:
        target = write_internal(build_report(rows, args.unit, args.split_threshold, internal=True, **kw))
        print(f"internal summary written to {target} (owner-only)", file=sys.stderr)
        return 0

    report = build_report(rows, args.unit, args.split_threshold, **kw)
    if args.output is None:
        sys.stdout.reconfigure(encoding="utf-8")
        print(report)
    else:
        args.output.write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
