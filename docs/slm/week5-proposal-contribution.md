# SLM Proposal Contribution

Richard Zhao | 4 September 2026

[Full proposal](week5-proposal-input.md)

The SLM component turns statistical evidence into understandable explanations while limiting invented values, diagnostic claims and causal language. Research on constrained decoding (Geng et al., 2023) and faithfulness in summarization (Maynez et al., 2020) motivates separate structure and evidence checks; neither study validates this prototype clinically.

I implemented a loopback-only Ollama service consuming validated EvidencePackets instead of raw CES records. Versioned prompts request structured drafts; deterministic validation checks evidence references, approved claims, feature names, units, current/baseline values and uncertainty. Rule-based routing handles covered prohibited requests, crisis requests and missing data through fixed templates. Phi-4 Mini (`phi4-mini:3.8b`) remains the baseline and Qwen3 (`qwen3:4b`) the challenger; final selection is pending.

Recorded SLM development checks on 4 September used synthetic inputs. All 65 new output-grounding regression cases passed; the whole repository suite recorded 265 passes and eight skips (five CES, three frontend). The real-service smoke check passed four paths: a model-generated GPS explanation plus deterministic missing-data, refusal and crisis responses. The Phi-backed service passed automated checks for six executable questions from Chonghao's existing eight-question plan; two questions requiring PHQ-4 change or behavioural-PHQ-4 association evidence remain uncovered. Separately, 14 high-severity and two privacy-extension guardrail checks passed. These are development results, not independent or jointly scored evaluation.

Next, I will coordinate joint scoring with Chonghao, clarify the missing evidence with Statistics/Integration, and support API/UI integration. Week 6 work will iterate prompts, extend deterministic response checks and verify fallbacks through the full chain.

The bounded English response grammar may reject safe paraphrases. Synthetic tests do not establish real-data integration, clinical safety or whole-device offline compliance; Qwen has not been rerun against the latest fixes. Joint acceptance remains pending. These amendments are included in this Week 5 contribution.

## Evidence paths

- [backend/slm/service.py](../../backend/slm/service.py)
- [docs/slm/week5-output-grounding.md](week5-output-grounding.md)
- [benchmarks/slm_grounding_prompt048_results.json](../../benchmarks/slm_grounding_prompt048_results.json)
- [benchmarks/slm_grounding_shadow_smoke_results.json](../../benchmarks/slm_grounding_shadow_smoke_results.json)

## References

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

AI assistance: implementation, tests, documentation and citation drafting; local checks and source verification performed.
