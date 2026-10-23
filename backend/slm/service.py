"""Safe orchestration from EvidencePacket to a user-facing local response."""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from backend.contracts.comparison_reasons import (
    STATE_C_EVIDENCE_NOT_REPORTABLE,
    STATE_C_TOO_FEW_RECORDED_DAYS,
)
from backend.contracts.evidence import EligibilityStatus, EvidencePacket, ResponseMode
from backend.slm.category_router import CategoryRouterLabel, OllamaCategoryRouter
from backend.slm.client import (
    GenerationMetrics,
    GenerationResult,
    SLMClientError,
    SLMResponseError,
    SLMTimeoutError,
    SLMUnavailableError,
)
from backend.slm.prompt_loader import (
    DEFAULT_APP_INFORMATION_TEMPLATES,
    DEFAULT_CAPABILITY_TEMPLATE,
    DEFAULT_CLINICAL_SCORE_BOUNDARY,
    DEFAULT_CRISIS_FALLBACK,
    DEFAULT_DIAGNOSIS_BOUNDARY,
    DEFAULT_GENERAL_UNCERTAINTY_TEMPLATE,
    DEFAULT_INSUFFICIENT_DATA_TEMPLATE,
    DEFAULT_OFF_TOPIC_SUPPORT,
    DEFAULT_SCOPE_FALLBACK,
    DEFAULT_TREATMENT_BOUNDARY,
    DEFAULT_WINDOW_FALLBACK,
    LoadedFallbackPrompt,
    load_fallback_prompt,
)
from backend.slm.request_policy import (
    RequestCategory,
    RequestDisposition,
    RequestPolicyDecision,
    app_information_reason,
    classify_request,
    deterministic_feature_id,
    is_general_uncertainty_question,
    request_scope_rejection,
)
from backend.slm.response_health import ResponseHealthReport, check_response_health
from backend.slm.safety_gate import validate_draft
from backend.slm.safety_screen import OllamaSafetyScreen, SafetyScreenLabel

FALLBACK_REASON_EVIDENCE_SOURCE_UNAVAILABLE = "evidence_source_unavailable"
FALLBACK_REASON_MODEL_TIMEOUT = "model_timeout"
FALLBACK_REASON_MODEL_UNAVAILABLE = "model_unavailable"
FALLBACK_REASON_MODEL_RESPONSE_INVALID = "model_response_invalid"
FALLBACK_REASON_MODEL_GENERATION_FAILED = "model_generation_failed"


class DraftGenerator(Protocol):
    def generate_draft(
        self, packet: EvidencePacket, question: str
    ) -> GenerationResult: ...


class AnswerKind(str, Enum):
    """Why an answer has the form it has, for the display tag only.

    Set from the evidence packet and the route, never from the answer text.
    None for refusals, crisis and fallbacks, which keep using
    request_category and rejection_reason.
    """

    COMPARISON_SHOWN = "comparison_shown"  # any generated answer, ELIGIBLE packet
    NO_CLEAR_DIFFERENCE = "no_clear_difference"  # State C, evidence not reportable
    FEW_RECENT_DAYS = "few_recent_days"  # State C, too few recorded days
    BUILDING_BASELINE = "building_baseline"  # PARTIAL packet, State B
    NOT_ENOUGH_DATA = "not_enough_data"  # insufficient-data template (State A)
    GENERAL_LIMITS = "general_limits"  # general-uncertainty template


_PARTIAL_ANSWER_KINDS = {
    STATE_C_EVIDENCE_NOT_REPORTABLE: AnswerKind.NO_CLEAR_DIFFERENCE,
    STATE_C_TOO_FEW_RECORDED_DAYS: AnswerKind.FEW_RECENT_DAYS,
}

