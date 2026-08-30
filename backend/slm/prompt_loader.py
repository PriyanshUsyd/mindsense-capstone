"""Versioned, safely loaded prompt manifests for the local SLM."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.contracts.evidence import (
    ApprovedClaimId,
    ProhibitedClaimId,
    ResponseMode,
)


class PromptManifestError(ValueError):
    """Raised when a prompt file cannot be safely loaded or validated."""


class EvidencePromptManifest(BaseModel):
    """Strict shape for the evidence-to-draft system prompt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    allowed_claim_ids: tuple[ApprovedClaimId, ...]
    prohibited_claim_ids: tuple[ProhibitedClaimId, ...]
    system_text: str = Field(min_length=1)

    @field_validator("allowed_claim_ids")
    @classmethod
    def require_allowed_claims(
        cls, value: tuple[ApprovedClaimId, ...]
    ) -> tuple[ApprovedClaimId, ...]:
        if not value:
            raise ValueError("allowed_claim_ids must not be empty")
        if len(value) != len(set(value)):
            raise ValueError("allowed_claim_ids must be unique")
        return value

    @field_validator("prohibited_claim_ids")
    @classmethod
    def require_all_prohibited_claims(
        cls, value: tuple[ProhibitedClaimId, ...]
    ) -> tuple[ProhibitedClaimId, ...]:
        if set(value) != set(ProhibitedClaimId):
            raise ValueError("prohibited_claim_ids must contain all prohibited claims")
        return value


class FallbackPromptManifest(BaseModel):
    """Strict shape shared by deterministic fallback templates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    template_id: str = Field(min_length=1)
    template_version: str = Field(min_length=1)
    response_mode: ResponseMode
    allowed_claim_ids: tuple[ApprovedClaimId, ...]
    prohibited_claim_ids: tuple[ProhibitedClaimId, ...]
    text: str = Field(min_length=1)
    review_note: str | None = None

    @field_validator("prohibited_claim_ids")
    @classmethod
    def require_all_prohibited_claims(
        cls, value: tuple[ProhibitedClaimId, ...]
    ) -> tuple[ProhibitedClaimId, ...]:
        if set(value) != set(ProhibitedClaimId):
            raise ValueError("prohibited_claim_ids must contain all prohibited claims")
        return value


@dataclass(frozen=True)
class LoadedEvidencePrompt:
    manifest: EvidencePromptManifest
    sha256: str
    source_path: Path


@dataclass(frozen=True)
class LoadedFallbackPrompt:
    manifest: FallbackPromptManifest
    sha256: str
    source_path: Path


DEFAULT_EVIDENCE_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "evidence_explainer.yaml"
)
DEFAULT_GENERIC_FALLBACK = (
    Path(__file__).resolve().parent / "prompts" / "generic_fallback.yaml"
)
DEFAULT_CRISIS_FALLBACK = (
    Path(__file__).resolve().parent / "prompts" / "crisis_aware.yaml"
)


def load_evidence_prompt(
    path: str | Path = DEFAULT_EVIDENCE_PROMPT,
) -> LoadedEvidencePrompt:
    """Load a versioned prompt with safe YAML and return its byte hash."""

    source_path = Path(path).resolve()
    try:
        raw = source_path.read_bytes()
        parsed = yaml.safe_load(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise PromptManifestError("prompt YAML must contain a mapping")
        manifest = EvidencePromptManifest.model_validate(parsed)
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValidationError) as exc:
        raise PromptManifestError(
            f"failed to load evidence prompt manifest: {source_path.name}"
        ) from exc

    return LoadedEvidencePrompt(
        manifest=manifest,
        sha256=hashlib.sha256(raw).hexdigest(),
        source_path=source_path,
    )


def load_fallback_prompt(
    path: str | Path = DEFAULT_GENERIC_FALLBACK,
) -> LoadedFallbackPrompt:
    """Load a deterministic fallback template with safe YAML."""

    source_path = Path(path).resolve()
    try:
        raw = source_path.read_bytes()
        parsed = yaml.safe_load(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise PromptManifestError("fallback YAML must contain a mapping")
        manifest = FallbackPromptManifest.model_validate(parsed)
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValidationError) as exc:
        raise PromptManifestError(
            f"failed to load fallback prompt manifest: {source_path.name}"
        ) from exc

    return LoadedFallbackPrompt(
        manifest=manifest,
        sha256=hashlib.sha256(raw).hexdigest(),
        source_path=source_path,
    )
