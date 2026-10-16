"""Machine-readable `PersonalBaseline.ineligible_reason` values shared by the
statistics side (`backend.statistics.participant_evidence`) and the output
grammar (`backend.slm.output_grounding`).

Added 2026-10-16 when the bootstrap intersection result was connected to
`/respond`. A `PARTIAL_DESCRIPTIVE_ONLY` packet used to mean only "too early
to compare" (State B). A State C participant (history long enough for a
comparison) whose comparison cannot be reported is also sent as
`PARTIAL_DESCRIPTIVE_ONLY`, because the frozen contract allows a baseline
value only on an `ELIGIBLE` packet that carries `StatisticalEvidence`
(`backend/slm/response_health.py`). These values tell the output grammar
which accurate sentence applies. Any other reason (State A/B) keeps the
"too early to compare" sentence.

This module adds string constants only; the `EvidencePacket` schema
(`backend/contracts/evidence.py`, contract 1.0.0) is unchanged.
"""

# State C, comparison computable, but the per-person evidence is `no_claim`
# under the bootstrap intersection, or the evidence table is unavailable
# (missing, stale, unreadable or wrongly permissioned cache): fail closed.
STATE_C_EVIDENCE_NOT_REPORTABLE = "state_c_history_sufficient_evidence_not_reportable"

# State C, but the recent-vs-baseline deviation is undefined this occasion:
# fewer than 7 valid days in the 14-day recent window, or a baseline window
# without a non-zero standard deviation (preregistration section 5.1).
STATE_C_TOO_FEW_RECORDED_DAYS = "state_c_history_sufficient_too_few_recorded_days"

STATE_C_REASONS = frozenset({STATE_C_EVIDENCE_NOT_REPORTABLE, STATE_C_TOO_FEW_RECORDED_DAYS})
