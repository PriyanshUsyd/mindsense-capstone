# SLM Proposal source register

Checked: 4 September 2026 (Australia/Sydney).
Scope: [Richard's Week 5 SLM Proposal input](../week5-proposal-input.md),
not a systematic review or the complete group Proposal.

## Citation-to-claim map

| Citation | Location in the Proposal | Passage checked in the source | Scope and limitation |
|---|---|---|---|
| Geng et al. (2023) | Research basis, paragraph 1 | Abstract and sections 1-2; printed pp. 10932-10934 | Output-structure constraints. Our post-generation text validator is not their decoding algorithm; no clinical claim. |
| Maynez et al. (2020) | Research basis, paragraph 2 | Abstract/introduction and sections 2.1-2.2; printed pp. 1906, 1908 | Input faithfulness can differ from fluent text. Summarisation study, not a Phi/Qwen or MindSense evaluation. |
| Microsoft (2025) | Technical summary, model-provenance paragraph | PDF p. 1 abstract and footnote 1 | Phi-4-Mini is 3.8B; multimodal and reasoning-enhanced variants are distinct. Report author is Microsoft on the title page. |
| Qwen Team (2025) | Technical summary, model-provenance paragraph | PDF p. 3, section 2 and Table 1 | Qwen3-4B is a dense candidate. Report author is Qwen Team on the title page; no final model decision. |
| Ollama (n.d.-b) | Research basis, paragraph 1 | Structured Outputs: schema generation and response-validation example | Runtime capability, not proof that schema-valid prose is accurate. |
| World Health Organization (2024) | Research basis, paragraph 3 | Official release: Potential benefits and risks; Key recommendations | General health-AI risks and well-defined tasks/stakeholder involvement, not Australian law, ethics approval or crisis-template validation. |
| Ollama (n.d.-a) | Limitations, privacy bullet | FAQ: upgrades, model pulls/proxy, local/cloud data, cloud disablement, network binding | Local serving and separate network-capable features; not an audit of this machine. |

## Sources and downloaded originals

Four PDFs and three original HTML pages were downloaded from public primary
sources. PDFs were parsed and their title pages visually checked; relevant
passages were read. No model weights, source datasets or participant records
were downloaded. These PDFs are papers/reports, not runtime dependencies.

The full bibliography is in the Proposal. Direct source/download links:

1. Geng et al.: [publisher record](https://aclanthology.org/2023.emnlp-main.674/),
   [original PDF](https://aclanthology.org/2023.emnlp-main.674.pdf).
   Local file: `local-downloads/geng2023_grammar-constrained-decoding.pdf`.
2. Maynez et al.: [publisher record](https://aclanthology.org/2020.acl-main.173/),
   [original PDF](https://aclanthology.org/2020.acl-main.173.pdf).
   Local file: `local-downloads/maynez2020_faithfulness-factuality.pdf`.
3. Microsoft: [versioned report](https://arxiv.org/abs/2503.01743v2),
   [original PDF](https://arxiv.org/pdf/2503.01743v2).
   Local file: `local-downloads/phi4-mini_2503.01743v2.pdf`.
4. Qwen Team: [versioned report](https://arxiv.org/abs/2505.09388v1),
   [original PDF](https://arxiv.org/pdf/2505.09388v1).
   Local file: `local-downloads/qwen3_2505.09388v1.pdf`.
5. Ollama: [FAQ](https://docs.ollama.com/faq).
   Local file: `local-downloads/ollama_faq_2026-09-04.html`.
6. Ollama: [Structured outputs](https://docs.ollama.com/capabilities/structured-outputs).
   Local file: `local-downloads/ollama_structured-outputs_2026-09-04.html`.
7. WHO: [official guidance summary](https://www.who.int/news/item/18-01-2024-who-releases-ai-ethics-and-governance-guidance-for-large-multi-modal-models).
   Local file: `local-downloads/who2024_official_guidance_summary.html`.

[source-manifest.json](source-manifest.json) records exact source URLs, file
sizes, retrieval dates and SHA-256 hashes for these seven originals. HTML
files are page snapshots, not complete offline websites; opening them in a
browser may request external assets. Their extracted `.txt` companions can
be read offline without running page scripts. The snapshots do not replace
checking later documentation changes against the installed runtime.

## Download limitation and evidence boundary

The linked full WHO guideline (ISBN 978-92-4-008475-9) returned HTML rather
than a PDF through its public IRIS download endpoint. The response was not
treated as a valid paper and was retained as
`local-downloads/who_iris_download_response_not_a_pdf.html` for audit.
The initial attempt log is historical, not the current source manifest.
The Proposal instead cites the accessible official news release by its
actual title and date. This is explicit partial access to WHO's materials,
not a claim that the full guideline was downloaded or read.

External references do not verify our 16-case, 6-case or automated-test
results, clinical safety, crisis wording, privacy compliance or joint
acceptance. Local results retain their own versioned project evidence.
The PHQ-4 substitution, dataset methodology and statistical model remain
other sections' responsibilities and need their owners' citations.

## Git and reuse policy

This English register, source manifest and the scoped `.gitignore` are part of
the Week 5 technical contribution. `local-downloads/` is ignored in Git, including
PDFs, HTML, text extracts and attempt logs. Do not force-add the originals.
Public availability is not a blanket redistribution licence; the original
publisher/author notices remain in each downloaded work. Link to the original
source in shared reports rather than republishing the full work.

Private meeting notes and Chinese explanations remain outside this checkout.
Future publication or PR changes still require the repository owner's authorisation.
