# Week 8 SLM Safety and Context Integration

- Owner: Richard Zhao, SLM Integration Lead
- Updated: 28 September 2026
- Integration base: `main@9abda9b369def04de1d370550c8a3db966b78263`
- Review branch: `Rz-week8`; Week 8 supplementary delivery following PR #34
- Earlier delivery: [PR #34](https://github.com/PriyanshUsyd/mindsense-capstone/pull/34), merged 26 September

## Current delivery and attribution

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

The [methodology](week8-prompting-methodology.md) remains documentation only:
zero/few-shot results tables are empty and planned multi-turn work retains its
own section. No prompting-method experiment has been run.

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

Never run broad pytest or the sealed integrity test. The scanner excludes the
entire sealed directory before file access. The earlier PR #34 restricted CI
result applies to its earlier head, not this local continuation. Automatic PR
CI still selects full scope. Publication retains `[skip ci]` to prevent that
automatic run; the existing manual `sealed-excluded` workflow is the permitted
validation path. Its result must be checked on this supplementary PR's exact
head, not inferred from PR #34. Workflow definitions are unchanged, and restricted
checks do not establish sealed integrity or full acceptance.

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

## Owner acceptance still outstanding

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
