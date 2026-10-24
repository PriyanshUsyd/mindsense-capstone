"""Single-label, fail-closed request routing for policy 0.5.0.

This router may refine a deterministic off-topic or feature-unclear decision.
It cannot select an answer feature without a separate deterministic feature
match in :mod:`backend.slm.request_policy`.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.slm.client import (
    JSONTransport,
    OllamaClientConfig,
    UrllibLoopbackTransport,
)
from backend.slm.request_classifier import ClassifierLabel as RouterLabel

DEFAULT_CATEGORY_ROUTER_TIMEOUT_SECONDS = 30.0
DEFAULT_CATEGORY_ROUTER_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "request_router_0_5_0.yaml"
)


class CategoryRouterPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    system_text: str = Field(min_length=1)


@dataclass(frozen=True)
class LoadedCategoryRouterPrompt:
    manifest: CategoryRouterPrompt
    sha256: str
    source_path: Path


def load_category_router_prompt(
    path: str | Path = DEFAULT_CATEGORY_ROUTER_PROMPT,
) -> LoadedCategoryRouterPrompt:
    source_path = Path(path).resolve()
    try:
        raw = source_path.read_bytes()
        parsed = yaml.safe_load(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("category-router prompt must contain a mapping")
        manifest = CategoryRouterPrompt.model_validate(parsed)
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValidationError) as exc:
        raise ValueError("failed to load category-router prompt manifest") from exc
    return LoadedCategoryRouterPrompt(
        manifest=manifest,
        sha256=hashlib.sha256(raw).hexdigest(),
        source_path=source_path,
    )


def _response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"category": {"type": "string", "enum": [x.value for x in RouterLabel]}},
        "required": ["category"],
        "additionalProperties": False,
    }


class OllamaCategoryRouter:
    """Ask the pinned local model for one strict route label, at most once."""

    def __init__(
        self,
        config: OllamaClientConfig,
        *,
        transport: JSONTransport | None = None,
        timeout_seconds: float = DEFAULT_CATEGORY_ROUTER_TIMEOUT_SECONDS,
        prompt: LoadedCategoryRouterPrompt | None = None,
    ) -> None:
        self.config = config
        self.transport = transport or UrllibLoopbackTransport()
        self.timeout_seconds = min(timeout_seconds, config.timeout_seconds)
        self.prompt = prompt or load_category_router_prompt()
        self._cache: OrderedDict[str, RouterLabel | None] = OrderedDict()
        self._lock = threading.Lock()

    def build_payload(self, question: str) -> dict[str, Any]:
        return {
            "model": self.config.model_tag,
            "messages": [
                {"role": "system", "content": self.prompt.manifest.system_text},
                {
                    "role": "user",
                    "content": json.dumps({"message": question}, ensure_ascii=False),
                },
            ],
            "stream": False,
            "format": _response_schema(),
            "think": False,
            "keep_alive": self.config.keep_alive,
            "options": {
                "temperature": 0,
                "seed": self.config.seed,
                "num_predict": 32,
            },
        }

    def route(self, question: str) -> RouterLabel | None:
        """Return a valid label, or ``None`` to preserve deterministic routing."""

        key = hashlib.sha256(question.encode("utf-8")).hexdigest()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            result = self._route_once(question)
            self._cache[key] = result
            while len(self._cache) > 256:
                self._cache.popitem(last=False)
            return result

    def _route_once(self, question: str) -> RouterLabel | None:
        try:
            response = self.transport.post_json(
                self.config.endpoint, self.build_payload(question), self.timeout_seconds
            )
        except Exception:
            # A router failure must preserve the existing deterministic route.
            return None
        message = response.get("message") if isinstance(response, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            return None
        try:
            parsed = json.loads(content, object_pairs_hook=_unique_object)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
        if not isinstance(parsed, dict) or set(parsed) != {"category"}:
            return None
        try:
            return RouterLabel(parsed["category"])
        except (ValueError, TypeError):
            return None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result
