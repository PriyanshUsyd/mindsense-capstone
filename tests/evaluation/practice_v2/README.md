# Practice v2

Fresh synthetic routing examples for policy 0.5.0. This is a practice evaluation, not held-out evidence.

- `train.json` contains 200 original questions, balanced across 16 routing categories. Use only this split for B5 tuning.
- `validation.json` is the locked independent 200-question split. Do not inspect, print, hash-check, or execute it until B6.
- `validation.sha256` records its integrity and is prepared before the first B6 run.
- `validation_2.json` is a fresh 100-question set, created only after a missed first validation and the single permitted train-only fix round; it is independently hashed before its one run.
- Its committed SHA-256 record is `validation_2.sha256`.

Each training record has an ID, target category, question, critical-tier flag and support-line expectation. Wording was authored independently; no spent or held-out prompt text is used in prompts, rules or tests.
