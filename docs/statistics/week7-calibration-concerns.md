# Week 7 calibration concerns (logged for Week 8)

**Owner:** Moe Tanaka, Statistical Analysis Lead
**Written:** 2026-09-20
**Revised:** 2026-09-20, after reading `main` at `a376715` (see item 1)
**Status:** primarily a record — as written on 2026-09-20 no code, spec or document outside this file was changed. **Exception: item 8 was resolved in Week 8 (2026-09-27)**, which did change code, tests and documents (see its Resolution).

**Tense note.** The "Observed" paragraphs describe the state of the repository on 2026-09-20 and are kept as written; they are not updated when an item is later resolved. Where an item has a "Resolution", read the Observed text as the old state (e.g. item 8's `reclassify_family213`, `bh_q_213` and `EXPECTED_FAMILY_SIZE = 213` no longer exist in that form).

## Scope of this document

`Weekly_Plan.md`, Week 7 (Pilot), Statistical Analysis Lead:

> Support the pilot; log calibration concerns for Week 8, no live changes.

The Week 7 pilot has already taken place: a lightweight remote rostered-pair session on 2026-09-20 (`docs/evaluation/week7-rostered-pair-pilot-main.md`). This document records what was observed on the statistics side during Week 7, so that it is available for Week 8. It is not a pre-pilot hand-over.

**This document is a record, not a change request.** Every item below is something observed during Week 7 that needs a decision or work in Week 8 or later. Nothing here modifies the frozen build. "Week 8" entries are proposals for the owner's decision, not commitments.

## Summary

| # | Item | Status |
|---|---|---|
| 1 | The evidence-derivation path was not wired into `/respond` | **Superseded** by `11df143` (2026-09-16) |
| 2 | Per-person standard errors are not in the production path | Cache implemented 2026-10-07 (runner only); B=500 rebuild and `/respond` wiring open |
| 3 | B=500 results vs. the current primary specification | **CLOSED** |
| 4 | B=500 results were only in a temporary scratchpad | Mitigated; storage location open |
| 5 | Participant sets differ between the two Tier-1 features | Open |
| 6 | The lowest-qualifying-state rule has no implementation | Open |
| 7 | Preregistration §1.4 fixed-effects formula does not match the implementation | Open — high priority |
| 8 | BH-FDR family size: labelling vs. what is computed | **Resolved** (2026-09-27) |

---

## 1. The evidence-derivation path was not wired into `/respond` — SUPERSEDED

**Superseded by commit `11df143` (2026-09-16, "Wire real evidence pipeline into /respond — remove hardcoded demo packet").** The first version of this item described the situation before that commit. It was written from a working tree at `31919b3` (2026-09-15) and was not re-checked against `main`, which already contained `11df143`. What is true on `main` now:

- `/respond` takes a `participant_id` (and optionally `feature_id`) and builds the `EvidencePacket` server-side with `participant_evidence.build_evidence_packet`. It no longer accepts a client-supplied packet.
- `classify_state` is called from `backend/statistics/participant_evidence.py:327`, on real CES pipeline output.
- The client cannot assert `eligibility_status` or `evidence_strength`. The frontend (`NormalResponse.tsx`) sends only a participant id; the hard-coded `EXAMPLE_ELIGIBLE_GPS_PACKET` (`'eligible'` / `'moderate'`) is gone.
- Since `e58012e` (2026-09-20) the feature is inferred from the question text (`request_policy.infer_feature_from_question`) instead of being fixed to `gps_distance`.

What remains open on the statistics side is item 2 (the bootstrap SE is not in this path), which now also carries the consequences for the pilot.

---

## 2. Per-person standard errors are not in the production path

**Observed.**
- `backend/statistics/tier1_runner.py` runs cleaning → model frame → mixed-effects fit → AR(1) fit → per-person point estimates → classification, and stops there. `slope_se` / `slope_p` are `None`, so `reclassify_family213` labels **every** participant `insufficient` (→ `no_claim`). This is the intended fail-safe (module docstring of `evidence.py`), not a bug.
- `backend/statistics/bootstrap.py` exists (parametric + cluster, B=500 each) and `evidence.build_person_slopes_from_bootstrap_se` / `intersect_bootstrap_evidence` can consume it, but `tier1_runner` does not call any of it. The docstring calls this "a deliberate extension point, not an oversight".
- **The request path has the same gap.** `participant_evidence.build_evidence_packet` (the code `/respond` now calls, item 1) uses `extract_person_slopes` + `reclassify_family213` with `slope_se=None`, so `evidence_strength` resolves to `insufficient` (→ `no_claim`) for every participant regardless of their fitted slope. Its module docstring names this as the follow-up: wiring the real intersection result in "needs a precomputed/cached per-participant table".
- The only real bootstrap run is the 2026-09-13 B=500 run on GPS distance: 23 of 214 participants `evidence_available` under the cross-method intersection (item 3, item 4). **That result is not reflected in any `/respond` response.** `unlock_num_ep_0` has no bootstrap SE at all (Week 5 §3.9: all 216 `insufficient`).
- Where a State C participant has no defensible per-person evidence, `participant_evidence.py` demotes the packet to `PARTIAL_DESCRIPTIVE_ONLY` (no baseline value shown), because `response_health.py` rejects `ELIGIBLE` without real `StatisticalEvidence` (`eligible_evidence_missing`). Under the current gap this applies to every State C participant. The code comments flag it for SLM review.

**Why.** `nlme` has no per-person conditional-variance extraction and `simulate.lme` refuses models with a `corStruct`, so the SE had to come from bootstrapping. That costs about 30–40 minutes per feature per method on the real dataset (`tier1_runner` docstring), which is too expensive to run inside a routine pipeline invocation or lazily inside a request.

**Consequence.**
- Any path that goes through `tier1_runner` or `/respond` alone will claim nothing at the per-person level. Real labels require running the bootstrap separately and feeding it in, per feature.
- **What the 2026-09-20 pilot could and could not exercise.** The pilot ran the real request path on the local de-identified CES dataset (`phi4-mini:3.8b`, build `b524f33`; Q1 unlock routing pass, Q2 three-day window fail, Q3 diagnosis refusal pass). It exercised state classification, feature routing and the safety behaviour. It could not exercise a response for a participant whose per-person evidence is `evidence_available` (a hedged relationship claim), because the path produces none. The frontend on `main` sends one fixed demo participant id, so sessions are answered for that participant (not checked against how the pilot build was configured).
- The Week 5 share of `C + no_claim` (64.1% of State C occasions, Appendix B) comes from the archived `analysis/` pipeline's labels (64 `evidence_available` / 149 `no_claim` of 213 participants, Week 5 §3.7). Under the current request path the share is effectively 100% of State C (everyone `insufficient`). Under the bootstrap-based labels it is unknown, and likely higher than 64% since 23 < 64. These three sources have not been reconciled.

**Relationship to `docs/statistics/bootstrap-caching-design.md`.** That document was written by Priyansh Khandelwal on 2026-09-20, transcribing what Moe Tanaka relayed over WhatsApp, and says so itself. It lists four things to settle in Week 7 (where the cached output lives; how `tier1_runner` reads it without triggering a live run; what invalidates it; whether a stale cache fails closed or warns) and states that none of them had been answered. **Decisions a–d below are the confirmed answers to those four points**, in a different order: (1) → a, (2) → d, (3) → b, (4) → c. The two documents do not conflict: one is the agenda, the other the answers. (They do disagree on where 23/214 came from and on whether a rerun is needed — see item 3.)

**Week 8.** Owner: Moe Tanaka. Design in Week 7; implementation in Week 8. Caching design decisions a–d are finalised. *(Implemented 2026-10-07 on branch `moe-week9-bootstrap-cache` — see "Implementation status" at the end of this item; the text of a–d below is the design as decided, with the changes made at implementation listed there.)*

**a. Storage and format — a-1.** Separate the raw checkpoint from the aggregated per-person SE.
- The raw checkpoint (JSON Lines, every iteration) stays under `outputs/` (gitignored). It is heavy and contains per-person BLUPs.
- The cache is stored separately and holds two things: the aggregated per-person SE (`uid`, `method`, `slope_se`, `n_occasions`) and the final `intersect_bootstrap_evidence` table.
- **Where the cache lives is on hold.** It should be tracked, but it contains participant `uid`, so it needs Yuktha Naveen's privacy review before a location is chosen. Until then nothing is to be committed (see item 4).

**b. Invalidation — fingerprint.** The conditions that make a cache stale are gathered into one dictionary and hashed with SHA-256:
- `feature` (`spec.name`)
- `transform_name`
- `master_seed`
- `n_iterations` (B)
- `engine` (R / python fallback)
- `git_commit` (HEAD for `backend/statistics/`; a dirty tree counts as `None` and invalidates immediately)

The cache stores its fingerprint, and it is valid only if the recomputed fingerprint matches. Collapsing many fields into one hash, rather than comparing them one by one, is deliberate: it prevents a field that someone forgot to add to the comparison from silently failing to invalidate.

*Two consequences of including `git_commit`, to settle at implementation time:*
- The 2026-09-13 B=500 run was executed from an uncommitted working tree, so under this scheme it produces no valid cache entry. Either rerun it under the final design, or grandfather it with the fingerprint recorded manually from the archive README.
- Keying on the last commit touching `backend/statistics/` means a change that does not affect the estimate invalidates a 30–40 minute result. `31919b3` (which removed an unused duplicate function and its tests from `evidence.py`, outside the production path) would have done exactly that. Narrowing the key to files that actually affect the estimate is worth considering, at the cost of a more complex and more error-prone rule.

**c. Missing vs. stale cache — two-stage.**
- **No cache** → continue with `insufficient` for everyone. The B=500 bootstrap is never started on its own.
- **Fingerprint mismatch** → stop with an exception.

"Missing" and "stale" must not be treated alike. If they were, an old environment with a forgotten leftover cache would quietly fall back to `insufficient`, and nobody would notice that a cache which should have been usable had in fact been invalidated.

When the runner stops on a fingerprint mismatch, the error must name which key changed, so the reader knows whether to rerun the bootstrap or whether the mismatch is spurious. Failing closed is only useful if the message says what to do next. This requires storing the key dictionary alongside the hash, not just the hash — the fingerprint alone cannot say which entry changed.

**d. How `tier1_runner` reads it — independent per feature.**
- If a cache exists, read it; if not, leave the feature at `insufficient`. Never begin the 30–40 minute computation implicitly.
- Only the feature whose cache fails to load raises; the other feature's processing continues.
- **Correction to how this was first framed:** it was described as matching an existing per-feature exception policy in `run_one_feature`. That policy does not exist yet. `run_one_feature` fits each feature independently, but `tier1_runner.main` calls it in a dict comprehension with no `try`/`except`, so an exception in one feature aborts the whole run and the other feature's result is lost. Per-feature exception handling is new behaviour that decision d requires, not something already in place.

Decisions a–d cover the runner. Reading the cache from `participant_evidence` (the `/respond` path) is not covered by them and needs its own decision.

### Implementation status (2026-10-07)

**Done** (`backend/statistics/bootstrap_cache.py`, `tier1_runner.py`, `bootstrap.prepare_model_frame`; tests in `tests/statistics/test_bootstrap_cache.py`):
- **a.** Raw checkpoint (`raw_checkpoint.jsonl` + `raw_fingerprint.json`) and the aggregated cache (`aggregated_cache.json`: per-person SE rows `uid, method, slope_se, n_occasions, n_bootstrap_draws`, and the `intersect_bootstrap_evidence` table) are separate files under `outputs/bootstrap_cache/<feature>/` (gitignored). This resolves "where the cache lives" for now as the ignored tree, not a tracked location: `docs/privacy/local-demo-privacy-check.md` forbids committing per-person bootstrap rows, so a tracked location is not needed for this cache (the location of the 2026-09-13 archive, item 4, is a separate question and still awaits Yuktha's review). Permissions (**fail-closed**, revised 2026-10-09 at the Privacy & Security Lead's request on PR #49; was best-effort): mode 700/600 on POSIX; on Windows `icacls` with inheritance removed and the current user only. The permissions are then **read back and verified** (`stat` mode; `icacls` output parsed, every ACE must be the current user with Full control) — a successful command is not taken as proof. If they cannot be restricted and verified, `PermissionRestrictionError` is raised and nothing is written (the temp file is restricted before any content is written). An *existing* cache folder is checked too, on load and on resume of a raw checkpoint: if not owner-only, one restriction attempt is made, and a failure raises. `PermissionRestrictionError` is deliberately not a `BootstrapCacheError`. The same helpers (`backend/statistics/private_files.py`, outside the fingerprint) protect `tier1_runner`'s uid-bearing outputs; unlike a stale cache, a permission failure aborts the whole run (design d's "the healthy feature is still written" covers statistical failures only).
- **b.** Fingerprint, key dictionary stored beside the SHA-256. **c.** No aggregated cache → `None` and everyone stays `insufficient`; mismatch → `BootstrapCacheStale` naming the changed keys. **d.** `tier1_runner.main` now catches per feature, writes the other features' output and then raises `Tier1RunFailed`.
- `tier1_runner` reads the cache only; the bootstrap is started only by `python -m backend.statistics.bootstrap_cache <feature>`. **Not wired into `/respond`** (`participant_evidence`), per the scope of this change; that still needs its own decision (above).

**Changes from design a–d:**
1. **`git_commit` is not a key.** Replaced by content hashes: the fingerprint has three layers — (A) a hash of the exact model frame the fit consumes, (B) content hashes of the estimation-path files (`bootstrap.py`, `mixed_effects_model.py`, `r_bridge.py`, `feature_specs.py`, `data_pipeline/{cleaning,gps_distance_feature,unlock_frequency_feature}.py`), (C) environment and configuration. This addresses the second consequence noted under b (a commit that does not touch the estimate no longer invalidates 30–40 minutes of work), and a test walks the real import graph so that a new module on the estimation path fails CI unless it is hashed or listed as excluded with a reason.
2. **Input data and environment were missing from the key.** The b list (feature, transform, seed, B, engine, `git_commit`) could not see a changed dataset (`dataset/` is gitignored), a changed cleaning rule outside `backend/statistics/`, or an R/`nlme`/numpy/scipy/pandas/rpy2 upgrade. Layers A and C add them. Per-file hashes normalise CRLF to LF so a Windows checkout does not invalidate a cache built on LF.
3. **Two-stage key (decision a, made concrete).** The aggregated cache's key is every raw key plus the content hash of `evidence.py` and the classification thresholds (`classify_evidence_strength`, `EXPECTED_FAMILY_SIZE`); a classification-only change invalidates the aggregate, not the raw checkpoint's fingerprint. (`classify_evidence_strength` lives in `mixed_effects_model.py`, which layer B hashes, so a threshold edit still invalidates the raw layer too — conservative, and recorded here rather than hidden.)
4. **Mixing legs on resume.** The 2026-09-13 run was resumed twice and nothing recorded each leg's code state. A raw checkpoint is now appended to only if its sidecar fingerprint equals the current one; a checkpoint with records but no sidecar is refused.
5. **Dirty-tree rule moved to write time.** "Dirty tree counts as `None` and invalidates" became: writing a raw checkpoint or an aggregated cache is refused when a keyed file is modified or untracked (`git status --porcelain`; also refused if git cannot answer). Reading compares hashes only and needs no git: identical content is identical code.

**Stage 1 reproducibility check (2026-10-07, from an uncommitted tree, so not a cache entry):** iterations 0–11 of both methods were rerun on current code (serial, `master_seed=20260913`) and compared with the archived 2026-09-13 records. The real fit matches (214 participants, 28,337 occasions, per-person `slope_i` max abs diff 1e-16). All 24 records match exactly: seeds, `usable`/`error`/fallback flags, cluster `uid_map` and `selection_counts`, and `ar1_phi`, β and every BLUP with max abs diff 0.0 (bit-identical).

**Full B=500 reproducibility check (2026-10-09, GPS `loc_dist_ep_0`):** the real B=500 rebuild was run on committed code (commit `2e46bd7`, R 4.6.1, `nlme` 3.1.169, `master_seed=20260913`; output in `outputs/bootstrap_cache/loc_dist_ep_0/`) and compared read-only with the 2026-09-13 archive. `raw_checkpoint.jsonl` has 1000 records (usable 1000, error 0), joining the archive one-to-one on `(method, iteration_index)`. **All 1000 records are bit-identical** on seed, `usable`/`error`/`used_random_slope`/`fallback_reason`, cluster `uid_map` and `selection_counts`, and `ar1_phi`, β and every BLUP (max abs diff 0.0; no iteration or method deviates). Per-person SE: max abs diff 5e-11 (max relative 1.1e-9 parametric, 6.1e-9 cluster), Spearman 1.0 for both methods; the difference comes from the archive CSVs being rounded to 10 decimal places, not from the fit. `evidence_available` is 23 of 214 under both, with an identical set (symmetric difference 0; `label_parametric` and `label_cluster` also identical). So the 2026-09-13 result is fully reproduced by the committed code, which closes the "bit-identical not verified" caveat; the archive README is updated accordingly.

**Not done / still open:** `unlock_num_ep_0` as a separate B=500 run, and reading the cache from `/respond` (above). The comparison above covers GPS only.

---

## 3. B=500 results vs. the current primary specification — CLOSED

**Observed.** Checked 2026-09-20. The 2026-09-13 B=500 run used the **post-reindex-fix code** and matches the current primary specification on all four points checked:

| Item | 2026-09-13 run | Current | Difference |
|---|---|---|---|
| Transform | `log(mean + 1000)` (log of the window mean, applied once) | `GPS_DISTANCE_SPEC`: `log_transform(1000)` | None in effect |
| Window | 14 days, lag 1, gate ≥ 7 valid days | identical | None |
| `extra_fixed_effects` | none (`x_within`, `x_between`) | none | None |
| Reindex range | extended by EMA dates (fixed) | same | None |

- **Occasions / participants:** 28,337 occasions, 214 participants. `n_occasions` in the archived output sums to 28,337, and rebuilding the GPS model frame with the current code matches all 214 participants' occasion counts exactly.
- **Fallback to intercept-only:** 0/500 for both methods (parametric and cluster), all 1000 records usable, 0 errors.
- **Scope:** GPS distance only. `unlock_num_ep_0` has no bootstrap SE (item 2).
- **Documents:** agree with `Week5_Statistical_Analysis_Deliverable.md` §3.3 and `preregistration.md` §1.1, §1.2, §1.4.1. Commit `4af4d7a` (2026-09-15, "AR(1) as primary") changed only these two documents, no code, so the primary switch did not change the fitted model.

**Why the dates look wrong.** The reindex fix is in commit `7509083`, dated 2026-09-14, but it was already in the working tree on the morning of 2026-09-13, before B=500 launched at 11:48. Evidence: `compare_before_after.py` (2026-09-13 11:19) already called the then-current working tree "AFTER the fix"; the 28,337 count above; the exact per-participant match. `bootstrap.py` was likewise first committed later (`a0c2780`, 2026-09-14) than the run that used it. The commit dates therefore do not reflect what code the run used.

**Discrepancy with `docs/statistics/bootstrap-caching-design.md`.** That document states that the 23/214 intersection "was computed against the `lme4` fit, from before AR(1) became the primary model", that the per-person classification will therefore shift under AR(1), and its Week 8 plan (rerun both bootstrap methods on the AR(1) fit, recompute the intersection) rests on that premise. **The premise is wrong.** `extract_person_slopes` builds `slope_i` from `fit_ar1_effect`, so the BLUPs were `nlme::lme + corAR1` from the start, and both bootstrap estimators refit through the same `nlme` path (`lme4` is only the sensitivity fit). The four-point comparison above found no difference from the current primary specification, and commit `4af4d7a` changed no code.

**Consequence.** The 23/214 result can be quoted as a result under the current primary specification. **No rerun is needed** on the grounds given in `bootstrap-caching-design.md`. Whether to rerun for other reasons (for example decision b's `git_commit` key, item 2) is a separate question.

**Week 8.** No re-verification needed. The AR(1)/`lme4` premise and the resulting rerun step in `bootstrap-caching-design.md` should be corrected at the source; because that document records what was relayed on Moe's behalf, the correction should come from Moe. (Item 7 is a separate, documentation-only issue that this check surfaced.)

---

## 4. B=500 results were only in a temporary scratchpad

**Observed.** The raw checkpoint and everything derived from it (the data behind 23/214) lived only in a session scratchpad under `%LOCALAPPDATA%\Temp\claude\…`, outside the repository and any backup.

Now archived (2026-09-20) to `C:\Users\moetn_fp7yru7\mindsense-bootstrap-archive\` (outside the repository, OneDrive and temp directories), with a README. SHA-256 of every file was compared against the source and matched.

- **Not committed:** the files contain `uid`, pending Yuktha Naveen's privacy review (item 2).
- **Scripts:** copied unmodified. They hard-code the original scratchpad path, so they need path edits to run.
- **Current code:** `build_model_frame` now requires a `feature_spec` argument, so the step4–6 scripts raise `TypeError` against it unless updated.
- **Reproduction:** regenerating from scratch takes about 7 hours (three legs on 2026-09-13, including one OS kill for memory). Same seed and code are expected to reproduce; bit-identical output was not verified.

**Why.** The bootstrap was run from throw-away scripts in a session scratchpad because `tier1_runner` deliberately does not run it (item 2).

**Consequence.** 23/214 is now recoverable, but the archive is a single local copy and cannot be committed as-is. The figure is cited in `evidence.py`, `preregistration.md` §4.1 and `Week5_Statistical_Analysis_Deliverable.md` §5.4 without a pointer to retrievable data.

**Week 8.** Move the data to a tracked location after Yuktha's privacy review; then update the README and fix or replace the scripts' hard-coded paths.

---

## 5. Participant sets differ between the two Tier-1 features

**Observed.** (`preregistration.md` §2.2, from `tier1_runner`, 2026-09-14.) `loc_dist_ep_0`'s model frame has **214** participants and `unlock_num_ep_0`'s has **216**. The GPS set is a strict subset. The 2 extra participants fail GPS's `quality_loc >= 12h` gate almost completely (0/356 and 3/1141 valid-quality days; one has no non-null raw `loc_dist_ep_0` at all) while their unlock coverage is complete (356/356 and 1141/1141), since unlock has no quality field to lose them on.

**Why.** Feature-specific cleaning: GPS has a quality gate, unlock does not.

**Consequence.** For those 2 people the system can say something per-person using unlock but never using GPS. Whether a feature has anything to say about a person is a per-feature question. The multiple-comparison family is also affected: the 213 (now 214, item 8) is specific to GPS distance, and the correct user-facing family is each person's per-feature statements batched together (Week 4 §2), so the family is not simply "213 × 2". With 214 + 216 participants the family definition needs to be settled before a second feature gets real per-person labels.

**Week 8.** Decide the two-feature family definition (per-person batching across features vs. per-feature cohort families) before unlock bootstrap SEs are produced.

---

## 6. The lowest-qualifying-state rule has no implementation

**Observed.** Week 4 §5 specifies that state is evaluated per feature and that the lowest qualifying state across the features in a turn governs that turn's framing; `backend/statistics/eligibility.py` repeats the rule in its docstring. Reading the current code on `main`:
- `classify_state(calendar_days, valid_sensor_days, ema_count)` classifies a **single** feature, and `participant_evidence.build_evidence_packet` calls it once, for one `feature_id` (`participant_evidence.py:327`).
- `request_policy.infer_feature_from_question` returns exactly one feature per request. A question that matches neither feature's keywords, or matches both, falls back to `gps_distance` and logs a warning; it is not answered from both features.
- No code takes several features' states and returns the minimum. A search of `backend/` for such aggregation found only the docstring above.

This was established by reading `participant_evidence.py`, `request_policy.py`, `app.py` and `eligibility.py`; it was not tested by running a two-feature turn.

**Why.** With one Tier-1 feature the rule was vacuous. With two confirmed Tier-1 features (`loc_dist_ep_0`, `unlock_num_ep_0`) it applies to any turn that involves both, but the request path is currently built around one feature per turn.

**Consequence.** A question that spans both features is answered from GPS alone, framed by GPS's state, not by the lower of the two. State itself is computed at runtime (item 1); what is missing is only the aggregation across features.

**Week 8.** Decide together with the request-path owner whether turns may span features. If they may, implement the aggregation; if not, record that the rule is moot by design.

*(The rule is cited from Week 4 §5 and `eligibility.py`. Section 4.4 of `docs/proposal/Group Proposal.md` is "Deployment" and does not contain it.)*

---

## 7. Preregistration §1.4 fixed-effects formula does not match the implementation

**Observed.**
- `preregistration.md` §1.4, "Fixed-effects specification as implemented": `phq4_score ~ x_within_it + x_within_lag1_it + x_between_i + week_in_study_it`, described as "frozen exactly as fitted".
- What `backend/statistics/` fits, and what produced the primary β_W = −0.184 and the B=500 run: `x_within + x_between`. No lag-1 term and no `week_in_study` (`Week5_Statistical_Analysis_Deliverable.md` §3.3: "the confirmatory model here does not carry a lag-1 term"; "has not been re-run with `extra_fixed_effects=["week_in_study"]`").

**Why.** §1.4's formula is the retired `analysis/` pipeline's model (27,530 occasions, §3.2/§3.3). The implementation is not wrong; the document describes a different specification. §1.4.1, which justifies AR(1) as primary, sits directly under §1.4 and refers to "the formula above".

**Consequence.** The preregistration is a frozen document, so this is the highest-priority item here. As written, §1.4 cannot be checked against what was actually run. The lag-1 and `week_in_study` figures in Week 5 §3.3 are explicitly historical and not AR(1)-corrected.

**Week 8.** A decision for the Statistical Analysis Lead, one of: amend §1.4 to state the fitted formula (with the change dated and flagged as post-hoc), or add the two terms to the backend fit and re-run. No change to either is proposed here.

**Statistical Analysis Lead's view: revise §1.4 to match the implementation.**

The lag-1 term is not implemented — `mixed_effects_model.py`'s docstring records it as out of scope, a scope limitation rather than a statistical choice. `week_in_study` is available via `extra_fixed_effects` and is not used in the primary fit; no record states why, only that it isn't.

§1.4 describes the retired `analysis/` pipeline (27,530 occasions). Adding terms to the implementation to match it would change the primary estimate and require rerunning the bootstrap — a larger change than correcting the text, and one made to fit a document rather than for a statistical reason.

**Not decided this week. Flagged as the owner's recommendation.**

---

## 8. BH-FDR family size: labelling vs. what is computed

**Status: Resolved (2026-09-27).** See "Resolution" below.

**Observed.**
1. **Labelling vs. reality.** `reclassify_family213`, `bh_q_213`, `holm_p_213` are hard-coded string literals (`evidence.py`). The family actually corrected is the number of non-NaN p-values (`_nan_safe_correction`), which is 214 in B=500 (no participant excluded, every participant has a defined p-value). `preregistration.md` §2.2 defines the family as "the participants who have a per-person slope for this feature" and calls the number data-dependent, so 214 conforms to the definition; only the label "213" is stale. "23/214" matches what was computed.
2. **`EXPECTED_FAMILY_SIZE = 213` (`evidence.py:123`) is not used in any logic.** The only reference is a test asserting the constant equals 213. It is never compared with the real family size, so drift produces no warning, despite the comment saying it should be "visibly worth a second look".
3. **Origin of 213 and non-reproducibility.** 213 comes from `MIN_OCCASIONS_PER_PERSON = 3` in `analysis/archive/evidence_model.py` (applied at line 61), not ported to `backend/` (consistent with `preregistration.md` §1.4). There is exactly one participant with 3 occasions in the B=500 output. That participant is *thought* to be the one dropped in the archived pipeline: the lag-1 term removes each person's first occasion, leaving 2 occasions, below the floor. **This is inferred from matching counts (2 lost occasions) and was not verified by re-running the archived pipeline.** The current primary has no lag-1 term, so this path does not reproduce.
4. **Sensitivity check.** Recomputing BH on the B=500 p-values for 213 (that participant removed) leaves the intersection at **23 participants; 0 moved**, and no q value crosses a threshold (among participants passing the effect-size and occasion gates, the smallest parametric q at or above 0.05 is 0.0518; a 213-vs-214 rescaling lowers q by at most about 0.5%, to about 0.0516). A leave-one-out over all 214 single removals also changes no intersection label. **Limitation:** this holds the p-values fixed and changes only the BH family size. It does not cover removing a participant from the model and re-running the bootstrap, whose stability is untested.

**Why.** The family size was fixed at 213 on the archived pipeline's frame (`preregistration.md` §2.2, CLAUDE.md "Finalised decisions") and the label and constant were carried into `backend/` while the dynamic behaviour (correcting whatever non-NaN p-values exist) was ported correctly.

**Consequence.** The numbers are right; the naming is misleading and the guard is inert. One participant's difference in family size does not change the conclusion under the fixed-p-value check. Any change to the family definition (item 5) is a separate question.

**Week 8.** Decisions for the Statistical Analysis Lead: (a) whether to keep "213" in names/columns or make them size-neutral; (b) whether `EXPECTED_FAMILY_SIZE` should be compared with the real family size or removed; (c) whether the 3-occasion floor is to be ported. *(As of 2026-09-20 this record changed no finalised decision; the Resolution below did, by updating CLAUDE.md.)*

**Resolution (2026-09-27).**

(a) **Size-neutral.** Renamed throughout `backend/statistics/evidence.py`, `participant_evidence.py`, `tier1_runner.py`, `tests/statistics/test_evidence.py`: `reclassify_family213` → `reclassify_cohort_family`; the DataFrame columns `bh_q_213` / `holm_p_213` → `bh_q` / `holm_p` (their `intersect_bootstrap_evidence`-derived suffixed forms, e.g. `bh_q_213_parametric`, follow automatically from pandas' merge `suffixes` — no separate rename needed there). Not renamed: `evidence.py`'s citation of `analysis/evidence_model.py::reclassify_family213`'s docstring, since that names the archived module's actual, unrenamed function; the archived module itself (`analysis/archive/evidence_model.py`) is frozen and untouched.

(b) **Compared, not removed.** `EXPECTED_FAMILY_SIZE` is updated to **214** (item 1's number, not the archived pipeline's 213) and is now compared against the real per-call family size (`len(person_slopes)`) inside `reclassify_cohort_family`, which calls `warnings.warn` (`UserWarning`, not an exception) on a mismatch. A mismatch is not always wrong — a different feature's eligible cohort, an added participant, or a changed filter can legitimately produce a different family size — so this is a visibility check, not a hard assertion; the warning text names both values, says a mismatch can be legitimate, and says the constant may need updating. `unlock_num_ep_0`'s 216-participant cohort will correctly trigger this warning when run through the same function — that is the intended behaviour, not a false positive to silence. *(Superseded 2026-10-06: this turned out to be a false positive after all — a single global 214 warned on every unlock run, and a warning that always fires gets ignored. See the 2026-10-06 follow-up below.)*

(c) **Not ported.** `MIN_OCCASIONS_PER_PERSON` is not brought into `backend/`: all 214 current participants already clear 3 occasions, so porting the floor changes no result today, and porting a floor that does nothing needs a statistical justification that isn't on record. Recorded in `reclassify_cohort_family`'s docstring, alongside the 213-vs-214 origin from item 3. That origin remains a **suspicion, not a verified fact** (inferred from matching counts; the archived pipeline was not re-run): the archived pipeline's floor may only have bound because its lag-1 term first dropped each person's earliest occasion. The current lag-1-free primary spec has no such term and gives 214.

**Follow-up (2026-10-06): per-feature expected size.** `EXPECTED_FAMILY_SIZE` is now `dict[str, int]` — `{"loc_dist_ep_0": 214, "unlock_num_ep_0": 216}`, keyed by the statistics-side `FeatureSpec.name` — and `reclassify_cohort_family` takes `feature_id: str | None = None`. It warns only when `feature_id` has an entry and the real family size differs; `None` or an unlisted feature skips the check silently. Callers: `tier1_runner.py` passes `spec.name`; `participant_evidence.py` passes `meta.spec.name` (its own `feature_id`, `gps_distance` / `unlock_count`, is the SLM-side name and deliberately not the key). The values are current observed values for a data-dependent family size, not fixed constants; the check makes a change visible, it does not forbid one. Tests: the mismatch test now passes a `feature_id`; new tests cover `feature_id=None`, an unlisted feature, and a matching size (all silent); and two `participant_evidence._evidence_table("unlock_count")` tests (R fit stubbed, real dataset) assert no warning at 216 and a warning when the expected value is patched to 999, so silence there cannot be a skipped check. Full `tests/` run: 650 passed, 22 skipped, 0 failed, and no "family size" warning anywhere in the output.

**CLAUDE.md "Finalised decisions" updated (2026-09-27, and re-worded 2026-10-06).** The "cohort-level family = 213" entry now reads "the participants holding a per-person slope for that feature (data-dependent; 214 for `loc_dist_ep_0`)", with BH-FDR reported and Holm as sensitivity unchanged. `preregistration.md` §2.2/§7 and `Week5_Statistical_Analysis_Deliverable.md` §3.5 and the other places that stated the definition were updated to match, and the "213 came from the lag-1 term" statement was reverted to "suspected, not verified" in all of them, including `evidence.py`'s `EXPECTED_FAMILY_SIZE` comment and the `reclassify_cohort_family` docstring.

`tests/statistics/test_evidence.py` updated in lockstep (renamed tests/imports/call sites/column assertions, `EXPECTED_FAMILY_SIZE` assertion now 214) plus a new test asserting the mismatch warning fires. Full suite green (`tests/statistics`: 90 passed, 17 skipped [unrelated R-bridge], 0 failed).

No in-repo CSV carried the old column names (checked: none exist under `analysis/output`). The external, already-frozen B=500 archive (`mindsense-bootstrap-archive`, outside the repo) does carry them — its README now notes the discrepancy rather than being edited to match.

---

## Appendix A. Current results, both Tier-1 features

Primary = `nlme::lme + corAR1` (AR(1) residual). Sensitivity = `lme4::lmer + lmerTest` (Satterthwaite, no AR(1)). Source: `Week5_Statistical_Analysis_Deliverable.md` §3.3, §3.9. Model as implemented: `x_within + x_between`, random intercept + random slope, no lag-1 term (see item 7).

| | `loc_dist_ep_0` (GPS distance) | `unlock_num_ep_0` (unlock count) |
|---|---|---|
| Predictor | `log(mean + 1000)` | raw mean (no transform) |
| Participants | 214 | 216 |
| Occasions | 28,337 | 34,235 |
| Primary β_W | −0.184 | 0.001265 |
| Primary p | 5.57×10⁻¹⁹ | 0.143 |
| Primary phi (AR(1)) | 0.606 | 0.599 |
| Sensitivity β_W | −0.277 (95% CI −0.337 to −0.217) | 0.000381 |
| Sensitivity p | 1.04×10⁻¹⁶ | 0.777 |
| Random-slope fallback | none | none |
| Per-person evidence | 23 of 214 `evidence_available` (B=500, intersection of parametric and cluster bootstrap) | all 216 `insufficient` (no bootstrap SE) |

The two features' β are on different scales (GPS log-scale; unlock in raw counts) and are not comparable in magnitude.

## Appendix B. Cold-start distribution (retrospective, all EMA occasions)

35,348 occasions, 218 participants (`Week5_Statistical_Analysis_Deliverable.md` §3.7.1, §3.8). The evidence axis uses the archived pipeline's labels, not the bootstrap intersection and not the current request path (see item 2).

| State | Evidence | Deviation computable | Occasions | % of all |
|---|---|---|---|---|
| A | any | — | 480 | 1.4% |
| B | any | — | 11,309 | 32.0% |
| C | `no_claim` | yes | 14,588 | 41.3% |
| C | `no_claim` | no | 517 | 1.5% |
| C | `evidence_available` | yes | 8,209 | 23.2% |
| C | `evidence_available` | no | 245 | 0.7% |

State C total 23,559 (66.7%). `C + no_claim` = 15,105 occasions (42.7% of all, 64.1% of State C). Cited by the source as a retrospective figure, not a forecast: this dataset has hundreds to over a thousand days of history per participant, so a deployed system with continuing new-user intake would show a higher State B share.
