"""Bounded, loopback-only category classifier for uncertain request routing."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from backend.slm.client import (
    JSONTransport,
    OllamaClientConfig,
    SLMClientError,
    UrllibLoopbackTransport,
)

ROUTER_PROMPT_PATH = Path(__file__).resolve().parent / "prompts/category_router.yaml"
ROUTER_TIMEOUT_SECONDS = 30.0


class CategoryRouterLabel(str, Enum):
    CRISIS = "crisis"
    DIAGNOSIS = "diagnosis"
    TREATMENT = "treatment"
    CAUSE = "cause"
    RISK = "risk"
    CLINICAL_SCORE = "clinical_score"
    INJECTION = "injection"
    SENSITIVE = "sensitive"
    APP_INFO = "app_info"
    CAPABILITY = "capability"
    TIME_WINDOW = "time_window"
    FEATURE_UNCLEAR = "feature_unclear"
    UNTRACKED = "untracked"
    IN_SCOPE_GPS = "in_scope_gps"
    IN_SCOPE_UNLOCKS = "in_scope_unlocks"
    OFF_TOPIC = "off_topic"


_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": [label.value for label in CategoryRouterLabel],
        }
    },
    "required": ["category"],
    "additionalProperties": False,
}


class OllamaCategoryRouter:
    """A single temperature-zero classification; errors retain rules routing."""

    def __init__(
        self,
        config: OllamaClientConfig,
        *,
        transport: JSONTransport | None = None,
        prompt_path: Path = ROUTER_PROMPT_PATH,
    ) -> None:
        self.config = config
        self.transport = transport or UrllibLoopbackTransport()
        self.timeout_seconds = min(ROUTER_TIMEOUT_SECONDS, config.timeout_seconds)
        raw = prompt_path.read_bytes()
        prompt = yaml.safe_load(raw)
        if not isinstance(prompt, dict) or set(prompt) != {
            "prompt_id", "prompt_version", "system_text"
        }:
            raise ValueError("category router prompt has an invalid manifest")
        if not all(isinstance(prompt[key], str) and prompt[key].strip() for key in prompt):
            raise ValueError("category router prompt fields must be nonempty strings")
        self.prompt_version = prompt["prompt_version"]
        self.prompt_sha256 = hashlib.sha256(raw).hexdigest()
        self.system_text = prompt["system_text"]

    def build_payload(self, question: str) -> dict[str, Any]:
        return {
            "model": self.config.model_tag,
            "messages": [
                {"role": "system", "content": self.system_text},
                {"role": "user", "content": json.dumps({"message": question}, ensure_ascii=False)},
            ],
            "stream": False,
            "format": _SCHEMA,
            "think": False,
            "keep_alive": self.config.keep_alive,
            "options": {
                "temperature": 0,
                "seed": self.config.seed,
                "num_predict": 32,
            },
        }

    def classify(self, question: str) -> CategoryRouterLabel | None:
        try:
            response = self.transport.post_json(
                self.config.endpoint, self.build_payload(question), self.timeout_seconds
            )
        except (SLMClientError, OSError, ValueError, TypeError):
            return None
        message = response.get("message") if isinstance(response, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            return None
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict) or set(parsed) != {"category"}:
            return None
        try:
            return CategoryRouterLabel(parsed["category"])
        except (ValueError, TypeError):
            return None
