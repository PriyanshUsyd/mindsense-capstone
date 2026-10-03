# Team Evaluation Session Runbook v0.1

Owner: Chonghao Shen, Evaluation Design  
Scope: one internal rostered-pair session; no external participants

## Before the session

1. Confirm both people are members of the eight-person project team and assign
   operator/evaluator roles.
2. Record the frozen commit, model tag, prompt/policy versions and response
   snapshot location.
3. Use only approved public synthetic or formally de-identified scenarios.
   Do not ask the evaluator to disclose personal mental-health information.
4. Confirm that no held-out Week 11 prompt or response is opened or executed.
5. Start the local web chatbot and perform a health check without changing the
   frozen build.

## During the session

1. The operator presents the assigned public scenario in the registered order.
2. The evaluator asks the supplied question without being shown an expected
   answer.
3. Save the exact question, evidence-packet ID, response, response mode and
   timing. Do not save raw identifiers or coordinates.
4. The evaluator independently completes the scenario sections of
   `participant-questionnaire-v0.2.md` before discussion.
5. For a crisis-route scenario, stop ordinary evaluation after confirming the
   deterministic route; do not role-play or solicit real distress disclosures.
6. If the app fails, record the failure and time. Do not silently restart and
   report only the successful attempt.

## After the session

1. Complete the once-per-session usability items and open questions.
2. Store ratings under a session code, not a teammate's name in the results
   table.
3. Check that all N/A values have a reason and all critical-failure Yes/No
   items are complete.
4. Compare independent developer ratings only after both Chonghao and Richard
   have locked their judgments.
5. Report median, range and denominator per dimension; do not run or imply a
   population-level significance test on the team-only sample.

## Stop conditions

Stop and notify the Evaluation and Privacy leads if the system reveals a raw
identifier/location, exposes instructions, produces an unsupported diagnosis or
causal claim, misses an explicit crisis route, or if any held-out material is
accidentally accessed. Preserve the response and version metadata without
copying sensitive content into chat or GitHub.

