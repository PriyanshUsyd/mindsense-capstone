# Final Submission Checklist

- **Owner:** Integration & QA Lead (group lead)
- **Prepared:** 16 October 2026, at `95e3171`
- **Rule:** an item is ticked only with its evidence link. The three open items
  at the top are the only work left before the freeze tag.

## 1. Before the freeze tag (open)

| # | Item | Owner | Status |
|---|---|---|---|
| 1 | Sealed 24-prompt held-out safety check, run once on the final build; commit the aggregate result with checksum `95acb455a8798c9941d0564efc9080883b0c222944b9725782d308d680c515b5` | SLM Integration Lead | Open |
| 2 | Privacy sign-off on the final build, including the whole-device offline test | Privacy & Security Lead | Open |
| 3 | Final freeze tag on the final build, after items 1 and 2; push it and confirm with `git ls-remote --tags origin` | Group lead | Open |

## 2. Build and verification (done)

| Item | Evidence |
|---|---|
| CI on `main` passes all 4 stages | GitHub Actions run `38833421820` on `95e3171` |
| Fresh-clone boot test: setup script, 1027 backend + 41 frontend tests, app answering with `phi4-mini:3.8b` | [release checklist §11, "Boot test"](release-candidate-checklist.md#final-build-records-16-october-2026-95e3171) |
| 4 evaluation questions asked again on the final build | [release checklist §11, "Re-ask"](release-candidate-checklist.md#final-build-records-16-october-2026-95e3171) |
| Final model recorded | `backend/slm/model_manifest.yaml` (`phi4-mini:3.8b`, `selection_status: selected`) |
| Held-out file unchanged since sealing | `tests/evaluation/test_held_out_integrity.py` (CI) |
| Dataset preflight | [`final-pipeline-methodology.md` §6.1](../data-pipeline/final-pipeline-methodology.md) |
| UI screenshots of the final build | [`docs/ui/final-build-screenshots.md`](../ui/final-build-screenshots.md) |

## 3. Final documentation (done)

| Area | Document |
|---|---|
| Data pipeline | [`docs/data-pipeline/final-pipeline-methodology.md`](../data-pipeline/final-pipeline-methodology.md) |
| Statistics | [`docs/statistics/final-statistical-methodology.md`](../statistics/final-statistical-methodology.md), [`preregistration.md`](../statistics/preregistration.md) |
| Main-evaluation statistics | [`docs/statistics/main-evaluation-statistical-writeup.md`](../statistics/main-evaluation-statistical-writeup.md) |
| SLM | [`docs/slm/final-slm-methodology.md`](../slm/final-slm-methodology.md) |
| Evaluation results | [`docs/evaluation/results/main-evaluation/pass-threshold-summary.md`](../evaluation/results/main-evaluation/pass-threshold-summary.md) |
| Privacy | [`docs/privacy/README.md`](../privacy/README.md), [`master-test-register.md`](../privacy/master-test-register.md) |
| Release | [`release-candidate-checklist.md`](release-candidate-checklist.md), this file |
| Plan status | [`Weekly_Plan.md`](../../Weekly_Plan.md) (every item Done with evidence or Closed with a reason) |
| Consistency pass (16 Oct 2026) | Relative links in every tracked Markdown file outside `docs/progress-report/` resolve; status wording on finished work updated in `build-reference.md`, `docs/privacy/README.md`, the SLM, statistics and evaluation documents; GitHub handles in new and updated text replaced by roles |

## 4. Client

| Item | Status |
|---|---|
| Live demonstration for the client | Closed: the demo video was shared with the client in place of the live screen-share (recorded by the group lead) |
| Running build on a team machine | Done: boot test above |

## 5. Course deliverables outside this repository

The Final Report, Presentation, demo video and Oral Defence are submitted
through the course site by the Documentation & Report Lead and the group lead.
They are listed here for completeness and are tracked outside the repository.

## 6. After the freeze tag

- No model, prompt or code change on `main` (release checklist §9).
- Documentation-only changes stay allowed in Week 12 (`Weekly_Plan.md`, Week 12).
