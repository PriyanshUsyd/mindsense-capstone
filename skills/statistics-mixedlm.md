# Skill: Statistics (Mixed-Effects Model)

Applies to: Statistical Analysis Lead primarily.

## The exact model

A linear mixed-effects model with a participant random intercept, using **person-mean-centred predictors**. This is not a generic regression — the centring is what makes it a genuine "you vs. your own baseline" statement rather than a population comparison, which is exactly what the client's spec asks for (`Client_Specs.md`, "Digital Phenotyping Pipeline" section: "calculate changes relative to each individual’s historical baseline rather than relying solely on population-level comparisons").

```
PHQ4_it = B0 + Bw(x_it - x_mean_i) + Bb * x_mean_i + Bt * time_it + b0_i + e_it
```

- `Bw` (the within-person deviation coefficient) is the **only** coefficient allowed to back a "your behaviour vs. your own baseline" statement to the user.
- `b0_i` (the random intercept) captures stable between-person differences — it does not by itself isolate someone's temporary deviation. That's specifically what the mean-centring does. Don't conflate the two.
- Use `statsmodels.MixedLM` — this is the entire model. No scikit-learn wrapper, no train/test split, no cross-validation, no `GridSearchCV`. If you find yourself reaching for scikit-learn, stop — see `build-reference.md`'s decisions log for why it's explicitly excluded.

## Eligibility rule (a safety decision, not just a statistical one)

Do not show "ready" evidence unless: (1) the observation window meets the agreed coverage threshold, AND (2) the participant has enough prior eligible windows to compute a real personal baseline. Otherwise return `insufficient_data` — this becomes the literal "not enough data yet" screen state. This eligibility check belongs in code, in your module — it is not something the UI invents on its own with a hardcoded number.

## Building the EvidencePacket

Your output feeds directly into the shared evidence contract (`backend/contracts/evidence.py`) — see `slm-ollama.md` for the consuming side. Your job is to populate, honestly:

- The within-person deviation estimate, confidence interval, direction, and an evidence-strength label (not a made-up confidence score — base it on the actual model output, e.g. CI width or p-value banding)
- Uncertainty reasons at both the item and packet level — if the model's estimate is shaky (small n, wide CI), say so explicitly, don't just hand over a point estimate
- The approved claim IDs the evidence genuinely supports — do not default to allowing every claim type just because a number exists

## Do not search after the fact

The model uses the locked 2-feature set and a predeclared coverage rule. It must never search across CES's other 200+ columns after seeing results, and it must never be re-run with a changed rule after seeing whether the results "look good." Any change to the eligibility threshold or model spec is versioned (`model_spec_id`) and requires the same sign-off as any other contract change.

## What NOT to do

- No scikit-learn, anywhere, in production code.
- No feature scaling/standardising before fitting — MixedLM estimates coefficients in original units, and scaling would make the "personal baseline deviation" harder to explain conversationally, not easier.
- Don't hand the SLM raw model output — always go through the validated `EvidencePacket` contract.
