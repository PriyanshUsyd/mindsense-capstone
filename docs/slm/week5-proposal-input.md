# Week 5 Proposal Input — Local SLM Integration and Safety

**Contributor:** Richard Zhao, SLM Integration

**Status:** Ready for Documentation Lead review; model selection remains
`comparison_pending`. Evaluation-alignment and reference amendments are included
in this Week 5 contribution; joint acceptance remains pending.
References checked on 4 September 2026.

For Honglin's 250-400-word request, use the [short contribution](week5-proposal-contribution.md).
This document provides the detailed SLM background and seven references.

## Research basis and design rationale

Grammar-constrained decoding provides a way to restrict a language model's
output structure (Geng et al., 2023). Ollama's structured-output interface
accepts a JSON schema and documents validation of the returned object
(Ollama, n.d.-b). These sources motivate a constrained interface, but do not
validate MindSense's implementation. Our design distinguishes JSON/schema
compliance from whether the text accurately expresses the supplied evidence;
the latter requires separate application checks. The current post-generation
English grammar is a project-specific validator, not a reimplementation of
Geng et al.'s decoding algorithm.

Maynez et al. (2020) found that fluent abstractive summaries can contain
information unsupported by their source documents. This motivates checking
input faithfulness separately from readability in MindSense. Their study
concerns document summarisation, not our models or mental-health application;
its reported performance cannot be transferred to this prototype.

WHO's official summary of its generative-AI guidance identifies inaccurate
outputs, automation bias and risks to patient information, and recommends
well-defined tasks and stakeholder involvement (World Health Organization,
2024). We use this as a general risk-management rationale for bounded
explanations, human review and explicit use limits. It is not Australian
ethics approval, clinical validation or endorsement of our crisis template.

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

The upstream reports describe Phi-4-Mini as a 3.8-billion-parameter language
model (Microsoft, 2025, p. 1) and Qwen3-4B as a dense member of the Qwen3
family (Qwen Team, 2025, section 2). They establish model provenance, not
which quantised candidate is safer or more accurate for MindSense. The Phi
report also covers separate multimodal and reasoning-enhanced variants;
their capabilities must not be attributed to the current baseline.

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
set of 14 high-severity and two privacy-extension requests passed 16/16 with zero unexpected model
calls. A one-repetition Phi/Qwen smoke comparison produced 3/3 deterministic
quality passes for Phi and 1/3 for Qwen, but this sample is too small for a
final model decision. The Week 11 sealed prompts were not opened or used for
model evaluation.

A local follow-up now maps Chonghao's existing eight public development
questions to the SLM implementation. Six can run with existing synthetic
evidence; PHQ-4 change and positive behavioural-wellbeing association cannot
yet be tested without a jointly agreed payload extension. The exercise exposed
and fixed a diagnosis-request routing gap and incomplete numerical comparisons.
With request policy 0.1.1, Prompt 0.4.8 and output grounding 0.1.1,
all six executable questions pass selected
developer checks; full responses and earlier incomplete outputs are retained.
These visible cases were used for development, not independent final evaluation.

The runtime now binds numeric values to their current/baseline roles and binds
feature names, units and declared/approved claims through a small English output
grammar. State B cannot add baseline comparisons behind a disclaimer. Unknown
paraphrases or additional assertions fail safely, reducing conversational variety.
This is deliberately bounded explanation, not general semantic verification.
The local model still generates the structured draft; failed generations are
not relabelled as successful model answers. See
[the output-grounding report](week5-output-grounding.md).

## Limitations to retain in the Proposal

- The earlier `0cf49cf` snapshot passed all four synthetic smoke paths and the full
  automated suite (179 passed, 8 skipped, no failures or deselections). This
  is developer evidence, not joint Evaluation Lead acceptance.
- The public 16-case result is provisional and still requires joint review
  with the Evaluation Lead; it is not the final or held-out score.
- The current amendment has 265 automated passes and eight skips, including
  65 new output-grounding regressions; the
  earlier 179-pass run above describes `0cf49cf`, not the current code. Six executable
  source questions do not establish complete coverage of all five response
  quality dimensions. Human ratings and the final agreed Week 5 suite are pending.
