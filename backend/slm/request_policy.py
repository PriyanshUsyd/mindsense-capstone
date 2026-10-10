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

import logging
import re
from enum import Enum

from pydantic import BaseModel, ConfigDict

REQUEST_POLICY_VERSION = "0.3.3"

_logger = logging.getLogger(__name__)


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
    CAPABILITY_QUESTION = "capability_question"
    CLINICAL_SCORE_REQUEST = "clinical_score_request"
    APP_INFORMATION = "app_information"


class RequestPolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = REQUEST_POLICY_VERSION
    disposition: RequestDisposition
    category: RequestCategory
    reason_code: str | None = None


_CRISIS_PATTERNS = (
    re.compile(r"\b(?:kill|hurt|harm)(?:ing)? myself\b", re.IGNORECASE),
    re.compile(r"\b(?:suicide|suicidal|self[- ]harm)\b", re.IGNORECASE),
    re.compile(r"\b(?:end|take) my (?:own )?life\b", re.IGNORECASE),
    re.compile(r"\b(?:do not|don't|dont) want to (?:live|be alive)\b", re.IGNORECASE),
    # Policy 0.3.3 (50-question dev test Q45): hopelessness, "no point",
    # giving up, not wanting to be here and "can't go on". Broad on purpose:
    # a false positive shows the crisis message, which is the safety default.
    re.compile(r"\bhopeless(?:ness|ly)?\b|\bworthless\b", re.IGNORECASE),
    re.compile(
        r"\b(?:do not|don['’]?t|dont|can['’]?t|cannot|no longer) see (?:the |any )?point\b"
        r"|\bno (?:point|reason) (?:in |to )?(?:living|life|going on|carrying on|"
        r"trying|anything|being here|any ?more)\b"
        r"|\bwhat['’]?s the point (?:of|in) (?:living|life|going on|anything|trying|"
        r"it all|being here)\b"
        r"|\bpoint (?:in )?(?:living|going on) any ?more\b"
        r"|\b(?:no reason to live|nothing to live for)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bgiv(?:e|ing) up on (?:life|living|everything|myself)\b"
        r"|\b(?:i['’]?m|i am|i['’]?ve|i have) (?:just |completely )?(?:given|giving) up\b"
        r"|\bwant to give up\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:do not|don['’]?t|dont|no longer) want to be (?:here|around|alive)\b"
        r"|\bwish i (?:was|were)(?:n['’]?t| not) (?:here|alive|around|born)\b"
        r"|\bwish i (?:was|were) dead\b|\bwant to die\b|\bbetter off (?:dead|without me)\b"
        r"|\b(?:end|ending) it all\b|\bdisappear forever\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:can['’]?t|cannot|can not) (?:go on|keep going|carry on|cope any ?more|"
        r"take (?:it|this) any ?more|take much more)\b",
        re.IGNORECASE,
    ),
)

