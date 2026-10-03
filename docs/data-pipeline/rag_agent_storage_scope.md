# Week 7 RAG / Agent Data Storage Scope

**Owner:** Honghao Li — Data Pipeline Lead  
**Status:** Week 7 scoping only  
**Scope:** Data-storage support for Base LLM, RAG, Agent, and RAG+Agent comparison

## 1. Purpose

The Week 7 architecture comparison introduces four answering approaches:

- Base LLM
- RAG
- Agent
- RAG+Agent

The frozen Tier-1 data pipeline will not be modified for this work.

Instead, this document scopes a local storage boundary between the existing
processed/statistical outputs and the new retrieval and agent interfaces.

The storage layer should allow approved participant-level summaries and
provenance to be accessed without exposing raw sensing rows directly to the
SLM context path.

The same storage boundary may also support the existing EvidencePacket
construction path, where expensive statistical results need to be precomputed
offline rather than recomputed during each request.

---

## 2. Existing Data Boundary

The existing data pipeline produces cleaned and quality-controlled Tier-1
feature information.

The pipeline records window and quality metadata such as:

- feature identifier;
- feature unit;
- feature window;
- observed days;
- expected days;
- coverage ratio;
- platform;
- quality flags.

The frozen pipeline remains the source of processed feature data.

The existing Statistics layer additionally produces participant-level
eligibility, baseline, and evidence information used to construct an
EvidencePacket.

Some production-intended participant-level statistical evidence requires
expensive offline bootstrap computation. This should not be recalculated
during an HTTP request.

The backend therefore identifies a need for a precomputed or cached
participant-level evidence table that can be looked up at request time.

Raw sensing records should remain outside the RAG, Agent, and SLM context
path.

---

## 3. Proposed Storage Boundary

The proposed architecture is:

Frozen Tier-1 Pipeline
        |
        v
Processed Feature Outputs
        |
        v
Offline Statistical Analysis
        |
        v
Approved Precomputed Summary Layer
        |
        v
Local Structured Storage
      /       |        \
     /        |         \
Evidence    Retriever   Approved Local Tools
Packet         |               |
Lookup         v               v
              RAG            Agent
                 \           /
                  \         /
                   Local SLM

The storage layer should contain only the minimum information required by
approved EvidencePacket lookup, retrieval, and tool operations.

It should not become a second copy of the raw CES sensing dataset.

---

## 4. Proposed Storage Schema

The storage schema should adapt to the existing frozen EvidencePacket contract
rather than introduce a competing data contract.

The EvidencePacket contract is frozen as contract-v1.0.0. Therefore, the
storage layer should preserve the information required to construct its
FeatureWindow, PersonalBaseline, and StatisticalEvidence components without
changing their meaning or field definitions.

### 4.1 Feature Summary

The structured store should preserve the fields required to reconstruct the
frozen FeatureWindow:

- feature_id
- unit
- window_start
- window_end
- value
- observed_days
- expected_days
- coverage_ratio
- platform
- quality_flags

This is the primary descriptive participant-level summary available to the
RAG and Agent paths.

### 4.2 Baseline Summary

Where available and contract-legal, the store should preserve the information
required to construct PersonalBaseline:

- method
- value
- n_baseline_observations
- eligibility_status
- ineligible_reason

The storage layer must preserve the distinction between insufficient data,
partial descriptive history, and fully eligible history.

A partial-descriptive participant may have a valid FeatureWindow value while
having no StatisticalEvidence.

### 4.3 Precomputed Statistical Evidence

Expensive participant-level statistical evidence should be computed offline
and persisted for request-time lookup rather than recomputed by the SLM,
Agent, Retriever, or HTTP request handler.

Where evidence is available, the stored result should preserve the fields
required by the frozen StatisticalEvidence contract:

- within_person_deviation_estimate
- confidence_interval_low
- confidence_interval_high
- direction
- evidence_strength

The storage layer must also preserve enough model/version provenance to
determine which approved statistical run produced the stored result.

The SLM and Agent must not derive these inferential fields themselves.

### 4.4 Storage Metadata

