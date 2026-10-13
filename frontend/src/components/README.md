# Shared components

Reusable, visually consistent building blocks shared across the chat states.

- `AppShell.tsx`: responsive navigation, privacy cue, local-SLM indicator, and
  current response-state badge.
- `BrandMark.tsx`: local SVG identity mark with compact and full variants.
- `ModelSelector.tsx`: accessible selector for the manifest-bounded local model
  tags returned by `GET /models`; it is hidden when runtime selection is
  disabled.

No externally hosted fonts, images, scripts, analytics, or chart libraries are
used. A chart is intentionally deferred until real time-series evidence is
available instead of visualising invented data.
