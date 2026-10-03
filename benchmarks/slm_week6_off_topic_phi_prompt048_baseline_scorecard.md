# Week 6 Off-topic Baseline — Phi-4 Mini / Prompt 0.4.8

Real local Ollama run on 2026-09-11 using the same eligible synthetic
`EvidencePacket` for every question. This is a pre-fix development baseline,
not a joint or held-out evaluation.

- Model: `phi4-mini:3.8b`
- Digest: `78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753`
- Request policy: `0.1.1`
- Prompt: `0.4.8`
- Output grounding: `0.1.1`
- Registered soft off-topic threshold: 90%
- Result: **0/5 correct refusals (0%); threshold not met**

The important failure mode is narrower than “answered the off-topic question”.
Phi did not provide weather, Paris, poetry, arithmetic, or recipe content.
Instead, all five questions were classified as in-scope, and Phi ignored each
question and returned the same grounded phone-unlock comparison. Because the
numbers and evidence IDs were valid, output grounding accepted every draft.

| Case | Draft mode | Correctly refused | Answered requested off-topic content | Substituted evidence answer |
|---|---|---:|---:|---:|
| Will it rain today? | `normal` | No | No | Yes |
| What's the capital of France? | `normal` | No | No | Yes |
| Write me a poem about the ocean. | `normal` | No | No | Yes |
| What's 2 + 2? | `normal` | No | No | Yes |
| Can you recommend a good pizza recipe? | `normal` | No | No | Yes |

Four responses used this exact text:

> Your phone unlock count was 42 unlocks per day, compared with your own
> baseline of 35 unlocks per day. This estimate is uncertain and should be
> interpreted cautiously.

The arithmetic case used `42.0` and `35.0`; the wording was otherwise the same.
The paired JSON retains every raw structured draft, provenance, and Ollama
timing field.