The storage layer may additionally require internal metadata that is not sent
directly to the SLM, such as:

- summary_id
- participant_lookup_key
- as_of_date
- contract_version
- model_spec_id
- provenance_reference
- generated_at

These fields support lookup, auditing, version control, and reconstruction of
PacketIdentity.

They do not create a new SLM-facing contract.

### 4.5 Participant Identifier Boundary

The persistent participant lookup key must never expose the raw CES uid to the
SLM context.

The frozen PacketIdentity contract already requires participant_ref to be an
opaque reference rather than the raw CES uid.

The current runtime pseudonymisation mechanism is process-local and therefore
should not automatically be reused as a persistent database key.

The persistent identifier strategy must be reviewed by Privacy and
Integration/QA before implementation.

### 4.6 Fields That Should Not Be Independently Recomputed by Storage

The storage layer should not independently invent or reinterpret:

- eligibility rules;
- evidence-strength thresholds;
- direction classifications;
- claim permissions;
- uncertainty policy;
- response modes.

These remain owned by the existing frozen contract and approved
Statistics/SLM policy logic.

Storage is responsible for preserving and retrieving approved outputs, not
creating a parallel statistical or safety policy.

---

## 5. RAG Data Access

The RAG variant should retrieve only approved local summaries or approved
public references.

The Retriever should:

1. query an approved local source;
2. return only bounded results;
3. preserve a stable context ID and provenance reference;
4. avoid returning raw sensing rows;
5. avoid exposing raw participant identifiers in generated context;
6. return only fields approved for SLM use.

The exact retrieval method remains an open design decision.

Because the current participant data is primarily structured numerical and
time-window data, deterministic structured lookup should be considered before
introducing semantic vector retrieval.

A vector index may become useful if a separately approved RAG corpus contains
substantial textual knowledge, guidelines, or public reference documents.

---

## 6. Agent Data Access

The Agent variant should not receive unrestricted database, SQL, or filesystem
access.

Instead, it should use a small whitelist of approved local tools.

Candidate tools include:

- get_recent_feature_summary(...)
- get_baseline_summary(...)
- get_feature_coverage(...)
- get_evidence_state(...)

Each tool should perform a bounded lookup against the approved summary store
and return a structured result that can be converted into the existing
tool-result context interface.

The Agent should not calculate new inferential statistics from raw participant
data.

Statistical evidence exposed through tools must be precomputed or explicitly
approved by the Statistics owner.

This keeps the Agent responsible for bounded orchestration rather than
statistical analysis.

---

## 7. RAG + Agent

The combined variant should use the same approved storage boundary rather than
maintaining a separate participant-data copy.

One possible execution path is:

Question
   |
   v
Approved Local Tool
   |
   v
Structured Participant Summary
   |
   v
Bounded Retrieval
   |
   v
Approved ContextItems
   |
   v
Local SLM

The tool may identify the relevant approved participant-level summary before
the Retriever supplies additional approved context.

The combined design should continue to respect the SLM interface limits on
tool calls, retrieval size, context count, and provenance.

---

## 8. Proposed Local Storage Design

The current backend supports a concrete local structured-storage design.

The storage layer should not persist raw CES sensing rows. Instead, it should
persist approved participant-level descriptive summaries and offline
statistical outputs required by the frozen EvidencePacket contract.

SQLite is the leading candidate for the initial implementation because the
main runtime access pattern is deterministic structured lookup rather than
semantic similarity search.

Three logical tables are proposed.

### 8.1 participant_feature_summary

Purpose:

Store the descriptive FeatureWindow and PersonalBaseline information required
for request-time EvidencePacket construction and approved RAG/Agent access.

Candidate fields:

- summary_id
- participant_lookup_key
- feature_id
- as_of_date

FeatureWindow fields:

- unit
- window_start
- window_end
- value
- observed_days
- expected_days
- coverage_ratio
- platform
- quality_flags

PersonalBaseline fields:

- baseline_method
- baseline_value
- n_baseline_observations
- eligibility_status
- ineligible_reason

Internal metadata:

