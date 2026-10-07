# Main-Evaluation Evidence

Create one directory per session and question:

```text
ME-P01/Q1/
ME-P01/Q2/
ME-P01/Q3/
ME-P01/Q4/
...
ME-P04/Q4/
```

Each question directory must contain:

- `ui.png` — exact question and complete visible response;
- `response.json` — the `/respond` response copied without modification;
- `notes.md` — date/time, operator/evaluator codes, observed failure or
  retry, and anything not represented in the JSON.

Do not store teammate names, raw participant identifiers, coordinates,
personal disclosures or held-out Week 11 content. A failed first attempt stays
in the evidence; do not replace it silently with a successful retry.

The matching questionnaire-category rows go in
`docs/evaluation/results/main-evaluation/session-responses.csv` and reference
the question directory through `evidence_path`.
