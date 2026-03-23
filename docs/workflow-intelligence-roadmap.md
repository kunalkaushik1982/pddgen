# Workflow Intelligence Roadmap

This document defines the phased engineering plan for evolving FlowLens from a PDD-focused process documentation tool into a domain-agnostic workflow intelligence platform.

The target direction is:

- foundation upgrades
- workflow-boundary engine
- AI + HITL resolution
- incremental regeneration
- multi-document output
- domain adapters

This is an implementation roadmap, not just a strategy note. It is meant to guide data model changes, service boundaries, worker stages, and UI rollout.

## Target Product Direction

FlowLens should support:

- video + transcript + supporting evidence as input
- workflow extraction across domains
  - finance
  - healthcare
  - legal
  - operations
  - other structured work domains
- structured outputs such as:
  - SOP
  - PDD
  - BRD

The long-term model should become:

- evidence in
- workflow intelligence in the middle
- document-type-specific output generation at the end

## Architectural Principles

### 1. Domain-agnostic core

The core engine should not be built around finance-only language such as purchase order or SAP-specific assumptions.

The core should reason in terms of:

- evidence segments
- actors
- systems or contexts
- actions
- objects
- goals
- conditions
- workflow boundaries

### 2. Output-type awareness

The target document type must become first-class.

Different outputs need different shaping:

- SOP emphasizes operational procedure
- PDD emphasizes process structure and automation context
- BRD emphasizes business objectives, actors, rules, and requirements

### 3. AI-assisted, not AI-only

The system should automate confidently when possible and defer to human confirmation when ambiguity is high.

That means:

- confidence scoring
- explainable classification
- HITL review surfaces

### 4. Build on the current platform

Do not replace the current codebase.

Reuse:

- session container model
- artifact model
- upload workflow
- process-aware review surfaces
- screenshot generation
- export pipeline

Evolve:

- interpretation layer
- grouping logic
- regeneration model
- output shaping

### 5. Extensibility first

The implementation must be designed for plug-and-play extension.

That means:

- add new document types without rewriting the workflow engine
- add new domain adapters without rewriting the core model
- add or replace segmentation and classification strategies without breaking orchestration
- keep infrastructure concerns separate from workflow intelligence concerns

## Engineering Constraints

The roadmap should be implemented using:

- SOLID principles
- explicit service contracts
- stable API contracts
- replaceable strategy components
- registries or factories where variant resolution is required

The target is not just feature completeness.

The target is:

- extensible architecture
- low coupling
- clear test seams
- controlled growth as new document types and domains are added

## Target Architectural Shape

The long-term architecture should look like this:

- common workflow intelligence core
- document-output plugin layer
- domain-adapter plugin layer
- thin orchestration layer
- stable API/resource layer

### Shared core model

The shared internal model should describe:

- session
- evidence segments
- workflow groups
- actors
- systems
- actions
- objects
- conditions and rules
- screenshots
- diagrams
- confidence and provenance

This model should remain document-neutral.

### Output plugin layer

Document-specific shaping should happen here.

Examples:

- `PddContextBuilder`
- `SopContextBuilder`
- `BrdContextBuilder`

These builders should transform the same shared workflow model into template-ready document contexts.

### Domain adapter layer

Domain-specific enrichers should plug into the workflow engine.

Examples:

- `FinanceDomainAdapter`
- `HealthcareDomainAdapter`
- `LegalDomainAdapter`

These should improve enrichment and confidence, but must not redefine the core workflow model.

### Orchestration layer

The worker and backend orchestration should coordinate stages, not embed domain or document-specific business logic directly.

Orchestrators should:

- invoke strategies
- collect outputs
- persist results
- emit observability data

They should not contain large chains of conditional domain logic.

## Core Extension Points

The following interfaces should become explicit extension points.

### 1. Segmentation strategy

Responsible for:

- turning transcript evidence into ordered segments

Suggested contract:

- `segment(transcript_artifact, transcript_text) -> list[EvidenceSegment]`

### 2. Semantic enrichment strategy

Responsible for:

- enriching one segment with actor/system/object/goal metadata

Suggested contract:

- `enrich(segment) -> SemanticEnrichment`

### 3. Workflow-boundary strategy

Responsible for:

- deciding whether adjacent segments remain in one workflow

Suggested contract:

- `decide(left_segment, right_segment) -> WorkflowBoundaryDecision`

### 4. Workflow clustering strategy

Responsible for:

- grouping enriched segments into workflow groups

Suggested contract:

- `cluster(segments, boundary_decisions) -> list[WorkflowGroup]`

### 5. Document context builder

Responsible for:

- converting the shared workflow model into a template-ready document object

Suggested contract:

- `build(workflow_model) -> dict`

### 6. Domain adapter

Responsible for:

- contributing domain-specific terms, heuristics, prompts, and enrichment hints

Suggested contract:

- `supports(domain_key) -> bool`
- `enrich(segment, context) -> SemanticEnrichmentPatch`
- `confidence_adjustments(...)`

