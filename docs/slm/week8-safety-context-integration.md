# Week 9 SLM Comparison, Safety and Context Integration

- Owner: Richard Zhao, SLM Integration Lead
- Updated: 9 October 2026
- Integration base (28 September): `main@9abda9b369def04de1d370550c8a3db966b78263`
- Review branch: `Rz-week9`; Week 9 comparison and prompting results
- Earlier delivery: [PR #34](https://github.com/PriyanshUsyd/mindsense-capstone/pull/34), merged 26 September

## Week 9 delivery status: 9 October

This is the reviewable SLM delivery status for the requested 10 October
handover. The existing 6 October protocol, benchmark, tests and result files
are retained unchanged. Public synthetic Z/F and Qwen companion runs completed
on 9 October. Human rubric scoring is pending and is not included in this
delivery. The separate release-candidate session has not been run.

| Requested delivery | Evidence available | Remaining requirement |
| --- | --- | --- |
| Base / RAG / Agentic / RAG+Agent comparison | Phi and Qwen public outputs and automated checks | Independent human rubric scoring remains Not assessed |
| Zero/few-shot results tables | Actual public synthetic results in the [methodology](week8-prompting-methodology.md): 168 executions, 24 model calls, 84/84 identical paired texts | Human quality remains Not assessed; no observed few-shot output benefit on this constrained sample |
| Phi4-mini versus Qwen3 recommendation | Same-source companion comparison below: all 264 paired final texts match | Comparative human quality and broader controlled evidence remain pending; final model selection stays open |
| Held-out approval source | Priyansh's dated one-run approval and the engineering-check distinction in the [methodology](week8-prompting-methodology.md#scope-and-authority) | CI may verify integrity/structure/privacy; the formal model evaluation is not completed and sealed questions must not guide development |

### Four-mode results: automated evidence and human status

The [6 October JSON](../../benchmarks/history/week9_variant_quality_phi_2026-10-06.json)
contains three repeats per mode, fixed Phi4-mini and public synthetic packets.
Counts below are successful automated executions / executed records, not
independent human judgments. Each mode has 22 unique executable questions and
two planned questions excluded as Not covered (Q2 and Q8, three repeats each).

| Mode | Source-plan checks (6 questions x 3) | Guardrail checks (14 x 3) | Privacy extensions (2 x 3) | Actual model calls | Human rubric / acceptance |
| --- | --- | --- | --- | --- | --- |
| Base | 18/18 | 42/42 | 6/6 | 9 | Not assessed |
| RAG | 18/18 | 42/42 | 6/6 | 9 | Not assessed |
| Agentic | 18/18 | 42/42 | 6/6 | 9 | Not assessed |
| RAG+Agent | 18/18 | 42/42 | 6/6 | 9 | Not assessed |

Total: 264 executed records, 24 Not covered records, 36 genuine model calls
and no recorded execution errors. The source-plan group includes deterministic
routes; it is not 18 generated answers. The run has two distinct generation
fixtures and five distinct response texts overall. Every question has identical
text across modes/repeats. Additional context IDs (0/2/2/4) verify the selected
paths, but demonstrate no quality improvement. RAG reuses the participant's
validated evidence summary; it does not search a document store.

The 100% automated checks above do not establish the human rubric's 90%
standard-quality threshold or 100% critical-safety acceptance. No separate
off-topic acceptance result or human median/range/valid-n is available.
Coverage gaps and repeated fixtures remain visible; neither Not covered nor
Not assessed is counted as a pass. The existing rubric/thresholds are unchanged.

### Qwen companion: 9 October

The [Qwen result](../../benchmarks/history/week9_variant_quality_qwen_2026-10-09.json)
extends the immutable Phi run under the separately frozen
[companion protocol](../../benchmarks/fixtures/week9_dual_model_protocol.json).
It uses the same public cases, synthetic packets, four modes, three repetitions,
Prompt 0.4.13, policy 0.3.1, grounding 0.1.1, temperature 0, seed 42 and 180-second
timeout. The installed Qwen digest is `359d7dd4bcda` with Ollama 0.33.2.
All 35 original Phi source hashes matched before execution; all 38 companion
sources matched before and after. No original Phi file was changed.

| Model / each mode | Source-plan automated checks | High-severity automated checks | Privacy automated checks | Genuine model calls | Human acceptance |
| --- | --- | --- | --- | --- | --- |
| Phi / Base, RAG, Agentic, RAG+Agent (each) | 18/18 | 42/42 | 6/6 | 9 | Not established |
| Qwen / Base, RAG, Agentic, RAG+Agent (each) | 18/18 | 42/42 | 6/6 | 9 | Not established |

Qwen adds 264 executed records, 24 Not covered records and 36 genuine model
calls, with no execution errors or unexpected fallback. All 264 paired final
texts match Phi, including all 36 generated pairs. This is a comparison of
post-gate system outputs with restricted answer options and only two generation
fixtures; identical text does not establish general model equivalence or an
architecture advantage. The runs occurred on different days and do not support
a controlled model-speed ranking.

Human rubric scoring is pending. All saved human-review fields remain null;
no rubric scores are supplied by this delivery.

Reproduction from the repository root (requires installed Qwen and a new,
absent output; this command was not rerun during the readiness audit):

```powershell
& '.venv/Scripts/python.exe' -m benchmarks.slm_dual_model_review --out benchmarks/history/week9_variant_quality_qwen_reproduction.json
```

The [entry point](../../benchmarks/slm_dual_model_review.py) replaces only the
two benchmark provenance aliases with an explicit source allow-list. It retains
the existing implementation, transport and gates, refuses baseline source drift,
checkpoints every block and cannot overwrite an existing result. The 9 October
readiness audit found that 28 of the 35 original source fingerprints change
under Git's CRLF-to-LF conversion. After verifying all 35 original raw hashes,
the protocol received a separately labelled post-run reproduction metadata block
with CRLF-to-LF fingerprints. The revised runner accepts original bytes or that
verified equivalent; any other content change still fails before generation.
Its explicit `--out` now permits a new JSON only in the existing history directory.

Eleven focused [tests](../../tests/slm/test_dual_model_review.py) and Ruff passed,
including in-memory LF/CRLF conversion, real-content drift, evidence tampering,
output confinement and overwrite protection. These were local synthetic tests,
not a Linux CI run. Publication validation subsequently passed on the initial
technical commit; its distinct scope is recorded below.

The recorded Qwen JSON, its embedded original protocol, and all original Phi
files remain byte-for-byte unchanged. The 38-source match above describes the
actual run; the companion runner, its tests and protocol were subsequently
corrected and are not claimed to have their recorded hashes today. The original
35 experimental sources still match. No model rerun or new experimental result
is claimed for the tooling correction. Original Windows result SHA256:
`3cb86e06ac7bc8d133c95f69d2d7617c2b58a5babd6f5316f5e2dfd33505a6fa`.
The same Qwen JSON after CRLF-to-LF conversion has SHA256
`fa0ce59c35c89e936aa4575106ef7dd9ad776f0064da6da6516cb75a35fba297`;
the Phi baseline's equivalent is recorded in the reproduction metadata. These
additional fingerprints do not replace or rewrite the original provenance.

The verified focused test command is:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
& '.venv/Scripts/python.exe' -m pytest -p pytest_socket -o required_plugins= --confcutdir=tests/slm tests/slm/test_dual_model_review.py -q
```

### Separate Z/F result: 9 October

The [public Z/F run](../../benchmarks/history/week9_prompting_phi_2026-10-09.json)
holds Phi/Base and safety controls fixed, adding two separate synthetic examples
only in F. Each condition passed 18/18 source-plan, 42/42 high-severity, 6/6
privacy, 15/15 off-topic and 3/3 supplemental State B checks. There were 12 model
calls per condition, all schema-valid and grounded, with no unexpected fallback
or execution error. Q2/Q8 remain Not covered.

All 84 paired executable records, including 12 generated pairs, have identical
text. This gives no observed output benefit under the constrained response-option
design; the product prompt stays unchanged. Subsequent service-call median/p95
were 718.480/839.213 ms for Z and 811.252/914.183 ms for F (n=11 each); first/load-bearing
calls are separate in the methodology. These tiny local samples do not establish
general performance or quality. Human judgments remain unavailable.

The runner, two fixtures and tests are isolated from product configuration.
Sixteen explicit synthetic/prompt-loader tests and Ruff passed; all 31 recorded
source hashes matched. No full suite, integrity or CI ran during that experiment.
Original four-mode files and their recorded evidence remain unchanged.

### Phi4-mini versus Qwen3: provisional recommendation

The recommendation is to retain `phi4-mini:3.8b` as the operational baseline
and `qwen3:4b` as a comparison candidate. The basis is integration continuity:
the matched outputs provide no evidence for a quality-driven model change.
Final selection remains `comparison_pending`; the comparison does not establish
superior conversational or clinical quality, and no runtime configuration changes
are included.

| Saved evidence | Phi4-mini | Qwen3 | Interpretation |
| --- | --- | --- | --- |
| [18 September comparison](../../benchmarks/history/slm_prompt0413_model_comparison/2026-09-18_phi-qwen_public.json) | 9/9 selected checks; 6 generated turns and 3 deterministic diagnosis refusals | Same counts | Two generated fixtures, each repeated three times; functional compatibility, no human quality winner |
| Generated calls only, same 18 September file | n=6; median 629.53 ms; range 613.73-742.27 ms | n=6; median 814.69 ms; range 752.98-873.63 ms | Recomputed from saved `model_invoked=true` records; separate warm-ups excluded; tiny local descriptive sample |
| [28 September Phi API smoke](../../benchmarks/history/week8_packet_api_phi_2026-09-28_policy031.json) / [Qwen API smoke](../../benchmarks/history/week8_packet_api_qwen_2026-09-28_policy031.json) | 8/8 selected checks | 8/8 selected checks | Two synthetic scenarios across four modes; compatibility under policy 0.3.1, not independent quality evaluation |
| 6 October four-mode run | 264 executions / 36 model calls | Not run in this protocol | Phi-only evidence cannot rank the two models |
| 9 October companion against unchanged Phi sources | Original 264 executions / 36 model calls retained | 264 executions / 36 model calls | All 264 final texts match; no observed output-quality separation on these restricted public fixtures |
| Independent human comparative rubric | Not assessed | Not assessed | Required before an evidence-based quality preference |

The 18 September run used Prompt 0.4.13 and request policy 0.2.0, so its
latencies are not a fresh policy-0.3.1/RC benchmark. Warm-up times were recorded
separately (Phi 3019.47 ms; Qwen 3031.77 ms). Its original pooled summary mixes
generated calls and pre-model refusals; the generated-only medians above avoid
that mixture. No significance or general speed ranking is claimed. The saved
GPU-memory deltas (including Phi's negative delta) do not provide a controlled
memory comparison. Model size on disk is not measured runtime memory usage.

A final preference still needs actual independent comparative quality review
and broader approved evidence capable of discriminating the candidates. The
companion now supplies matched public cases, gates and prompting conditions;
a speed claim would additionally require balanced/interleaved order and separate
cold/warm calls. The Z/F run remains Phi-only and cannot rank models. Multi-turn
remains a separate planned factor.

### Delivery boundary

This benchmark delivery uses public synthetic inputs and contains no completed
human rubric scores or participant-session evidence. Individual ratings,
screenshots and full session responses remain local. Any later session summary
requires approval for publication.

ME-P02 has not been run. It is separate from these developer benchmarks and
requires the published, confirmed-ready `rc-eval-1` during 10-15 October;
`b60cb84` is superseded. The application still reuses the participant's validated
evidence summary for RAG, and its live association path remains `no_claim`.
Bootstrap SE wiring into `/respond` is outside this delivery.

### CI verification is separate from held-out evaluation

The initial technical commit `eda2b6f` passed all four stages of the manual
[sealed-excluded run](https://github.com/PriyanshUsyd/mindsense-capstone/actions/runs/37926288038).
The later documentation commit `657f60e` passed all four stages of
[automatic full CI](https://github.com/PriyanshUsyd/mindsense-capstone/actions/runs/37929997010).
These results apply to their recorded revisions; checks for subsequent commits
are reported on the PR. This delivery changes no workflow and uses no skip marker.

Full CI performs automated checksum, JSON-structure and privacy checks. These
engineering checks are separate from the authorised one-off held-out model
evaluation, which has not been run. The public benchmark experiments did not
use held-out data. A subsequent machine-only structural check confirmed the
required fields and 24 entries without displaying question text. Neither that
check nor CI supplies model-evaluation results.

### Earlier local verification: 9 October

After synchronisation to `main@b742ad8`, the six explicit related SLM test
modules passed 80 tests and Ruff passed. All 35 source hashes from the 6 October
run still matched; the saved result remained unchanged. No model rerun was
performed for this check. Human rubric scoring and ME-P02 remained pending.

The sections below retain dated Week 8 records. Their documentation-only Z/F
status and restricted-CI procedure describe earlier deliveries.

## Week 8 close-out status on 6 October

The integration continuation was merged in
[PR #43](https://github.com/PriyanshUsyd/mindsense-capstone/pull/43) on 3 October.
Richard's remaining Week 8 deliverable is the complete four-variant quality
comparison. Its technical run and review package are available locally; actual
independent judgments and the separate ME-P02 session are not complete.

| Deliverable | Evidence and remaining work |
| --- | --- |
| Guardrails, safe defaults and packet-summary integration | Delivered in merged #34/#43; the 28 September evidence remains below |
| Zero/few-shot methodology and separate multi-turn plan | Documentation only; no new prompt-method experiments |
| Configured four-variant execution | Complete local run on the `f39f07f` main baseline with an uncommitted benchmark and explicit source hashes |
| Developer rubric decisions | Richard and Chonghao must independently record judgments and resolve disagreements |
| ME-P02 | Richard/Sheng session still not run; use the existing pairing plan |

The [fixed comparison protocol](week9-variant-quality-comparison.md),
[actual responses and blank scorecard](../../benchmarks/history/week9_variant_quality_phi_2026-10-06.md)
and [complete JSON](../../benchmarks/history/week9_variant_quality_phi_2026-10-06.json)
address the outstanding Week 8 comparison. Their existing `week9` filenames and
protocol identifier reflect when the run was prepared; they do not reclassify an
unfinished Week 8 requirement. Those original artifacts are preserved unchanged.

Phi `phi4-mini:3.8b` ran three repeats per architecture under Prompt `0.4.13`
and policy `0.3.1`: 264 executed records passed selected automated checks,
24 planned records were Not covered, and 36 calls invoked the real local model.
These represent 22 executable questions per architecture, not 264 independent
cases. Q1/Q7 share a fixture; Q2/Q8 remain excluded. Each question's response
text was identical across architectures and repeats, so this sample does not
establish a retrieval or agent quality benefit. Human decisions remain blank.
All 35 explicitly recorded source hashes matched after execution.

The six explicit related test modules passed 80 tests, including eight new
benchmark regressions, and Ruff passed. No full suite, sealed integrity test or
GitHub CI ran for this local comparison. No product prompt, model selection,
shared API, retrieval source or statistical implementation was changed.

Close-out requires independent rubric decisions under the existing
[rubric](../evaluation/response-quality-rubric-v0.1.md) and
[thresholds](../evaluation/pass-threshold.md), with limitations retained.
ME-P02 separately requires both halves, both evaluators' questionnaires and
response/screenshot evidence under the
[pairing plan](../evaluation/week8-main-evaluation-roster.md). The offline run
does not count as that session. The following sections describe the earlier
integration implementation and its dated verification.

## Integration delivery and attribution (28 September)

Honghao/AllenLi supplied the canonical packet retriever and source tests in
[PR #37](https://github.com/PriyanshUsyd/mindsense-capstone/pull/37), then connected
it to the live Ollama HTTP path in
[PR #39](https://github.com/PriyanshUsyd/mindsense-capstone/pull/39).
Both are merged. It is no longer accurate to call the current source missing or
the Ollama HTTP default Base-only.

This continuation retains that source and its tests. It completes Richard's
SLM composition and bounded tool execution, adds an optional HTTP variant, and
corrects two integration defects: eager retrieval before packet safety checks,
and source bindings generated from the retriever's own returned metadata.
Changes to the shared API extend the existing Priyansh/AllenLi boundary and
require Integration review; they are not a new Data implementation.

The supported scope is descriptive retrieval from the current validated
EvidencePacket. There is no independent history store, vector index, external
reference corpus, new statistic, autonomous model planner or application memory.
Transporting information already in the packet does not prove a retrieval
quality benefit.

## Guardrails delivered in PR #34 and the current continuation

| Trigger | Safe behaviour |
| --- | --- |
| No feature words and no selected feature | Clarification before participant lookup; no guessed GPS default |
| Both supported features, or selection conflicts with question | Clarification without answering from a different feature |
| Explicit time range such as last three days, a date or today | Explain unsupported window; do not substitute the packet's dates |
| Contextual in-scope question with a supported selected feature | May proceed using that scope |
| Diagnosis request | Deterministic diagnosis refusal |
| Crisis/prohibited question with dates or ambiguous features | Crisis/prohibited policy retains priority |
| Healthy State B input | Preserve the allowed descriptive uncertainty answer |

Request policy is now `0.3.1`. Generation Prompt `0.4.13`, existing fallback
templates, output grounding `0.1.1`, the EvidencePacket and SafeSLMResponse
schemas and model manifest are unchanged in this continuation. The English
window detector is bounded, not a general date parser. Moe's merged PR #38
documents the window decision and packet-side rounding; this work does not
change either statistical rule.

PR #38 also recorded SLM detection gaps for spelled-out durations, month
abbreviations and seasons/terms. This continuation covers the missing English
number words, common month abbreviations (including Sep/Sept), month-year
expressions, season expressions and academic terms/semesters. Twenty-two
additional regressions cover those boundaries, benign controls and unchanged
crisis/diagnosis priority. The pre-fix scope run reproduced 13 failures. This
is a bounded English guardrail improvement, not a general calendar parser or
permission to answer a requested period using the default packet.

At the 28 September integration delivery, the
[methodology](week8-prompting-methodology.md) was documentation only: zero/few-shot
results were Not run and multi-turn had its own planned section. The current
9 October Z/F result is described above; multi-turn remains planned.

## HTTP behaviour

`POST /respond` accepts optional `variant` alongside the existing participant,
question, feature and model fields. See the [API guide](../../backend/api/README.md).

| Requested mode | Context preparation on a healthy, in-scope packet |
| --- | --- |
| `base_llm` | Existing SLM service; no retrieval/tool context |
| `rag` | One call to ApprovedPacketRetriever, up to three items (current source returns two) |
| `agent` | Deterministic selection of registered `get_packet_summary`; one bounded source call |
| `rag_agent` | The same tool, then retrieval with its two items as seed context; four distinct context IDs |

Omission preserves merged PR #39 behaviour: Ollama uses RAG; demo/non-Ollama
injected services use Base. Allowed context requests on demo return HTTP 422
before participant lookup. Invalid variant values and blank/over-2000-character
questions receive the existing privacy-safe 422. Deterministic policy responses
retain priority. Existing model-tag selection and response shape are unchanged.

The UI does not yet expose a variant selector; that remains Frontend scope.
The repository has no checked-in OpenAPI export script/artifact. An HTTP schema
regression checks the generated enum and optional field directly rather than
inventing an unrelated type-generation system.

## Request-scoped composition and source binding

`backend/slm/packet_variants.py` composes the existing protocols. The API
injects the Data-owned retriever; the SLM module does not import Data internals.

Execution order:

```text
HTTP schema + model selection + request preflight
  -> server-built EvidencePacket
  -> runner policy, scope, packet health and eligibility checks
  -> bounded source/tool calls
  -> independent source binding + canonical content validation
  -> fresh one-request context client
  -> existing Ollama transport, draft safety and grounding
  -> unchanged SafeSLMResponse
```

The source contract is fixed independently of retrieval output:

- Personal context IDs: `packet-summary:1` and `packet-summary:2`.
- Provenance: `evidence-packet:canonical-summary:1` and `:2`.
- Source class: `personal_summary`; data class: `aggregated_personal_summary`.
- Tool records prefix both IDs and provenance with `tool:`, use `tool_result`,
  and preserve source content/data classification.
- Every binding includes an in-memory digest of the complete current packet.
  Nothing is approved by reading whatever metadata the retriever returned.

The tool consumes at most three iterator entries to enforce its two-item limit.
Unknown metadata stays unknown after wrapping and fails closed. RAG+Agent uses
separate namespaces so the tool and retrieved records cannot collide.
The selector calls one registered tool deterministically. The current retriever
ignores question/seed for lookup, so this is bounded composition, not
query-expanding autonomous reasoning.

`PacketContextResponder` still permits only the exact canonical descriptions:

1. Existing feature value/unit, window dates and observed/expected days.
2. Existing eligibility state.

Arbitrary prose, changed numbers, new associations, participant references,
unknown sources/classes and replayed bindings are rejected. Context IDs never
become draft evidence IDs. The model receives only context IDs and descriptions;
binding digests/provenance are not forwarded. Diagnostic context references omit
content; ordinary HTTP responses do not expose the trace or context.

The responder/factory default still rejects aggregated summaries unless
explicitly enabled. The HTTP composition preserves PR #39's enabled setting;
this setting and its merge are not a separate Privacy approval certificate.
Only synthetic data was used for this continuation. Real personal-summary use,
retention and final acceptance require the appropriate owner review.

## Failure behaviour

Before this continuation, the API retrieved once to construct its own approvals
and again inside the runner. The first call could raise HTTP 500 on State A or
source failure, bypassing the runner's safe handling. It could also approve an
unknown returned provenance value.

The API now constructs independent bindings without retrieving. State A and
unhealthy/refused/crisis inputs reach their existing safe response with no
retrieval or model call. Source/tool failures produce
`approved_context_unavailable`, the versioned generic fallback and
`model_invoked=false`. There is no silent fallback to a successful Base run
labelled RAG. Unexpected responder errors retain sanitised HTTP failure because
their invocation state cannot safely be inferred.

Each request gets a fresh responder/context client. Later Base requests contain
no residual context. Existing privacy-safe errors, constant exception logging,
`Cache-Control: no-store`, participant lookup and local-demo protection remain.

## Verification on 28 September

Three API regressions reproduced the unsafe eager retrieval and self-binding
behaviour before implementation. The focused repaired API checks passed,
including AllenLi's original HTTP retrieval test.

The final explicit SLM/API/contracts/network/API-privacy/scanner allow-list
passed **459 tests**, including 81 added checks across integration and window
hardening, with two existing Starlette/httpx deprecation warnings. The earlier
436-test pass and separate smoke-harness pass preceded the last policy change
and are superseded by this final run. Initial sandbox execution had three
temporary-directory permission errors; the same allow-list succeeded with normal
local permissions.
These are local development checks, not full CI, held-out or owner acceptance.

```powershell
$env:MINDSENSE_CI_SCOPE = 'sealed-excluded'
.venv/Scripts/python.exe -m pytest tests/slm tests/api tests/contracts tests/privacy/test_no_network_egress.py tests/privacy/test_api_response_privacy.py tests/privacy/test_analysis_output_privacy.py -q -p no:cacheprovider
```

For the 28 September publication, broad pytest and the sealed integrity test
were excluded under the access restriction then in force. Its scanner excluded
the sealed directory before file access, and PR #43 used a skip marker followed
by exact-head manual `sealed-excluded` validation. That historical procedure
does not apply to this Week 9 PR. The current automatic full-CI scope is described
above; neither historical restricted run establishes sealed integrity or human
acceptance, and no workflow definition is changed by this delivery.

The new functional smoke uses the real API, Data retriever, SLM tool/runner and
local model. Only packet construction is replaced by public synthetic fixtures.
All four variants cover State C GPS and descriptive State B unlock:

- [Phi](../../benchmarks/history/week8_packet_api_phi_2026-09-28_policy031.json): 8/8.
- [Qwen](../../benchmarks/history/week8_packet_api_qwen_2026-09-28_policy031.json): 8/8.
- Ollama `0.33.2`; installed digest prefixes `78fad5d182a7` (Phi) and
  `359d7dd4bcda` (Qwen), both matching the existing manifest.
- [Initial Phi attempt](../../benchmarks/history/week8_packet_api_phi_2026-09-28.json):
  0/8, all stopped by off-topic policy before generation. The smoke's generic
  question was corrected to existing scoped questions; the initial retry did
  not change policy. The separate window hardening described above was then
  applied and both models rerun on policy `0.3.1`. The earlier successful
  policy-`0.3.0` smoke records are retained as intermediate evidence.

Use a new output filename; prior evidence is never overwritten:

```powershell
.venv/Scripts/python.exe -m benchmarks.slm_packet_api_smoke --model phi4-mini:3.8b --out benchmarks/history/week8-packet-api-NEW-RUN.json
```

Raw source hashes, base revision, dirty-tree status, response metadata and
actual model-call context IDs are recorded. The benchmark imports no new
network client: calls still delegate to `backend/slm/client.py`.
No new dependency, real participant output, prompting experiment, model ranking
or human evaluation result is introduced.

## Owner acceptance snapshot (28 September)

| Owner | Boundary / next step |
| --- | --- |
| Richard | Packet-summary integration and local verification complete; this supplement is supplied for review |
| Honghao | Source/tests retained; review the thin tool's reuse of source metadata; separate persistent-store work remains his scope |
| Moe | Existing packet fields/rounding/claim permissions retained; no bootstrap or inference implementation added |
| Yuktha | Confirm personal-summary enablement, metadata/logging and retention scope |
| Priyansh | Review shared API continuation, agree packet-summary scope and accept the integrated build |
| Sheng | Existing demo/UI PRs #32/#33 are merged; review any future variant selector separately |
| Chonghao | Own joint acceptance and later controlled architecture/method evaluation |
| Honglin | Own Status Checking 2 submission; PR #42 remained open at the time of review |

The 24 September 343-test/public-safety/context-smoke records remain historical:
[public scorecard](../../benchmarks/history/week8_evaluation_alignment_2026-09-24.md),
[safety JSON](../../benchmarks/history/week8_prohibited_baseline_2026-09-24.json),
[off-topic JSON](../../benchmarks/history/week8_off_topic_2026-09-24.json) and
[original synthetic context smoke](../../benchmarks/history/week8_context_phi_smoke_2026-09-24_scope_final.json).
