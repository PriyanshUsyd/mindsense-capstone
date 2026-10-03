"""Factory for the pinned, loopback-only local SLM runtime."""

from __future__ import annotations

import math
import os
from pathlib import Path

import yaml

from backend.slm.client import (
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    OllamaClient,
    OllamaClientConfig,
)
from backend.slm.service import SLMService

MODEL_MANIFEST_PATH = Path(__file__).resolve().parent / "model_manifest.yaml"
OLLAMA_TIMEOUT_SECONDS_ENV = "MINDSENSE_OLLAMA_TIMEOUT_SECONDS"


def configured_timeout_seconds() -> float:
    """Return the bounded local inference deadline used by the API runtime."""

    raw = os.environ.get(OLLAMA_TIMEOUT_SECONDS_ENV)
    if raw is None or not raw.strip():
        return DEFAULT_OLLAMA_TIMEOUT_SECONDS
    try:
        timeout_seconds = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"{OLLAMA_TIMEOUT_SECONDS_ENV} must be a number from 1 to 300"
        ) from exc
    if not math.isfinite(timeout_seconds) or not 1.0 <= timeout_seconds <= 300.0:
        raise ValueError(f"{OLLAMA_TIMEOUT_SECONDS_ENV} must be a number from 1 to 300")
    return timeout_seconds


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


def default_model_tag(manifest_path: Path = MODEL_MANIFEST_PATH) -> str:
    """Return the manifest default only when it is also an allowed candidate."""

    parsed = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise TypeError("model manifest must contain a mapping")
    tag = parsed.get("model_tag")
    if not isinstance(tag, str) or tag not in listed_model_tags(manifest_path):
        raise ValueError("manifest model_tag must name a comparison candidate")
    return tag


def create_local_service(
    *,
    model_tag: str | None = None,
    endpoint: str = "http://127.0.0.1:11434/api/chat",
    timeout_seconds: float | None = None,
) -> SLMService:
    """Create the Week 5 shadow service for a manifest-listed candidate."""

    allowed_tags = listed_model_tags()
    selected_model_tag = model_tag or default_model_tag()
    if selected_model_tag not in allowed_tags:
        raise ValueError(
            f"model_tag must be one of the pinned comparison candidates: {allowed_tags}"
        )

    client = OllamaClient(
        OllamaClientConfig(
            model_tag=selected_model_tag,
            endpoint=endpoint,
            timeout_seconds=(
                configured_timeout_seconds()
                if timeout_seconds is None
                else timeout_seconds
            ),
        )
    )
    return SLMService(client)