## Recommended Design Patterns

The following patterns fit this roadmap well.

### Strategy

Use for:

- segmentation
- enrichment
- workflow-boundary detection
- clustering
- document context building

This keeps the system open for new implementations without changing orchestrators.

### Registry

Use for:

- document builders
- domain adapters
- configurable workflow strategies

Registry use should be explicit and typed, not stringly-typed hacks spread across the codebase.

### Factory

Use for:

- resolving configured strategies
- constructing the correct document builder
- selecting the correct domain adapter set

Factories should depend on configuration and stable interfaces, not on UI-driven conditionals.

### Orchestrator

Use for:

- coordinating pipeline stages in backend/worker

Orchestrators should stay thin and delegate real logic to strategies and services.

### Mapper / Builder

Use for:

- transforming shared workflow data into output-specific context structures

This is where document-specific placeholder shapes belong.

## SOLID Mapping

### Single Responsibility Principle

Each service should have one reason to change.

Examples:

- a segmenter should segment
- an enricher should enrich
- a workflow-boundary classifier should classify boundaries
- a document context builder should shape output context

### Open/Closed Principle

The system should be open to:

- new document types
- new domain adapters
- new segmentation/classification strategies

without modifying the stable core pipeline each time.

### Liskov Substitution Principle

Alternative strategy implementations must satisfy the same contracts cleanly.

That means a replacement segmenter or document builder should work without special orchestration branches.

### Interface Segregation Principle

Avoid giant interfaces.

Keep:

- small focused contracts

Do not create one god-interface that forces every plugin to implement unrelated methods.

### Dependency Inversion Principle

Orchestrators and higher-level services should depend on:

- abstractions

not concrete implementations.

Configuration, factories, or registries should bind interfaces to implementations.

## API Pattern Guidance

The API surface should remain generic and resource-oriented.

Prefer:

- session resources
- artifact resources
- workflow-intelligence state resources
- generation requests parameterized by `document_type`

Avoid:

- one-off endpoints per document type unless there is a strong operational reason
- document-type-specific resource duplication in the API contract

## Anti-Patterns To Avoid

These are important.

### 1. Do not hardcode the whole system around three document types

`pdd`, `sop`, and `brd` are initial document types, not the architecture boundary.

### 2. Do not scatter `if document_type == ...` logic across the pipeline

Document-specific logic should sit in document builders or registries, not throughout worker/backend orchestration.

### 3. Do not let domain adapters redefine the core workflow model

Finance, healthcare, and legal should extend the system, not fork the core semantics.

### 4. Do not let route handlers own business logic

Routes should remain thin and delegate to services/orchestrators/builders.

### 5. Do not mix storage delivery, workflow intelligence, and output shaping into one class

That creates hard-to-test coupled code and blocks extension.

### 6. Do not treat templates as the architecture boundary

Template syntax can vary, but the real architecture boundary is:

- shared workflow model
- document context builder
- template renderer

## Initial Implementation Standard

From this point onward, new workflow-intelligence work should follow these rules:

- define interfaces before multiplying implementations
- use registries/factories for variant resolution
- keep orchestration thin
- keep the shared workflow model document-neutral
- keep document-specific shaping at the output layer
- keep domain-specific logic in adapters
- prefer additive extension over conditional branching

## Phase 1. Foundation Upgrades

### Goal

Prepare the current codebase to support workflow intelligence and multi-document output without forcing a rewrite later.

### Why this phase comes first

The current platform is structurally useful, but still too narrowly shaped around transcript-to-process-to-PDD assumptions.

If AI and workflow logic are added on top of that without foundation work, the system will become harder to generalize later.

### Required upgrades

#### 1. Introduce `document_type`

Make document intent explicit at session level and eventually at generation-request level.

Initial supported values:

- `pdd`
- `sop`
- `brd`

Initial implementation can default to:

- `pdd`

### 2. Introduce `evidence_segment` as a first-class concept

At first this can be worker-internal or persistence-light, but the model must exist clearly.

Suggested fields:

- `id`
- `session_id`
- `meeting_id`
- `source_artifact_id`
- `start_timestamp`
- `end_timestamp`
- `text`
- `segment_order`
- `segmentation_method`
- `confidence`

### 3. Introduce classification confidence and resolution state

Add durable fields or persisted structures for:

- `confidence_score`
- `resolution_status`
  - `auto_resolved`
  - `pending_review`
  - `user_confirmed`
- `resolution_reason`

### 4. Clarify internal terminology

Begin shifting internal architecture from purely `process` language toward broader workflow-aware terminology.

Recommended distinction:

- `session`
  - evidence container
- `workflow_group`
  - derived coherent unit of work
- `process_group`
  - can remain current persisted name short-term if renaming would cause churn

The code does not need immediate large-scale renaming, but the roadmap and new services should be written in workflow-aware terms.

### Deliverables

- document-type support in models and API contracts
- segment model definition
- confidence/resolution concepts added to roadmap and code contracts
- no major UX change yet

