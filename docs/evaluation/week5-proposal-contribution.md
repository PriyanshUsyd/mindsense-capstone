# Evaluation Proposal Contribution

Chonghao Shen | 4 September 2026

The Evaluation component addresses whether MindSense communicates personal behavioural and wellbeing evidence accurately, understandably and safely. The central risk is not only an incorrect number, but also a response that overstates limited evidence, treats association as causation, makes a mental-health diagnosis, or hides uncertainty. The evaluation therefore tests both response quality and deterministic safety behaviour. The College Experience Study provides the longitudinal mobile-sensing context (Nepal et al., 2024), while PHQ-4 is treated as a validated screening measure rather than a diagnostic result (Kroenke et al., 2009).

The workflow combines a public synthetic development suite, pre-registered thresholds and a sealed held-out set reserved until Week 11. Each executable response is rated Pass/Fail against evidence faithfulness, personal-baseline interpretation, wellbeing boundaries, association-versus-causation language, uncertainty, correct response routing and prohibited disclosure. High-severity guardrail cases must achieve 100%; standard cases retain the locked 90% threshold. Human evaluation later maps directly to the client's ten criteria, including comprehensibility, usefulness, personal relevance, trust, usability and privacy perceptions.

Completed work includes Evaluation Plan v0.1, the response-quality rubric, approval of the Week 5 public case mapping, and an independent review of the recorded `phi4-mini:3.8b` Prompt 0.4.8 responses. All six currently executable source-plan questions passed. Fourteen high-severity guardrail cases and two separate privacy-extension cases also passed, with no critical failure observed. The complete branch test suite recorded 268 passes and eight environment/data-dependent skips.

Two source questions remain explicitly not covered: longitudinal PHQ-4 change and behavioural-PHQ-4 association interpretation. The current evidence contract cannot yet represent those inputs, so they were neither fabricated nor counted as passes or failures. Current results use fixed synthetic cases and do not establish general paraphrase coverage, clinical safety, human usefulness or held-out performance. Joint comparison with a second independent reviewer also remains outstanding. Next work will finalise the ten-dimension participant rubric, evaluation data-source decision and one-page session runbook before piloting.

## Evidence paths

- [Evaluation Plan v0.1](../../backend/evaluation/evaluation_plan_v0.1.md)
- [Response Quality Rubric v0.1](response-quality-rubric-v0.1.md)
- [Week 5 Public Development Review](week5-development-review.md)
- [Public Evaluation Mapping](../../benchmarks/fixtures/week5_evaluation_alignment.json)
- [Evaluation Regression Tests](../../tests/evaluation/test_week5_review.py)

## References

- Kroenke, K., Spitzer, R. L., Williams, J. B. W., & Löwe, B. (2009). An ultra-brief screening scale for anxiety and depression: The PHQ-4. *Psychosomatics, 50*(6), 613-621. [https://doi.org/10.1176/appi.psy.50.6.613](https://doi.org/10.1176/appi.psy.50.6.613)
- Nepal, S., Liu, W., Pillai, A., Wang, W., Vojdanovski, V., Huckins, J. F., Rogers, C., Meyer, M. L., & Campbell, A. T. (2024). Capturing the college experience: A four-year mobile sensing study of mental health, resilience and behavior of college students during the pandemic. *Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies, 8*(1), Article 38. [https://doi.org/10.1145/3643501](https://doi.org/10.1145/3643501)

AI assistance: contribution drafting and reference formatting; evaluation decisions, repository evidence and test outcomes were reviewed against the versioned project artifacts.
