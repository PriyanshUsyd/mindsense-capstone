CES Dataset Validation Report

## 1. Purpose

The College Experience Study (CES) dataset was re-verified against the local copy stored in `dataset/ces/` to determine whether it satisfies the data requirements of the MindSense project.

The validation was performed using the scripted check in `scripts/validate_ces.py` rather than relying solely on the dataset documentation.

The validation focused on three main requirements:

* participant coverage;
* repeated PHQ-4 wellbeing measurements; and
* completeness of candidate Tier-1 behavioural features.

Longitudinal sensing coverage and the final eligible participant cohort were also checked to determine whether sufficient data are available for downstream behavioural–wellbeing analysis.

---

## 2. Participant Coverage

The local CES copy contains:

* **220 participants** in the EMA data;
* **220 participants** in the sensing data;
* **218 participants** with at least one valid PHQ-4 measurement; and
* **218 participants** with both sensing data and PHQ-4 data.

This provides a large matched cohort for linking smartphone-derived behavioural features with longitudinal wellbeing measurements.

**Result: PASS**

---

## 3. PHQ-4 Repeat Density

PHQ-4 was selected as the candidate longitudinal wellbeing outcome.

The scripted validation found:

| PHQ-4 coverage           | Participants |
| ------------------------ | -----------: |
| At least 1 measurement   |          218 |
| At least 2 measurements  |          217 |
| At least 5 measurements  |          217 |
| At least 10 measurements |          215 |

Across participants with valid PHQ-4 data:

* **Minimum:** 1 measurement
* **Median:** 169.5 measurements
* **Mean:** 162.1 measurements
* **Maximum:** 441 measurements

Therefore, PHQ-4 is repeatedly measured for almost all participants rather than being available only as a single cross-sectional assessment. This supports the longitudinal requirements of the project.

**Result: PASS**

---

## 4. Longitudinal Sensing Coverage

The sensing dataset contains **220 participants**.

Observation-day coverage was:

| Minimum sensing coverage | Participants |
| ------------------------ | -----------: |
| ≥ 7 days                 |    217 / 220 |
| ≥ 14 days                |    217 / 220 |
| ≥ 30 days                |    217 / 220 |

The median sensing coverage was **1,143.5 observation days per participant**, with a mean of **982.1 days** and a range of **2–1,370 days**.

For the current contract check, **30 sensing days** was used as a conservative minimum threshold for identifying participants with sufficient longitudinal sensing coverage.

**Result: PASS**

---

## 5. Candidate Tier-1 Feature Mapping

The CES sensing data contains **651 columns**. Candidate behavioural features were mapped to the project requirements using the CES daily sensing data dictionary.

The current candidate Tier-1 set is:

| Behavioural concept | CES field              | Interpretation                              |
| ------------------- | ---------------------- | ------------------------------------------- |
| Mobility            | `loc_dist_ep_0`        | Full-day distance travelled                 |
| Device engagement   | `unlock_duration_ep_0` | Full-day duration of unlocked phone use     |
| Unlock frequency    | `unlock_num_ep_0`      | Full-day number of phone lock/unlock events |

The `ep_0` fields represent full-day aggregates and are therefore suitable for alignment with daily longitudinal wellbeing observations.

Physical inactivity (`act_still_ep_0`) was also examined as an alternative candidate feature.

---

## 6. Feature Completeness

### Mobility — `loc_dist_ep_0`

* Non-null rows: **172,565 / 216,065 (79.9%)**
* Missing rate: **20.1%**
* Participant coverage: **218 / 220 (99.1%)**
* Median valid observation days: **805.0**
* Participants with ≥30 valid days: **214 / 220**

Although mobility contains noticeable row-level missingness, participant-level and longitudinal coverage remain high.

### Device Engagement — `unlock_duration_ep_0`

* Non-null rows: **216,065 / 216,065 (100.0%)**
* Missing rate: **0.0%**
* Participant coverage: **220 / 220 (100.0%)**
* Median valid observation days: **1,143.5**
* Participants with ≥30 valid days: **217 / 220**

### Unlock Frequency — `unlock_num_ep_0`

* Non-null rows: **216,065 / 216,065 (100.0%)**
* Missing rate: **0.0%**
* Participant coverage: **220 / 220 (100.0%)**
* Median valid observation days: **1,143.5**
* Participants with ≥30 valid days: **217 / 220**

### Alternative: Physical Inactivity — `act_still_ep_0`

* Non-null rows: **216,065 / 216,065 (100.0%)**
* Missing rate: **0.0%**
* Participant coverage: **220 / 220 (100.0%)**
* Median valid observation days: **1,143.5**
* Participants with ≥30 valid days: **217 / 220**

Overall, the candidate behavioural features provide sufficient participant and longitudinal coverage for downstream analysis.

**Result: PASS**

---

## 7. Eligible Participant Cohort

For the current validation, a participant was considered eligible for downstream analysis when all of the following conditions were satisfied:

1. at least **30 sensing observation days**;
2. at least **2 valid PHQ-4 measurements**;
3. at least **30 valid days of `loc_dist_ep_0`**;
4. at least **30 valid days of `unlock_duration_ep_0`**; and
5. at least **30 valid days of `unlock_num_ep_0`**.

The validation produced:

* Participants with ≥30 sensing days: **217**
* Participants with ≥2 PHQ-4 measurements: **217**
* Participants with ≥30 valid mobility days: **214**
* Participants with ≥30 valid device-engagement days: **217**
* Participants with ≥30 valid unlock-frequency days: **217**
* Participants satisfying the Tier-1 feature requirements: **214**

After taking the intersection of all requirements:

> **214 / 220 participants (97.3%) satisfy the current eligibility contract.**

This provides a sufficiently large cohort for downstream longitudinal behavioural–wellbeing analysis.

**Result: PASS**

---

## 8. Known Limitations

The validation identified several issues that should be considered in later pipeline development.

First, daily mobility (`loc_dist_ep_0`) has **20.1% row-level missingness**. This does not prevent its use because 214 participants still have at least 30 valid mobility observation days, but an explicit missing-data policy will be required.

Second, several aggregated sensing variables, including unlock frequency and unlock duration, contain no null values in the aggregated sensing table. A non-null value does not necessarily guarantee valid sensor coverage. In particular, zero-valued observations should be checked against the CES preprocessing conventions before being interpreted as genuine zero behaviour.

Finally, the current Tier-1 set is a candidate feature set for contract validation. Final Tier-1 selection may be refined jointly with the statistical analysis requirements.

---

## 9. Final Decision

**Overall contract result: PASS**

The real CES copy satisfies the current dataset contract for participant coverage, repeated wellbeing measurement, longitudinal sensing coverage, and candidate Tier-1 feature completeness.

**CES is therefore suitable to be locked as the primary dataset for the MindSense project.**

Under the current eligibility criteria, **214 of 220 participants (97.3%)** are available for downstream analysis.

The main identified data-quality issue is the **20.1% row-level missingness in daily mobility**, which should be handled explicitly during pipeline development rather than treated as a reason to reject the dataset.