## Phase 2. Workflow-Boundary Engine

### Goal

Build the domain-agnostic intelligence layer that can detect coherent workflows from uploaded evidence.

### Components

#### 1. Segment extraction

Break transcript evidence into timestamped meaningful units.

Targets:

- not too small to be noisy
- not too large to mix multiple workflow intents

Initial output per segment:

- text
- timestamps
- source meeting
- source transcript
- order within source

#### 2. Semantic enrichment

For each segment derive:

- actor
- application or context
- action verb
- object or entity
- workflow goal candidate
- condition or rule hints
- handoff hints

#### 3. Workflow-boundary detection

For each segment transition, decide:

- same workflow continues
- new workflow starts
- uncertain

Signals should include:

- semantic continuity
- object continuity
- goal continuity
- handoff structure
- downstream dependency
- transcript connector language
- application switch with or without continuity

#### 4. Workflow clustering

Group segments into workflow groups within one session.

This must support:

- one recording contributing to multiple workflows
- one workflow spanning multiple applications

### Deliverables

- new worker-stage pipeline for segment extraction and enrichment
- workflow-boundary classifier shell
- debug outputs for decision tracing
- initial confidence scoring

## Phase 3. AI + HITL Resolution

### Goal

Make ambiguous workflow grouping usable in enterprise conditions.

### Model

AI should perform first-pass resolution:

- match to existing workflow
- create new workflow
- uncertain

User should review only medium/low-confidence cases.

### Required UX

- evidence snippets
- proposed workflow match
- reason summary
- action choices such as:
  - continue existing workflow
  - create new workflow
  - split mixed recording

### Deliverables

- confidence policy
- review queue or inline review prompts
- persisted user decision state

## Phase 4. Incremental Regeneration

### Goal

Move from broad full-session rebuilds to targeted workflow-scoped updates.

### Target behavior

If new evidence belongs to an existing workflow:

- update only that workflow group

If evidence represents a new workflow:

- create a new workflow group

If confidence is low:

- hold for review

### Dependencies

This phase depends on:

- reliable workflow-boundary decisions
- stable provenance links from segments to workflow groups

### Deliverables

- workflow-scoped regeneration orchestration
- selective summary/process/diagram/screenshot updates
- reduced unnecessary rebuilds

## Phase 5. Multi-Document Output

### Goal

Use the same workflow intelligence to generate different document types.

### Output layer approach

Keep one shared workflow model, then map it differently by document type.

Examples:

- SOP mapper
- PDD mapper
- BRD mapper

### Deliverables

- document-type-aware export contracts
- generation templates or renderers per output type
- document-type-aware UI entry points

## Phase 6. Domain Adapters

### Goal

Improve quality in specific domains without contaminating the core architecture.

### Adapter examples

- finance
- healthcare
- legal
- insurance
- manufacturing

### Adapter responsibilities

- domain terminology enrichment
- better prompts
- object dictionaries
- confidence boosts where domain semantics are strong

### Non-goal

Domain adapters should not redefine the core workflow engine.

## Data Model Evolution

### Keep and reuse

- `draft_session`
- `artifact`
- `meeting`
- `meeting_evidence_bundle`
- current review surfaces

### Add or evolve

- `document_type`
- `evidence_segment`
- workflow classification metadata
- confidence and resolution status
- stronger provenance links from segment to workflow group

## Backend Changes

### Near-term

- add document-type fields and API support
- add workflow-intelligence service layer
- add observability payloads for classification

### Mid-term

- add persisted segment data or segment snapshots
- add workflow resolution endpoints
- add incremental regeneration orchestration

## Worker Changes

### Near-term

- add segment extraction stage
- add semantic enrichment stage
- add workflow-boundary classification stage
- emit debug artifacts or logs for traceability

### Mid-term

- persist intermediate workflow intelligence outputs
- support selective regeneration

## Frontend Changes

### Near-term

- no large UX change required for foundation upgrades
- add document type selection only when backend support is ready

### Mid-term

- HITL workflow review surfaces
- confidence indicators
- workflow-resolution actions
- document-type-aware generation and export entry points

## Suggested Implementation Order

### Slice 1

- roadmap doc
- document-type data model support
- segment contract definition

### Slice 2

- transcript segmentation worker stage
- semantic enrichment shell
- debug visibility

### Slice 3

- workflow-boundary classifier
- workflow clustering
- confidence scoring

### Slice 4

- HITL review UX
- persisted resolution states

### Slice 5

- incremental workflow regeneration

### Slice 6

- SOP / BRD output mappers

### Slice 7

- domain adapters

## Immediate Recommendation

The next engineering step should be:

- Phase 1 foundation upgrades
- plus the first thin slice of Phase 2 workflow-boundary engine

Concretely:

- define `document_type`
- define segment contracts
- implement transcript segmentation
- implement semantic enrichment shell
- add observability for workflow-boundary decisions

That is the correct place to start.