- contract_version
- model_spec_id
- generated_at
- provenance_reference

A possible logical lookup key is:

(participant_lookup_key, feature_id, as_of_date)

The participant_lookup_key remains unresolved until Privacy and Integration
approve a persistent pseudonymisation strategy.

### 8.2 participant_statistical_evidence

Purpose:

Persist expensive offline participant-level statistical evidence so it does
not need to be recomputed during an HTTP request.

Candidate fields:

- evidence_id
- participant_lookup_key
- feature_id
- statistical_run_id
- within_person_deviation_estimate
- confidence_interval_low
- confidence_interval_high
- direction
- evidence_strength
- evidence_available
- generated_at

These values must come from the approved Statistics pipeline.

The Agent, Retriever, SLM, and storage adapter must not independently
calculate or reinterpret these fields.

A row may be absent when defensible StatisticalEvidence is unavailable.

This preserves the frozen contract rule that descriptive FeatureWindow data
may exist without StatisticalEvidence.

### 8.3 statistical_run

Purpose:

Record provenance for the offline statistical computation that produced a
participant_statistical_evidence result.

Candidate fields:

- statistical_run_id
- feature_id
- model_spec_id
- contract_version
- bootstrap_method
- bootstrap_iterations
- generated_at
- source_artifact_reference
- status

This table separates statistical provenance from participant-facing summary
data and allows stored evidence to be traced to an approved offline run.

### 8.4 Relationship to Existing Statistical Outputs

The existing Tier-1 runner already writes per-feature summary JSON files and
per-person evidence CSV files.

However, the Tier-1 runner intentionally performs only the cheaper statistical
path.

Without separately computed bootstrap standard errors, its per-person evidence
classification safely remains insufficient.

The bootstrap module separately produces per-person slope standard errors and
combines them with the real fitted participant slope estimates.

The production-intended evidence path therefore requires an offline sequence
similar to:

Tier-1 statistical preparation
        |
        v
Real participant slope estimates
        |
        v
Parametric + cluster bootstrap
        |
        v
Per-person bootstrap SE
        |
        v
Evidence intersection
        |
        v
Approved persisted statistical evidence
        |
        v
Request-time lookup

The proposed local store should persist the approved output of this offline
process, not the individual bootstrap replicates.

### 8.5 What Should Not Be Persisted for Runtime RAG/Agent Access

The runtime summary store should not expose:

- raw sensing.csv rows;
- raw GPS observations;
- raw CES uid values;
- individual bootstrap replicate records;
- unrestricted model-frame rows;
- unrestricted SQL access;
- intermediate statistical objects that are not part of the approved
  EvidencePacket-facing result.

Detailed bootstrap artifacts may remain in the existing gitignored analytical
output area for audit or reproducibility, but they should not become the
runtime RAG/Agent data source.

### 8.6 RAG and Agent Access

RAG and Agent should access the store through approved adapters rather than
direct database access.

Example bounded interfaces include:

- get_recent_feature_summary(...)
- get_baseline_summary(...)
- get_feature_coverage(...)
- get_evidence_state(...)

The Retriever may use approved structured summaries as ContextItems.

The Agent may call only registered local tools backed by these bounded lookup
interfaces.

Neither path should receive arbitrary SQL execution capability.

### 8.7 Vector Retrieval

A vector database is not required for the participant-level data described
above.

The current participant summaries are structured, keyed data and are better
suited to deterministic lookup.

If a separate approved textual corpus is later introduced for RAG, semantic
retrieval may be added as a separate retrieval layer without changing the
participant summary store.

---

## 9. Adapter Boundary to the SLM Variant Interface

The proposed storage layer should integrate with the existing Week 7 variant
interface without modifying the frozen EvidencePacket contract or the SLM
variant protocols.

The existing variant interface already defines the required runtime boundary:

- Retriever receives an EvidencePacket, question, top_k, and optional seed
  context, and returns a bounded sequence of ContextItems.
- LocalContextTool receives an EvidencePacket and question and returns a
  bounded sequence of ContextItems.