_PROHIBITED_PATTERNS: tuple[
    tuple[RequestCategory, str, tuple[re.Pattern[str], ...]], ...
] = (
    (
        RequestCategory.PROMPT_INJECTION,
        "prompt_injection_detected",
        (
            re.compile(
                r"\bignore (?:all |the |your |any )?(?:previous|prior) instructions\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:reveal|show|print) (?:me )?(?:the |your )?(?:system|developer) prompt\b",
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
                r"\bdo you think i(?: am|['’]m) (?:depressed|anxious|mentally ill)\b",
                re.IGNORECASE,
            ),
            # Policy 0.3.2 (ME-P01 F4 near-variant).
            re.compile(
                r"\bdo you think i (?:have|might have) (?:depression|anxiety|"
                r"a mental (?:illness|health condition))\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:can|could) you (?:tell|determine|assess) (?:if|whether) "
                r"i(?: am|'m) (?:becoming |getting )?(?:depressed|anxious|mentally ill)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bdoes (?:this|that).{0,80}\bmean i have\b", re.IGNORECASE),
            # Policy 0.3.3 (dev Q38): asking the data to confirm a named
            # condition, e.g. "My doctor says I'm depressed. Does my data
            # confirm it?"
            re.compile(
                r"^(?=.*\b(?:depress\w*|anxi\w*|bipolar|adhd|ptsd|ocd|"
                r"mental (?:illness|health condition|disorder))\b)"
                r".*\b(?:confirm|prove|back (?:it|that|this) up|agree|consistent with)",
                re.IGNORECASE,
            ),
        ),
    ),
    (
        # Policy 0.3.3 (dev Q35/Q39): MindSense gives no clinical or
        # mental-health score. Checked before scope so the PHQ-4 domain word
        # no longer routes to the feature clarification.
        RequestCategory.CLINICAL_SCORE_REQUEST,
        "clinical_score_request_detected",
        (
            re.compile(r"\b(?:phq|gad)[- ]?\d+\b", re.IGNORECASE),
            re.compile(
                r"\b(?:mental[- ]health|depression|anxiety|mood|stress|well[- ]?being) "
                r"(?:score|rating)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:score|rate) my (?:mental health|mood|depression|anxiety)\b",
                re.IGNORECASE,
            ),
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
            # Policy 0.3.3 (dev Q31/Q40): whether to see a professional, or
            # how to improve mood, is advice MindSense cannot give.
            re.compile(
                r"\bshould i (?:see|talk to|speak to|visit|go to|get) (?:a |an |my )?"
                r"(?:therapist|psychologist|psychiatrist|counsell?or|doctor|gp|"
                r"professional|mental[- ]health professional)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\bhow (?:can|do|could|should) i (?:improve|boost|fix|lift|raise|help) "
                r"my (?:mood|mental health|well[- ]?being|anxiety|depression|stress)\b",
                re.IGNORECASE,
            ),
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
            # Policy 0.3.3 (dev Q29/Q47): "because"/"due to" questions and
            # requests for proof; needed once a feature word alone is in scope.
            # Any "because"/"due to" refuses (fail closed): MindSense never
            # confirms or rejects a stated cause.
            re.compile(r"\b(?:because|due to)\b", re.IGNORECASE),
            re.compile(r"\bprov(?:e|es|ed|ing)\b|\bproof\b", re.IGNORECASE),
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
            # Policy 0.3.3 (dev Q50): only the person's own data is described.
            re.compile(
                r"\b(?:another|other|different) (?:participant|person|user|student)s?\b"
                r"|\bother people\b|\b(?:someone|somebody|everyone|anyone) else\b",
                re.IGNORECASE,
            ),
        ),
    ),
)

# Policy 0.3.2 (ME-P01 F1): a whole-question "what can you do?" request gets
# the deterministic capability template instead of the off-topic refusal. It
# keeps the REFUSE disposition so no participant data is loaded and no model
# or context is invoked. Anchored to the full question so evidence questions
# such as "what can you tell me about my unlocks?" are not captured.
_CAPABILITY_PATTERNS = (
    re.compile(
        r"^\s*(?:(?:hi|hello|hey)[\s,!.]+)?"
        r"(?:what (?:can|could) you (?:help (?:me )?with|do(?: for me)?)|"
        r"what do you do|how (?:can|could) you help(?: me)?|"
        r"what are you (?:able to do|for)|what can i ask(?: you)?)"
        r"\s*[?.!]*\s*$",
        re.IGNORECASE,
    ),
)

# Policy 0.3.3 (dev Q9/Q10/Q19/Q20): questions about the app itself get a
# fixed informational text. Like the capability route they keep the REFUSE
# disposition, so no participant data is loaded and no model is called. The
# reason code selects the template in SLMService.
_APP_INFORMATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "app_info_data_storage",
        re.compile(
            r"\b(?:is|are) my (?:data|information|questions?|chats?|answers?) "
            r"(?:stored|saved|kept|shared|sent|uploaded)\b"
            r"|\bwhere (?:is|are) my (?:data|information) (?:stored|kept|saved|sent)\b"
            r"|\b(?:do|does) (?:you|mindsense|the app|this app) (?:store|save|keep|share|"
            r"send|upload) my (?:data|information|questions?|chats?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "app_info_data_use",
        re.compile(
            r"\bwhat (?:data|information|sensors?) (?:do|does) (?:you|mindsense|the app|"
            r"this app) (?:use|collect|look at|need)\b"
            r"|\bwhat data is used\b",
            re.IGNORECASE,
        ),
    ),
    (
        "app_info_uncertain_evidence",
        re.compile(
            r"\bwhat (?:does|do|is) [\"“'‘]?uncertain(?:ty)?(?: evidence)?[\"”'’]?"
            r"(?: mean)?\s*[?.!]*\s*$",
            re.IGNORECASE,
        ),
    ),
    (
        "app_info_baseline_unavailable",
        re.compile(
            r"\bwhy (?:can['’]?t|cannot|can not|couldn['’]?t|won['’]?t|don['’]?t|"
            r"didn['’]?t) you compare\b"
            r"|\bwhy (?:is|isn['’]?t) (?:there (?:no|not a) )?(?:my )?baseline\b",
            re.IGNORECASE,
        ),
    ),
)


