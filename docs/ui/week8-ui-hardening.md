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
