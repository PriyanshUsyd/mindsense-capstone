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
from backend.slm.client import (
    GenerationMetrics,
    GenerationResult,
    SLMClientError,
    SLMResponseError,
    SLMTimeoutError,
    SLMUnavailableError,
)
from backend.slm.category_router import OllamaCategoryRouter, RouterLabel
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
    classify_crisis_request,
    classify_request,
    infer_feature_from_question,
    is_general_uncertainty_question,
    request_scope_rejection,
)
from backend.slm.request_classifier import (
    ClassifierLabel,
    OllamaRequestClassifier,
    RequestClassification,
)
from backend.slm.response_health import ResponseHealthReport, check_response_health
from backend.slm.safety_gate import (
    PROHIBITED_PHRASE_DETECTED,
    contains_prohibited_assertion,
    validate_draft,
)
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
        request_classifier: OllamaRequestClassifier | None = None,
    ) -> None:
        self.client = client
        self.safety_screen = safety_screen
        # `category_router` remains as a compatibility seam for existing
        # injected test doubles; the Ollama runtime uses the v0.6 classifier.
        self.category_router = category_router
        self.request_classifier = request_classifier
        # Deterministic yes/no results only, keyed by a hash of the question,
        # so /respond screens once across preflight and generation.
        self._screen_cache: OrderedDict[str, SafetyScreenLabel] = OrderedDict()
        self._screen_lock = threading.Lock()
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

        scope_reason = self._scope_rejection(
            question, request_decision, feature_id=packet.feature_window.feature_id
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
        if decision.reason_code in {
            "unsupported_time_window",
            "ambiguous_feature_request",
            "feature_request_mismatch",
        }:
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
        scope_reason = self._scope_rejection(
            question,
            decision,
            feature_id=feature_id,
            require_feature=require_feature,
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
        """Crisis rules, safety screen, local classifier, then deterministic guard.

        The screen can only add a crisis route: yes or unclear goes to the
        crisis template. It is unchanged by policy 0.6.0. Classifier failures
        fail closed after deterministic high-priority guards are applied.
        """

        crisis_decision = classify_crisis_request(question)
        if crisis_decision is not None:
            return crisis_decision, SafetyScreenLabel.NOT_RUN
        if self.safety_screen is None:
            screen_label = SafetyScreenLabel.SKIPPED
        else:
            screen_label = self._screen(question.strip())
            if screen_label in {SafetyScreenLabel.YES, SafetyScreenLabel.UNCLEAR}:
                return (
                    RequestPolicyDecision(
                        disposition=RequestDisposition.CRISIS,
                        category=RequestCategory.CRISIS_SELF_HARM,
                        reason_code="safety_screen_flagged",
                    ),
                    screen_label,
                )
        if self.request_classifier is not None:
            classification = self.request_classifier.classify(question)
            deterministic = classify_request(question)
            return (
                self._guard_classifier_decision(
                    question, deterministic, classification
                ),
                screen_label,
            )
        decision = classify_request(question)
        return self._route_uncertain_request(question, decision), screen_label

    def _guard_classifier_decision(
        self,
        question: str,
        deterministic: RequestPolicyDecision,
        classification: RequestClassification | None,
    ) -> RequestPolicyDecision:
        """Keep every answer behind deterministic rules and feature checks."""

        # Crisis is normally returned before the safety screen. Retain this
        # guard in case a future deterministic family adds a crisis decision.
        if deterministic.disposition == RequestDisposition.CRISIS:
            return deterministic

        # These deterministic rules have explicit precedence in the 0.6.0
        # guard. Time-window checks are text-only and run before any data load.
        if deterministic.category in {
            RequestCategory.PROMPT_INJECTION,
            RequestCategory.SENSITIVE_DATA_REQUEST,
        }:
            return deterministic
        scope_reason = request_scope_rejection(question)
        if scope_reason == "unsupported_time_window":
            return RequestPolicyDecision(
                disposition=RequestDisposition.ALLOW,
                category=RequestCategory.IN_SCOPE,
                reason_code=scope_reason,
            )

        if classification is None:
            return self._classifier_failure_fallback(question, deterministic)

        model_decision = self._decision_from_router_label(
            question, deterministic, classification.label
        )
        if classification.label in {
            ClassifierLabel.IN_SCOPE_GPS,
            ClassifierLabel.IN_SCOPE_UNLOCKS,
        }:
            expected_feature = (
                "gps_distance"
                if classification.label == ClassifierLabel.IN_SCOPE_GPS
                else "unlock_count"
            )
            inferred_feature = infer_feature_from_question(question)
            if deterministic.disposition != RequestDisposition.ALLOW:
                return deterministic
            if inferred_feature is None:
                return RequestPolicyDecision(
                    disposition=RequestDisposition.ALLOW,
                    category=RequestCategory.IN_SCOPE,
                    reason_code="ambiguous_feature_request",
                )
            if inferred_feature != expected_feature:
                return RequestPolicyDecision(
                    disposition=RequestDisposition.ALLOW,
                    category=RequestCategory.IN_SCOPE,
                    reason_code="feature_request_mismatch",
                )
            if scope_reason:
                return RequestPolicyDecision(
                    disposition=RequestDisposition.ALLOW,
                    category=RequestCategory.IN_SCOPE,
                    reason_code=scope_reason,
                )
            # The model can agree with an answer route but cannot select the
            # feature or bypass the existing deterministic in-scope decision.
            return deterministic

        if classification.label == ClassifierLabel.FEATURE_UNCLEAR:
            if deterministic.disposition == RequestDisposition.ALLOW:
                if is_general_uncertainty_question(question):
                    return deterministic
                if infer_feature_from_question(question) is None:
                    return RequestPolicyDecision(
                        disposition=RequestDisposition.ALLOW,
                        category=RequestCategory.IN_SCOPE,
                        reason_code="ambiguous_feature_request",
                    )
                return deterministic
            if (
                deterministic.category == RequestCategory.OFF_TOPIC
                and deterministic.reason_code == "off_topic_request_detected"
                and infer_feature_from_question(question) is None
            ):
                return RequestPolicyDecision(
                    disposition=RequestDisposition.ALLOW,
                    category=RequestCategory.IN_SCOPE,
                    reason_code="ambiguous_feature_request",
                )
            return deterministic

        return model_decision

    def _classifier_failure_fallback(
        self, question: str, deterministic: RequestPolicyDecision
    ) -> RequestPolicyDecision:
        """Use a matching deterministic refusal, otherwise fail closed."""

        if deterministic.disposition == RequestDisposition.REFUSE:
            return deterministic
        scope_reason = request_scope_rejection(question)
        if scope_reason:
            return RequestPolicyDecision(
                disposition=RequestDisposition.ALLOW,
                category=RequestCategory.IN_SCOPE,
                reason_code=scope_reason,
            )
        return RequestPolicyDecision(
            disposition=RequestDisposition.REFUSE,
            category=RequestCategory.OFF_TOPIC,
            reason_code="off_topic_request_detected",
            support_line=True,
        )

    def _route_uncertain_request(
        self, question: str, decision: RequestPolicyDecision
    ) -> RequestPolicyDecision:
        if decision.category == RequestCategory.IN_SCOPE:
            # The deterministic classifier already selected the in-scope
            # route. Feature validation remains deterministic at preflight;
            # the category model cannot replace a named route with a refusal.
            return decision
        if decision.category != RequestCategory.OFF_TOPIC or self.category_router is None:
            return decision
        label = self.category_router.route(question)
        if label is None:
            return decision
        routed = self._decision_from_router_label(question, decision, label)
        # Policy 0.5.1: when a specific refusal or information rule matched
        # (anything but the generic off-topic fallback), the router may swap
        # it only for another refusal or the crisis route, never for feature
        # clarification, a time-window message or an answer.
        if (
            routed.disposition == RequestDisposition.ALLOW
            and decision.reason_code != "off_topic_request_detected"
        ):
            return decision
        return routed

    @staticmethod
    def _decision_from_router_label(
        question: str,
        rule_decision: RequestPolicyDecision,
        label: RouterLabel,
    ) -> RequestPolicyDecision:
        if label == RouterLabel.CRISIS:
            return RequestPolicyDecision(
                disposition=RequestDisposition.CRISIS,
                category=RequestCategory.CRISIS_SELF_HARM,
                reason_code="category_router_crisis",
            )

        refusal_routes = {
            RouterLabel.INJECTION: (
                RequestCategory.PROMPT_INJECTION, "category_router_injection"
            ),
            RouterLabel.SENSITIVE: (
                RequestCategory.SENSITIVE_DATA_REQUEST, "category_router_sensitive"
            ),
            RouterLabel.DIAGNOSIS: (
                RequestCategory.DIAGNOSIS_SEEKING, "category_router_diagnosis"
            ),
            RouterLabel.TREATMENT: (
                RequestCategory.TREATMENT_ADVICE_SEEKING, "category_router_treatment"
            ),
            RouterLabel.RISK: (
                RequestCategory.RISK_PREDICTION_SEEKING, "category_router_risk"
            ),
            RouterLabel.CAUSE: (
                RequestCategory.CAUSAL_INFERENCE_SEEKING, "category_router_cause"
            ),
            RouterLabel.CLINICAL_SCORE: (
                RequestCategory.CLINICAL_SCORE_REQUEST,
                "category_router_clinical_score",
            ),
            RouterLabel.CAPABILITY: (
                RequestCategory.CAPABILITY_QUESTION, "capability_question_detected"
            ),
            # Policy 0.5.1: the matching app-information text, else the
            # general description of what MindSense uses, never a text about
            # a different app topic.
            RouterLabel.APP_INFO: (
                RequestCategory.APP_INFORMATION,
                app_information_reason(question) or "app_info_data_use",
            ),
        }
        route_priorities = {
            RequestCategory.PROMPT_INJECTION: 1,
            RequestCategory.SENSITIVE_DATA_REQUEST: 2,
            RequestCategory.DIAGNOSIS_SEEKING: 3,
            RequestCategory.TREATMENT_ADVICE_SEEKING: 4,
            RequestCategory.RISK_PREDICTION_SEEKING: 5,
            RequestCategory.CAUSAL_INFERENCE_SEEKING: 6,
            RequestCategory.CLINICAL_SCORE_REQUEST: 7,
            RequestCategory.CAPABILITY_QUESTION: 8,
            RequestCategory.APP_INFORMATION: 8,
            RequestCategory.OFF_TOPIC: 8,
        }
        if label in refusal_routes:
            category, reason = refusal_routes[label]
            candidate = RequestPolicyDecision(
                disposition=RequestDisposition.REFUSE,
                category=category,
                reason_code=reason,
                support_line=True,
            )
            if rule_decision.disposition == RequestDisposition.REFUSE:
                current_priority = route_priorities.get(rule_decision.category, 8)
                candidate_priority = route_priorities.get(candidate.category, 8)
                if current_priority < candidate_priority:
                    return rule_decision
            return candidate

        if label == RouterLabel.TIME_WINDOW:
            return RequestPolicyDecision(
                disposition=RequestDisposition.ALLOW,
                category=RequestCategory.IN_SCOPE,
                reason_code="unsupported_time_window",
            )
        if label == RouterLabel.FEATURE_UNCLEAR:
            return RequestPolicyDecision(
                disposition=RequestDisposition.ALLOW,
                category=RequestCategory.IN_SCOPE,
                reason_code="ambiguous_feature_request",
            )
        if label == RouterLabel.UNTRACKED:
            return RequestPolicyDecision(
                disposition=RequestDisposition.REFUSE,
                category=RequestCategory.OFF_TOPIC,
                reason_code="untracked_measure_request",
                support_line=True,
            )
        if label == RouterLabel.OFF_TOPIC:
            return RequestPolicyDecision(
                disposition=RequestDisposition.REFUSE,
                category=RequestCategory.OFF_TOPIC,
                reason_code="off_topic_request_detected",
                support_line=True,
            )

        expected_feature = (
            "gps_distance"
            if label == RouterLabel.IN_SCOPE_GPS
            else "unlock_count"
            if label == RouterLabel.IN_SCOPE_UNLOCKS
            else None
        )
        if expected_feature is not None:
            inferred_feature = infer_feature_from_question(question)
            if inferred_feature != expected_feature:
                return RequestPolicyDecision(
                    disposition=RequestDisposition.ALLOW,
                    category=RequestCategory.IN_SCOPE,
                    reason_code=(
                        "ambiguous_feature_request"
                        if inferred_feature is None
                        else "feature_request_mismatch"
                    ),
                )
            scope_reason = request_scope_rejection(question)
            if scope_reason:
                return RequestPolicyDecision(
                    disposition=RequestDisposition.ALLOW,
                    category=RequestCategory.IN_SCOPE,
                    reason_code=scope_reason,
                )
            return RequestPolicyDecision(
                disposition=RequestDisposition.ALLOW,
                category=RequestCategory.IN_SCOPE,
            )
        return rule_decision

    @staticmethod
    def _scope_rejection(
        question: str,
        decision: RequestPolicyDecision,
        *,
        feature_id: str | None = None,
        require_feature: bool = False,
    ) -> str | None:
        if decision.reason_code in {
            "unsupported_time_window",
            "ambiguous_feature_request",
            "feature_request_mismatch",
        }:
            return decision.reason_code
        return request_scope_rejection(
            question, feature_id=feature_id, require_feature=require_feature
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

        if contains_prohibited_assertion(template.manifest.text):
            # Same phrase gate as a model draft: an answer-mode template with
            # causal or clinical wording falls back instead of reaching the user.
            return self._fallback(
                str(PROHIBITED_PHRASE_DETECTED),
                request_decision=decision,
                model_invoked=False,
            )
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
