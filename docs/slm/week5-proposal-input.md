# Week 5 Proposal Input — Local SLM Integration and Safety

**Contributor:** Richard Zhao, SLM Integration

**Status:** Ready for Documentation Lead review; model selection remains
`comparison_pending`.

## Paste-ready technical summary

MindSense uses a local, schema-constrained SLM only after the statistical
layer has produced a validated `EvidencePacket`. The SLM interface does not
read raw GPS coordinates, raw sensing rows, or raw PHQ-4 records. The current
development fixtures are synthetic, and the participant-reference field is
redacted before the packet is sent to the model. This field-level protection
does not automatically anonymise arbitrary free-text questions or packet IDs.
The current runtime is Ollama on loopback, with `phi4-mini:3.8b` as
the baseline and `qwen3:4b` as the challenger. Final model selection remains
pending a larger fixed evaluation.

The SLM returns a structured `AssistantDraft`, which is checked again before
any text becomes user-facing. The deterministic gate verifies packet and
evidence identifiers, permitted response modes and claim IDs, prohibited
causal/diagnostic/treatment language, eligibility consistency, and explicit
uncertainty wording. High-severity user requests are also routed before model
generation: diagnosis, causal inference, treatment advice, risk prediction,
prompt injection, and sensitive-data requests receive a fixed refusal, while
crisis/self-harm language receives a separate Australia-specific support
template. State A missing-data cases use a deterministic insufficient-data
template rather than asking the model to guess.

The Week 5 shadow build has demonstrated one synthetic GPS happy path through
the real local Phi model, plus deterministic missing-data, refusal, and crisis
paths without a complete UI. A provisional, public, non-held-out development
set of 16 high-severity requests passed 16/16 with zero unexpected model
calls. A one-repetition Phi/Qwen smoke comparison produced 3/3 deterministic
quality passes for Phi and 1/3 for Qwen, but this sample is too small for a
final model decision. The Week 11 sealed prompts were not opened or used for
model evaluation.

## Limitations to retain in the Proposal

- A 4 September rerun passed all four synthetic smoke paths and the full
  automated suite (179 passed, 8 skipped, no failures or deselections). This
  is developer evidence, not joint Evaluation Lead acceptance.
- The public 16-case result is provisional and still requires joint review
  with the Evaluation Lead; it is not the final or held-out score.
- The English rule-based request detector is a development guardrail, not a
  clinical assessment and not participant-ready without review.
- The Australia-specific crisis text contains verified public resources but
  still needs participant-facing and governance approval.
- The current evidence fixtures are synthetic; they do not demonstrate that
  the final statistics pipeline or API integration is complete.
- Association must not be presented as causation, and PHQ-4 must not be
  presented as a diagnosis.
- The Week 5 privacy spot-check documents local transport protections and
  upstream runtime behaviour. Whole-device offline verification and peer
  approval remain required before participant-facing use.

## AI acknowledgement input

Generative AI tools assisted with implementation drafting, test generation,
documentation reconciliation, and code review. All generated code and text
were reviewed against the project's evidence contract and safety rules, run
locally through automated tests, and checked with synthetic inputs. No
participant data, raw CES records, credentials, or sealed evaluation prompts
were supplied to the generative AI tools for this work.
