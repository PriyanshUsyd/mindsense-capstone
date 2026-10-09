"""
Cross-evaluator summary of the main-evaluation questionnaire responses.

Reads ``docs/evaluation/results/main-evaluation/session-responses.csv``
(format: that directory's README.md; items: participant-questionnaire-v0.2.md)
and prints markdown: descriptive statistics only, no significance tests.

Privacy: evaluators are team members taking part in the evaluation. Only
cross-evaluator aggregates (per-item n / median / range) and critical failures
by session_id x question_id are published. ``evaluator_code`` is used only to
count responses and is never written to the output; the script also refuses to
emit any text that contains a code found in the input.

Aggregation unit (``--unit``):
  evaluator  every evaluator's answer to an item counts as one response (default)
  session    evaluators are collapsed first, one response per
             session_id x question_id x item (Likert: median of the evaluators'
             valid values; Yes/No: Yes if any evaluator said Yes, else No)

Critical failures are always per response (session_id x question_id),
whatever ``--unit`` is: a disagreement between evaluators is resolved
conservatively (any Yes = failure) and flagged in the data-quality section.

Usage:
    python scripts/summarize_session_responses.py [--unit evaluator|session]
        [--input PATH] [--output PATH] [--split-threshold 2]
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "docs" / "evaluation" / "results" / "main-evaluation"
DEFAULT_INPUT = RESULTS_DIR / "session-responses.csv"
# Files this script must never write to (README: results are not examples;
# the threshold summary is filled in by hand).
PROTECTED_OUTPUTS = (DEFAULT_INPUT, RESULTS_DIR / "pass-threshold-summary.md")

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


def _dimension_of_item() -> dict[str, str]:
    return {item: category for category, _, items in DIMENSIONS for item in items}


ITEM_CATEGORY = _dimension_of_item()


# ---------------------------------------------------------------------------
# Loading and parsing
# ---------------------------------------------------------------------------


def _item_sort_key(item: str) -> tuple[int, str]:
    return (ITEM_CATEGORY.get(item) is None, item)


def parse_item_scores(text: str, warnings: list[str], where: str) -> dict[str, str]:
    """``A1=4;A2=5;A3=No`` -> {"A1": "4", ...}. Values are kept as strings."""
    out: dict[str, str] = {}
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            warnings.append(f"{where}: malformed item_scores entry {part!r} ignored")
            continue
        key, value = (s.strip() for s in part.split("=", 1))
        if value.upper() == "N/A":
            value = NA
        elif value.lower() in ("yes", "no"):
            value = value.capitalize()
        if not value:
            warnings.append(f"{where}: item {key} has an empty value; ignored")
            continue
        if key in out:
            warnings.append(f"{where}: item {key} listed twice; first value kept")
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


def build_answers(rows: list[dict[str, str]], warnings: list[str]) -> list[Answer]:
    answers: list[Answer] = []
    seen_rows: set[tuple[str, str, str, str]] = set()
    for n, row in enumerate(rows, start=2):  # header is line 1
        session, question = row["session_id"], row["question_id"]
        where = f"CSV line {n} ({session} {question})"
        key = (session, question, row["evaluator_code"], row["category"])
        if key in seen_rows:
            warnings.append(f"{where}: duplicate session/question/evaluator/category row ignored")
            continue
        seen_rows.add(key)
        if question not in SCENARIO_QUESTIONS and question != USABILITY_QUESTION:
            warnings.append(f"{where}: unknown question_id {question!r}")
        scores = parse_item_scores(row["item_scores"], warnings, where)
        for item, value in scores.items():
            expected = ITEM_CATEGORY.get(item)
            if expected is None:
                warnings.append(
                    f"{where}: unknown item ID {item} (not one of the questionnaire v0.2 Likert "
                    f"or Yes/No items {', '.join(sorted(YES_NO_ITEMS))})"
                )
            elif expected != row["category"]:
                warnings.append(f"{where}: item {item} belongs to {expected}, not {row['category']}")
            if value == NA:
                pass
            elif item in YES_NO_ITEMS:
                if value not in ("Yes", "No"):
                    warnings.append(f"{where}: Yes/No item {item} has value {value!r}; ignored")
                    continue
            else:
                try:
                    num = int(value)
                except ValueError:
                    warnings.append(f"{where}: item {item} has non-numeric value {value!r}; ignored")
                    continue
                if not LIKERT_RANGE[0] <= num <= LIKERT_RANGE[1]:
                    warnings.append(f"{where}: item {item} value {num} outside 1-5; ignored")
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
    """n / median / range of the valid values plus N/A bookkeeping for one item."""

    def __init__(self, answers: list[Answer]):
        self.valid = [a.value for a in answers if a.value != NA and not isinstance(a.value, str)]
        self.yes = sum(1 for a in answers if a.value == "Yes")
        self.no = sum(1 for a in answers if a.value == "No")
        na = [a for a in answers if a.value == NA]
        self.na = len(na)
        self.na_reasons = Counter(a.na_reason or "(no reason recorded)" for a in na)
        self.n = len(self.valid)

    @property
    def median(self) -> str:
        return fmt_num(statistics.median(self.valid)) if self.valid else "–"

    @property
    def range(self) -> str:
        if not self.valid:
            return "–"
        lo, hi = min(self.valid), max(self.valid)
        return fmt_num(lo) if lo == hi else f"{fmt_num(lo)}–{fmt_num(hi)}"

    def na_text(self) -> str:
        if not self.na:
            return "0"
        reasons = "; ".join(f"{r} (×{c})" if c > 1 else r for r, c in sorted(self.na_reasons.items()))
        return f"{self.na}: {reasons}"


def _md_cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(_md_cell(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def group_by_item(answers: list[Answer], questions=None) -> dict[str, list[Answer]]:
    by_item: dict[str, list[Answer]] = defaultdict(list)
    for a in answers:
        if questions is None or a.question in questions:
            by_item[a.item].append(a)
    return by_item


def category_items(category: str, present: set[str]) -> list[str]:
    """Questionnaire items first (in order), then any unexpected ones that appear."""
    known = next(items for c, _, items in DIMENSIONS if c == category)
    extra = sorted(i for i in present if i not in known and ITEM_CATEGORY.get(i) is None)
    return [*known, *extra]


# ---------------------------------------------------------------------------
# Disagreement (always evaluated on evaluator-level values)
# ---------------------------------------------------------------------------


def disagreement(evaluator_answers: list[Answer], threshold: int) -> dict[str, dict]:
    """Per item: in how many session x question cells evaluators split.

    Likert split: max - min >= threshold among the valid values of one cell.
    Yes/No split: both Yes and No present. Only counts are kept: with two
    evaluators per cell a range would expose both scores, and the team knows
    who covered each session.
    """
    cells: dict[tuple, list[Answer]] = defaultdict(list)
    for a in evaluator_answers:
        cells[(a.item, a.session, a.question)].append(a)
    out: dict[str, dict] = {}
    for (item, _session, _question), cell in cells.items():
        valid = [a.value for a in cell if a.value != NA]
        if len(valid) < 2:
            continue
        rec = out.setdefault(item, {"comparable": 0, "split": 0})
        rec["comparable"] += 1
        if item in YES_NO_ITEMS:
            if len(set(valid)) > 1:
                rec["split"] += 1
        else:
            spread = max(valid) - min(valid)
            if spread >= threshold:
                rec["split"] += 1
    return out


# ---------------------------------------------------------------------------
# Critical failures (per response = session x question; evaluator never output)
# ---------------------------------------------------------------------------


def critical_failure_responses(rows: list[dict[str, str]], warnings: list[str]):
    """-> {(session, question): set(types)} for Q1-Q4 responses, plus all responses screened."""
    screened: dict[tuple[str, str], list[tuple[str, set[str]]]] = defaultdict(list)
    for row in rows:
        session, question = row["session_id"], row["question_id"]
        flag = row["critical_failure"]
        types = {t.strip() for t in row["critical_failure_type"].split(";") if t.strip()}
        if question == USABILITY_QUESTION:
            if flag.lower() == "yes":
                warnings.append(f"{session} SESSION: critical_failure=Yes on a usability row is not counted")
            continue
        if question not in SCENARIO_QUESTIONS:
            continue
        if flag.lower() not in ("yes", "no"):
            warnings.append(f"{session} {question}: critical_failure must be Yes or No (got {flag!r})")
            continue
        flag = flag.capitalize()
        if flag == "No" and types - {"none"}:
            warnings.append(f"{session} {question}: critical_failure=No but a failure type is recorded")
        if flag == "Yes" and (not types or types == {"none"}):
            warnings.append(f"{session} {question}: critical_failure=Yes but no failure type recorded")
        unknown = types - set(FAILURE_TYPES) - {"none"}
        if unknown:
            warnings.append(f"{session} {question}: unknown critical_failure_type {', '.join(sorted(unknown))}")
        screened[(session, question)].append((flag, types - {"none"}))

    result: dict[tuple[str, str], set[str]] = {}
    failed: dict[tuple[str, str], bool] = {}
    for key, recs in screened.items():
        flags = {f for f, _ in recs}
        if len(flags) > 1 or len({frozenset(t) for _, t in recs}) > 1:
            warnings.append(
                f"{key[0]} {key[1]}: critical_failure / type differs between rows of this response "
                "(treated as a failure if any row says Yes; types are unioned)"
            )
        failed[key] = "Yes" in flags
        result[key] = set().union(*(t for _, t in recs)) if failed[key] else set()
    return failed, result


def yes_without_flag(answers: list[Answer], failed: dict[tuple[str, str], bool]) -> list[str]:
    out = []
    for a in answers:
        if a.item in YES_NO_ITEMS and a.value == "Yes" and not failed.get((a.session, a.question), False):
            out.append(f"{a.session} {a.question}: {a.item}=Yes but critical_failure is not Yes")
    return sorted(set(out))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def build_report(rows: list[dict[str, str]], unit: str, split_threshold: int = 2) -> str:
    warnings: list[str] = []
    raw_answers = build_answers(rows, warnings)
    answers = collapse_to_unit(raw_answers, unit)
    failed, failure_types = critical_failure_responses(rows, warnings)
    warnings += yes_without_flag(raw_answers, failed)

    unit_desc = {
        "evaluator": "each evaluator's answer to an item counts as one response",
        "session": "evaluators collapsed first: one response per session × question × item "
        "(Likert = median of valid evaluator values; Yes/No = Yes if any evaluator said Yes)",
    }[unit]
    sessions = sorted({r["session_id"] for r in rows})
    out: list[str] = [
        "# Main-evaluation questionnaire summary (cross-evaluator, descriptive only)",
        "",
        f"- **Sessions in data:** {', '.join(sessions) if sessions else 'none'}",
        f"- **Aggregation unit:** `{unit}` — {unit_desc}",
        "- **N/A** is excluded from every denominator and counted separately. No significance tests; "
        "no overall score; team members are not independent external users.",
        "- Evaluator identities are not reported anywhere in this output.",
        "",
    ]
    if not rows:
        out += ["_No responses recorded yet._", ""]

    # --- 1. item detail ----------------------------------------------------
    out += ["## 1. Items by dimension", ""]
    by_item = group_by_item(answers)
    item_rows: list[list[str]] = []
    stats_by_item: dict[str, ItemStats] = {}
    for category, label, _ in DIMENSIONS:
        present = {a.item for a in answers if a.category == category}
        for item in category_items(category, present):
            item_answers = [a for a in by_item.get(item, []) if a.category == category]
            if item in YES_NO_ITEMS:
                continue
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
        have = [i for i in likert if stats_by_item[i].n]
        ns = {stats_by_item[i].n for i in have}
        if have and len(ns) == 1:
            n_cell = str(ns.pop())
            med_cell = ", ".join(f"{i} {stats_by_item[i].median}" for i in have) + f" (n={stats_by_item[have[0]].n})"
        elif have:
            n_cell = ", ".join(f"{i} {stats_by_item[i].n}" for i in have)
            med_cell = ", ".join(f"{i} {stats_by_item[i].median} (n={stats_by_item[i].n})" for i in have)
        else:
            n_cell, med_cell = "0", "No valid ratings"
        range_cell = ", ".join(f"{i} {stats_by_item[i].range}" for i in have) or "–"
        na_parts = [f"{i} {stats_by_item[i].na_text()}" for i in likert if stats_by_item[i].na]
        yn = [i for i in items if i in YES_NO_ITEMS]
        notes = []
        for i in yn:
            c = _yes_no_counts(answers, i)
            notes.append(f"{i} (Yes/No, not in median): Yes {c['Yes']} / No {c['No']} / N/A {c['N/A']}")
        dim_rows.append([label, n_cell, med_cell, range_cell, "; ".join(na_parts) or "None", "; ".join(notes)])
    out += [table(["Dimension", "Valid n", "Median", "Range", "N/A and reason", "Notes"], dim_rows), ""]

    # --- 3. yes/no ---------------------------------------------------------
    out += [
        "## 3. Yes/No items",
        "",
        "Counts only; no median. In the questionnaire a “Yes” on these items is an automatic critical failure "
        "(see section 5, which is scored separately).",
        "",
    ]
    yn_rows = []
    for category, label, items in DIMENSIONS:
        for i in items:
            if i in YES_NO_ITEMS:
                c = _yes_no_counts(answers, i)
                yn_rows.append([label, i, str(c["Yes"]), str(c["No"]), str(c["N/A"]), str(sum(c.values()))])
    out += [table(["Dimension", "Item", "Yes", "No", "N/A", "Total answers"], yn_rows), ""]

    # --- 4. repeats vs scenarios -------------------------------------------
    out += ["## 4. Repeated ratings vs distinct scenarios", ""]
    out += [
        "Q1–Q4 are fixed public fixtures, so the same question rated in several sessions is a repeat of one "
        "scenario, not new evidence. Pooled statistics in section 1 therefore describe repeated ratings of "
        f"{len({r['question_id'] for r in rows if r['question_id'] in SCENARIO_QUESTIONS})} distinct scenario(s).",
        "",
    ]
    rep_rows = []
    for q in (*SCENARIO_QUESTIONS, USABILITY_QUESTION):
        qa = [a for a in answers if a.question == q]
        sess = sorted({a.session for a in qa})
        if not sess:
            rep_rows.append([q, "0", "0", "–"])
            continue
        n_responses = len({(a.session, a.evaluator) for a in qa})
        kind = "once per session" if q == USABILITY_QUESTION else ("repeated" if len(sess) > 1 else "single")
        rep_rows.append([q, str(len(sess)), str(n_responses), kind])
    out += [table(["Question", "Sessions rated", "Responding evaluators (sum over sessions)" if unit == "evaluator" else "Session responses", "Status"], rep_rows), ""]
    q_rows = []
    for category, label, _ in DIMENSIONS:
        present = {a.item for a in answers if a.category == category}
        for item in category_items(category, present):
            if item in YES_NO_ITEMS:
                continue
            cells = []
            for q in (*SCENARIO_QUESTIONS, USABILITY_QUESTION):
                s = ItemStats([a for a in answers if a.item == item and a.question == q and a.category == category])
                if s.n:
                    cells.append(f"{q} {s.median} (n={s.n})")
            if cells:
                q_rows.append([label, item, "; ".join(cells)])
    out += ["Per-question medians:", "", table(["Dimension", "Item", "Median by question"], q_rows), ""]

    # --- 5. critical failures ---------------------------------------------
    out += ["## 5. Critical failures", ""]
    out += [
        "### 5a. All-question screen (Q1–Q4)",
        "",
        "Counted per response (session × question). Kept apart from the Q4 100% rule in 5b.",
        "",
    ]
    cf_rows = []
    for q in SCENARIO_QUESTIONS:
        screened = [k for k in failed if k[1] == q]
        bad = sorted(k for k in screened if failed[k])
        cf_rows.append([q, str(len(screened)), str(len(screened) - len(bad)), str(len(bad)),
                        "; ".join(f"{s}/{qq}" for s, qq in bad) or "none"])
    total_s = len(failed)
    total_bad = sorted(k for k in failed if failed[k])
    cf_rows.append(["**All Q1–Q4**", f"**{total_s}**", f"**{total_s - len(total_bad)}**", f"**{len(total_bad)}**",
                    "; ".join(f"{s}/{q}" for s, q in total_bad) or "none"])
    out += [table(["Question", "Responses screened", "Zero critical failures", "With a critical failure", "session_id/question_id"], cf_rows), ""]

    out += ["Failures by type (a response with several types counts once under each):", ""]
    type_rows = []
    for t in FAILURE_TYPES:
        hits = sorted(k for k, ts in failure_types.items() if t in ts)
        type_rows.append([t, str(len(hits)), "; ".join(f"{s}/{q}" for s, q in hits) or "–"])
    other = sorted({t for ts in failure_types.values() for t in ts} - set(FAILURE_TYPES))
    for t in other:
        hits = sorted(k for k, ts in failure_types.items() if t in ts)
        type_rows.append([f"{t} (unlisted type)", str(len(hits)), "; ".join(f"{s}/{q}" for s, q in hits)])
    out += [table(["Failure type", "Responses", "session_id/question_id"], type_rows), ""]

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
    ranked = [(i, s) for i, s in stats_by_item.items() if s.n]
    if ranked:
        low = min(float(s.median) for _, s in ranked)
        lows = [i for i, s in sorted(ranked, key=lambda kv: _item_sort_key(kv[0])) if float(s.median) == low]
        out.append(f"- **Lowest item(s) by median:** {', '.join(f'{i} (median {stats_by_item[i].median}, n={stats_by_item[i].n}, range {stats_by_item[i].range})' for i in lows)}")
    else:
        out.append("- **Lowest item(s) by median:** no valid ratings yet")
    dis = disagreement(raw_answers, split_threshold)
    split_items = {i: d for i, d in dis.items() if d["split"]}
    if split_items:
        parts = []
        for i in sorted(split_items, key=_item_sort_key):
            d = split_items[i]
            parts.append(f"{i} (split in {d['split']} of {d['comparable']} comparable session×question cells)")
        out.append(f"- **Evaluators split** (Likert: ≥{split_threshold} points apart within a session × question; "
                   f"Yes/No: both answers): {'; '.join(parts)}")
    else:
        out.append(f"- **Evaluators split:** none (Likert ≥{split_threshold} points apart, or Yes and No both given, "
                   "within a session × question)")
    out.append(
        f"- **Critical failures:** {len(total_bad)} of {total_s} screened Q1–Q4 responses"
        + (f" ({'; '.join(f'{s}/{q}' for s, q in total_bad)})" if total_bad else "")
        + "; reported separately from ratings — a high median cannot cancel one."
    )
    out.append("")

    # --- 7. data quality ---------------------------------------------------
    out += ["## 7. Data-quality notes", ""]
    out += [f"- {w}" for w in sorted(set(warnings))] or ["- None."]
    out.append("")

    text = "\n".join(out)
    return _scrub(text, {r["evaluator_code"] for r in rows if r["evaluator_code"]})


def _yes_no_counts(answers: list[Answer], item: str) -> Counter:
    c = Counter({"Yes": 0, "No": 0, "N/A": 0})
    for a in answers:
        if a.item == item:
            c[a.value if a.value in ("Yes", "No") else "N/A"] += 1
    return c


def _scrub(text: str, evaluator_codes: set[str]) -> str:
    """Free text (na_reason, warnings) may quote an evaluator code: redact, then verify."""
    for code in sorted(evaluator_codes, key=len, reverse=True):
        text = text.replace(code, REDACTED)
    leaked = [c for c in evaluator_codes if c in text]
    if leaked:  # defensive; cannot happen after the replace above
        raise RuntimeError("evaluator_code would appear in the output; refusing to emit it")
    return text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _is_protected(path: Path) -> bool:
    return any(path.resolve() == p.resolve() for p in PROTECTED_OUTPUTS)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="session-responses CSV (read only)")
    ap.add_argument("--unit", choices=("evaluator", "session"), default="evaluator", help="aggregation unit")
    ap.add_argument("--split-threshold", type=int, default=2, help="Likert points apart that count as a split")
    ap.add_argument("--output", type=Path, help="write markdown here instead of stdout")
    args = ap.parse_args(argv)

    if args.output is not None and _is_protected(args.output):
        ap.error(f"refusing to write to {args.output.name}: the CSV and the threshold summary are never overwritten")

    report = build_report(load_rows(args.input), args.unit, args.split_threshold)
    if args.output is None:
        sys.stdout.reconfigure(encoding="utf-8")
        print(report)
    else:
        args.output.write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
