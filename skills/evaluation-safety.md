# Skill: Evaluation & Safety Testing

Applies to: Evaluation Design Lead primarily.

## The rubric maps to the client's actual 10 criteria

Do not invent evaluation dimensions independently — build directly around the 10 named in the client's spec (Section 4), reproduced in `build-reference.md` Section 9:

1. Accuracy and faithfulness
2. Comprehensibility
3. Usefulness
4. Perceived personal relevance
5. Trust
6. Appropriate communication of uncertainty
7. Ability to distinguish correlation from causation
8. Inappropriate mental-health inference (the rubric must actively test for this failure mode, not just measure positive qualities)
9. Usability
10. Privacy perceptions

## The adversarial test suite

Freeze the taxonomy and expected response class per test case in Week 4 — this is not something to keep casually expanding throughout the project. Pre-register the pass threshold **before** seeing results (e.g. 100% on high-severity/crisis categories, a fixed percentage on softer categories) — deciding the bar after seeing how the model performs defeats the purpose of having one.

## The held-out set — the single most important discipline here

Set aside 20-30 prompts in Week 4 that **nobody looks at again until Week 11**. This is what proves the system generalises, rather than just having been tuned against the exact test set repeatedly. If anyone — including you — peeks at these prompts or the model's responses to them before Week 11, the held-out set is compromised and the final safety claim is weaker. Treat this literally: store it somewhere it won't be accidentally opened during normal Week 5-10 iteration.

## Session design

- Draft the one-page participant information sheet and the facilitator crisis-response script in Week 4 — these need review time, not a rush job in Week 6.
- Pilot (Week 7): 4-5 participants against a frozen build. Check protocol health after the very first participant — if something's clearly broken about the session flow itself, fix the process before running the rest, don't push through a broken protocol for consistency's sake.
- Main evaluation (Week 9): 10-15 participants, rostered in 2-person facilitation pairs, on a version-locked build. Sessions must complete at least 2 working days before the Progress Report deadline — this is a hard rule, not a nice-to-have.
- Week 10's smaller round (5-8 participants) is a directional smoke-test re-checking specific fixed issues — report it honestly as that, not as a second full study.

## What NOT to do

- Don't add new adversarial test cases after Week 4 without team sign-off — the frozen taxonomy is what makes the pre-registered threshold meaningful.
- Don't let "the model got better since we wrote this test" become a reason to quietly retire or soften a test case.
- Don't run the held-out set early "just to check" — that single act invalidates the point of holding it out.
