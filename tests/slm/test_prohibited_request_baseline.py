from benchmarks.slm_prohibited_request_baseline import load_cases, run_baseline


def test_public_development_fixture_covers_all_high_severity_categories():
    cases = load_cases()

    assert {case["category"] for case in cases} == {
        "crisis_self_harm",
        "diagnosis_seeking",
        "causal_inference_seeking",
        "treatment_advice_seeking",
        "risk_prediction_seeking",
        "prompt_injection",
        "sensitive_data_request",
    }
    assert len({case["case_id"] for case in cases}) == len(cases)


def test_week5_prohibited_request_baseline_meets_preregistered_threshold():
    result = run_baseline()

    assert result["scope"] == "provisional_public_development_subset_not_held_out"
    assert result["data_classification"] == "synthetic_prompts_and_fixture_only"
    assert result["summary"] == {
        "total": 16,
        "passed": 16,
        "failed": 0,
        "pass_rate": 1.0,
        "meets_threshold": True,
        "unexpected_model_calls": 0,
    }
