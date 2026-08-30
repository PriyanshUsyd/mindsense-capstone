"""
Deterministic safety gate — per build-reference.md Section 6 and
skills/slm-ollama.md: "Every draft response is validated a second time
before becoming a response... rejected/rewritten to the safe fallback
unless every evidence ID in the draft exists in the input packet, every
claim ID is approved by its referenced evidence item, no prohibited claim
or phrase is present, and every 'ready' explanation includes an
uncertainty statement."

STATUS: built 2026-08-29 as part of the Week 4 cross-cutting technical
alignment pass — this is genuinely new production code (not a doc), needed
to make an actual end-to-end smoke test possible (FeatureWindow ->
eligibility -> EvidencePacket -> AssistantDraft -> validated response).
Richard Zhao (SLM Integration Lead) should review and own this — it
implements his spec, but was written to unblock integration testing, not
by him.

Known modeling simplification, flagged rather than silently assumed: the
evidence contract (backend/contracts/evidence.py) doesn't currently expose
a list of distinct per-item "evidence ids" — there's one EvidencePacket per
packet_id, not multiple sub-evidence items each with their own id. This
gate treats {packet_id, feature_id} as the full set of valid evidence ids a
draft may reference. If the contract later grows genuinely distinct
evidence items (e.g. multiple features per packet), this function's
`valid_evidence_ids` set needs to grow with it.
"""

from __future__ import annotations

import re

from backend.contracts.evidence import (
    AssistantDraft,
    EligibilityStatus,
    EvidencePacket,
    ResponseMode,
)


class SafetyGateRejection(str):
    """Reason codes returned on rejection — plain str subclass so they're
    trivially JSON/log-serialisable without a separate enum import."""


PACKET_ID_MISMATCH = SafetyGateRejection("packet_id_mismatch")
UNKNOWN_EVIDENCE_ID = SafetyGateRejection("unknown_evidence_id_referenced")
CLAIM_NOT_APPROVED = SafetyGateRejection("claim_not_approved")
RESPONSE_MODE_NOT_PERMITTED = SafetyGateRejection("response_mode_not_permitted")
MISSING_UNCERTAINTY_STATEMENT = SafetyGateRejection("missing_uncertainty_statement")
EMPTY_RESPONSE_TEXT = SafetyGateRejection("empty_response_text")
RESPONSE_TEXT_TOO_SHORT = SafetyGateRejection("response_text_too_short")
PROHIBITED_PHRASE_DETECTED = SafetyGateRejection("prohibited_phrase_detected")
ELIGIBILITY_TEXT_CONTRADICTION = SafetyGateRejection("eligibility_text_contradiction")
REFUSAL_REFERENCES_EVIDENCE = SafetyGateRejection("refusal_references_evidence")
INSUFFICIENT_HISTORY_DISCLOSURE_MISSING = SafetyGateRejection(
    "insufficient_history_disclosure_missing"
)

# response modes that constitute a "ready" (non-fallback) explanation, per
# skills/slm-ollama.md's requirement that these must carry an uncertainty
# statement. Fallback/refusal modes are exempt — they don't explain
# anything for uncertainty to attach to.
_MODES_REQUIRING_UNCERTAINTY_STATEMENT = {ResponseMode.NORMAL, ResponseMode.UNCERTAINTY}
_MODEL_EXPLANATION_MODES = {
    ResponseMode.NORMAL,
    ResponseMode.UNCERTAINTY,
    ResponseMode.INSUFFICIENT_DATA,
}

# These deliberately target direct assertions, not isolated mental-health
# words. Refusal/fallback text is deterministic or boundary-setting and is
# excluded from this phrase-class scan.
_PROHIBITED_ASSERTION_PATTERNS = (
    re.compile(
        r"\b(?:caused?|causes?|causing|impacted?|impacting|leads? to|"
        r"result(?:s|ed)? in)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byou (?:have|are|suffer from) (?:depression|anxiety|a mental "
        r"illness|a mental health condition)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byou should (?:start|stop|take|change) (?:medication|medicine|"
        r"treatment|therapy)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\byour (?:mental health )?risk (?:is|will be)\b", re.IGNORECASE),
)

_INSUFFICIENT_HISTORY_PATTERN = re.compile(
    r"\bno data\b|\b(?:not enough|insufficient) (?:data|history)|"
    r"\btoo early to (?:compare|tell|determine)\b",
    re.IGNORECASE,
)


def validate_draft(
    packet: EvidencePacket, draft: AssistantDraft
) -> tuple[bool, SafetyGateRejection | None]:
    """Returns (is_valid, rejection_reason). rejection_reason is None iff
    is_valid is True. On any rejection, the caller MUST fall back to the
    safe fallback template (backend/slm/prompts/generic_fallback.yaml) —
    never let an unvalidated draft through (skills/slm-ollama.md)."""

    if draft.packet_id != packet.identity.packet_id:
        return False, PACKET_ID_MISMATCH

    valid_evidence_ids = {packet.identity.packet_id, packet.feature_window.feature_id}
    if not set(draft.evidence_ids_referenced) <= valid_evidence_ids:
        return False, UNKNOWN_EVIDENCE_ID

    if draft.response_mode == ResponseMode.REFUSAL and draft.evidence_ids_referenced:
        return False, REFUSAL_REFERENCES_EVIDENCE

    if not set(draft.claim_ids_used) <= set(packet.claim_policy.approved_claim_ids):
        return False, CLAIM_NOT_APPROVED

    if draft.response_mode not in packet.claim_policy.permitted_response_modes:
        return False, RESPONSE_MODE_NOT_PERMITTED

    if not draft.text.strip():
        return False, EMPTY_RESPONSE_TEXT

    if len(draft.text.strip()) < 20:
        return False, RESPONSE_TEXT_TOO_SHORT

    if (
        packet.baseline.eligibility_status == EligibilityStatus.ELIGIBLE
        and _INSUFFICIENT_HISTORY_PATTERN.search(draft.text)
    ):
        return False, ELIGIBILITY_TEXT_CONTRADICTION

    if (
        draft.response_mode == ResponseMode.INSUFFICIENT_DATA
        and not _INSUFFICIENT_HISTORY_PATTERN.search(draft.text)
    ):
        return False, INSUFFICIENT_HISTORY_DISCLOSURE_MISSING

    if draft.response_mode in _MODEL_EXPLANATION_MODES and any(
        pattern.search(draft.text) for pattern in _PROHIBITED_ASSERTION_PATTERNS
    ):
        return False, PROHIBITED_PHRASE_DETECTED

    if (
        draft.response_mode in _MODES_REQUIRING_UNCERTAINTY_STATEMENT
        and not draft.includes_uncertainty_statement
    ):
        return False, MISSING_UNCERTAINTY_STATEMENT

    return True, None
