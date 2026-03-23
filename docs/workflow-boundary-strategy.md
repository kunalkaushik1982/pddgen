# Workflow-Boundary Strategy

This document defines how to build the stronger workflow-boundary capability on top of the current multi-process session model.

It focuses on four workstreams:

- segment extraction
- semantic enrichment
- process boundary detection
- AI + HITL classification

## Why This Exists

The current system can separate simpler same-vs-different process cases, but it is still too weak for enterprise workflow boundary decisions.

Current grouping is largely transcript-level.

That is not sufficient for scenarios like:

- one long recording containing multiple workflows
- one workflow spanning multiple applications
- one later upload refining an existing process without changing others
- mixed same-process and new-process evidence inside the same session

## Current Baseline

The existing worker already has:

- transcript interpretation
- simple process grouping
- canonical merge within process groups
- process-aware review surfaces

Relevant current components:

- `worker/services/ai_transcript_interpreter.py`
- `worker/services/process_grouping_service.py`
- `worker/services/draft_generation_stage_services.py`
- `worker/services/canonical_process_merge.py`

Current weakness:

- grouping happens at transcript level, not at segment level
- classifier is not yet reasoning strongly over workflow continuity
- there is no real confidence-based AI + HITL decision path

## Product Rule This Strategy Must Support

### Rule 1. Same Process

If new evidence belongs to an existing workflow:

- update only that process group
- improve matching steps
- insert missing steps
- do not create a duplicate process tab

### Rule 2. Different Process

If new evidence introduces a different workflow:

- create a new process group
- leave existing process groups unchanged

### Rule 3. Cross-Application Flow

If one workflow spans multiple applications:

- treat it as one process group when business objective and downstream continuity remain the same

### Rule 4. One Recording, Multiple Workflows

If one long recording contains multiple workflows:

- split by segment
- allow one transcript to contribute to multiple process groups

## Core Design Principle

Do not classify whole transcripts as if they belong to exactly one workflow.

Instead:

- split transcripts into meaningful segments
- enrich each segment semantically
- detect workflow boundaries between adjacent segments
- group segments into process groups

This moves the system from transcript-level grouping to workflow-level grouping.

## Stage 1. Segment Extraction

### Goal

Turn a transcript into timestamped units of workflow meaning.

### Segment Definition

A segment is:

- a short timestamped transcript chunk
- representing one business action or a small action bundle

### Required Output Per Segment

- `id`
- `session_id`
- `meeting_id`
- `transcript_artifact_id`
- `start_timestamp`
- `end_timestamp`
- `text`
- `segment_order`

### Extraction Heuristics

Start with deterministic segmentation before AI refinement:

- transcript timestamps
- sentence boundaries
- imperative/action phrases
- speaker transitions if available
- transition phrases such as:
  - `now`
  - `next`
  - `after that`
  - `once saved`
  - `then go to`

### Notes

This should begin as a worker-side transient structure before introducing a permanent DB model.

## Stage 2. Semantic Enrichment

### Goal

Label each segment with business-relevant semantics so downstream workflow-boundary reasoning has stronger signals.

### Target Enrichment Fields

- `application_name`
- `business_object`
- `action_verb`
- `business_goal_candidate`
- `handoff_hint`
- `screen_or_tcode`
- `confidence`

### Example

Segment:

- `Open VA01 and enter sold-to party`

Enrichment:

- app: `SAP`
- object: `sales order`
- action: `create / populate`
- goal candidate: `sales order creation`

### Implementation Approach

Use AI first, but normalize the result into deterministic enums or narrow strings where possible.

This should happen in the worker after segment extraction and before process grouping.

## Stage 3. Workflow-Boundary Detection

### Goal

Decide whether the next segment:

- continues the same workflow
- starts a different workflow
- or is uncertain

### Key Signals

- business goal continuity
- business object continuity
- downstream handoff continuity
- application hop with same business objective
- explicit transcript transition markers
- sharp narrative break
- timestamp gap

### Important Rule

Application boundary is not process boundary.

