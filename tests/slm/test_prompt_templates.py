"""
Validation tests for the two Week 4 SLM fallback templates and the model
manifest, added 2026-08-29 as part of the 50-test verification pass.
Confirms they parse as valid YAML and carry every field the contract/skill
file requires — not just that the files exist.
"""

from pathlib import Path

import pytest
import yaml

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "backend" / "slm" / "prompts"
MANIFEST_PATH = (
    Path(__file__).resolve().parents[2] / "backend" / "slm" / "model_manifest.yaml"
)

REQUIRED_TEMPLATE_FIELDS = {
    "template_id",
    "template_version",
    "response_mode",
    "allowed_claim_ids",
    "prohibited_claim_ids",
    "text",
}

VALID_RESPONSE_MODES = {
    "normal",
    "insufficient_data",
    "uncertainty",
    "refusal",
    "generic_fallback",
    "crisis_aware_fallback",
}

APPROVED_CLAIM_IDS = {
    "observation_of_deviation",
    "within_person_association",
    "trend_description",
    "uncertainty_disclosure",
    "not_enough_data",
    "non_diagnostic_boundary",
}

PROHIBITED_CLAIM_IDS = {
    "diagnosis",
    "causal_explanation",
    "treatment_or_crisis_advice",
    "risk_prediction",
}


@pytest.fixture(params=["generic_fallback.yaml", "crisis_aware.yaml"])
def template(request):
    path = TEMPLATE_DIR / request.param
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f), request.param


def test_template_parses_as_valid_yaml(template):
    data, name = template
    assert isinstance(data, dict), f"{name} did not parse to a dict"


def test_template_has_all_required_fields(template):
    data, name = template
    missing = REQUIRED_TEMPLATE_FIELDS - data.keys()
    assert not missing, f"{name} is missing required fields: {missing}"


def test_template_response_mode_is_valid(template):
    data, name = template
    assert data["response_mode"] in VALID_RESPONSE_MODES, (
        f"{name} has unknown response_mode {data['response_mode']!r}"
    )


def test_template_allowed_claim_ids_are_all_approved(template):
    data, name = template
    unknown = set(data["allowed_claim_ids"]) - APPROVED_CLAIM_IDS
    assert not unknown, f"{name} allows unknown/non-approved claim ids: {unknown}"


def test_template_prohibited_claim_ids_cover_all_four(template):
    data, name = template
    assert set(data["prohibited_claim_ids"]) == PROHIBITED_CLAIM_IDS, (
        f"{name} does not list all 4 prohibited claim ids"
    )


def test_template_no_overlap_between_allowed_and_prohibited(template):
    data, name = template
    overlap = set(data["allowed_claim_ids"]) & set(data["prohibited_claim_ids"])
    assert not overlap, (
        f"{name} allows a claim id that is also listed prohibited: {overlap}"
    )


def test_template_text_is_nonempty(template):
    data, name = template
    assert isinstance(data["text"], str) and data["text"].strip(), (
        f"{name} has empty text"
    )


def test_generic_fallback_does_not_contain_crisis_resources():
    """The generic fallback must not accidentally contain crisis-line
    content — that's the crisis template's job specifically, and mixing
    them would blur the two required distinct templates."""
    with open(TEMPLATE_DIR / "generic_fallback.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    text_lower = data["text"].lower()
    assert "988" not in text_lower
    assert "lifeline" not in text_lower


def test_crisis_aware_contains_real_helpline_reference():
    with open(TEMPLATE_DIR / "crisis_aware.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    text_lower = data["text"].lower()
    assert "lifeline" in text_lower
    assert "13 11 14" in text_lower
    assert "000" in text_lower
    assert "1300 659 467" in text_lower


def test_crisis_aware_is_localised_for_australia_only():
    with open(TEMPLATE_DIR / "crisis_aware.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    text_lower = data["text"].lower()
    assert "australia" in text_lower
    assert "988" not in text_lower
    assert "741741" not in text_lower
    assert "united states" not in text_lower
    assert "if you're in the us" not in text_lower


def test_template_ids_are_unique_across_both_files():
    ids = []
    for name in ["generic_fallback.yaml", "crisis_aware.yaml"]:
        with open(TEMPLATE_DIR / name, "r", encoding="utf-8") as f:
            ids.append(yaml.safe_load(f)["template_id"])
    assert len(ids) == len(set(ids))


def test_model_manifest_parses_and_pins_exact_tag():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    assert manifest["model_tag"] == "phi4-mini:3.8b"
    assert "latest" not in manifest["model_tag"]


def test_model_manifest_marks_phi_and_qwen_as_comparison_candidates():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    assert manifest["selection_status"] == "comparison_pending"
    tags = {candidate["model_tag"] for candidate in manifest["comparison_candidates"]}
    assert tags == {"phi4-mini:3.8b", "qwen3:4b"}
    assert all("latest" not in tag for tag in tags)


def test_model_manifest_has_temperature_zero():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    assert manifest["call_pattern"]["temperature"] == 0.0
    assert manifest["call_pattern"]["seed"] == 42
