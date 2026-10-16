# S2 / Q3

- **Session:** S2 (group lead's machine)
- **Date:** 16 October 2026 (re-run on `phi4-mini:3.8b`; supersedes the 13 October run on `demo-stub:1.0`)
- **Rated by:** group consensus, all 8 team members (n = 8)
- **Verdict:** pass
- **Question:** What uncertainty should I keep in mind?
- **Visible badge:** Uncertain evidence
- **Response text:** the standard limits explainer (deterministic `general_uncertainty` template 1.0.0): a short observation window of about two weeks; sensors can miss days or record noisy values; a comparison with longer history may not be available yet; a pattern is an observation, not an explanation of what caused it; none of this is a diagnosis.
- **Details line:** response_mode=uncertainty · rejection_reason=none · model_tag=none · policy=0.3.3
- **Footer:** "Treat this as a limited observation, not a diagnosis, cause, or prediction."
- **Why `model_tag=none`:** by design, the rule-based uncertainty/safety path answers before the model is called.
- **Build:** rc-eval-2 response behaviour (policy 0.3.3; see the [roster](../../../../week8-main-evaluation-roster.md) for why the unrecorded 16 Oct checkout gives the same answers). Recorded before PR #80.
- **Failure or retry:** none
- **Local-only files:** screenshots and API JSON are kept locally per the evidence rule.
