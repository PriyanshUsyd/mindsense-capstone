"""Runtime regression tests using public synthetic data, never held-out prompts."""

from pathlib import Path

import pytest

from backend.contracts.evidence import ApprovedClaimId, AssistantDraft, ResponseMode
from backend.slm.client import GenerationMetrics, GenerationResult
from backend.slm.service import SLMService
from backend.slm.shadow_cli import load_packet
from benchmarks.slm_model_comparison import comparison_cases

FIXTURES = Path(__file__).parent / "fixtures"
UNCERTAINTY = "This estimate is uncertain and should be interpreted cautiously."
GPS = (
    "Your GPS distance was 3.8 kilometres per day, compared with your own "
    "baseline of 4.6 kilometres per day. " + UNCERTAINTY
)
PARTIAL = (
    "Your phone unlock count was 18 unlocks per day in the observed window. "
    "It is too early to compare with your own baseline."
)


class Stub:
    def __init__(self, draft):
        self.draft = draft

    def generate_draft(self, packet, question):
        return GenerationResult(
            draft=self.draft,
            model_tag="synthetic-stub:1.0",
            prompt_id="grounding-regression",
            prompt_version="1",
            prompt_sha256="0" * 64,
            metrics=GenerationMetrics(),
        )


def respond(packet, text, *, mode=None, claims=None, evidence_ids=None):
    mode = mode or packet.claim_policy.permitted_response_modes[0]
    ready = mode in {ResponseMode.NORMAL, ResponseMode.UNCERTAINTY}
    if claims is None:
        claims = (
            (
                ApprovedClaimId.OBSERVATION_OF_DEVIATION,
                ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
            )
            if ready
            else (ApprovedClaimId.TREND_DESCRIPTION, ApprovedClaimId.NOT_ENOUGH_DATA)
        )
    draft = AssistantDraft(
        packet_id=packet.identity.packet_id,
        response_mode=mode,
        claim_ids_used=claims,
        evidence_ids_referenced=(
            (packet.feature_window.feature_id,)
            if evidence_ids is None
            else evidence_ids
        ),
        text=text,
        includes_uncertainty_statement=ready,
    )
    return SLMService(Stub(draft)).respond(
        packet, "Please describe my recent activity."
    )


@pytest.fixture
def gps():
    return load_packet(FIXTURES / "week5_gps_eligible.json")


@pytest.fixture
def partial():
    return comparison_cases()[1].packet


@pytest.mark.parametrize(
    "text",
    [
        "Your GPS distance was 999 kilometres per day. This estimate is uncertain.",
        GPS.replace("3.8", "999"),
        GPS.replace("baseline of 4.6", "baseline of 25"),
        GPS.replace("3.8", "SWAP").replace("4.6", "3.8").replace("SWAP", "4.6"),
        GPS.replace("3.8", "4.6"),
        GPS.replace("3.8", "3.800000000000001"),
        GPS.replace("3.8", "-3.8"),
        GPS.replace("3.8", "NaN"),
        GPS.replace("3.8", "infinity"),
        GPS.replace("3.8", "three point eight"),
        GPS.replace("GPS distance", "sleep duration"),
        GPS.replace("kilometres per day", "hours per day"),
        GPS.replace("was 3.8", "was not 3.8"),
        GPS + " Your mood improved.",
        GPS + " Your activity is 17% lower.",
        GPS + " The past 25 days show a trend.",
        GPS + " Your distance was nine hundred and ninety-nine.",
        GPS.replace("3.8", "3.8\u200b"),
        GPS.replace("GPS", "GРS"),  # Cyrillic look-alike, not a new language feature.
    ],
)
def test_unsupported_numeric_or_extra_claims_fall_back(gps, text):
    response = respond(gps, text)
    assert response.used_fallback is True
    assert response.response_mode == ResponseMode.GENERIC_FALLBACK
    assert response.text != text
    assert response.rejection_reason


@pytest.mark.parametrize(
    "text",
    [
        "Your phone unlock count is 80% above your baseline. It is too early to compare.",
        PARTIAL + " This is above your usual activity.",
        PARTIAL + " This is lower than normal.",
        PARTIAL + " Activity has doubled.",
        PARTIAL + " There was no change from your baseline.",
        PARTIAL.replace("18", "80"),
        PARTIAL.replace("18", "eighteen"),
        PARTIAL.replace("phone unlock count", "phone usage"),
        PARTIAL.replace("in the observed window", "over the past 25 days"),
        PARTIAL.replace("It is too early to compare", "We can compare"),
    ],
)
def test_state_b_comparison_cannot_hide_behind_disclaimer(partial, text):
    response = respond(partial, text)
    assert response.used_fallback is True
    assert response.response_mode == ResponseMode.GENERIC_FALLBACK
    assert response.text != text


