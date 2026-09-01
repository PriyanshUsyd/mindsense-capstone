# Week 5 Proposal Input — Local SLM Integration and Safety

**Contributor:** Richard Zhao, SLM Integration Lead  
**Status:** Ready for Documentation Lead review; model selection remains
`comparison_pending`.

## Paste-ready technical summary

MindSense uses a local, schema-constrained SLM only after the statistical
layer has produced a validated `EvidencePacket`. The model does not receive
raw GPS coordinates, raw sensing rows, participant identifiers, or raw PHQ-4
records. The current runtime is Ollama on loopback, with `phi4-mini:3.8b` as
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

## AI acknowledgement input

Generative AI tools assisted with implementation drafting, test generation,
documentation reconciliation, and code review. All generated code and text
were reviewed against the project's evidence contract and safety rules, run
locally through automated tests, and checked with synthetic inputs. No
participant data, raw CES records, credentials, or sealed evaluation prompts
were supplied to the generative AI tools for this work.

