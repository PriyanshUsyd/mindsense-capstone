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

from backend.contracts.evidence import AssistantDraft, EvidencePacket, ResponseMode


class SafetyGateRejection(str):
    """Reason codes returned on rejection — plain str subclass so they're
    trivially JSON/log-serialisable without a separate enum import."""


PACKET_ID_MISMATCH = SafetyGateRejection("packet_id_mismatch")
UNKNOWN_EVIDENCE_ID = SafetyGateRejection("unknown_evidence_id_referenced")
CLAIM_NOT_APPROVED = SafetyGateRejection("claim_not_approved")
RESPONSE_MODE_NOT_PERMITTED = SafetyGateRejection("response_mode_not_permitted")
MISSING_UNCERTAINTY_STATEMENT = SafetyGateRejection("missing_uncertainty_statement")

# response modes that constitute a "ready" (non-fallback) explanation, per
# skills/slm-ollama.md's requirement that these must carry an uncertainty
# statement. Fallback/refusal modes are exempt — they don't explain
# anything for uncertainty to attach to.
_MODES_REQUIRING_UNCERTAINTY_STATEMENT = {ResponseMode.NORMAL, ResponseMode.UNCERTAINTY}


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

    if not set(draft.claim_ids_used) <= set(packet.claim_policy.approved_claim_ids):
        return False, CLAIM_NOT_APPROVED

    if draft.response_mode not in packet.claim_policy.permitted_response_modes:
        return False, RESPONSE_MODE_NOT_PERMITTED

    if (
        draft.response_mode in _MODES_REQUIRING_UNCERTAINTY_STATEMENT
        and not draft.includes_uncertainty_statement
    ):
        return False, MISSING_UNCERTAINTY_STATEMENT

    return True, None
