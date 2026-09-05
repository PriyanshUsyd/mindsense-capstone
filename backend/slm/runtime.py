"""Factory for the pinned, loopback-only local SLM runtime."""

from __future__ import annotations

from pathlib import Path

import yaml

from backend.slm.client import OllamaClient, OllamaClientConfig
from backend.slm.service import SLMService

MODEL_MANIFEST_PATH = Path(__file__).resolve().parent / "model_manifest.yaml"


def listed_model_tags(manifest_path: Path = MODEL_MANIFEST_PATH) -> tuple[str, ...]:
    """Return only exact model tags listed in the versioned manifest."""

    parsed = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise TypeError("model manifest must contain a mapping")

    candidates = parsed.get("comparison_candidates")
    if not isinstance(candidates, list):
        raise TypeError("model manifest must list comparison_candidates")

    tags = tuple(
        candidate.get("model_tag")
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("model_tag"), str)
    )
    if not tags or len(tags) != len(candidates):
        raise ValueError("every comparison candidate must have a model_tag")
    if len(tags) != len(set(tags)):
        raise ValueError("model manifest contains duplicate model tags")
    return tags


def create_local_service(
    *,
    model_tag: str = "phi4-mini:3.8b",
    endpoint: str = "http://127.0.0.1:11434/api/chat",
    timeout_seconds: float = 120.0,
) -> SLMService:
    """Create the Week 5 shadow service for a manifest-listed candidate."""

    allowed_tags = listed_model_tags()
    if model_tag not in allowed_tags:
        raise ValueError(
            f"model_tag must be one of the pinned comparison candidates: {allowed_tags}"
        )

    client = OllamaClient(
        OllamaClientConfig(
            model_tag=model_tag,
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
        )
    )
    return SLMService(client)
