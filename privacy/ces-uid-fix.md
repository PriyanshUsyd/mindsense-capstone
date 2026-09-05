# Privacy fix: raw participant UIDs in CES eligibility output

Date: 2026-09-05
Fixed by: Priyansh Khandelwal (Integration/QA), flagged during Week 5 verification.

## The issue

`backend/data_pipeline/ces_eligibility.py`'s `summarize()` function printed
the raw CES `uid` for every ineligible participant, in both the
`ineligible_uids` list and the `ineligible_reasons` dict keys. Any run of
this script (stdout, a redirected log file, a shared terminal screenshot)
exposed real participant identifiers from the CES dataset — a live
violation of the "no raw participant identifiers in logs/output" rule in
`skills/privacy-security.md` and of `backend/contracts/evidence.py`'s own
rule that `participant_ref` must never be the raw CES uid.

`backend/data_pipeline/verify_ces.py` was checked too — it only ever
reports aggregate counts/percentages and never lists or keys anything by
uid, so it needed no change.

## The fix

`ces_eligibility.summarize()` now takes a `pseudonymize` callable (default:
`make_pseudonymizer()`), which maps each raw uid to `"p_" + sha256(salt +
uid)[:12]`. The salt is 16 random bytes generated fresh per call and never
persisted or logged, so:

- the pseudonym cannot be reversed back to the raw uid, and
- pseudonyms from two separate runs of the script cannot be matched to each
  other (no cross-run re-identification via a stable hash).

The field `ineligible_uids` was renamed to `ineligible_participant_pseudonyms`
so callers can't mistake pseudonyms for real ids by name alone.

## Verification

`tests/data_pipeline/test_ces_eligibility_privacy.py` asserts, against a
synthetic dataset with known raw uids:

- neither `summarize()`'s returned dict nor the real captured stdout of
  `main()` ever contains a raw uid or a raw-uid substring,
- pseudonyms are well-formed (`p_[0-9a-f]{12}`) and don't trivially embed
  the raw uid,
- two independent runs (fresh salts) produce disjoint pseudonym sets, and
- a fixed salt is deterministic (confirms it's a real hash function, not
  just random output).

## Scope check

Grepped the rest of the repo (`backend/`, `benchmarks/`, `tests/`) for any
other code path reading the CES `uid` column or printing/logging it. The
only other files touching `uid` are `verify_ces.py` (aggregate-only, no
fix needed) and `backend/contracts/evidence.py` (defines `participant_ref`
as an opaque field, already documented as never the raw uid). No other
raw-UID leak was found.