_ROUTER_REFUSALS = {
    CategoryRouterLabel.INJECTION: (RequestCategory.PROMPT_INJECTION, "prompt_injection_detected"),
    CategoryRouterLabel.SENSITIVE: (RequestCategory.SENSITIVE_DATA_REQUEST, "sensitive_data_request_detected"),
    CategoryRouterLabel.DIAGNOSIS: (RequestCategory.DIAGNOSIS_SEEKING, "diagnosis_request_detected"),
    CategoryRouterLabel.TREATMENT: (RequestCategory.TREATMENT_ADVICE_SEEKING, "treatment_advice_request_detected"),
    CategoryRouterLabel.RISK: (RequestCategory.RISK_PREDICTION_SEEKING, "risk_prediction_request_detected"),
    CategoryRouterLabel.CAUSE: (RequestCategory.CAUSAL_INFERENCE_SEEKING, "causal_inference_request_detected"),
    CategoryRouterLabel.CLINICAL_SCORE: (RequestCategory.CLINICAL_SCORE_REQUEST, "clinical_score_request_detected"),
}
_REFUSAL_PRIORITY = (
    RequestCategory.PROMPT_INJECTION,
    RequestCategory.SENSITIVE_DATA_REQUEST,
    RequestCategory.DIAGNOSIS_SEEKING,
    RequestCategory.TREATMENT_ADVICE_SEEKING,
    RequestCategory.RISK_PREDICTION_SEEKING,
    RequestCategory.CAUSAL_INFERENCE_SEEKING,
    RequestCategory.CLINICAL_SCORE_REQUEST,
    RequestCategory.OFF_TOPIC,
)
_SCOPE_REASONS = {"unsupported_time_window", "ambiguous_feature_request"}


def _generated_answer_kind(packet: EvidencePacket) -> AnswerKind | None:
    status = packet.baseline.eligibility_status
    if status == EligibilityStatus.ELIGIBLE:
        # Any generated answer on an ELIGIBLE packet, whatever its mode.
        return AnswerKind.COMPARISON_SHOWN
    if status == EligibilityStatus.PARTIAL_DESCRIPTIVE_ONLY:
        return _PARTIAL_ANSWER_KINDS.get(
            packet.baseline.ineligible_reason, AnswerKind.BUILDING_BASELINE
        )
    return None


