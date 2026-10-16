# Week 10 Local-Demo Privacy Verification and Scoped Sign-off

**Decision date:** 17 October 2026 (Australia/Sydney)

**Tested code:** `df66eac843ddce2f99b9f0a73dee46f6465911a9`

**Branch:** `codex/privacy-week10-signoff`, created from the fetched `origin/main` at that commit

**Reviewer:** Yuktha Naveen, Privacy and Security Lead

## Decision

I sign off the **tested, single-machine local demo configuration** with the
installed `phi4-mini:3.8b` model, a trusted operator, local CES data, and the
documented loopback-only services. The actual application and model returned
answers while this Mac's Wi-Fi was off and a direct public-network probe was
unreachable. This is a scoped runtime privacy pass, not approval for real-user
accounts or a claim that the entire computer can never transmit data.

**Repository evidence publication remains on hold.** Older tracked UI images,
an evaluation PDF, and accompanying text contain CES-derived single-person
activity summaries. They show no visible participant ID in the inspected
examples, and an older UI record says publication had been approved. However,
this conflicts with `docs/privacy/local-demo-privacy-check.md`, which says not
to commit screenshots of participant summaries. The conflict must be resolved
and the relevant history assessed before anyone describes the repository as
privacy-clean. None of the new offline screenshots or full responses are added
by this sign-off.

## Assumptions and Scope

- The fresh post-history-cleanup clone and the exact commit above are the build
  being assessed. A code, dependency, model, logging, or retrieval change
  requires a new review.
- This is a trusted-operator local demonstration on one Mac, not a multi-user
  deployment. The backend still accepts a caller-supplied participant ID
  without authentication or an ownership check.
- The CES files and two B=500 bootstrap caches were already provisioned
  locally. The dataset and caches remain ignored by Git. The installed model
  was available before disconnection.
- The Week 11 sealed held-out evaluation set belongs to the Evaluation/SLM
  process and was deliberately excluded from these development test commands.
- The offline probe checked Wi-Fi power and one public HTTPS destination. It
  did not perform packet capture or test every possible network interface.

## Checks Performed and Findings

| Check | Method and assumption | Observed result | Meaning / limit |
| --- | --- | --- | --- |
| Exact build and clean branch | Fetched origin, compared `main`, `origin/main`, and HEAD; checked working tree before documentation | All resolved to the tested commit; clean before documentation | Prevents attributing results to another revision. |
| Full unsealed Python/integration suite | Ran with `MINDSENSE_CI_SCOPE=sealed-excluded` under `privacy/macos-loopback.sb`; held-out files excluded before collection | **1,062 passed, 21 skipped, 82 warnings** in 92.43 s; 0 failures | No tested regression on this machine. Skips and warnings are not passes. The first nested tool attempt could not apply the macOS profile; the permitted rerun above completed. |
| Focused privacy suite | `tests/privacy` on the same code | **49 passed, 2 skipped**, 1 deprecation warning; 0 failures | The two skips need a usable local R/rpy2 package stack. CI's dedicated real-R stage passed separately. These tests do not OCR screenshots or extract PDFs. |
| Frontend | Ran Vitest, lint, and production build locally | **41/41 tests passed**; lint and build passed | UI regressions passed; this is not a substitute for the live offline workflow. |
| Dependencies and four-stage CI | Local `pip check`; inspected GitHub Actions run `38886676044` for this exact SHA | No broken local Python requirements; Python, R, frontend, and privacy/security jobs all succeeded, including the CI dependency audits | CI is additional evidence, not evidence of Wi-Fi-off operation. No dependency was added for this sign-off. |
| Live offline API and model | On 16 Oct, verified Wi-Fi Off and public HTTPS probe failure, then requested local frontend/asset, `/health`, `/models`, and two `/respond` feature categories | Local pages and API returned HTTP 200. Movement and unlock requests returned `uncertainty` with `model_tag=phi4-mini:3.8b`, `model_invoked=true`, `used_fallback=false`, and `Cache-Control: no-store`. Wi-Fi and public reachability were restored afterward. | Demonstrates usable local inference during the tested disconnection. Only redacted response metadata is retained. |
| Manual browser workflow | Reviewed the privacy lead's Chrome captures made while the Mac showed Wi-Fi off | Phi-selected movement and unlock answers rendered in the local app | Confirms the user-facing flow. A later Qwen selection/fallback display is not evidence that Qwen worked offline; Qwen is outside this sign-off. Original captures remain local because they show participant-derived values and browser details. |
| Local storage and Git inventory | Checked Git tracking/ignore rules and filesystem modes | No `dataset/`, `outputs/`, or `.env` file was tracked. Dataset and both cache directories were owner-only (`700`); cache files were owner-only (`600`). | Prevents these local raw/cache files being added by an ordinary `git add`. It does not erase already-tracked evidence or stop root/same-account access. |
| Tracked text and binary spot-check | Searched tracked text for credential, email/home-path, and raw UID-shaped patterns; visually inspected selected evidence images and extracted evaluation-PDF text | No match for the tested credential, email, or real home-path patterns in tracked text; one documented Windows example path uses `you`. Existing images/PDF/text do expose CES-derived individual summary values without visible IDs. | This is the repository-publication hold. Automated privacy tests do not cover image/PDF contents. The spot-check is not a proof that every embedded binary field is harmless. |

The backend was launched with `--no-access-log` for the offline demo. This
sign-off does not claim a fresh exhaustive review of every library log line;
the earlier Week 9 live-log review remains separate historical evidence.

## Evidence Handling and Follow-up

- Redacted machine-readable results: `benchmarks/history/privacy_security/2026-10-17_week10-local-demo-signoff.json`.
- Exact-SHA CI: `https://github.com/PriyanshUsyd/mindsense-capstone/actions/runs/38886676044`.
- The unredacted local offline screenshots are **not** copied into Git. They
  include participant-derived values and browser/terminal details. Do not
  publish them as-is or use an AI-regenerated image as purported test evidence.
- Existing evidence needing a publication decision includes
  `docs/ui/evidence/final-build-q1-unlock.png`,
  `docs/ui/evidence/final-build-q2-movement.png`,
  `docs/ui/final-build-screenshots.md`, and
  `docs/evaluation/evidence/main-evaluation/ME-P01/ME-P01.pdf`. Other tracked
  demo/evaluation screenshots and text should be reviewed at the same time.
  If these are removed or redacted, ordinary deletion commits do not remove
  prior Git history; coordinate any history cleanup with the repository lead.
- Before real-user access, implement authentication, verified sessions,
  backend-only participant ownership mapping, access tests, and a retention/
  deletion decision. No PIN-only lookup or caller-chosen participant ID is
  approved by this sign-off.

**Signed decision:** Local Phi-4 Mini demo runtime at the tested commit:
**approved within the scope above**. Repository evidence publication and
real-user deployment: **not signed off**.