@pytest.mark.parametrize("mode", [ResponseMode.NORMAL, ResponseMode.UNCERTAINTY])
@pytest.mark.parametrize(
    "text",
    [
        GPS,
        GPS.replace("3.8", "3.800").replace("4.6", "4.60"),
        GPS.replace("3.8", "3.8e0"),
        GPS.lower(),
        "  " + GPS.replace(" ", "\n") + "  ",
    ],
)
def test_correct_bound_values_and_supported_formatting_are_accepted(gps, mode, text):
    response = respond(gps, text, mode=mode)
    assert response.used_fallback is False
    assert response.response_mode == mode
    assert response.text == text


def test_state_b_describes_current_value_without_comparison(partial):
    response = respond(partial, PARTIAL)
    assert response.used_fallback is False
    assert response.response_mode == ResponseMode.INSUFFICIENT_DATA
    assert response.text == PARTIAL


def test_second_approved_comparison_sentence_form(gps):
    text = GPS.replace(", compared with", " in the observed window. Compared with")
    text = text.replace(". This estimate", ", this estimate")
    assert respond(gps, text).used_fallback is False


@pytest.mark.parametrize(
    "mutation", ["current", "baseline", "unit", "extra", "negation"]
)
def test_second_sentence_form_cannot_bypass_bindings(gps, mutation):
    text = GPS.replace(", compared with", " in the observed window. Compared with")
    text = text.replace(". This estimate", ", this estimate")
    if mutation == "current":
        text = text.replace("3.8", "999")
    elif mutation == "baseline":
        text = text.replace("4.6", "3.8")
    elif mutation == "unit":
        text = text.replace("kilometres", "miles")
    elif mutation == "extra":
        text += " You are doing better."
    else:
        text = text.replace("was 3.8", "was not 3.8")
    assert respond(gps, text).used_fallback is True


@pytest.mark.parametrize("value", [0.0, 1.0, 42.125, 1000.0])
def test_numbers_are_bound_to_input_not_hardcoded_fixture(gps, value):
    packet = gps.model_copy(
        update={
            "feature_window": gps.feature_window.model_copy(update={"value": value})
        }
    )
    text = GPS.replace("3.8", str(value))
    assert respond(packet, text).used_fallback is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("feature_id", "sleep_duration"),
        ("unit", "miles_per_day"),
        ("value", float("nan")),
        ("value", float("inf")),
        ("value", -1.0),
    ],
)
def test_unsupported_feature_unit_or_measurement_fails_closed(gps, field, value):
    packet = gps.model_copy(
        update={"feature_window": gps.feature_window.model_copy(update={field: value})}
    )
    assert respond(packet, GPS).used_fallback is True


@pytest.mark.parametrize("baseline", [None, float("nan"), float("inf"), -1.0])
def test_invalid_comparison_baseline_fails_closed(gps, baseline):
    packet = gps.model_copy(
        update={"baseline": gps.baseline.model_copy(update={"value": baseline})}
    )
    assert respond(packet, GPS).used_fallback is True


@pytest.mark.parametrize(
    "missing",
    [
        ApprovedClaimId.OBSERVATION_OF_DEVIATION,
        ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
    ],
)
def test_text_needs_corresponding_declared_and_approved_claims(gps, missing):
    claims = tuple(
        c
        for c in (
            ApprovedClaimId.OBSERVATION_OF_DEVIATION,
            ApprovedClaimId.UNCERTAINTY_DISCLOSURE,
        )
        if c != missing
    )
    assert respond(gps, GPS, claims=claims).used_fallback is True


def test_numeric_explanation_must_reference_its_packet(gps):
    assert respond(gps, GPS, evidence_ids=()).used_fallback is True


@pytest.mark.parametrize("extra", ["baseline", "evidence"])
def test_state_b_rejects_inconsistent_upstream_comparison_fields(partial, gps, extra):
    packet = partial.model_copy(
        update={
            extra: (
                partial.baseline.model_copy(update={"value": 35.0})
                if extra == "baseline"
                else gps.evidence
            )
        }
    )
    assert respond(packet, PARTIAL).used_fallback is True


def test_model_refusal_mode_cannot_bypass_grounding(gps):
    packet = gps.model_copy(
        update={
            "claim_policy": gps.claim_policy.model_copy(
                update={
                    "permitted_response_modes": (ResponseMode.REFUSAL,),
                    "approved_claim_ids": (ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,),
                }
            )
        }
    )
    response = respond(
        packet,
        "Your GPS distance was 999 kilometres per day.",
        mode=ResponseMode.REFUSAL,
        claims=(ApprovedClaimId.NON_DIAGNOSTIC_BOUNDARY,),
        evidence_ids=(),
    )
    assert response.used_fallback is True
    assert response.rejection_reason == "model_must_not_select_refusal"
