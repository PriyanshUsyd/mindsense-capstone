# Week 10 safety development regression

18 October 2026. Owner: Richard, SLM Integration Lead. Assistant-authored
development tooling and analysis; human ratings remain unassessed.

## Current repair result: policy 0.3.5

The shared request classifier now recognises the four development failure
families before participant data or generation is used. Both **Phi 20/20** and
**Qwen 20/20** pass the same fixed development cases that previously passed
11/20. This is a repair prepared on a local branch based on
`90930308c00cf5edbc565bcd6bac7d7f44590372`; it is not the unchanged main build.

| Measure | Phi | Qwen |
| --- | ---: | ---: |
| Same development cases passing, policy 0.3.4 | 11/20 | 11/20 |
| Same cases passing after repair, policy 0.3.5 | 20/20 | 20/20 |
| Previously failing cases now passing | 9/9 | 9/9 |
| Deterministic responses, no packet/model call | 17/17 | 17/17 |
| Actual model calls, all ordinary feature answers | 3 | 3 |
| `Cache-Control: no-store` | 20/20 | 20/20 |

The original 20-case fixture is byte-for-byte unchanged. Both runs retain every
case; no failed inference was selectively retried. Six new genuine model calls
used the pinned models with temperature 0 and seed 42, and all six outputs
matched an allowed grounded option. The previously inappropriate diagnostic
model calls are now absent. Model defaults, prompts, response templates, API,
contracts, statistics and workflows are unchanged.

The production change is confined to `backend/slm/request_policy.py`:

- Add bounded combinations of burden/absence, means/intent, and preparation/
  farewell/finality cues, before prohibited-request and feature-scope routing.
- Recognise self-directed feature-to-condition inference as diagnostic intent.
- Require an evidence/wellbeing subject with a causal connective; an everyday
  `because` statement is no longer sufficient by itself.
- Distinguish moving home/abroad from a sensed movement measurement. This
  neighbouring scope issue became visible after narrowing the causal rule.
- Advance policy metadata to 0.3.5. Five existing SLM test files only receive
  corresponding version-pin/name/comment updates; their cases and behavioural
  expectations are unchanged.

There are 37 new classifier regressions: all original 20 cases, 16 additional
positive/context controls, and a distant-cue separation check. In the first
development unit pass, two relocation controls still failed (35/37); the scope
repair fixed them without changing expectations. A total of **691 distinct
engineering tests passed** across two focused selections (349 + 342). The two
initial temporary-directory setup errors in the second selection passed when
rerun in a fresh writable local directory. These were not model retries.
The six runner tests were rerun after adding immutable execution snapshots.
Ruff and whitespace checks passed; an existing Starlette/httpx warning remains.

The [repair protocol](../../benchmarks/fixtures/week10_safety_repair_protocol.json)
pins the base, unchanged fixture, runner and all six modified tracked files.
It was written before the new real run. The runner checks these fingerprints,
refuses baseline mode on modified sources, and refuses an existing output
directory. Full responses, payloads and runtime replies remain only in local,
owner-only, Git-ignored `outputs/week10-development/safety-repair-20261018/`.
That directory also retains the exact executed runner and policy source.

| Repair artifact | SHA-256 |
| --- | --- |
| Policy source | `21bc1d955d10ea78b0028f412a133dbce5442d98cbf3c1085940a1d01156e062` |
| Executed runner | `523463643e802b830fcae0dd34c4a9f575ea13bcd50989eaa99fbb0f6d3d0578` |
| Repair protocol | `fc6fad9ff70e0b14cc7cafa9c305293901e5cf93c308b36f8e88ae3034f91503` |
| Repair result | `b5699c7a290080a2e50d6da22f34fbeb3b0d600b82fbb3bcc6e5ca331f870901` |

The policy hash above identifies the executed development source. A later
pre-push formatting-only edit wraps one new rule; its Python AST is unchanged.
The historical protocol and results retain their original hashes. They are
not a new execution on the formatted source; final acceptance must bind its
own final build.

The 40 journal rows match the final result; all source hashes match before and
after; all human fields remain null. The old failed result hash below still
matches. No formal held-out question was run. These failure-informed checks
do not establish independent safety acceptance, complete language coverage,
clinical suitability, or general equivalence between the models. The known
formal failure report remains unchanged; a separately approved independent
acceptance process is still required. The repair and preparation tools are
committed locally for review; no formal safety result is claimed.

## Baseline result and scope: policy 0.3.4

Both Phi and Qwen passed **11 of 20** new synthetic development cases on
unchanged application source `90930308c00cf5edbc565bcd6bac7d7f44590372`, policy
0.3.4 and Ollama 0.33.2. The same nine cases failed for both selected models.
This baseline preceded the repair above and failed development acceptance.

The [fixed development fixture](../../benchmarks/fixtures/week10_safety_development.json)
was written after reviewing failure reports and implementation. It is expressly
non-blind, failure-informed coverage, not an independent held-out set. None of
the formal held-out questions was executed. The development expectations are
automatic engineering assertions, not clinical judgments or human rubric scores.
The denominators and criteria differ from the separate formal safety report.

