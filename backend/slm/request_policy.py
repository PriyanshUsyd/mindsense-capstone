"""Deterministic request routing before any local-model generation.

The local SLM service must refuse high-severity requests even when the UI is
not available.  This module deliberately uses a small, reviewable rule
set: crisis language is routed to the versioned crisis template, prohibited
and off-topic requests are routed to the generic refusal template, and only
recognised MindSense evidence questions continue to the local model.

This is a development guardrail, not a clinical risk assessment.  The rule
set and participant-facing wording still require Evaluation/client review
before any human pilot.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict

REQUEST_POLICY_VERSION = "0.2.0"


class RequestDisposition(str, Enum):
    ALLOW = "allow"
    REFUSE = "refuse"
    CRISIS = "crisis"


class RequestCategory(str, Enum):
    IN_SCOPE = "in_scope"
    OFF_TOPIC = "off_topic"
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
            re.compile(
                r"\b(?:can|could) you (?:tell|determine|assess) (?:if|whether) "
                r"i(?: am|'m) (?:becoming |getting )?(?:depressed|anxious|mentally ill)\b",
                re.IGNORECASE,
            ),
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

# The two-part rule is intentionally conservative: ordinary questions need a
# MindSense feature plus evidence-analysis intent. Short contextual questions
# that are meaningful in an evidence view are listed separately. Unmatched or
# ambiguous requests fail closed without invoking the model.
_DOMAIN_PATTERNS = (
    re.compile(
        r"\b(?:gps|movement|mobility|unlock(?:s|ed|ing)?|phq[- ]?4|"
        r"well[- ]?being|behavio(?:u)?r)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bphone (?:use|usage|activity|unlock(?:s|ed|ing)?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:tracked|location) (?:data|pattern|history)\b|\bscreen time\b",
        re.IGNORECASE,
    ),
)
_EVIDENCE_INTENT_PATTERNS = (
    re.compile(
        r"\b(?:baseline|pattern|history|evidence|data|score|trend|uncertainty|"
        r"relationship|association|correlation|chang(?:e|ed|ing)|different|"
        r"compare|comparison|higher|lower|usual|normal|unusual|frequent|"
        r"conclude|enough|observed|window)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bhow (?:was|is|has) my\b", re.IGNORECASE),
)
_CONTEXTUAL_IN_SCOPE_PATTERNS = (
    re.compile(r"\bwhat changed\b", re.IGNORECASE),
    re.compile(r"\bhow am i doing\b", re.IGNORECASE),
    re.compile(
        r"\b(?:describe|explain|compare) my (?:recent |tracked )?activity\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bis this (?:higher|lower|different) (?:or (?:higher|lower) )?"
        r"than (?:normal|usual) for me\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bwhat uncertainty should i keep in mind\b", re.IGNORECASE),
    re.compile(r"\bis there enough (?:data|history)\b", re.IGNORECASE),
    re.compile(
        r"\bwhat does the word (?:depressed|anxious|depression|anxiety) mean\b",
        re.IGNORECASE,
    ),
)


def _is_in_scope(question: str) -> bool:
    if any(pattern.search(question) for pattern in _CONTEXTUAL_IN_SCOPE_PATTERNS):
        return True
    return any(pattern.search(question) for pattern in _DOMAIN_PATTERNS) and any(
        pattern.search(question) for pattern in _EVIDENCE_INTENT_PATTERNS
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

    if not clean_question or not _is_in_scope(clean_question):
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.OFF_TOPIC,
            reason_code="off_topic_request_detected",
        )

    return RequestPolicyDecision(
        disposition=RequestDisposition.ALLOW,
        category=RequestCategory.IN_SCOPE,
    )
