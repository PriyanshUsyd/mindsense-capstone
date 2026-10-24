# Request policy 0.5.0

Policy 0.5.0 keeps deterministic safety rules as the first routing layer and
adds a single-label category router to the local Ollama runtime. The demo
runtime remains deterministic and does not instantiate the router.

## Safety and routing order

1. Deterministic crisis rules run first. They include self-harm signals and
   personal abuse, violence, threats, coercive control, and not feeling safe
   at home. A crisis route always returns the versioned crisis template.
2. The Ollama runtime's existing safety screen runs next. `yes` or `unclear`
   returns the crisis template. `no` or an error leaves the deterministic
   decision in place.
3. Only an off-topic rule decision or an in-scope request without one
   deterministic feature route is sent once to `phi4-mini:3.8b` for one label
   from the versioned prompt at
   `backend/slm/prompts/request_router_0_5_0.yaml`. The call uses strict JSON,
   temperature 0, and a 30-second timeout. The message is not logged.
4. A `crisis` label returns the crisis template. An `in_scope_gps` or
   `in_scope_unlocks` label can proceed only when the deterministic feature
   matcher independently finds the same feature. Otherwise the service asks
   the user to clarify. The router never selects or creates evidence.
5. When two refusal routes disagree, priority is crisis, injection, sensitive
   data, diagnosis, treatment, risk, cause, clinical score, then other routes.
   A router error, timeout, malformed JSON, or invalid label leaves the
   deterministic decision unchanged.

The router labels are `crisis`, `diagnosis`, `treatment`, `cause`, `risk`,
`clinical_score`, `injection`, `sensitive`, `app_info`, `capability`,
`time_window`, `feature_unclear`, `untracked`, `in_scope_gps`,
`in_scope_unlocks`, and `off_topic`. Definitions are versioned in the prompt
manifest rather than embedded in runtime-generated instructions.

### Pre-merge rule amendments (2026-10-24)

These are post-hoc fixes to deterministic rule families, made after the spent
practice-v2 validation sets and the spent v6 set had been seen. They are not
evidence of held-out accuracy; a fresh blind set is still required.

- **Abuse and violence family (crisis).** Any physical or threat verb (hurt,
  hit, grabbed, pushed, shoved, slapped, punched, kicked, choked, strangled,
  bruised, threatened, attacked) by a person (someone, he, she, they, or a
  partner, ex, family member, carer or housemate) against "me" or a part of
  the person's body; being left bruised or marked; "I was/got pushed, hit,
  ..."; and fear of a partner or family member or of what they will do. The
  family is checked with the other crisis rules, before every refusal route.
  Everyday senses are excluded ("hit me up", "grabbed me a coffee", "pushed
  me to walk more", "hit with deadlines"). `v6-03` now reaches the crisis
  route; this is recorded as a post-hoc regression only.
- **Causal family.** An explaining or originating verb (explain, be behind,
  bring about/on, give rise to, trigger, led to) linking a behaviour to a
  feeling or wellbeing word, in either order. A feeling word is required, so
  "explain my GPS distance" keeps its evidence route.
- **Sensitive-data family.** Another account, profile, login, device or
  phone; a specific, particular, named or identifiable person; and
  expose/reveal/leak/disclose with precise movement locations or whereabouts.
- **Deterministic answer-mode templates pass the phrase gate.** The
  safety gate's prohibited-assertion scan
  (`safety_gate.contains_prohibited_assertion`) now also runs on the
  general-limits and insufficient-data templates; a match falls back to the
  generic fallback with `prohibited_phrase_detected`. The general-limits
  template (1.1.0) now says "not an explanation of why something changed" instead of "... of what caused it".

## Non-answer support information

Every non-answer carries the GP or mental-health professional suggestion,
Lifeline 13 11 14, and Triple Zero (000) for immediate danger. This includes
scope clarifications, unsupported time-window messages, app-information
templates, capability responses, and insufficient-data responses.

The crisis template also names 1800RESPECT (1800 737 732) for domestic,
family, or sexual violence, with the qualification to contact them only if it
is safe. The number and 24/7 availability were confirmed on 23 October 2026
from the [official 1800RESPECT contact FAQ](https://1800respect.org.au/FAQ).
The complete participant-facing template remains subject to the review noted
in that versioned prompt.

## Evaluation status

Practice-v2 train and validation scores are development evidence only. They
are not held-out results. One fresh blind set must be run once after merge.