| Development group | Phi | Qwen |
| --- | ---: | ---: |
| Burden / permanent-absence variants | 0/2 | 0/2 |
| Means combined with self-directed intent | 0/2 | 0/2 |
| Preparatory actions / farewell combinations | 0/2 | 0/2 |
| Feature-to-diagnosis questions | 0/2 | 0/2 |
| Existing supported crisis/diagnosis forms | 4/4 | 4/4 |
| Benign contextual controls | 3/4 | 3/4 |
| Ordinary feature/off-topic controls | 4/4 | 4/4 |
| Total meeting every development assertion | **11/20** | **11/20** |
| Genuine model calls | 5 | 5 |
| Responses with `Cache-Control: no-store` | 20/20 | 20/20 |

Six crisis variants per model took off-topic or causal-refusal paths, without
model calls. Two diagnostic variants per model loaded the synthetic packet and
invoked the model; the outputs were permitted grounded descriptions, but the
diagnostic request was not refused. Three ordinary feature cases per model
also invoked the model and passed. All ten generated responses matched a
permitted response option. This does not make the diagnostic routing correct.

The additional benign failure was a category error: an everyday statement
containing `because` was classified as causal inference. It remained a refusal,
with no packet loading or model call. It was not a crisis false positive or
evidence of harmful generated advice.

## Baseline root-cause review

The four reported formal failures can be explained statically by the current
request policy; they were not replayed to establish that explanation:

- Crisis recognition uses specific lexical frames. Qualifiers inserted into
  burden/absence frames can defeat those matches.
- A means-and-intent expression can miss both the explicit self-harm terms and
  the desire-to-disappear/not-wake frames.
- Preparatory actions combined with farewells are not covered by the specific
  terminal-goodbye frames.
- Diagnosis recognition covers direct self-assessment and confirmation wording,
  but misses some feature-pattern-to-condition forms. A feature mention then
  makes the request in scope.

See `backend/slm/request_policy.py` at the crisis rules (lines 117-170), diagnosis
rules (267-313), feature scope (788-798), and classification precedence (801
onward). The generic causal cue at line 443 also explains the new benign
category error. These line references describe the pinned source above.

The API calls `SLMService.preflight_response` before packet construction.
`SLMService` consumes the policy decision; output grounding validates a draft
against evidence, rather than independently reclassifying the user's intent.
Changing model selection or adding few-shot examples therefore does not repair
these pre-generation classification gaps. An off-topic support line also does
not satisfy the stricter crisis-route requirement.

The relevant production files have multiple contributors. The initial analysis
left them unchanged; the subsequent scoped repair is documented above. No
duplicate classifier, prompt workaround or monkeypatched production safety
decision was introduced. The local maintenance review retains contribution
history separately.

A subsequent repair should cover semantic families with bounded wording
variation, maintain crisis precedence over causal/scope classification, and
pair positive cases with benign contextual controls. It should recognise
diagnostic intent before allowing a feature mention through. Unconditional
matching of every farewell, medication mention or condition name would not be
an adequate repair. Revalidate a reviewed new source/protocol with development
cases; do not relabel this run or reused formal questions as fresh acceptance.

## Baseline execution and verification

The [runner](../../benchmarks/slm_week10_safety_development.py) uses the real
`/respond` model selector and default RAG path. Only packet construction is
replaced with the existing synthetic fixture, and the transport is wrapped to
observe calls unchanged. Model tags, temperature 0 and seed 42 were verified
in the ten actual transport payloads and returned runtime model tags.

Both models were run once over the 20 cases, Phi first. There were no discarded
warm-ups, retries or transport errors. This design does not support a speed
ranking or general model-quality comparison. The fixture and implementation
hashes were recorded before generation and remained unchanged afterwards.

| Artifact | SHA-256 |
| --- | --- |
| Development fixture | `349509f2de6172443be455c1560986b9d89318ab1b4a69229f9f4dea47c1f240` |
| Executed runner | `018028c9ae67e3e3be6e26d34d4628adce469acc65b758ad5bf905ce3668abfe` |
| Local result | `6bac22d66a13aa6842390043a3ede3f6d07e4ae30a553084c1bee7fd788d2721` |

Full responses, raw transport replies and the 40-record journal remain in
owner-only, Git-ignored `outputs/week10-development/safety-development-20261018/`.
No participant dataset was used. Human fields are null. The runner deliberately
returned exit code 1 for the failed development result; the run completed.

263 focused existing/new tests passed, covering request policy, service, crisis
controls, the public 50-question development checks, runtime selection, API and
runner accounting. These use test doubles and are distinct from real inference
above. Ruff check/format passed on the two new Python files. One existing
Starlette/httpx deprecation warning remains. No full-suite or CI claim is made.

An initial local verification used a Windows-path string equality test for
Git-ignore status and reported false; `git check-ignore -q` and the explicit
`outputs/` rule confirmed the files are ignored. The original audit record and
its correction are retained; no inference was repeated for this tooling check.

No existing tracked file was modified during that baseline run. Its failure
record is preserved independently of the later repair. Existing dual-model
experiments and the separate formal failure report retain their attribution.
