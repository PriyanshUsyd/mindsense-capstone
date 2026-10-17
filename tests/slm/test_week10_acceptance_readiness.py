"""Preparation safeguards only; no formal prompts or model generation."""

import pytest

from benchmarks import slm_week10_acceptance_readiness as prep


@pytest.mark.parametrize(
    "endpoint", ["/api/chat", "/api/generate", "https://example.org", "/respond"]
)
def test_preflight_rejects_generation_or_external_endpoint(endpoint):
    with pytest.raises(ValueError, match="metadata GET only"):
        prep.get_runtime_metadata(endpoint)


def test_runtime_metadata_refuses_redirect():
    with pytest.raises(ValueError, match="redirects are forbidden"):
        prep.NoRedirects().redirect_request(
            None, None, 302, "", {}, "https://example.org"
        )


def test_technical_success_never_authorises_formal_run(monkeypatch):
    for name in (
        "source_check",
        "runtime_check",
        "api_check",
        "cache_check",
        "evidence_check",
    ):
        monkeypatch.setattr(prep, name, lambda: {"test_only": True})
    result = prep.collect()
    assert result["technical_preparation_passed"] is True
    assert result["ready_for_formal_run"] is False
    assert result["pending_human_decisions"]
    assert result["human_ratings"] is None


def test_failure_preserved_without_printing_sensitive_exception(monkeypatch):
    def fail():
        raise ValueError("participant-bearing private detail")

    for name in (
        "source_check",
        "runtime_check",
        "api_check",
        "cache_check",
        "evidence_check",
    ):
        monkeypatch.setattr(prep, name, dict)
    monkeypatch.setattr(prep, "cache_check", fail)
    result = prep.collect()
    assert not result["technical_preparation_passed"]
    assert result["checks"]["cache"] == {"passed": False, "error_type": "ValueError"}
    assert "participant-bearing" not in str(result)


def test_templates_cover_both_models_without_prefilling_scores():
    records = prep.blank_records()
    assert len(records) == 48
    for model in prep.MODELS:
        rows = [r for r in records if r["selected_model_tag"] == model]
        assert [r["slot"] for r in rows] == list(range(1, 25))
    for row in records:
        assert all(
            value is None
            for key, value in row.items()
            if key not in {"slot", "selected_model_tag"}
        )


@pytest.mark.parametrize("name", ["../elsewhere", "C:/elsewhere", "a/b", "a\\b", "."])
def test_output_name_cannot_escape_private_root(name):
    with pytest.raises(ValueError, match="single local directory"):
        prep.main(["--output-name", name])
