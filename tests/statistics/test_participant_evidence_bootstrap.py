"""Bootstrap intersection result on the `/respond` packet path (preregistration
section 4.1, wired 2026-10-16).

CI has no CES data and no bootstrap cache, so every test here uses synthetic
sensing/EMA rows and a synthetic intersection table. No participant identifier
from the real dataset appears in this file.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

import pandas as pd
import pytest

from backend.api.app import DeterministicDemoClient
from backend.contracts.comparison_reasons import (
    STATE_C_EVIDENCE_NOT_REPORTABLE,
    STATE_C_TOO_FEW_RECORDED_DAYS,
)
from backend.contracts.evidence import EligibilityStatus, EvidenceStrength, ResponseMode
from backend.slm.output_grounding import render_grounded_response_option
from backend.slm.service import SLMService
from backend.statistics import bootstrap_cache
from backend.statistics import participant_evidence as pe
from backend.statistics.private_files import PermissionRestrictionError

UID = "synthetic-participant"
QUESTION = "How was my movement different from my recent baseline?"
LAST_DAY = date(2026, 3, 31)
NEW_SENTENCE = (
    "Your history is long enough to compare with your own baseline, but there "
    "is not enough statistical evidence to report a comparison."
)
TOO_FEW_SENTENCE = (
    "Your history is long enough to compare with your own baseline, but there "
    "are too few recorded days in the comparison periods to report one."
)
TOO_EARLY = "It is too early to compare with your own baseline."
# Wording no answer may contain: causes, diagnoses, treatment, risk, or a
# comparison with other people.
FORBIDDEN = re.compile(
    r"\bcaus|\bbecause\b|\bdiagnos|\bdepress|\btreat|\brisk\b|\bpredict"
    r"|\bother (?:people|users|participants|students)\b|\baverage person\b",
    re.IGNORECASE,
)


def _sensing(n_days: int, *, recent_gap: bool = False) -> pd.DataFrame:
    """`n_days` consecutive days ending LAST_DAY, GPS in metres. With
    `recent_gap`, only 5 of the last 14 days have a valid value."""
    rows = []
    for i in range(n_days):
        day = LAST_DAY - timedelta(days=n_days - 1 - i)
        value = 20_000.0 + (i % 5) * 1_500.0
        if recent_gap and (LAST_DAY - day).days < 14 and (LAST_DAY - day).days >= 5:
            value = float("nan")
        rows.append(
            {"uid": UID, "day": int(day.strftime("%Y%m%d")), "is_ios": 1, "loc_dist_ep_0_clean": value}
        )
    return pd.DataFrame(rows)


def _ema(n_days: int) -> pd.DataFrame:
    days = [LAST_DAY - timedelta(days=d) for d in range(0, n_days, 7)]
    return pd.DataFrame(
        {"uid": UID, "day": [int(d.strftime("%Y%m%d")) for d in days], "phq4_score": 3.0}
    )


def _table(label: str = "evidence_available", **overrides) -> pd.DataFrame:
    row = {
        "uid": UID,
        "slope_i": 0.4,
        "n_occasions": 12,
        "std_effect": 0.15,
        "slope_se_parametric": 0.12,
        "slope_se_cluster": 0.03,
        "label_parametric": "moderate" if label == "evidence_available" else "insufficient",
        "label_cluster": "moderate" if label == "evidence_available" else "weak",
        "label_intersection": label,
    }
    row.update(overrides)
    return pd.DataFrame([row])


@pytest.fixture
def synthetic(monkeypatch):
    """Point the packet builder at synthetic rows; returns a setter."""

    def install(n_days=60, *, recent_gap=False, table=None, unavailable_reason=None):
        sensing = _sensing(n_days, recent_gap=recent_gap)

        def cleaned(feature_id):
            if feature_id != "gps_distance":
                raise pe.UnknownFeature(feature_id)
            return sensing

        monkeypatch.setattr(pe, "_cleaned_sensing", cleaned)
        monkeypatch.setattr(pe, "_ema", lambda: _ema(n_days))
        result = pe._EvidenceTable(
            None if table is None else table.set_index("uid"), unavailable_reason
        )
        monkeypatch.setattr(pe, "_evidence_table", lambda feature_id: result)

    return install


def _respond(packet):
    return SLMService(DeterministicDemoClient()).respond(packet, QUESTION)


def test_qualifying_participant_gets_own_baseline_comparison_with_uncertainty(synthetic):
    synthetic(table=_table("evidence_available"))
    packet = pe.build_evidence_packet(UID)

    assert packet.baseline.eligibility_status == EligibilityStatus.ELIGIBLE
    assert packet.baseline.value == int(packet.baseline.value)
    assert packet.evidence is not None
    assert packet.evidence.evidence_strength == EvidenceStrength.MODERATE
    # CI uses the larger (parametric) SE: 0.4 +/- 1.96 * 0.12.
    assert packet.evidence.confidence_interval_low == pytest.approx(0.4 - 1.959963984540054 * 0.12)

    response = _respond(packet)
    assert response.used_fallback is False, response.rejection_reason
    assert response.response_mode == ResponseMode.NORMAL
    assert f"compared with your own baseline of {int(packet.baseline.value)} kilometres per day" in response.text
    assert "This estimate is uncertain and should be interpreted cautiously." in response.text
    assert ".0 " not in response.text
    assert not FORBIDDEN.search(response.text)


def test_full_history_without_evidence_gets_accurate_sentence_not_too_early(synthetic):
    synthetic(table=_table("no_claim"))
    packet = pe.build_evidence_packet(UID)

    assert packet.baseline.eligibility_status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY
    assert packet.baseline.ineligible_reason == STATE_C_EVIDENCE_NOT_REPORTABLE
    assert packet.baseline.value is None and packet.evidence is None

    response = _respond(packet)
    assert response.used_fallback is False, response.rejection_reason
    assert NEW_SENTENCE in response.text
    assert TOO_EARLY not in response.text
    assert not FORBIDDEN.search(response.text)


def test_full_history_with_too_few_recent_days_gets_its_own_sentence(synthetic):
    synthetic(recent_gap=True, table=_table("evidence_available"))
    packet = pe.build_evidence_packet(UID)

    assert packet.baseline.eligibility_status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY
    assert packet.baseline.ineligible_reason == STATE_C_TOO_FEW_RECORDED_DAYS
    response = _respond(packet)
    assert response.used_fallback is False, response.rejection_reason
    assert TOO_FEW_SENTENCE in response.text
    assert TOO_EARLY not in response.text


def test_cold_start_participant_still_gets_too_early(synthetic):
    # 10 days: State B (>= 7 calendar days, >= 5 sensor-days, >= 1 EMA).
    synthetic(n_days=10, table=_table("evidence_available"))
    packet = pe.build_evidence_packet(UID)

    assert packet.baseline.eligibility_status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY
    assert packet.baseline.ineligible_reason not in {
        STATE_C_EVIDENCE_NOT_REPORTABLE,
        STATE_C_TOO_FEW_RECORDED_DAYS,
    }
    response = _respond(packet)
    assert response.used_fallback is False, response.rejection_reason
    assert TOO_EARLY in response.text
    assert NEW_SENTENCE not in response.text


@pytest.mark.parametrize(
    "table, reason",
    [
        (None, "per-person evidence unavailable: no bootstrap cache"),
        (_table("evidence_available", slope_se_parametric=float("nan")), None),
        (_table("evidence_available", label_cluster="weak"), None),
    ],
    ids=["cache-missing", "se-not-finite", "label-inconsistent"],
)
def test_missing_or_unusable_evidence_fails_closed_to_no_claim(synthetic, table, reason):
    synthetic(table=table, unavailable_reason=reason)
    packet = pe.build_evidence_packet(UID)

    assert packet.baseline.eligibility_status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY
    assert packet.evidence is None
    assert packet.baseline.value is None
    assert NEW_SENTENCE in _respond(packet).text


# --- _load_evidence_table: every failure is None, never an exception -------


@pytest.fixture
def loader(monkeypatch):
    monkeypatch.setattr(pe, "_EVIDENCE_TABLE_CACHE", {})
    monkeypatch.setattr(pe.r_bridge, "r_bridge_available", lambda: True)
    monkeypatch.setattr(pe, "_cleaned_sensing", lambda feature_id: _sensing(60))
    monkeypatch.setattr(pe, "_ema", lambda: _ema(60))
    monkeypatch.setattr(pe, "build_model_frame", lambda *a, **k: pd.DataFrame())
    return monkeypatch


def test_no_r_engine_skips_the_cache(monkeypatch):
    monkeypatch.setattr(pe, "_EVIDENCE_TABLE_CACHE", {})
    monkeypatch.setattr(pe.r_bridge, "r_bridge_available", lambda: False)
    assert pe._evidence_table("gps_distance").table is None


@pytest.mark.parametrize(
    "error",
    [
        bootstrap_cache.BootstrapCacheStale("fingerprint changed", ["code.backend/statistics/evidence.py"]),
        bootstrap_cache.BootstrapCacheError("unreadable"),
        PermissionRestrictionError("not owner-only"),
        OSError("disk"),
    ],
    ids=["stale", "unreadable", "permissions", "os-error"],
)
def test_cache_errors_fail_closed(loader, error):
    def boom(*args, **kwargs):
        raise error

    loader.setattr(pe.bootstrap_cache, "load_aggregated_cache", boom)
    result = pe._evidence_table("gps_distance")
    assert result.table is None
    assert result.unavailable_reason == "per-person evidence unavailable: bootstrap cache unusable"


def test_absent_cache_fails_closed(loader):
    loader.setattr(pe.bootstrap_cache, "load_aggregated_cache", lambda *a, **k: None)
    assert pe._evidence_table("gps_distance").table is None


def test_malformed_cache_table_fails_closed(loader):
    cached = bootstrap_cache.AggregatedCache("0" * 64, 500, pd.DataFrame(), _table().drop(columns="label_intersection"), {})
    loader.setattr(pe.bootstrap_cache, "load_aggregated_cache", lambda *a, **k: cached)
    assert pe._evidence_table("gps_distance").table is None


def test_corrupt_cache_file_on_disk_fails_closed(loader, tmp_path):
    feature_dir = tmp_path / "loc_dist_ep_0"
    feature_dir.mkdir()
    (feature_dir / bootstrap_cache.AGGREGATED_NAME).write_text("{not json", encoding="utf-8")
    loader.setattr(pe, "BOOTSTRAP_CACHE_ROOT", tmp_path)
    assert pe._evidence_table("gps_distance").table is None


def test_valid_cache_table_is_indexed_by_uid(loader):
    cached = bootstrap_cache.AggregatedCache("0" * 64, 500, pd.DataFrame(), _table(), {})
    loader.setattr(pe.bootstrap_cache, "load_aggregated_cache", lambda *a, **k: cached)
    table = pe._evidence_table("gps_distance").table
    assert table is not None and UID in table.index


# --- whole-number display ----------------------------------------------------


def test_whole_values_render_without_decimal_point(synthetic):
    synthetic(table=_table("no_claim"))
    packet = pe.build_evidence_packet(UID)
    text = render_grounded_response_option(packet, ResponseMode.UNCERTAINTY)["text"]
    value = packet.feature_window.value
    assert value == int(value)
    assert f"was {int(value)} kilometres per day" in text
    assert f"{int(value)}.0" not in text