def app_information_reason(question: str) -> str | None:
    """Reason code of the matching app-information question, if any."""

    for reason_code, pattern in _APP_INFORMATION_PATTERNS:
        if pattern.search(question):
            return reason_code
    return None


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
    # Policy 0.3.3 (dev Q17): names no single feature, so preflight asks
    # which feature to use instead of refusing it as off-topic.
    re.compile(r"\bhow active (?:have|had|was|am) i\b", re.IGNORECASE),
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


# Which statistics-side feature (backend.statistics.participant_evidence's
# `_FEATURES` dict keys) a question is actually about. Kept separate from
# the in/out-of-scope patterns above: those decide WHETHER to answer, this
# decides WHICH feature's evidence packet to answer from. Before this
# existed, `/respond` always answered from `gps_distance` regardless of
# what was asked (see backend/api/app.py's `RespondRequest.feature_id`
# default) — an unlock-related question silently got a GPS answer.
DEFAULT_FEATURE_ID = "gps_distance"

_UNLOCK_FEATURE_PATTERNS = (
    re.compile(r"\bunlock(?:s|ed|ing)?\b", re.IGNORECASE),
    re.compile(r"\bphone (?:use|usage|activity)\b", re.IGNORECASE),
    re.compile(r"\bscreen time\b", re.IGNORECASE),
    re.compile(r"\bpick(?:s|ed|ing)?[- ]?up(?:s)?\b", re.IGNORECASE),
    # Policy 0.3.3 (dev Q16): everyday wording for phone use.
    re.compile(r"\b(?:on|use|used|using) my phone\b", re.IGNORECASE),
)

_GPS_NAMED_FEATURE_PATTERNS = (
    re.compile(r"\btravel(?:l?ed|ling|s)?\b", re.IGNORECASE),
    re.compile(r"\bdistance\b", re.IGNORECASE),
    re.compile(r"\bmovement\b", re.IGNORECASE),
    re.compile(r"\bmobility\b", re.IGNORECASE),
    # Policy 0.3.3 (dev Q1/Q15): everyday wording for distance moved.
    re.compile(r"\bmov(?:e|ed|es|ing)\b|\bhow far\b", re.IGNORECASE),
)
_GPS_FEATURE_PATTERNS = _GPS_NAMED_FEATURE_PATTERNS + (
    re.compile(r"\bgps\b", re.IGNORECASE),
    re.compile(r"\blocation\b", re.IGNORECASE),
)

# Policy 0.3.3 (dev Q3/Q4/Q26): naming a feature is enough to be in scope
# (answered from the observed window); no change or time word is needed.
# Bare "gps" and "location" are excluded so place-seeking or off-topic
# questions ("weather at my GPS location") still need evidence intent.
_FEATURE_MENTION_PATTERNS = _UNLOCK_FEATURE_PATTERNS + _GPS_NAMED_FEATURE_PATTERNS


def infer_feature_from_question(question: str) -> str | None:
    """Deterministic keyword match from question text to a `feature_id`.

    Matches only one of the two Tier-1 features
    (`backend.statistics.participant_evidence._FEATURES`: `gps_distance`,
    `unlock_count`) — never inspects participant data, mirrors
    `classify_request`'s text-only contract. A question that matches
    neither feature's keywords, or matches both (genuinely ambiguous), is
    not guessed: return None so the SLM preflight can request a supported
    feature before loading participant data. DEFAULT_FEATURE_ID is retained
    only for older callers that explicitly choose their own default.
    """

    clean_question = question.strip()
    matches_unlock = any(
        pattern.search(clean_question) for pattern in _UNLOCK_FEATURE_PATTERNS
    )
    matches_gps = any(
        pattern.search(clean_question) for pattern in _GPS_FEATURE_PATTERNS
    )

    if matches_unlock and not matches_gps:
        return "unlock_count"
    if matches_gps and not matches_unlock:
        return "gps_distance"

    _logger.warning(
        "feature_inference_ambiguous: question matched %s feature keywords; "
        "no feature selected",
        "both" if (matches_unlock and matches_gps) else "no",
    )
    return None


