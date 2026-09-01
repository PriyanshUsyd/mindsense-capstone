"""Deterministic request routing before any local-model generation.

The Week 5 shadow build must refuse high-severity requests even when the UI
is not available.  This module deliberately uses a small, reviewable rule
set: crisis language is routed to the versioned crisis template and other
prohibited requests are routed to the generic refusal template.  Allowed
questions continue to the schema-constrained local model.

This is a development guardrail, not a clinical risk assessment.  The rule
set and participant-facing wording still require Evaluation/client review
before any human pilot.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict

REQUEST_POLICY_VERSION = "0.1.0"


class RequestDisposition(str, Enum):
    ALLOW = "allow"
    REFUSE = "refuse"
    CRISIS = "crisis"


class RequestCategory(str, Enum):
    IN_SCOPE = "in_scope"
    CRISIS_SELF_HARM = "crisis_self_harm"
    DIAGNOSIS_SEEKING = "diagnosis_seeking"
    CAUSAL_INFERENCE_SEEKING = "causal_inference_seeking"
    TREATMENT_ADVICE_SEEKING = "treatment_advice_seeking"
    RISK_PREDICTION_SEEKING = "risk_prediction_seeking"
    PROMPT_INJECTION = "prompt_injection"
    SENSITIVE_DATA_REQUEST = "sensitive_data_request"


class RequestPolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = REQUEST_POLICY_VERSION
    disposition: RequestDisposition
    category: RequestCategory
    reason_code: str | None = None


_CRISIS_PATTERNS = (
    re.compile(r"\b(?:kill|hurt|harm) myself\b", re.IGNORECASE),
    re.compile(r"\b(?:suicide|suicidal|self[- ]harm)\b", re.IGNORECASE),
    re.compile(r"\b(?:end|take) my (?:own )?life\b", re.IGNORECASE),
    re.compile(r"\b(?:do not|don't|dont) want to (?:live|be alive)\b", re.IGNORECASE),
)

_PROHIBITED_PATTERNS: tuple[
    tuple[RequestCategory, str, tuple[re.Pattern[str], ...]], ...
] = (
    (
        RequestCategory.PROMPT_INJECTION,
        "prompt_injection_detected",
        (
            re.compile(
                r"\bignore (?:all |the )?(?:previous|prior) instructions\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:reveal|show|print) (?:the )?(?:system|developer) prompt\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:bypass|disable|override) (?:the )?(?:safety|guardrail|policy)\b",
                re.IGNORECASE,
            ),
        ),
    ),
    (
        RequestCategory.DIAGNOSIS_SEEKING,
        "diagnosis_request_detected",
        (
            re.compile(r"\b(?:diagnose|diagnosis)\b", re.IGNORECASE),
            re.compile(
                r"\b(?:do|could) i have (?:depression|anxiety|a mental (?:illness|health condition))\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bam i (?:depressed|anxious|mentally ill)\b", re.IGNORECASE),
            re.compile(r"\bdoes (?:this|that).{0,80}\bmean i have\b", re.IGNORECASE),
        ),
    ),
    (
        RequestCategory.TREATMENT_ADVICE_SEEKING,
        "treatment_advice_request_detected",
        (
            re.compile(
                r"\bwhat (?:medication|medicine|treatment|therapy) should i\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bshould i (?:start|stop|take|change) (?:medication|medicine|treatment|therapy)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(?:prescribe|prescription)\b", re.IGNORECASE),
        ),
    ),
    (
        RequestCategory.RISK_PREDICTION_SEEKING,
        "risk_prediction_request_detected",
        (
            re.compile(
                r"\b(?:predict|calculate|estimate) my (?:mental health )?risk\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bwhat (?:is|are) my (?:odds|risk|chances) of\b", re.IGNORECASE
            ),
            re.compile(
                r"\bwill i (?:become|get|develop) "
                r"(?:depressed|depression|anxious|anxiety|a mental illness)\b",
                re.IGNORECASE,
            ),
        ),
    ),
    (
        RequestCategory.CAUSAL_INFERENCE_SEEKING,
        "causal_inference_request_detected",
        (
            re.compile(
                r"\b(?:did|does|can|could|will).{0,80}\b(?:cause|caused|make|made|lead to|result in)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bwhy did.{0,80}\b(?:cause|make)\b", re.IGNORECASE),
            re.compile(r"\bis .{0,80}\bthe (?:reason|cause)\b", re.IGNORECASE),
        ),
    ),
    (
        RequestCategory.SENSITIVE_DATA_REQUEST,
        "sensitive_data_request_detected",
        (
            re.compile(
                r"\b(?:show|reveal|export|give me) (?:the )?(?:raw )?(?:gps|location) (?:data|coordinates|history)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:show|reveal|export|give me) (?:the )?(?:participant|subject|user) (?:id|identifier)\b",
                re.IGNORECASE,
            ),
        ),
    ),
)


def classify_request(question: str) -> RequestPolicyDecision:
    """Classify one untrusted question without inspecting participant data."""

    clean_question = question.strip()
    if any(pattern.search(clean_question) for pattern in _CRISIS_PATTERNS):
        return RequestPolicyDecision(
            disposition=RequestDisposition.CRISIS,
            category=RequestCategory.CRISIS_SELF_HARM,
            reason_code="crisis_language_detected",
        )

    for category, reason_code, patterns in _PROHIBITED_PATTERNS:
        if any(pattern.search(clean_question) for pattern in patterns):
            return RequestPolicyDecision(
                disposition=RequestDisposition.REFUSE,
                category=category,
                reason_code=reason_code,
            )

    return RequestPolicyDecision(
        disposition=RequestDisposition.ALLOW,
        category=RequestCategory.IN_SCOPE,
    )
