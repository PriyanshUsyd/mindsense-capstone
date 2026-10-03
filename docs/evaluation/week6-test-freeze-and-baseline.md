# Week 6 Public Test Freeze and Baseline

Owner: Chonghao Shen, Evaluation Design  
Freeze date: 11 September 2026  
Branch: `chonghao/evaluation-week6`

## Frozen version

The Week 6 public-development baseline is tied to the following immutable Git
objects. Any later code or test change must be reported as a new run rather than
silently replacing this baseline.

| Item | Frozen value |
| --- | --- |
| Source commit (`origin/main` at branch creation) | `e7a25381480054ff30049612f16eff177d31d44f` |
| `tests/` tree | `d6f80099c31a2bf75a95432aebc322eb175a5716` |
| `benchmarks/fixtures/` tree | `762e2812db9322d1a43e781d5747b1b052994ef6` |
| Registered thresholds | 100% high-severity; 90% standard |
| Evaluation rubric | `docs/evaluation/response-quality-rubric-v0.1.md` |

The thresholds and public cases are not changed after viewing the baseline.
Failures must lead to a product change or a documented limitation, not removal
of the failed case.

## Held-out exclusion

The sealed Week 11 prompts were not opened, executed, edited, copied, or used to
select product changes. The following test was deliberately excluded because it
accesses the sealed artefact:

`tests/evaluation/test_held_out_integrity.py`

This Week 6 branch must not alter anything under
`tests/evaluation/held_out/`. Integrity verification will be performed only at
the agreed final-evaluation stage.

## Baseline command and environment

```text
.venv\Scripts\python.exe -m pytest -q --ignore=tests/evaluation/test_held_out_integrity.py
```

| Environment item | Value |
| --- | --- |
| Operating system | Windows 11 (`10.0.26200`) |
| Python | 3.12.14 |
| pytest | 9.1.1 |
| NumPy | 2.5.3 |
| pandas | 3.0.5 |
| statsmodels | 0.15.0 |
| FastAPI | 0.141.1 |

## Result

| Passed | Failed | Skipped | Warnings |
| ---: | ---: | ---: | ---: |
| 308 | 0 | 29 | 76 |

The same counts were reproduced immediately with `-rs` enabled to expose the
skip reasons. The 29 skips comprise:

- 14 tests requiring an unavailable R/rpy2/lme4/lmerTest/pbkrtest/nlme stack;
- 12 end-to-end checks requiring the gitignored real CES dataset; and
- 3 frontend build checks requiring npm and installed `node_modules`.

The warnings were predominantly expected `statsmodels` convergence warnings on
synthetic mixed-effects fixtures, plus two dependency deprecation warnings.
They did not produce functional test failures, but remain visible rather than
being presented as a warning-free run.

## Setup incident retained for reproducibility

Before the declared dependencies were installed, the first collection attempt
stopped with seven import errors (`fastapi`, `pandas`, and `numpy` unavailable).
After installing the repository's `requirements.txt` into the local virtual
environment, the baseline above completed. This was an environment setup
failure, not a failed product assertion, and is retained here so another team
member can reproduce the same conditions.

## Scope of the claim

This result is evidence that the executable public automated suite passed in
this environment. It is **not** 308 independent chatbot conversations, a human
usability result, a real-participant result, an R-backend result, a real-CES
end-to-end result, or held-out performance.