- ToolSelector selects only tools exposed by the approved registry.
- VariantRequest already carries the EvidencePacket required to identify the
  participant/feature context for a lookup.

The Data-side storage work should therefore provide adapters behind these
interfaces rather than introduce a new SLM-facing API.

### 9.1 Proposed Storage Repository

A small internal repository abstraction should isolate SQLite-specific access
from the RAG and Agent interfaces.

Conceptually:

Local SQLite Store
        |
        v
ApprovedSummaryRepository
       / \
      /   \
Retriever  Local Tools
    |          |
    v          v
ContextItem  ContextItem

Candidate repository operations include:

- get_feature_summary(...)
- get_baseline_summary(...)
- get_statistical_evidence(...)
- get_evidence_state(...)

The repository should perform deterministic, parameterised lookups only.

It should not expose unrestricted SQL execution to the Retriever, Agent,
ToolSelector, or SLM.

### 9.2 Retriever Adapter

A future SQLite-backed Retriever can implement the existing Retriever protocol
without changing `backend/slm/variants.py`.

Conceptually:

retrieve(
    packet,
    question,
    top_k,
    seed_context
) -> Sequence[ContextItem]

The adapter may use information already present in the EvidencePacket to
select approved participant/feature summaries from the local store.

Retrieved database records must be converted into bounded ContextItems before
they enter the SLM context path.

The Retriever should not return raw database rows directly.

For the initial structured participant-summary use case, retrieval should be
deterministic rather than semantic.

The question may help determine which approved summary type is relevant, but
it must not be converted into arbitrary SQL.

### 9.3 Agent Tool Adapters

Agent access should use a small registry of LocalContextTool implementations.

Candidate tools include:

- get_recent_feature_summary
- get_baseline_summary
- get_feature_coverage
- get_evidence_state

Each tool should:

1. receive the existing EvidencePacket and question;
2. perform one bounded repository lookup;
3. convert the approved result into one or more ContextItems;
4. return no raw sensing rows;
5. expose no unrestricted database interface.

The existing ToolSelector should only be able to select registered tool names.

### 9.4 ContextItem Mapping

All information leaving the storage boundary for RAG or Agent use must be
mapped into the existing ContextItem contract.

The mapping should provide:

- context_id
- source
- data_classification
- content
- provenance_ref
- relevance_score, when applicable

The content field should contain only an approved human-readable summary of
the structured result.

Example conceptual content:

"Recent mobility-distance summary: 2.4 km/day over the previous 14-day
window, based on 12 observed days."

The exact wording and which statistical fields may be included require SLM,
Statistics, and Privacy approval.

The ContextItem should never contain:

- raw CES uid;
- raw sensing rows;
- unrestricted model output;
- bootstrap replicate data;
- information outside the approved summary schema.

### 9.5 Context Identity and Provenance

context_id should identify the bounded context item rather than expose a raw
participant identifier.

provenance_ref should allow the result to be traced back to an approved stored
summary or statistical run.

A possible relationship is:

stored summary
    |
    +-- summary_id
    |
    +-- statistical_run_id
             |
             v
       provenance_ref

The exact identifier format remains subject to Privacy and Integration review.

### 9.6 Logging Boundary

The existing variant interface intentionally separates ContextItem content
from the content-free context references retained in VariantRunRecord.

The storage adapter should preserve this design.

Normal benchmark and comparison logs should record identifiers and provenance
needed for audit without copying participant-derived ContextItem content into
the run record.

This keeps storage retrieval auditable while reducing unnecessary duplication
of sensitive context.

### 9.7 No Change Required to variants.py

No modification to the current Retriever, LocalContextTool, ToolSelector, or
VariantRequest protocols is required for the proposed storage design.

The Data-side implementation can be introduced behind those existing
interfaces once the storage schema and privacy boundaries are approved.

This also keeps the Week 7 work compatible with the frozen-build rule:
storage scoping can proceed without modifying the current production RAG/Agent
orchestration interface.

---

## 10. Relationship to Existing Backend Caches

The current participant evidence implementation already uses in-process caches
for cleaned sensing data, EMA data, and per-feature evidence tables.

