import pytest

from backend.contracts.evidence import (
    ApprovedClaimId,
    AssistantDraft,
    ClaimPolicy,
    EvidencePacket,
    ProhibitedClaimId,
    ResponseMode,
)
from backend.slm.safety_gate import (
    ELIGIBILITY_TEXT_CONTRADICTION,
    EMPTY_RESPONSE_TEXT,
    INSUFFICIENT_HISTORY_DISCLOSURE_MISSING,
    PROHIBITED_PHRASE_DETECTED,
    REFUSAL_REFERENCES_EVIDENCE,
    RESPONSE_TEXT_TOO_SHORT,
    UNCERTAINTY_TEXT_MISSING,
    validate_draft,
)


def test_gate_rejects_empty_text(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    draft = valid_draft.model_copy(update={"text": "   "})

    ok, reason = validate_draft(eligible_packet, draft)

    assert ok is False
    assert reason == EMPTY_RESPONSE_TEXT


def test_gate_rejects_direct_causal_language(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    draft = valid_draft.model_copy(
        update={"text": "Your reduced movement caused your wellbeing score."}
    )

    ok, reason = validate_draft(eligible_packet, draft)

    assert ok is False
    assert reason == PROHIBITED_PHRASE_DETECTED


def test_gate_rejects_direct_diagnosis_language(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    draft = valid_draft.model_copy(update={"text": "You have depression."})

    ok, reason = validate_draft(eligible_packet, draft)

    assert ok is False
    assert reason == PROHIBITED_PHRASE_DETECTED


def test_gate_rejects_insufficient_history_claim_for_eligible_packet(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    draft = valid_draft.model_copy(
        update={"text": "There is not enough data to compare with your baseline."}
    )

    ok, reason = validate_draft(eligible_packet, draft)

    assert ok is False
    assert reason == ELIGIBILITY_TEXT_CONTRADICTION


def test_gate_rejects_evidence_references_in_refusal_mode(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    refusal_policy = ClaimPolicy(
        approved_claim_ids=(ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,),
        prohibited_claim_ids=tuple(ProhibitedClaimId),
        permitted_response_modes=(ResponseMode.REFUSAL,),
    )
    packet = eligible_packet.model_copy(update={"claim_policy": refusal_policy})
    draft = valid_draft.model_copy(
        update={
            "response_mode": ResponseMode.REFUSAL,
            "claim_ids_used": (ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,),
            "evidence_ids_referenced": (packet.feature_window.feature_id,),
            "text": "This app cannot diagnose a condition.",
            "includes_uncertainty_statement": False,
        }
    )

    ok, reason = validate_draft(packet, draft)

    assert ok is False
    assert reason == REFUSAL_REFERENCES_EVIDENCE


def test_gate_rejects_too_short_model_text(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    draft = valid_draft.model_copy(update={"text": "A"})

    ok, reason = validate_draft(eligible_packet, draft)

    assert ok is False
    assert reason == RESPONSE_TEXT_TOO_SHORT


@pytest.mark.parametrize(
    "text",
    [
        "This pattern is uncertain; consult with a healthcare professional.",
        "This pattern is uncertain; seek professional advice for next steps.",
    ],
)
def test_gate_rejects_unrequested_clinical_referral(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft, text: str
):
    draft = valid_draft.model_copy(update={"text": text})

    ok, reason = validate_draft(eligible_packet, draft)

    assert ok is False
    assert reason == PROHIBITED_PHRASE_DETECTED


def test_gate_does_not_trust_uncertainty_boolean_without_text(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    draft = valid_draft.model_copy(
        update={
            "text": (
                "Your movement was below your baseline with moderate evidence strength."
            ),
            "includes_uncertainty_statement": True,
        }
    )

    ok, reason = validate_draft(eligible_packet, draft)

    assert ok is False
    assert reason == UNCERTAINTY_TEXT_MISSING


def test_gate_requires_insufficient_history_disclosure(
    eligible_packet: EvidencePacket, valid_draft: AssistantDraft
):
    partial_policy = ClaimPolicy(
        approved_claim_ids=(ApprovedClaimId.NOT_ENOUGH_DATA,),
        prohibited_claim_ids=tuple(ProhibitedClaimId),
        permitted_response_modes=(ResponseMode.INSUFFICIENT_DATA,),
    )
    packet = eligible_packet.model_copy(update={"claim_policy": partial_policy})
    draft = valid_draft.model_copy(
        update={
            "response_mode": ResponseMode.INSUFFICIENT_DATA,
            "claim_ids_used": (ApprovedClaimId.NOT_ENOUGH_DATA,),
            "text": "The current window contains eighteen unlocks.",
            "includes_uncertainty_statement": False,
        }
    )

    ok, reason = validate_draft(packet, draft)

    assert ok is False
    assert reason == INSUFFICIENT_HISTORY_DISCLOSURE_MISSING
