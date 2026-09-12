# Data Pipeline Proposal Report

**Owner:** Honghao Li  
**Role:** Data Pipeline Lead

## 1. Problem Addressed

The data pipeline addresses the challenge of converting longitudinal smartphone sensing data into reliable and interpretable behavioural features that can be used by the statistical analysis and subsequently by the local SLM.

The primary dataset is the College Experience Study (CES), which contains repeated smartphone sensing measurements and PHQ-4 wellbeing outcomes. A key challenge is that the sensing data contain missing observations, extreme values, varying participant coverage, and potential platform differences. Therefore, the raw sensing fields cannot be used directly without validation and cleaning.

## 2. Proposed Method and Workflow

The proposed data pipeline consists of two main stages.

First, a scripted data-contract validation checks participant coverage, minimum observation days, repeated PHQ-4 measurements, required sensing fields, and Tier-1 feature availability.

Second, the pipeline cleans and processes the three final Tier-1 behavioural features agreed with the Statistical Analysis Lead:

- GPS distance travelled (`loc_dist_ep_0`)
- Home duration (`loc_home_dur`)
- Phone unlock frequency (`unlock_num_ep_0`)

The cleaned daily features are aggregated into 14-day windows preceding each PHQ-4 assessment, excluding the assessment day. Each FeatureWindow records the feature value, observed and expected days, coverage ratio, platform, and quality flags.

## 3. Work Completed

The CES data-contract validation and the Tier-1 feature pipeline have been implemented.

The validation script verifies the real CES dataset against the project requirements, including participant coverage, longitudinal sensing duration, repeated PHQ-4 measurements, and availability of the three final Tier-1 fields.

Cleaning and processing logic has also been implemented for GPS distance, home duration, and unlock frequency. The pipeline can generate FeatureWindow records suitable for downstream statistical analysis while preserving coverage and data-quality information.

## 4. Work in Progress / Planned

The next stage is downstream integration with the statistical analysis and SLM components.

Further work will focus on ensuring that the generated FeatureWindow representation is consumed consistently by downstream components and continuing to validate feature semantics, participant coverage, and missing-data behaviour during integration.

## 5. Confirmed Results and Test Outcomes

Validation of the real CES dataset identified 220 sensing participants. Of these, 214 satisfy the current source-data contract requiring at least 30 sensing observation days, at least two PHQ-4 measurements, and at least 30 valid days for all three final Tier-1 fields.

GPS distance required the most substantial cleaning. Approximately 20.1% of raw `loc_dist_ep_0` observations are missing. Location data are restricted to records with at least 12 hours of location quality coverage, values above 500 km/day are treated as invalid, and per-participant P1–P99 winsorisation is applied.

Sensitivity checks using 250 km, 500 km, and 1000 km daily GPS cut-offs produced consistent substantive statistical conclusions.

The completed Tier-1 pipeline generates 106,044 FeatureWindow records across the three Tier-1 features. The current automated data-pipeline test suite passes all 11 tests.

## 6. Key Risks and Limitations

The main limitations include substantial GPS missingness, extreme location values, differences in sensing behaviour or availability across mobile platforms, and varying longitudinal coverage between participants.

The pipeline must also distinguish genuine zero values from missing or platform-unsupported measurements. In addition, PHQ-4 is a wellbeing/mental-health screening measure rather than a diagnostic outcome, so downstream interpretations should avoid unsupported diagnostic or causal claims.

## 7. GitHub Evidence

Relevant implementation, validation, testing, and documentation files include:

- `scripts/validate_ces.py`
- `scripts/build_gps_feature.py`
- `tests/data_pipeline/test_ces_contract.py`
- `tests/data_pipeline/test_tier1_features.py`
- `docs/data-pipeline/dataset_validation_CES.md`
- `docs/data-pipeline/gps_feature_pipeline.md`
- `docs/data-pipeline/tier1_feature_pipeline.md`

## 8. References

Nepal, S., Liu, W., Pillai, A., Wang, W., Vojdanovski, V., Huckins, J. F., Rogers, C., Meyer, M. L., & Campbell, A. T. (2024). Capturing the college experience: A four-year mobile sensing study of mental health, resilience, and behavior of college students during the pandemic. Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies, 8(1), Article 38. https://doi.org/10.1145/3643501
Wang, R., Chen, F., Chen, Z., Li, T., Harari, G. M., Tignor, S., Zhou, X., Ben-Zeev, D., & Campbell, A. T. (2014). StudentLife: Assessing mental health, academic performance and behavioral trends of college students using smartphones. In Proceedings of the 2014 ACM International Joint Conference on Pervasive and Ubiquitous Computing (pp. 3–14). ACM. https://doi.org/10.1145/2632048.2632054