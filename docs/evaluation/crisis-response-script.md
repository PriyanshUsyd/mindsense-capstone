# Facilitator Crisis-Response Script (DRAFT)

**Status: DRAFT, built to fill a Week 4 gap on 2026-08-29.** For Chonghao
Shen (Evaluation Design Lead) to review, adapt, and — ideally — check against
real facilitator-training guidance or a campus counselling contact before
Week 7's pilot. This is a facilitator-facing script, separate from the
app's own `backend/slm/prompts/crisis_aware.yaml` deterministic message.

## When to use this

Use this script if, during a session, a participant:
- says something suggesting they are in crisis or considering self-harm,
  whether or not the app itself triggers its crisis-aware fallback,
- appears visibly distressed, or
- explicitly asks for help beyond what the study session can provide.

**The app's own behaviour and your response as a facilitator are separate.**
Even if the app doesn't trigger its crisis template, you as the human
facilitator in the room are the actual safety layer — don't wait for the
software to react.

## What to say

1. Pause the session. It's fine to say plainly: *"Let's pause here for a
   moment — I want to check in with you."*
2. *"I'm not able to give you medical or mental health advice myself, but
   I want to make sure you get to real support. Would it be okay if we
   talked about some options?"*
3. Offer, calmly and without pressure:
   - If they're in immediate danger: *"If you feel unsafe right now, please
     contact [local emergency number] or go to your nearest emergency room."*
   - Otherwise: *"[Local crisis line — same resources as
     backend/slm/prompts/crisis_aware.yaml, once confirmed for the actual
     study location] is available if you'd like to talk to someone."*
   - Campus-specific: *"[Placeholder — insert the actual university
     counselling service contact for wherever sessions are run]."*
4. Ask if they want to stop the session. **Always honour this — do not try
   to continue the study protocol over a participant's wellbeing.**
5. After the session (whether or not they continued), note what happened in
   the session log without recording unnecessary personal detail, and
   inform the Evaluation lead so the incident is tracked, per the study's
   actual ethics/safety reporting process.

## What NOT to do

- Don't try to assess clinical risk yourself — you're not qualified to, and
  neither is the app. Your job is to connect them to real support, not to
  evaluate how serious it is.
- Don't minimise ("I'm sure it's nothing") or over-react in a way that
  embarrasses the participant.
- Don't skip this step because "the app already showed the crisis message" —
  the app's message is not a substitute for a human checking in.

---

*[Placeholder: real local crisis-line numbers and the specific campus
counselling contact need to be filled in once the actual study
location/institution is confirmed — currently uses the same placeholder
resource list as `backend/slm/prompts/crisis_aware.yaml`, flagged there as
needing real review too.]*