Example:

- SAP -> Oracle -> SFDC

can still be one process group if business objective and downstream continuity remain intact.

### Output

For each adjacent segment pair:

- `same_workflow`
- `new_workflow`
- `uncertain`

plus confidence and reason summary.

## Stage 4. AI + HITL Classification

### Goal

Use AI for semantic judgment, but avoid AI-only authority.

### Correct Operating Model

- AI does first-pass workflow classification
- deterministic checks support the decision
- low-confidence decisions go to user confirmation

### Decision Modes

#### High Confidence

- auto-merge into existing process group
- or auto-create a new process group

#### Medium / Low Confidence

Surface HITL choice:

- `Merge into existing process`
- `Create new process`

### HITL UX Requirement

The user must not be asked abstract questions.

The UI should show:

- proposed process title
- evidence snippet
- why the system thinks it matches or differs

## Proposed Implementation Phases

## Phase 1. Observability First

Before changing persistence heavily, add debug visibility for:

- extracted segments
- enriched semantics
- candidate workflow labels
- confidence
- boundary decisions

### Deliverable

Worker logs and optional debug payload structure.

## Phase 2. In-Memory Segment Pipeline

Implement:

- segment extraction
- semantic enrichment
- boundary detection

without changing the DB schema yet.

### Deliverable

A worker-internal segment graph that can replace transcript-level grouping input.

## Phase 3. Segment-Aware Grouping

Replace transcript-level grouping with segment-aware process grouping.

### Deliverable

One transcript can contribute segments to:

- one process group
- or multiple process groups

depending on workflow boundaries.

## Phase 4. Confidence Scoring

Add explicit confidence bands:

- high
- medium
- low

for same-vs-new process decisions.

### Deliverable

Worker output that can drive HITL UI.

## Phase 5. HITL Resolution

Add a user-facing ambiguity resolution step for low-confidence process assignment.

### Deliverable

Session UI support for:

- accept suggested match
- choose another existing process
- create a new process

## Phase 6. Incremental Regeneration

Once process resolution becomes strong enough, move from full rebuild to process-group-scoped regeneration.

### Deliverable

- same-process upload updates only that process group
- different-process upload creates a new process group
- unrelated processes remain unchanged

## Suggested Code Changes

### New Worker Module Candidates

- `worker/services/transcript_segmenter.py`
- `worker/services/segment_enrichment_service.py`
- `worker/services/workflow_boundary_service.py`
- `worker/services/process_resolution_service.py`

### Existing Services To Evolve

- `worker/services/ai_transcript_interpreter.py`
- `worker/services/process_grouping_service.py`
- `worker/services/draft_generation_stage_services.py`
- `worker/services/canonical_process_merge.py`

## Suggested Data Shape For Internal Processing

```python
{
  "segment_id": "...",
  "transcript_artifact_id": "...",
  "meeting_id": "...",
  "start_timestamp": "00:03:21",
  "end_timestamp": "00:03:54",
  "text": "...",
  "application_name": "SAP",
  "business_object": "purchase order",
  "action_verb": "enter",
  "business_goal_candidate": "purchase order creation",
  "handoff_hint": "continues in supplier validation",
  "workflow_boundary_confidence": "medium",
  "process_group_candidate": "purchase-order-creation"
}
```

## Success Criteria

The strategy should eventually support all of these correctly:

### Case 1. Same Process Across Multiple Meetings

- later evidence updates the same process group

### Case 2. Different Processes Across Multiple Meetings

- later evidence creates a new process group

### Case 3. One Long Meeting With Multiple Workflows

- one transcript contributes to multiple process groups

### Case 4. One Workflow Across Multiple Applications

- one process group spans SAP, Oracle, SFDC when the business objective remains continuous

## Immediate Recommended Next Step

Start with:

- Phase 1 observability
- Phase 2 in-memory segment pipeline

Do not jump directly to DB-heavy persistence changes first.

That keeps the next iteration measurable and lowers rework risk while the workflow-boundary logic is still being tuned.
