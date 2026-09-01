import hashlib

import pytest

from backend.contracts.evidence import ProhibitedClaimId
from backend.slm.prompt_loader import (
    DEFAULT_CRISIS_FALLBACK,
    DEFAULT_EVIDENCE_PROMPT,
    DEFAULT_INSUFFICIENT_DATA_TEMPLATE,
    PromptManifestError,
    load_evidence_prompt,
    load_fallback_prompt,
)


def test_evidence_prompt_loads_and_hashes_exact_bytes():
    loaded = load_evidence_prompt()

    assert loaded.manifest.prompt_id == "evidence_explainer"
    assert loaded.manifest.prompt_version == "0.4.3"
    assert set(loaded.manifest.prohibited_claim_ids) == set(ProhibitedClaimId)
    assert (
        loaded.sha256
        == hashlib.sha256(DEFAULT_EVIDENCE_PROMPT.read_bytes()).hexdigest()
    )


def test_generic_fallback_loads_with_safe_yaml():
    loaded = load_fallback_prompt()

    assert loaded.manifest.template_id == "generic_fallback"
    assert loaded.manifest.text.strip()


def test_crisis_fallback_loads_with_safe_yaml():
    loaded = load_fallback_prompt(DEFAULT_CRISIS_FALLBACK)

    assert loaded.manifest.template_id == "crisis_aware_fallback"
    assert loaded.manifest.template_version == "1.1.0"
    assert loaded.manifest.text.strip()


def test_insufficient_data_template_loads_with_safe_yaml():
    loaded = load_fallback_prompt(DEFAULT_INSUFFICIENT_DATA_TEMPLATE)

    assert loaded.manifest.template_id == "insufficient_data"
    assert loaded.manifest.response_mode.value == "insufficient_data"
    assert loaded.manifest.text.strip()


def test_prompt_loader_rejects_unknown_fields(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text(
        DEFAULT_EVIDENCE_PROMPT.read_text(encoding="utf-8") + "\nunknown: true\n",
        encoding="utf-8",
    )

    with pytest.raises(PromptManifestError):
        load_evidence_prompt(path)


def test_prompt_loader_rejects_unsafe_yaml_tags(tmp_path):
    marker = tmp_path / "must-not-exist"
    path = tmp_path / "unsafe.yaml"
    path.write_text(
        f"!!python/object/apply:pathlib.Path.write_text ['{marker}', 'bad']\n",
        encoding="utf-8",
    )

    with pytest.raises(PromptManifestError):
        load_evidence_prompt(path)
    assert not marker.exists()