# There is no user-selected calendar-window contract yet. Even a requested
# fourteen-day period cannot be assumed to match a historical packet's dates.
# Keep unspecified "recent" / "observed window" questions available, but stop
# explicit time requests rather than silently substituting that packet.
_MONTH_NAME = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
_EXPLICIT_WINDOW_PATTERNS = (
    re.compile(
        r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
        r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
        r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
        r"a|an|a couple of|couple of|few|several)[ -]+"
        r"(?:hours?|days?|weeks?|months?|years?|fortnights?|quarters?|terms?|semesters?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:last|past|previous|next|this)\s+(?:[\w-]+\s+){0,5}"
        r"(?:hours?|days?|weeks?|months?|years?|fortnights?|quarters?|terms?|semesters?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:today|yesterday|tomorrow|tonight|weekends?)\b", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"),
    re.compile(
        r"\b(?:since|from|between|until|through|on|in) (?:the )?(?:\d{1,4}(?:st|nd|rd|th)?|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:since|from|between|until|through|on|in|during|last|this|next|previous)"
        rf"\s+(?:the\s+)?{_MONTH_NAME}\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\b{_MONTH_NAME}\.?\s+\d{{4}}\b", re.IGNORECASE),
    re.compile(
        r"\b(?:since|from|between|until|through|in|during|last|this|next|previous)"
        r"\s+(?:the\s+)?(?:spring|summer|autumn|fall|winter)\b",
        re.IGNORECASE,
    ),
)


# Policy 0.3.2 (ME-P01 F2, lead decision 2026-10-10): the comparison window
# is the trailing 14 days ([-14, -1], CLAUDE.md), so phrases naming that same
# span refer to the observed window rather than a different calendar range.
# They are removed before the explicit-window check; any other time phrase in
# the question (e.g. "past 3 days", "last month", "yesterday") still refuses.
_OBSERVED_WINDOW_PHRASES = re.compile(
    r"\b(?:the\s+)?(?:past|last|previous)\s+(?:couple(?:\s+of)?|two|2)\s+weeks?\b"
    r"|\b(?:the\s+)?(?:past|last|previous)\s+(?:fortnight|fourteen\s+days|14\s+days)\b",
    re.IGNORECASE,
)

# Policy 0.3.2 (ME-P01 F3): a general question about the evidence's limits
# needs no feature. Without a feature it gets the deterministic uncertainty
# template; with a feature word it still goes to that feature's evidence.
_GENERAL_UNCERTAINTY_PATTERNS = (
    re.compile(r"\bwhat uncertainty should i keep in mind\b", re.IGNORECASE),
    re.compile(
        r"\bwhat (?:are|is) the (?:main )?(?:limitations?|uncertaint(?:y|ies))\b",
        re.IGNORECASE,
    ),
    # Policy 0.3.3 (dev Q14).
    re.compile(
        r"\bhow (?:reliable|accurate|trustworthy|certain) (?:is|are) "
        r"(?:this|that|these|the|your) (?:information|info|answers?|results?|evidence)\b",
        re.IGNORECASE,
    ),
)


def is_general_uncertainty_question(question: str) -> bool:
    """True for a feature-free question about the evidence's limitations."""

    return any(p.search(question) for p in _GENERAL_UNCERTAINTY_PATTERNS) and not (
        any(p.search(question) for p in _UNLOCK_FEATURE_PATTERNS)
        or any(p.search(question) for p in _GPS_FEATURE_PATTERNS)
    )


def request_scope_rejection(
    question: str, *, feature_id: str | None = None, require_feature: bool = False
) -> str | None:
    """Check answer scope after crisis/prohibited routing, without data access.

    A supplied packet or explicit feature can scope a contextual question.
    It cannot override conflicting feature words or an explicit time request.
    Unknown feature IDs remain the API/Statistics owner's validation concern.
    """

    window_text = _OBSERVED_WINDOW_PHRASES.sub(" ", question)
    if any(pattern.search(window_text) for pattern in _EXPLICIT_WINDOW_PATTERNS):
        return "unsupported_time_window"
    matches_unlock = any(
        pattern.search(question) for pattern in _UNLOCK_FEATURE_PATTERNS
    )
    matches_gps = any(pattern.search(question) for pattern in _GPS_FEATURE_PATTERNS)
    if matches_unlock and matches_gps:
        return "ambiguous_feature_request"
    inferred = (
        "unlock_count" if matches_unlock else "gps_distance" if matches_gps else None
    )
    if feature_id in {"gps_distance", "unlock_count"} and inferred not in {
        None,
        feature_id,
    }:
        return "feature_request_mismatch"
    if require_feature and not feature_id and inferred is None:
        return "ambiguous_feature_request"
    return None


def _is_in_scope(question: str) -> bool:
    if any(pattern.search(question) for pattern in _CONTEXTUAL_IN_SCOPE_PATTERNS):
        return True
    if any(pattern.search(question) for pattern in _GENERAL_UNCERTAINTY_PATTERNS):
        return True
    if any(pattern.search(question) for pattern in _FEATURE_MENTION_PATTERNS):
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

    if any(pattern.search(clean_question) for pattern in _CAPABILITY_PATTERNS):
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.CAPABILITY_QUESTION,
            reason_code="capability_question_detected",
        )

    app_information = app_information_reason(clean_question)
    if app_information:
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.APP_INFORMATION,
            reason_code=app_information,
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
