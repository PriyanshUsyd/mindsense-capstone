# Week 7 Fallback Refinement

**Owner:** Richard Zhao, SLM Integration

**Baseline:** `origin/main@a376715`

**Scope:** public development checks only; the sealed held-out prompt set is
outside this work.

## Problem closed by this change

The repository already had versioned generic and crisis templates and
deterministic safety routing. The Week 7 pilot exposed two integration gaps:

1. a cold local generation took about 134.7 seconds and exceeded the previous
   120-second request deadline; and
2. a missing gitignored dataset raised an unhandled `/respond` 500 instead of
   producing a safe, auditable state.

This refinement does not change participant-facing fallback wording or the
crisis trigger policy. It improves the routing and audit boundary around those
existing reviewed templates.

## Resulting behaviour

| Condition | HTTP/result | Reason code | Model invoked |
|---|---|---|---:|
| Crisis, prohibited, or off-topic question | deterministic crisis/refusal | existing policy reason | No |
| Local evidence files missing or unreadable | generic fallback | `evidence_source_unavailable` | No |
| Ollama exceeds the configured deadline | generic fallback | `model_timeout` | Attempted |
| Ollama cannot be reached | generic fallback | `model_unavailable` | Attempted |
| Ollama returns invalid structured output | generic fallback | `model_response_invalid` | Attempted |
| Other expected generation validation failure | generic fallback | `model_generation_failed` | Attempted |

Policy routing now occurs before participant evidence is loaded. Besides being
faster for deterministic routes, this avoids unnecessary participant-data
access and ensures crisis wording remains available even when the dataset is
not provisioned. Unknown participant and unknown feature requests retain their
404/422 semantics.

## Cold-start deadline

The API-created Ollama runtime now defaults to 180 seconds, above the observed
134.7-second cold result while remaining bounded. A local operator can set
`MINDSENSE_OLLAMA_TIMEOUT_SECONDS` to a finite value from 1 through 300. This is
a demo-machine control, not permission to weaken fallback or safety checks.
Preloading the selected model before the client demonstration is still
recommended; the timeout remains the fail-safe if warm-up is ineffective.

## Ownership boundary

Richard owns the SLM/client fallback classification and its public tests.
Priyansh owns acceptance of the shared HTTP behaviour and the demo timeout
budget. Sheng owns user-facing error differentiation and the clean frontend run
on Richard's machine. Honghao/Priyansh own approved local data provisioning.
Any change to crisis wording or the facilitator protocol still requires
client, Evaluation, and Privacy/safety review.

This work does not implement the rostered-pair pilot, bootstrap-SE cache,
retrieval source, frontend model selector, chat persistence, or production
RAG/Agent variants.

## Latest-main alignment

The fallback change was rebased after `main` gained the deterministic
question-to-feature routing fix and the rostered-pair pilot record. For an
allowed question, `/respond` now runs the fallback preflight and then uses the
new feature inference before building participant evidence. Deterministic
crisis, prohibited and off-topic requests still stop before feature inference
or data access.

The merged pilot confirms phone-unlock routing and records separate open issues
for requested time windows, participant-facing numeric precision and diagnosis
taxonomy. Those items are not reclassified as fallback defects here. Moe's
statistics calibration log is also a separate, currently unmerged owner record:
it confirms that the packet is built from real data, while the bootstrap-SE
cache remains outside the request path.

## Verification on Richard's machine

- Focused SLM/API regression after the latest-main rebase: 100 passed.
- Allowed-scope repository regression: 459 passed and 21 skipped; the sealed
  held-out directory and its integrity test were explicitly excluded. Six
  cases initially blocked by sandbox temp/subprocess permissions passed when
  rerun with an approved writable temp directory and the system Git client.
- Public prohibited/crisis script: 16/16 passed with zero unexpected model
  calls.
- Public off-topic script: 5/5 passed with zero model calls.
- Frontend: 23/23 tests, Oxlint, TypeScript build, and Vite production build
  passed.
- Real Ollama `0.33.2`: Phi and Qwen each completed Base 3/3, passed quality
  checks 3/3, and had zero execution failures. The one fallback for each model
  was the expected pre-model diagnosis refusal. The latest medians were 610.53
  ms for Phi and 785.81 ms for Qwen. Both models were unloaded after the checks.
- Isolated live check on port 8001: `/health` passed, `/models` exposed both
  manifest candidates, off-topic preflight returned refusal without a model
  call, and a real server-built participant packet selected Qwen and returned
  `uncertainty` without fallback. The frontend preview returned HTTP 200.

A latest-main replay of the port-8001 participant request again returned HTTP
200 without SLM fallback, but the Windows console emitted R startup/package and
worker-thread warnings. It is therefore valid SLM/API result evidence, not a
claim that the complete Statistics runtime log is clean. Yuktha's current
unmerged privacy branch contains a worker-thread conversion-context fix; any
promotion of that change and the remaining R environment warnings belongs to
the Statistics/Privacy/Integration owners.

The normal port-8000 browser path could not be claimed as a clean end-to-end
run because Windows refuses the port-8000 bind with `WinError 10013` on
Richard's machine and the current frontend hardcodes that port. A fresh check
on the latest main started Vite successfully on 5173 but failed the backend
bind before browser interaction, so no Priyansh-confirmed demo-machine claim
was made. Richard did not alter the system listener or Frontend-owned code.
Priyansh and Sheng must accept a configurable loopback API base URL (or agree
on another local port) before the final joint demo-machine check.
