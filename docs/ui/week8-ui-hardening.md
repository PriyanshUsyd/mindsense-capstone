# Week 8 UI Hardening

**Owner:** Sheng Wang, Conversational Interface Lead  
**Branch:** `sheng-week8-ui-hardening`  
**Base:** `main` at `822214c`  
**Date:** 2026-09-22

## Scope

This change addresses frontend issues recorded during the Week 7 pilot and
adds the approved visual-polish task for Week 8. It does not change statistical
calibration, request-policy thresholds, fallback wording returned by the
backend, or local-model behaviour.

## Pilot fixes

1. A network failure (`TypeError` from `fetch`) is shown as **Local service
   unavailable** with startup guidance.
2. A non-success HTTP response is shown as **Local processing failed**. The UI
   no longer claims the API was unreachable when FastAPI returned an error.
3. The obsolete normal-response panel containing `Synthetic demo data`,
   `see response text`, and Week 5 packet copy is removed. The frontend renders
   the validated backend response and a truthful local-data boundary until the
   response contract exposes a structured evidence summary.
4. The provisional TypeScript response contract includes the backend's
   `off_topic` request category.
5. Frontend setup and chat documentation now describes the current
   `{ participant_id, question, optional feature_id }` request.
6. A request still running after 12 seconds is now identified as **Local model
   warming up**. The browser keeps the request active under the backend's
   bounded 180-second deadline and tells the user that a first local response
   may take up to three minutes.
7. The macOS backend setup now requires a project-local `.venv`. A checked-in
   Python 3.12 constraints file pins the verified compatible NumPy 2.5.3,
   SciPy 1.18.1, and statsmodels 0.15.0 combination, and the setup script runs
   both `pip check` and a three-package import check.

## Visual direction

The visual refresh follows the supplied botanical reference while keeping the
existing MindSense identity and accessibility constraints:

- deep forest sidebar with clearer selected navigation and recent-chat rows;
- warm paper background, botanical landscape banner, and restrained leaf
  decoration;
- softer response cards with stronger hierarchy and compact local-evidence
  framing;
- floating rounded composer and clearer primary action;
- preserved non-colour labels and distinct icons for uncertainty,
  insufficient-data, refusal, generic fallback, and crisis states;
- responsive layout, keyboard focus states, and reduced-motion support;
- local SVG assets only: no CDN, external font, analytics, telemetry, or
  network-loaded imagery.

The supplied image is a style reference only. Its example numbers, messages,
and decorative character are not treated as application data or copied into
the request flow.

## Verification

Run from `frontend/`:

```sh
npm test
npm run lint
npm run build
```

The visual review should cover the welcome view, normal response, all safety
states, retry behaviour, desktop width, and phone width.

### Sheng's Mac verification boundary

On 2026-09-22, Sheng verified commit `bc47185` on a macOS MacBook Air using the
project-local `.venv`, Ollama, and the Vite frontend. The frontend loaded at
`127.0.0.1:5173`, FastAPI started at `127.0.0.1:8000`, and repeated
`POST /respond` requests returned HTTP 200. The browser correctly rendered the
handled evidence-source fallback and the known development off-topic refusal.
Frontend tests (25), lint, and the production build passed.

This evidence confirms that the frontend itself ran cleanly on Sheng's machine.
It does not close the separate pipeline/data-provisioning gap: without the
approved local sensing dataset, an allowed evidence question safely returns
`generic_fallback` with `evidence_source_unavailable` rather than a normal
evidence response. The cold-start notice and constrained setup added after
`bc47185` require one final Mac rerun before the two pilot items can be marked
closed on the latest commit.

Run this final check from the repository root:

```bash
./scripts/setup_local_python_env.sh
source .venv/bin/activate
python -m pip check
python -c "import numpy, scipy, statsmodels; print(numpy.__version__, scipy.__version__, statsmodels.__version__)"
MINDSENSE_SLM_RUNTIME=ollama python -m uvicorn backend.api.app:app --reload
```

In a second terminal:

```bash
cd frontend
npm test -- --run
npm run lint
npm run build
npm run dev
```