These caches reduce repeated computation within one running process, but they
do not provide a persistent storage boundary for expensive offline statistical
results.

The proposed storage layer should therefore not simply duplicate the existing
in-memory cache.

Its purpose would be to provide an approved persistent lookup source for
precomputed outputs that are too expensive or inappropriate to derive during
request handling.

This creates a possible shared boundary for:

- EvidencePacket construction;
- RAG retrieval;
- Agent tools;
- RAG+Agent combined execution.

---

## 11. Privacy and Safety Requirements

The storage design should:

- remain local-only;
- exclude raw GPS and other raw sensing rows from the SLM context path;
- expose only the minimum necessary summary data;
- never expose the raw CES uid to the SLM;
- use a privacy-approved participant lookup mechanism;
- preserve provenance for retrieved and tool-generated context;
- avoid copying retrieved sensitive content into benchmark logs;
- support bounded retrieval;
- support bounded and white-listed tool execution;
- avoid giving the Agent unrestricted SQL or filesystem access;
- keep inferential statistical computation outside the SLM/Agent path.

Persistent participant-derived summaries should not be introduced into the
production path until the storage fields, identifier strategy, retention
requirements, and access boundary have received the required Privacy and
Integration review.

---

## 12. Open Decisions

The following items require coordination with other role owners before
implementation.

### Statistics

- Which precomputed participant summaries may be persisted and exposed?
- Is baseline value available and approved for lookup?
- Which evidence states or statistical outputs may be returned by tools?
- Which offline bootstrap/intersection outputs should become part of the
  request-time lookup path?
- What constitutes the authoritative statistical source for each stored field?
- Which bootstrap result should be treated as the approved source for
  participant-level StatisticalEvidence?

### SLM

- What exact query should the RAG Retriever support?
- What ContextItem fields are required from the storage adapter?
- What structured tool-result schemas are required by the Agent variant?
- Does the first RAG experiment require participant summaries only, public
  textual references, or both?
- Which participant-derived fields are approved for inclusion in ContextItem
  content?

### Integration / QA

- Where should the storage repository and adapters sit in the backend?
- How should the persistent store connect to EvidencePacket construction?
- How should it connect to the existing VariantRunner?
- Should the same repository serve EvidencePacket, Retriever, and Agent tools?
- How should database/schema version compatibility be checked at startup?

### Privacy

- Which participant-derived fields may be persisted?
- What stable pseudonymous lookup key, if any, may be persisted without
  storing or exposing the raw CES uid?
- What retention and deletion requirements apply?
- What provenance and logging information is acceptable?
- Should participant-derived summaries be encrypted at rest?
- Which ContextItem data classification should be used for participant-derived
  summaries?

---

## 13. Week 7 Recommendation

For the first implementation, prefer one local structured source shared by the
EvidencePacket lookup, RAG Retriever, and Agent tools rather than introducing
separate participant-data stores for each architecture.

SQLite is the leading candidate for this structured local lookup requirement,
but implementation should wait until the stored fields, participant identifier
strategy, and access contracts are reviewed by the relevant role owners.

The initial design should prioritise:

1. approved precomputed summary data;
2. deterministic structured lookup;
3. compatibility with the frozen EvidencePacket contract;
4. explicit statistical provenance;
5. bounded Retriever and Agent access;
6. local-only execution;
7. separation of raw sensing data from the SLM context path;
8. privacy-minimised logging.

The proposed implementation boundary is:

Offline Statistics
        |
        v
Approved Summary Store
        |
        v
ApprovedSummaryRepository
      /        |         \
Evidence   Retriever    Local Tools
Packet         |            |
               \            /
                ContextItem
                    |
                    v
             RAG / Agent / RAG+Agent

Semantic/vector retrieval should only be added if an approved textual RAG
corpus requires similarity search.

No new Tier-1 features or modifications to the frozen data pipeline are
required for this Week 7 storage-scoping task.

The immediate next step is owner review of the proposed stored fields,
participant identifier strategy, and statistical evidence source before any
production database implementation begins.