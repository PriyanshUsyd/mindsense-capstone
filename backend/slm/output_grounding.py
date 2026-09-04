"""Bounded English output grammar for the current single-feature SLM scope.

This is not a general natural-language truth checker. Unrecognised wording,
features, units or claims fail closed; the service uses its versioned fallback.
No measurements, comparisons or wellbeing relationships are computed here.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal

from backend.contracts.evidence import (
    ApprovedClaimId,
    AssistantDraft,
    EligibilityStatus,
    EvidencePacket,
    ResponseMode,
)

OUTPUT_GROUNDING_VERSION = "0.1.1"
UNCERTAINTY_TEXT = "This estimate is uncertain and should be interpreted cautiously."
# Explicit mappings: never guess a unit or interpolate arbitrary upstream labels.
_LABELS = {
    ("unlock_count", "count_per_day"): ("phone unlock count", "unlocks per day"),
    ("unlock_count", "count"): ("phone unlock count", "unlocks"),
    ("gps_distance", "kilometres_per_day"): ("GPS distance", "kilometres per day"),
    ("gps_distance", "km_per_day"): ("GPS distance", "kilometres per day"),
    ("gps_distance", "km"): ("GPS distance", "kilometres"),
}
_NUMBER = r"[+]?[0-9]{1,32}(?:\.[0-9]{1,32})?(?:[eE][+-]?[0-9]{1,3})?"
_READY = {ResponseMode.NORMAL, ResponseMode.UNCERTAINTY}


def _finite_nonnegative(value: float | None) -> bool:
    return value is not None and math.isfinite(value) and value >= 0


def _shape(
    packet: EvidencePacket, mode: ResponseMode
) -> tuple[str, set[ApprovedClaimId], dict[str, float]]:
    feature = packet.feature_window
    labels = _LABELS.get((feature.feature_id, feature.unit))
    if labels is None:
        raise ValueError("grounding_unsupported_feature_unit")
    if not _finite_nonnegative(feature.value):
        raise ValueError("grounding_invalid_packet")
    label, unit = labels
    values = {"current": feature.value}
    prefix = f"Your {label} was {{current}} {unit}"
    if packet.baseline.eligibility_status == EligibilityStatus.ELIGIBLE:
        if (
            mode not in _READY
            or not _finite_nonnegative(packet.baseline.value)
            or packet.baseline.n_baseline_observations <= 0
            or packet.evidence is None
        ):
            raise ValueError("grounding_invalid_packet")
        values["baseline"] = packet.baseline.value
        text = (
            prefix
            + f", compared with your own baseline of {{baseline}} {unit}. "
            + UNCERTAINTY_TEXT
        )
        claims = {
            ApprovedClaimId.OBSERVATION_OF_DEVIATION,
            ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
        }
    elif (
        packet.baseline.eligibility_status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY
    ):
        if (
            packet.baseline.value is not None
            or packet.evidence is not None
            or mode not in {ResponseMode.INSUFFICIENT_DATA, ResponseMode.UNCERTAINTY}
        ):
            raise ValueError("grounding_invalid_packet")
        text = (
            prefix + " in the observed window. "
            "It is too early to compare with your own baseline."
        )
        claims = {ApprovedClaimId.TREND_DESCRIPTION, ApprovedClaimId.NOT_ENOUGH_DATA}
        if mode == ResponseMode.UNCERTAINTY:
            text += " " + UNCERTAINTY_TEXT
            claims.add(ApprovedClaimId.UNCERTAINTY_DISCLOSURE)
    else:
        raise ValueError("grounding_unsupported_state")
    return text, claims, values


def render_grounded_example(packet: EvidencePacket, mode: ResponseMode) -> str:
    """Example for synthetic test generators, NOT a replacement for model output."""
    template, _, values = _shape(packet, mode)
    return template.format(**{key: str(value) for key, value in values.items()})


def validate_output_grounding(
    packet: EvidencePacket, draft: AssistantDraft
) -> str | None:
    """Return a stable rejection reason, or None for a fully bound sentence.

    Existing metadata/mode/uncertainty checks must also pass in validate_draft.
    Only ASCII case/whitespace and exactly equivalent decimal notation vary.
    """
    try:
        template, required, values = _shape(packet, draft.response_mode)
    except ValueError as exc:
        return str(exc)
    declared = set(draft.claim_ids_used)
    if (
        not required <= declared
        or not required <= set(packet.claim_policy.approved_claim_ids)
        or not declared <= required | {ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY}
    ):
        return "grounding_claim_mismatch"
    valid_ids = {packet.identity.packet_id, packet.feature_window.feature_id}
    if (
        not draft.evidence_ids_referenced
        or not set(draft.evidence_ids_referenced) <= valid_ids
    ):
        return "grounding_evidence_reference_missing"
    if len(draft.text) > 2048:
        return "grounding_text_mismatch"
    text = re.sub(r"[ \t\r\n]+", " ", draft.text).strip(" \t\r\n")
    templates = [template]
    if packet.baseline.eligibility_status == EligibilityStatus.ELIGIBLE:
        # Same two bound values/units and uncertainty, split into two sentences.
        # This is an explicit second grammar, not arbitrary text between numbers.
        templates.append(
            template.replace(
                ", compared with", " in the observed window. Compared with", 1
            ).replace(". This estimate", ", this estimate", 1)
        )
    match = None
    for allowed in templates:
        pattern = re.escape(allowed)
        for key in values:
            pattern = pattern.replace(
                re.escape("{" + key + "}"), f"(?P<{key}>{_NUMBER})"
            )
        match = re.fullmatch(pattern, text, flags=re.IGNORECASE | re.ASCII)
        if match is not None:
            break
    if match is None:
        return "grounding_text_mismatch"
    if any(Decimal(match[key]) != Decimal(str(value)) for key, value in values.items()):
        return "grounding_value_mismatch"
    return None
