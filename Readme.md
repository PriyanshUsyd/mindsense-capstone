# MindSense

MindSense is a local, privacy-preserving conversational assistant that helps a
person explore their own smartphone behaviour patterns. It turns passive
sensing data into two behavioural features, compares them with the person's
own history, and lets them ask about it in plain English. A small language
model runs on the same machine; nothing is sent to a cloud model.

MindSense describes patterns. It does not diagnose, explain causes, give
treatment advice, predict risk or compare a person with other people.

## Architecture

```text
question ─► 1. request screening ─► 2. evidence packet ─► 3. personal baseline ─► 4. local model ─► 5. answer gate ─► answer
               (crisis, diagnosis,     (14-day window,       (28-day own baseline;    (phi4-mini:3.8b    (claims, mode, wording,
                off-topic, windows)     cold-start state)     bootstrap evidence)      via Ollama)        uncertainty, exact grounding)
```

1. **Request screening** (`backend/slm/request_policy.py`, policy 0.3.3) routes
   crisis language, diagnosis, treatment and clinical-score requests, off-topic
   questions and unsupported time windows to fixed, reviewed answers before any
   participant data is loaded.
2. **Evidence packet** (`backend/statistics/participant_evidence.py`) is built
   server-side from the local dataset: the 14-day value, the cold-start state
   (A/B/C) and what may be claimed. The browser never assembles evidence.
3. **Personal baseline**: a participant with enough history (State C) is
   compared with their own 28-day baseline only when the precomputed bootstrap
   result (both bootstrap methods agree after false-discovery control;
   `docs/statistics/preregistration.md` §4.1) supports it. Otherwise the answer
   says so plainly; "too early to compare" is used only when the history is
   genuinely too short.
4. **Local model**: `phi4-mini:3.8b` through Ollama on `127.0.0.1`, with
   schema-constrained JSON, temperature 0 and seed 42.
5. **Answer gate** (`backend/slm/safety_gate.py`, `output_grounding.py`):
   every draft must use only approved claims and modes, reference its own
   evidence, avoid prohibited wording, include an uncertainty statement where
   required, and match an exact grounded sentence with the packet's numbers.
   Anything else is replaced by a reviewed fallback.

Frontend: React + TypeScript (Vite) in `frontend/`. Backend: FastAPI in
`backend/api/app.py`.

## Features

- Two cross-platform features: **GPS distance travelled** and **phone unlock
  count**, shown as whole numbers.
- Comparison with the person's own baseline when the evidence supports it,
  always with an explicit uncertainty sentence.
- Fixed, reviewed answers for crisis language (with Australian support
  services), diagnosis, treatment and clinical-score questions.
- A Details line under each answer (`response_mode`, `rejection_reason`,
  `model_tag`, `policy`) for evaluation and audit.
- Local model selector: `phi4-mini:3.8b` (final, default) and `qwen3:4b`
  (comparison only).

## Setup

Requirements: Git, Python 3, Node.js with npm, and Ollama for real model
answers. **Python versions:** CI runs **Python 3.14** and installs
`requirements.txt` without constraints; the setup scripts also apply
`constraints-python312.txt`, a scientific-stack pin verified on **Python
3.12**. If those pins do not install on your Python, use 3.12. R is optional (see
`docs/statistics/r-bridge-setup.md`): the per-person evidence cache (step 3)
builds with or without it.

### 1. Python environment

macOS / Linux (or Git Bash on Windows):

```bash
./scripts/setup_local_python_env.sh
source .venv/bin/activate          # Git Bash on Windows: source .venv/Scripts/activate
```

Windows PowerShell:

```powershell
.\scripts\setup_local_python_env.ps1
.venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, run `Set-ExecutionPolicy -Scope Process Bypass` first.

### 2. Dataset

The College Experience Study data is licensed and is **not** in this
repository. Download it from Kaggle and place it under `dataset/` at the
repository root (git-ignored), following
[`docs/data-pipeline/ces_local_provisioning.md`](docs/data-pipeline/ces_local_provisioning.md),
which also has the preflight check.

### 3. Per-person evidence cache (baseline comparison)

The comparison with a participant's own baseline needs a B=500 bootstrap
cache built from the dataset. Build it once, from a clean checkout:

```bash
python -m backend.statistics.bootstrap_cache --all
```

It uses R when R is usable in that shell and the pure-Python engine
otherwise (force one with `--engine python` or `--engine r`). With the Python
engine both features took 31 minutes on a 12-thread laptop (measured
16 October 2026, with an R build running alongside); the R engine is much
slower. The cache is
written to `outputs/bootstrap_cache/` (git-ignored, owner-only) and must
never be committed: it is derived from the licensed dataset. Without it the
app still answers, and says the history is long enough but the comparison
cannot be reported.

### 4. Ollama and the model

Install Ollama from <https://ollama.com/download> (macOS and Windows
installers), start it, then pull the pinned model:

```bash
ollama pull phi4-mini:3.8b
ollama pull qwen3:4b               # optional, comparison only
```

### 5. Run

Backend with the real local model, macOS / Linux:

```bash
MINDSENSE_SLM_RUNTIME=ollama python -m uvicorn backend.api.app:app --reload
```

Windows PowerShell:

```powershell
$env:MINDSENSE_SLM_RUNTIME="ollama"
python -m uvicorn backend.api.app:app --reload
```

Without `MINDSENSE_SLM_RUNTIME=ollama` the backend uses a deterministic demo
stub (`model_tag=demo-stub:1.0`) that needs no model; use it only for UI work
and tests.

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. **The first answer can take about 135 seconds**
while Ollama loads the model (one cold generation measured 134.7 s); the UI
shows "Local model warming up". Later answers are faster once the model is
loaded.

## Testing

```bash
python -m pytest                    # backend; network is blocked except loopback
cd frontend && npm test && npm run lint && npm run build
```

CI runs four stages on every push and pull request: Python application and
integration, R statistical runtime, frontend test/lint/build, and privacy and
security gates. A 50-question development set (`tests/slm/test_dev_50q.py`)
checks routing and refusals. Tests that need the real dataset or R skip
cleanly where those are absent.

## Model choice

`phi4-mini:3.8b` is the final model and the default
(`backend/slm/model_manifest.yaml`, `selection_status: selected`). `qwen3:4b`
stays installed and selectable only for comparison.

## Scope and design choices

- **Everything runs locally by design.** The client brief specifies a locally
  deployed language model so that personal sensing data is never sent to an
  external language-model service. Real-data tests run locally; CI uses
  synthetic fixtures so the licensed dataset never leaves the machine.
- **Evaluation** combined structured team session evaluation (3 sessions, all
  8 members; `docs/evaluation/week8-main-evaluation-roster.md`) with automated
  testing (four CI stages and a 50-question development set).
- **Architecture variants.** The Base, RAG, Agent and RAG+Agent variants are
  compared on a fixed public synthetic development protocol
  (`docs/slm/week9-variant-quality-comparison.md`).
- **Two cross-platform features** (GPS distance, phone unlocks) were chosen for
  reliability on both iPhone and Android (`build-reference.md`).
- **Two-level evidence.** Participants see either a hedged comparison or a
  plain statement that it cannot be reported; internal evidence tiers are not
  shown (`docs/statistics/preregistration.md` §5).

## Final documentation

| Area | Document |
|---|---|
| Data pipeline | [docs/data-pipeline/final-pipeline-methodology.md](docs/data-pipeline/final-pipeline-methodology.md) |
| Statistics | [docs/statistics/final-statistical-methodology.md](docs/statistics/final-statistical-methodology.md), [preregistration](docs/statistics/preregistration.md) |
| Evaluation results | [pass-threshold-summary.md](docs/evaluation/results/main-evaluation/pass-threshold-summary.md), [statistical write-up](docs/statistics/main-evaluation-statistical-writeup.md) |
| SLM | [docs/slm/final-slm-methodology.md](docs/slm/final-slm-methodology.md) |
| UI | [docs/ui/final-build-screenshots.md](docs/ui/final-build-screenshots.md) |
| Release | [release-candidate-checklist.md](docs/release/release-candidate-checklist.md), [final-submission-checklist.md](docs/release/final-submission-checklist.md) |

## Dataset citation

College Experience Study, [Kaggle](https://www.kaggle.com/datasets/subigyanepal/college-experience-dataset):

Subigya Nepal, Wenjun Liu, Arvind Pillai, Weichen Wang, Vlado Vojdanovski,
Jeremy F. Huckins, Courtney Rogers, Meghan L. Meyer, and Andrew T. Campbell.
2024. *Capturing the College Experience: A Four-Year Mobile Sensing Study of
Mental Health, Resilience, and Behavior of College Students during the
Pandemic*. Proc. ACM Interact. Mob. Wearable Ubiquitous Technol. 8, 1, Article
38 (March 2024), 37 pages. [DOI](https://doi.org/10.1145/3643501).
