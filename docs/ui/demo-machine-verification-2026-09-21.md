# Demo-Machine Frontend Verification — 2026-09-21

**UI owner:** Sheng Wang

**Demo-machine operator:** Richard Zhao

**Current target build:** `main` at `822214c`

**Status:** Visual working confirmation recorded at the group lead's request.

## Evidence provenance and privacy

The group lead reported that Richard had the frontend working on the demo
machine and asked Sheng to commit the three supplied screenshots as
confirmation. The screenshots visibly identify the local model as
`phi4-mini:3.8b`; they do not display the machine's Git SHA, operating-system
version, terminal output, HTTP status, browser console, or measured latency.
Those details are therefore not invented or claimed here.

The supplied images contain participant-derived GPS and phone-unlock aggregate
values. Sheng confirmed that project privacy approval was obtained to publish
the original screenshots. The three JPEG files are therefore committed exactly
as supplied, without cropping, redaction, metadata removal or other image
modification. No participant identifier or raw record is visible, and no
held-out guardrail question is identified or used in this record.

## Visual confirmation

### Multi-turn uncertainty rendering

The interface displays two in-scope questions in one conversation and renders
both responses with the distinct `Uncertain evidence` treatment. The header
shows `Local model · phi4-mini:3.8b`, and the composer remains available after
both turns.

![Original multi-turn uncertainty evidence](evidence/demo-machine-multiturn-uncertainty.jpeg)

### Diagnosis-seeking refusal

After an uncertainty response, the known development diagnosis-seeking prompt
is rendered as `Outside MindSense's scope`, while the page-level state changes
to `Safe boundary`. It is not presented as a normal behavioural insight.

![Original uncertainty and refusal evidence](evidence/demo-machine-uncertainty-and-refusal.jpeg)

### Phone-unlock uncertainty state

The phone-unlock question independently renders the uncertainty state with its
warning icon, limitation language and local-model indicator.

![Original phone-unlock uncertainty evidence](evidence/demo-machine-phone-unlock-uncertainty.jpeg)

## Verification summary

| ID | Check | Evidence-based result | Status |
|---|---|---|---|
| DM-UI-01 | Frontend loads on Richard's demo machine | MindSense chat shell, navigation, composer, local-model indicator and response-state badge are visible. | Pass |
| DM-UI-02 | In-scope GPS flow | GPS question renders an uncertainty response rather than a transport/generic fallback. | Pass |
| DM-UI-03 | In-scope phone-unlock flow | Phone-unlock question renders an uncertainty response rather than a transport/generic fallback. | Pass |
| DM-UI-04 | Safety boundary | A diagnosis-seeking development prompt renders the dedicated refusal state and scope explanation. | Pass |
| DM-UI-05 | Multi-turn presentation | Two completed in-scope turns remain visible in the same conversation without a duplicated turn. | Pass |
| DM-UI-06 | Responsive/mobile layout | The supplied evidence is desktop-width only. | Not evidenced |
| DM-UI-07 | Runtime logs and latency | No error is visible in the supplied UI captures, but backend logs, browser console, exact HTTP status and latency were not captured. | Not evidenced |

## UI follow-up

The original screenshots rendered participant-derived daily values with
excessive decimal precision. This does not block the demonstrated response
states, but the user-facing values should be rounded to an agreed precision
before the 2026-09-25 client demo.

## Conclusion

The supplied demo-machine evidence confirms that the frontend is visually
functional with Richard's local `phi4-mini:3.8b` path for both supported
in-scope uncertainty responses and the dedicated diagnosis-refusal state. This
closes the requested visual working confirmation. It does not claim the
uncaptured runtime metadata listed above.