- The English rule-based request detector is a development guardrail, not a
  clinical assessment and not participant-ready without review.
- The Australia-specific crisis text contains verified public resources but
  still needs participant-facing and governance approval.
- The current evidence fixtures are synthetic; they do not demonstrate that
  the final statistics pipeline or API integration is complete.
- Association must not be presented as causation, and PHQ-4 must not be
  presented as a diagnosis.
- The Week 5 privacy spot-check documents local transport protections and
  upstream runtime behaviour. Ollama documents local serving, cloud-feature
  disablement and separate model-download/desktop-update behaviour
  (Ollama, n.d.-a). Disabling cloud features is not proof of complete network
  isolation. Whole-device offline verification and peer approval remain
  required before participant-facing use.

## Evidence provenance and integration note

External sources above support background and design rationale only. The
16-case result, six executable questions, historical model comparison and
265-pass local suite are project observations, documented in the
[Week 5 build report](week5-shadow-build-report.md),
[evaluation alignment](week5-evaluation-alignment.md),
[output-grounding report](week5-output-grounding.md) and
[privacy spot-check](week5-dependency-privacy-review.md). Reference drafting
itself added no code or model runs; subsequent publication verification is
recorded in the build report.

Honglin should integrate the relevant paragraphs AND their references into
the group Proposal, unify the report-wide citation style, and keep the
historical-run/current-amendment distinction. This contribution does not
establish that the group's dataset, statistical method or PHQ-4/WHO-5
substitution is fully referenced or approved; those sections need their
owners' sources. The [source register](references/README.md) maps each
citation to its passage and records local-download limitations.

## AI acknowledgement input

Generative AI tools assisted with implementation drafting, test generation,
documentation reconciliation, code review, literature discovery and citation
drafting. Implementation and tests were checked locally with synthetic inputs;
documentation was checked against the project's evidence contract and safety
rules. Citation metadata and supporting passages were checked against the
original publications or official pages, not accepted from generated summaries.
No participant data, raw CES records, credentials, or sealed evaluation prompts
were supplied to the generative AI tools for this work.

## References

The model reports use the group authors printed on their PDF title pages.
They are technical reports/preprints, not clinical studies. Author-date
formatting here is an integration aid; the group report's required style
still takes precedence. Web documentation was accessed on 4 September 2026.

- Geng, S., Josifoski, M., Peyrard, M., & West, R. (2023).
  *Grammar-constrained decoding for structured NLP tasks without finetuning*.
  In *Proceedings of the 2023 Conference on Empirical Methods in Natural
  Language Processing* (pp. 10932-10952). Association for Computational
  Linguistics. [DOI: 10.18653/v1/2023.emnlp-main.674](https://doi.org/10.18653/v1/2023.emnlp-main.674).
- Maynez, J., Narayan, S., Bohnet, B., & McDonald, R. (2020).
  *On faithfulness and factuality in abstractive summarization*.
  In *Proceedings of the 58th Annual Meeting of the Association for
  Computational Linguistics* (pp. 1906-1919). Association for Computational
  Linguistics. [DOI: 10.18653/v1/2020.acl-main.173](https://doi.org/10.18653/v1/2020.acl-main.173).
- Microsoft. (2025). *Phi-4-Mini technical report: Compact yet powerful
  multimodal language models via mixture-of-LoRAs* (arXiv:2503.01743v2)
  [Technical report/preprint]. [Versioned source](https://arxiv.org/abs/2503.01743v2).
- Ollama. (n.d.-a). *FAQ* [Software documentation].
  [Official source](https://docs.ollama.com/faq).
- Ollama. (n.d.-b). *Structured outputs* [Software documentation].
  [Official source](https://docs.ollama.com/capabilities/structured-outputs).
- Qwen Team. (2025). *Qwen3 technical report* (arXiv:2505.09388v1)
  [Technical report/preprint]. [Versioned source](https://arxiv.org/abs/2505.09388v1).
- World Health Organization. (2024, January 18).
  *WHO releases AI ethics and governance guidance for large multi-modal models*
  [Official news release summarising guidance, not the full guideline].
  [Official source](https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models).