class SafeSLMResponse(BaseModel):
    """Final response metadata retained for audit and evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response_mode: ResponseMode
    text: str
    used_fallback: bool
    rejection_reason: str | None
    model_tag: str | None
    generation_prompt_sha256: str | None
    fallback_prompt_sha256: str | None
    metrics: GenerationMetrics | None
    request_disposition: RequestDisposition
    request_category: RequestCategory
    request_policy_version: str
    model_invoked: bool
    # Policy 0.3.5 local-model safety screen: yes, no, unclear, error,
    # not_run (the rules already chose crisis) or skipped (demo stub).
    # model_invoked still describes answer generation only.
    safety_screen: SafetyScreenLabel | None = None
    # Display tag only; see AnswerKind. Never inferred from the answer text.
    answer_kind: AnswerKind | None = None


class SLMService:
    """Validate every model draft or return the versioned safe fallback."""

    def __init__(
        self,
        client: DraftGenerator,
        *,
        generic_fallback: LoadedFallbackPrompt | None = None,
        crisis_fallback: LoadedFallbackPrompt | None = None,
        insufficient_data_template: LoadedFallbackPrompt | None = None,
        safety_screen: OllamaSafetyScreen | None = None,
        category_router: OllamaCategoryRouter | None = None,
    ) -> None:
        self.client = client
        self.safety_screen = safety_screen
        self.category_router = category_router
        # Deterministic yes/no results only, keyed by a hash of the question,
        # so /respond screens once across preflight and generation.
        self._screen_cache: OrderedDict[str, SafetyScreenLabel] = OrderedDict()
        self._screen_lock = threading.Lock()
        self._router_cache: OrderedDict[str, CategoryRouterLabel] = OrderedDict()
        self._router_lock = threading.Lock()
        self.generic_fallback = generic_fallback or load_fallback_prompt()
        self.crisis_fallback = crisis_fallback or load_fallback_prompt(
            DEFAULT_CRISIS_FALLBACK
        )
        self.insufficient_data_template = (
            insufficient_data_template
            or load_fallback_prompt(DEFAULT_INSUFFICIENT_DATA_TEMPLATE)
        )
        self.scope_fallback = load_fallback_prompt(DEFAULT_SCOPE_FALLBACK)
        self.window_fallback = load_fallback_prompt(DEFAULT_WINDOW_FALLBACK)
        # Policy 0.3.2 category-specific deterministic texts (ME-P01 F1/F3/F4).
        self.capability_template = load_fallback_prompt(DEFAULT_CAPABILITY_TEMPLATE)
        self.diagnosis_boundary = load_fallback_prompt(DEFAULT_DIAGNOSIS_BOUNDARY)
        self.general_uncertainty_template = load_fallback_prompt(
            DEFAULT_GENERAL_UNCERTAINTY_TEMPLATE
        )
        # Policy 0.3.3 deterministic texts (50-question dev test).
        self.treatment_boundary = load_fallback_prompt(DEFAULT_TREATMENT_BOUNDARY)
        self.clinical_score_boundary = load_fallback_prompt(
            DEFAULT_CLINICAL_SCORE_BOUNDARY
        )
        self.app_information_templates = {
            reason_code: load_fallback_prompt(path)
            for reason_code, path in DEFAULT_APP_INFORMATION_TEMPLATES.items()
        }
        # Support-line refusal: policy 0.3.4 off-topic default, every refusal
        # without its own template from 0.3.5.
        self.off_topic_support = load_fallback_prompt(DEFAULT_OFF_TOPIC_SUPPORT)
        if (
            self.generic_fallback.manifest.response_mode
            != ResponseMode.GENERIC_FALLBACK
        ):
            raise ValueError("generic fallback manifest has the wrong response_mode")
        if (
            self.crisis_fallback.manifest.response_mode
            != ResponseMode.CRISIS_AWARE_FALLBACK
        ):
            raise ValueError("crisis fallback manifest has the wrong response_mode")
        if (
            self.insufficient_data_template.manifest.response_mode
            != ResponseMode.INSUFFICIENT_DATA
        ):
            raise ValueError(
                "insufficient-data template manifest has the wrong response_mode"
            )

    def respond(self, packet: EvidencePacket, question: str) -> SafeSLMResponse:
        request_decision, screen = self._classify(question)
        return _stamp(self._respond(packet, question, request_decision), screen)

    def _respond(
        self,
        packet: EvidencePacket,
        question: str,
        request_decision: RequestPolicyDecision,
    ) -> SafeSLMResponse:
        if request_decision.disposition != RequestDisposition.ALLOW:
            return self._policy_response(request_decision)
        if request_decision.reason_code in _SCOPE_REASONS:
            return self._scope_response(request_decision, request_decision.reason_code)
        health = self.check_response_health(packet)
        if not health.healthy:
            return self._fallback(
                health.rejection_reason or "evidence_contract_violation",
                request_decision=request_decision,
                model_invoked=False,
            )
        if packet.baseline.eligibility_status in {
            EligibilityStatus.INELIGIBLE_INSUFFICIENT_WINDOW,
            EligibilityStatus.INELIGIBLE_INSUFFICIENT_BASELINE,
        }:
            return self._insufficient_data_response(request_decision)

        scope_reason = request_scope_rejection(
            question, feature_id=packet.feature_window.feature_id
        )
        if scope_reason:
            return self._scope_response(request_decision, scope_reason)

        try:
            generation = self.client.generate_draft(packet, question)
        except SLMTimeoutError:
            return self._fallback(
                FALLBACK_REASON_MODEL_TIMEOUT, request_decision=request_decision
            )
        except SLMUnavailableError:
            return self._fallback(
                FALLBACK_REASON_MODEL_UNAVAILABLE,
                request_decision=request_decision,
            )
        except SLMResponseError:
            return self._fallback(
                FALLBACK_REASON_MODEL_RESPONSE_INVALID,
                request_decision=request_decision,
            )
        except (SLMClientError, ValueError):
            return self._fallback(
                FALLBACK_REASON_MODEL_GENERATION_FAILED,
                request_decision=request_decision,
            )

        draft = generation.draft
        if draft.response_mode == ResponseMode.REFUSAL:
            return self._fallback(
                "model_must_not_select_refusal",
                request_decision=request_decision,
                generation=generation,
            )
        if draft.response_mode == ResponseMode.CRISIS_AWARE_FALLBACK:
            return self._fallback(
                "model_must_not_select_crisis_fallback",
                request_decision=request_decision,
                generation=generation,
            )
        if draft.response_mode == ResponseMode.GENERIC_FALLBACK:
            return self._fallback(
                "model_requested_fallback",
                request_decision=request_decision,
                generation=generation,
            )

        is_valid, rejection = validate_draft(packet, draft)
        if not is_valid:
            return self._fallback(
                str(rejection),
                request_decision=request_decision,
                generation=generation,
            )

        return SafeSLMResponse(
            response_mode=draft.response_mode,
            text=draft.text,
            used_fallback=False,
            rejection_reason=None,
            model_tag=generation.model_tag,
            generation_prompt_sha256=generation.prompt_sha256,
            fallback_prompt_sha256=None,
            metrics=generation.metrics,
            request_disposition=request_decision.disposition,
            request_category=request_decision.category,
            request_policy_version=request_decision.policy_version,
            model_invoked=True,
            answer_kind=_generated_answer_kind(packet),
        )

    def check_response_health(self, packet: EvidencePacket) -> ResponseHealthReport:
        """Expose the SLM boundary health check for Integration/QA wiring."""

        return check_response_health(packet)

    def preflight_response(
        self,
        question: str,
        *,
        feature_id: str | None = None,
        require_feature: bool = False,
    ) -> SafeSLMResponse | None:
        """Route deterministic policy cases before participant data is loaded."""

        decision, screen = self._classify(question)
        if decision.disposition != RequestDisposition.ALLOW:
            return _stamp(self._policy_response(decision), screen)
        if decision.reason_code in _SCOPE_REASONS:
            return _stamp(self._scope_response(decision, decision.reason_code), screen)
        if not feature_id and is_general_uncertainty_question(question):
            return _stamp(
                self._template_response(
                    decision,
                    self.general_uncertainty_template,
                    answer_kind=AnswerKind.GENERAL_LIMITS,
                ),
                screen,
            )
        scope_reason = request_scope_rejection(
            question, feature_id=feature_id, require_feature=require_feature
        )
        if scope_reason:
            return _stamp(self._scope_response(decision, scope_reason), screen)
        return None

    def context_unavailable_response(self, question: str) -> SafeSLMResponse:
        """Safe public boundary for failed retrieval, tools or context validation."""

        preflight = self.preflight_response(question)
        if preflight is not None:
            return preflight
        decision, screen = self._classify(question)
        return _stamp(
            self._fallback(
                "approved_context_unavailable",
                request_decision=decision,
                model_invoked=False,
            ),
            screen,
        )

    def _scope_response(
        self, decision: RequestPolicyDecision, reason: str
    ) -> SafeSLMResponse:
        template = (
            self.window_fallback
            if reason == "unsupported_time_window"
            else self.scope_fallback
        )
        return self._fallback(
            reason, request_decision=decision, model_invoked=False
        ).model_copy(
            update={
                "text": template.manifest.text,
                "fallback_prompt_sha256": template.sha256,
            }
        )

    def evidence_unavailable_response(self, question: str) -> SafeSLMResponse:
        """Fail closed when the approved local evidence source cannot be read."""

        decision, screen = self._classify(question)
        if decision.disposition != RequestDisposition.ALLOW:
            return _stamp(self._policy_response(decision), screen)
        return _stamp(
            self._fallback(
                FALLBACK_REASON_EVIDENCE_SOURCE_UNAVAILABLE,
                request_decision=decision,
                model_invoked=False,
            ),
            screen,
        )

    def safety_screen_label(self, question: str) -> SafetyScreenLabel:
        """Screen label for a question (cached after the first yes/no)."""

        return self._classify(question)[1]

    def _classify(
        self, question: str
    ) -> tuple[RequestPolicyDecision, SafetyScreenLabel]:
        """Rules first; then, unless already crisis, the local safety screen.

        The screen can only add a crisis route: yes or unclear goes to the
        crisis template. A timeout or error keeps the rules-only decision
        (every refusal still carries the support line) and is logged as error.
        """

        decision = classify_request(question)
        if decision.disposition == RequestDisposition.CRISIS:
            return decision, SafetyScreenLabel.NOT_RUN
        if self.safety_screen is None:
            return decision, SafetyScreenLabel.SKIPPED
        label = self._screen(question.strip())
        if label in {SafetyScreenLabel.NO, SafetyScreenLabel.ERROR}:
            if self.category_router is None or not (
                decision.category == RequestCategory.OFF_TOPIC
                or (
                    decision.disposition == RequestDisposition.ALLOW
                    and decision.reason_code not in _SCOPE_REASONS
                )
            ):
                return decision, label
            routed = self._route_uncertain(question.strip())
            return self._apply_router(decision, routed, question), label
        return (
            RequestPolicyDecision(
                disposition=RequestDisposition.CRISIS,
                category=RequestCategory.CRISIS_SELF_HARM,
                reason_code="safety_screen_flagged",
            ),
            label,
        )

    def _screen(self, question: str) -> SafetyScreenLabel:
        key = hashlib.sha256(question.encode("utf-8")).hexdigest()
        with self._screen_lock:
            cached = self._screen_cache.get(key)
        if cached is not None:
            return cached
        assert self.safety_screen is not None
        label = self.safety_screen.screen(question)
        if label in {SafetyScreenLabel.YES, SafetyScreenLabel.NO}:
            with self._screen_lock:
                self._screen_cache[key] = label
                while len(self._screen_cache) > 256:
                    self._screen_cache.popitem(last=False)
        return label

    def _route_uncertain(self, question: str) -> CategoryRouterLabel | None:
        key = hashlib.sha256(question.encode("utf-8")).hexdigest()
        with self._router_lock:
            cached = self._router_cache.get(key)
        if cached is not None:
            return cached
        assert self.category_router is not None
        routed = self.category_router.classify(question)
        if routed is not None:
            with self._router_lock:
                self._router_cache[key] = routed
                while len(self._router_cache) > 256:
                    self._router_cache.popitem(last=False)
        return routed

    @staticmethod
    def _apply_router(
        decision: RequestPolicyDecision,
        routed: CategoryRouterLabel | None,
        question: str,
    ) -> RequestPolicyDecision:
        if routed is None:
            return decision
        if routed == CategoryRouterLabel.CRISIS:
            return RequestPolicyDecision(
                disposition=RequestDisposition.CRISIS,
                category=RequestCategory.CRISIS_SELF_HARM,
                reason_code="category_router_crisis",
            )
        if routed in _ROUTER_REFUSALS:
            category, reason = _ROUTER_REFUSALS[routed]
            if (
                decision.disposition == RequestDisposition.REFUSE
                and decision.category in _REFUSAL_PRIORITY
                and _REFUSAL_PRIORITY.index(decision.category)
                < _REFUSAL_PRIORITY.index(category)
            ):
                return decision
            return RequestPolicyDecision(
                disposition=RequestDisposition.REFUSE,
                category=category,
                reason_code=reason,
                support_line=True,
            )
        if routed == CategoryRouterLabel.APP_INFO:
            return RequestPolicyDecision(
                disposition=RequestDisposition.REFUSE,
                category=RequestCategory.APP_INFORMATION,
                reason_code=app_information_reason(question) or "app_info_data_use",
            )
        if routed == CategoryRouterLabel.CAPABILITY:
            return RequestPolicyDecision(
                disposition=RequestDisposition.REFUSE,
                category=RequestCategory.CAPABILITY_QUESTION,
                reason_code="capability_question_detected",
            )
        if routed in {CategoryRouterLabel.TIME_WINDOW, CategoryRouterLabel.FEATURE_UNCLEAR}:
            if (
                decision.disposition == RequestDisposition.ALLOW
                and deterministic_feature_id(question) is not None
                and routed == CategoryRouterLabel.FEATURE_UNCLEAR
            ):
                return decision
            if decision.category == RequestCategory.OFF_TOPIC and (
                routed == CategoryRouterLabel.FEATURE_UNCLEAR
                or deterministic_feature_id(question) is None
            ):
                return decision
            return RequestPolicyDecision(
                disposition=RequestDisposition.ALLOW,
                category=RequestCategory.IN_SCOPE,
                reason_code=(
                    "unsupported_time_window"
                    if routed == CategoryRouterLabel.TIME_WINDOW
                    else "ambiguous_feature_request"
                ),
            )
        if routed in {CategoryRouterLabel.IN_SCOPE_GPS, CategoryRouterLabel.IN_SCOPE_UNLOCKS}:
            if decision.disposition != RequestDisposition.ALLOW:
                return decision
            expected = (
                "gps_distance"
                if routed == CategoryRouterLabel.IN_SCOPE_GPS
                else "unlock_count"
            )
            return RequestPolicyDecision(
                disposition=RequestDisposition.ALLOW,
                category=RequestCategory.IN_SCOPE,
                reason_code=(
                    None
                    if deterministic_feature_id(question) == expected
                    else "ambiguous_feature_request"
                ),
            )
        return decision

    def _policy_response(self, decision: RequestPolicyDecision) -> SafeSLMResponse:
        if decision.disposition == RequestDisposition.CRISIS:
            template = self.crisis_fallback
            response_mode = ResponseMode.CRISIS_AWARE_FALLBACK
        elif decision.category == RequestCategory.DIAGNOSIS_SEEKING:
            template = self.diagnosis_boundary
            response_mode = ResponseMode.REFUSAL
        elif decision.category == RequestCategory.CAPABILITY_QUESTION:
            template = self.capability_template
            response_mode = ResponseMode.REFUSAL
        elif decision.category == RequestCategory.TREATMENT_ADVICE_SEEKING:
            template = self.treatment_boundary
            response_mode = ResponseMode.REFUSAL
        elif decision.category == RequestCategory.CLINICAL_SCORE_REQUEST:
            template = self.clinical_score_boundary
            response_mode = ResponseMode.REFUSAL
        elif decision.category == RequestCategory.APP_INFORMATION:
            template = self.app_information_templates[decision.reason_code]
            response_mode = ResponseMode.REFUSAL
        elif decision.support_line:
            # Policy 0.3.5: every refusal without its own template (off-topic,
            # cause, risk, prompt injection, sensitive data) carries the
            # support line.
            template = self.off_topic_support
            response_mode = ResponseMode.REFUSAL
        else:
            template = self.generic_fallback
            response_mode = ResponseMode.REFUSAL

        return SafeSLMResponse(
            response_mode=response_mode,
            text=template.manifest.text,
            used_fallback=True,
            rejection_reason=decision.reason_code,
            model_tag=None,
            generation_prompt_sha256=None,
            fallback_prompt_sha256=template.sha256,
            metrics=None,
            request_disposition=decision.disposition,
            request_category=decision.category,
            request_policy_version=decision.policy_version,
            model_invoked=False,
        )

    def _insufficient_data_response(
        self, decision: RequestPolicyDecision
    ) -> SafeSLMResponse:
        return self._template_response(
            decision,
            self.insufficient_data_template,
            answer_kind=AnswerKind.NOT_ENOUGH_DATA,
        )

    def _template_response(
        self,
        decision: RequestPolicyDecision,
        template: LoadedFallbackPrompt,
        *,
        answer_kind: AnswerKind | None = None,
    ) -> SafeSLMResponse:
        """Deterministic allowed-route text: no model call, no participant data."""

        return SafeSLMResponse(
            response_mode=template.manifest.response_mode,
            text=template.manifest.text,
            used_fallback=False,
            rejection_reason=None,
            model_tag=None,
            generation_prompt_sha256=None,
            fallback_prompt_sha256=template.sha256,
            metrics=None,
            request_disposition=decision.disposition,
            request_category=decision.category,
            request_policy_version=decision.policy_version,
            model_invoked=False,
            answer_kind=answer_kind,
        )

    def _fallback(
        self,
        reason: str,
        *,
        request_decision: RequestPolicyDecision,
        generation: GenerationResult | None = None,
        model_invoked: bool = True,
    ) -> SafeSLMResponse:
        return SafeSLMResponse(
            response_mode=ResponseMode.GENERIC_FALLBACK,
            text=self.generic_fallback.manifest.text,
            used_fallback=True,
            rejection_reason=reason,
            model_tag=generation.model_tag if generation else None,
            generation_prompt_sha256=(generation.prompt_sha256 if generation else None),
            fallback_prompt_sha256=self.generic_fallback.sha256,
            metrics=generation.metrics if generation else None,
            request_disposition=request_decision.disposition,
            request_category=request_decision.category,
            request_policy_version=request_decision.policy_version,
            model_invoked=model_invoked,
        )


def _stamp(response: SafeSLMResponse, label: SafetyScreenLabel) -> SafeSLMResponse:
    return response.model_copy(update={"safety_screen": label})
