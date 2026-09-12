# Week 6 Client Evaluation Readiness

Owner: Chonghao Shen, Evaluation Design  
Date: 11 September 2026

## Direct response to the four client requests

### 1. Ethics and human evaluation

No external participants will be recruited because the project does not have
ethics approval. Evaluation is restricted to rostered pairs drawn from the
eight-person project team. Sessions use public synthetic or formally
de-identified scenarios and do not request personal mental-health disclosure.
The procedure is defined in `team-session-runbook-v0.1.md`; no human results are
claimed yet.

### 2. Metrics and evidence

The questionnaire now maps explicitly to all ten client-named dimensions.

| Client dimension | Operational evidence | Main rationale source |
| --- | --- | --- |
| Accuracy / faithfulness | Values, units, direction, baseline and inventions | Maynez et al. (2020) |
| Comprehensibility | First-reading clarity and terminology | Hoffman et al. (2018) |
| Usefulness | Understanding gained and sufficient detail | Hoffman et al. (2018) |
| Personal relevance | Scenario/person specificity and own-baseline relevance | Client criterion; own-baseline design |
| Trust | Honest evidence reflection and visible limits | Jian et al. (2000); Hoffman et al. (2018) |
| Uncertainty communication | Clarity of uncertainty and insufficient-data behaviour | Hoffman et al. (2018); WHO (2024) |
| Correlation vs causation | Association language; automatic fail for unsupported causality | Hernán and Robins (2020) |
| Inappropriate mental-health inference | No diagnosis, treatment or risk prediction | WHO (2024); PHQ-4 scope in Kroenke et al. (2009) |
| Usability | Ease, consistency and confidence using the prototype | Brooke (1996), adapted items only |
| Privacy perceptions | Data minimisation, disclosure and perceived concern | Malhotra et al. (2004); repository privacy controls |

The project-specific questionnaire is informed by these sources, not presented
as a validated new scale. Exact references and scoring rules are in
`participant-questionnaire-v0.2.md`.

### 3. Interactive web chatbot

Current evidence on `main` includes a React/Vite interface and a FastAPI
endpoint. The current API is explicitly a thin local pass-through: it does not
yet provide authentication, session state or multi-turn memory. A separate
`sheng-week6-ui` branch connects the Week 6 chat to a local model, but it must be
reviewed and merged before it can be called the frozen team-evaluation build.
The real Ollama demonstration remains machine-specific and is planned on
Richard's configured machine. Therefore the honest status is **prototype
available; integrated frozen build and team pilot pending**, not deployed or
externally validated.

Before the client demonstration, record: merged commit, machine/model tag,
health-check result, at least one normal response, one insufficient-data route,
one privacy refusal and one crisis route through the actual UI/API path.

### 4. Input and prompting comparisons

The comparison is pre-specified as a within-case development benchmark:

- hold model, evidence packets, questions, decoding settings and scoring rubric
  constant;
- vary only the declared condition: zero-shot versus few-shot;
- report each public case, not only an aggregate average;
- evaluate single-turn versus multi-turn only in a standalone benchmark until
  privacy review clears state handling;
- keep fine-tuning as a deferred condition unless a versioned model, local-only
  privacy decision and sufficient training data are approved.

No zero/few-shot, multi-turn or fine-tuning result is claimed at Week 6. Empty
tables are preparation, not evidence.

| Condition | Model/version | Public cases | Faithfulness pass | Critical failures | Median usability | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Zero-shot | TBD | TBD | — | — | — | Planned |
| Few-shot | TBD | TBD | — | — | — | Planned |
| Single-turn | TBD | TBD | — | — | — | Planned |
| Multi-turn standalone | TBD | TBD | — | — | — | Planned after privacy review |
| Fine-tuned | Not approved | 0 | — | — | — | Deferred |

## Evidence already available

| Evidence | Current result | Limitation |
| --- | --- | --- |
| Week 6 public automated baseline | 308 passed, 29 skipped, 0 failed | Excludes held-out integrity test; environment-specific |
| Week 5 source-plan review | 6/6 executable questions passed | Q2 and Q8 not covered; Q1/Q7 share a fixture |
| Week 5 high-severity public checks | 14/14 passed | Public synthetic subset only |
| Week 5 privacy extensions | 2/2 passed | Safe generic wording; usability refinement remains |
| Team questionnaire | Ten dimensions defined in v0.2 | No completed team ratings yet |

## Week 6 joint calibration with Richard

Both reviewers must lock independent ratings before discussing them. Do not
manufacture disagreement: if ratings match, report agreement. At minimum,
review these public boundary cases:

| Case | Chonghao independent judgment | Richard independent judgment | Agreed outcome / rationale |
| --- | --- | --- | --- |
| Q7 repeated Q1 fixture | Pending | Pending | Pending; response quality and independent-coverage count are separate decisions |
| Privacy refusal wording | Pending | Pending | Pending; safety pass and usability reservation are scored separately |

## Remaining claims that cannot yet be made

- No external-user, population, clinical-effectiveness or diagnostic-validity
  result.
- No completed team-only human-evaluation result.
- No held-out performance result before Week 11.
- No real-CES end-to-end result from the Week 6 baseline environment.
- No completed zero-shot/few-shot, multi-turn or fine-tuning comparison.
- No claim that a modified subset of SUS or IUIPC items produces an official
  standardised score.

## References

1. Maynez, J., Narayan, S., Bohnet, B., & McDonald, R. (2020).
   https://aclanthology.org/2020.acl-main.173/
2. Hoffman, R. R., Mueller, S. T., Klein, G., & Litman, J. (2018).
   https://arxiv.org/abs/1812.04608
3. Jian, J.-Y., Bisantz, A. M., & Drury, C. G. (2000).
   https://doi.org/10.1207/S15327566IJCE0401_04
4. Brooke, J. (1996). https://hci-studies.org/methods-and-measures/downloads/SUS_Brooke1996.pdf
5. Malhotra, N. K., Kim, S. S., & Agarwal, J. (2004).
   https://doi.org/10.1287/isre.1040.0032
6. Hernán, M. A., & Robins, J. M. (2020).
   https://miguelhernan.org/whatifbook
7. World Health Organization. (2024).
   https://www.who.int/publications/b/70584
8. Kroenke, K., Spitzer, R. L., Williams, J. B. W., & Löwe, B. (2009).
   https://pubmed.ncbi.nlm.nih.gov/19996233/

