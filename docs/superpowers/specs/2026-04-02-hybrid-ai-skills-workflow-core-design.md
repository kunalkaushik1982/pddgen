# Hybrid AI Skills Workflow Core Design

## Purpose

This document defines the second implementation slice for the hybrid AI skill architecture in `PddGenerator`.

The first slice established:

- the worker-side hybrid AI skill framework
- the first migrated skill: `transcript_to_steps`
- compatibility wiring through [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py)
- runtime proof that the real worker flow used the new skill path

This second slice extends that architecture into the workflow-intelligence core by migrating:

- `semantic_enrichment`
- `workflow_boundary_detection`

These are the two most important next capabilities because they drive:

- segment-level workflow understanding
- workflow continuity reasoning
- future grouping quality
- future human-in-the-loop workflow review

## Scope

This slice will implement:

- one new hybrid AI skill for semantic enrichment
- one new hybrid AI skill for workflow-boundary detection
- registry wiring for both skills
- service-layer integration so current strategy classes call the new skills
- compatibility preservation through the current worker orchestration and heuristic fallback logic
- targeted tests and runtime logs

This slice will not implement:

- process-group title resolution migration
- workflow-group matching migration
- summary generation migration
- diagram generation migration
- session Q&A migration
- database changes
- API changes
- UI changes
- HITL workflow review surfaces
- retry or rate-limit handling improvements

## Why These Two Skills Next

`semantic_enrichment` and `workflow_boundary_detection` are the real workflow-intelligence center of gravity.

In the current codebase:

- transcript-to-steps produces structured step output
- enrichment interprets segment meaning
- boundary detection decides whether adjacent segments remain one workflow

Those two skills already have explicit strategy seams in:

- [worker/services/workflow_strategy_interfaces.py](C:/Users/work/Documents/PddGenerator/worker/services/workflow_strategy_interfaces.py)
- [worker/services/evidence_segmentation_service.py](C:/Users/work/Documents/PddGenerator/worker/services/evidence_segmentation_service.py)

That makes them the most natural next migration targets.

## Current Architecture Snapshot

Current AI and fallback behavior is split like this:

### Deterministic fallback

In [worker/services/evidence_segmentation_service.py](C:/Users/work/Documents/PddGenerator/worker/services/evidence_segmentation_service.py):

- `HeuristicSemanticEnrichmentStrategy`
- `HeuristicWorkflowBoundaryStrategy`

These use deterministic, text-based logic and should remain in place.

### AI path

Also in [worker/services/evidence_segmentation_service.py](C:/Users/work/Documents/PddGenerator/worker/services/evidence_segmentation_service.py):

- `AISemanticEnrichmentStrategy.enrich(...)`
- `AIWorkflowBoundaryStrategy.decide(...)`

These currently call methods on [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py):

- `enrich_workflow_segment(...)`
- `classify_workflow_boundary(...)`

This means the AI behavior is still embedded inside the large interpreter class rather than being isolated as first-class skills.

## Goal Of This Slice

Move the AI behavior for these two capabilities out of the interpreter-centered design and into explicit skill modules, while preserving:

- the current strategy-based orchestration
- the current heuristic fallbacks
- the current downstream `SemanticEnrichment` and `WorkflowBoundaryDecision` domain objects

## Proposed Folder Structure

The new files should be added under the existing framework:

```text
worker/services/ai_skills/
  semantic_enrichment/
    SKILL.md
    prompt.md
    schemas.py
    skill.py
  workflow_boundary_detection/
    SKILL.md
    prompt.md
    schemas.py
    skill.py
```

These should follow the same pattern as:

- [worker/services/ai_skills/transcript_to_steps/skill.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/transcript_to_steps/skill.py)

## Skill 1: Semantic Enrichment

### Purpose

Interpret one evidence segment into workflow-relevant business labels.

### Current source behavior

Today this AI behavior lives in:

- `AITranscriptInterpreter.enrich_workflow_segment(...)`

And is currently used from:

- `AISemanticEnrichmentStrategy.enrich(...)`

### Input

The new `semantic_enrichment` skill input should include:

- `transcript_name`
- `segment_text`
- `segment_context`
  - `segment_order`
  - `start_timestamp`
  - `end_timestamp`
  - `segmentation_method`

This keeps parity with the current interpreter call.

### Output

The new `semantic_enrichment` skill output should include:

- `actor`
- `actor_role`
- `system_name`
- `action_verb`
- `action_type`
- `business_object`
- `workflow_goal`
- `rule_hints`
- `domain_terms`
- `confidence`
- `rationale`

### Runtime behavior

The skill should:

- load prompt content from markdown
- call the shared AI client
- parse JSON through shared runtime helpers
- normalize confidence values
- normalize list fields like `rule_hints` and `domain_terms`

### Integration behavior

`AISemanticEnrichmentStrategy.enrich(...)` should:

1. build heuristic fallback enrichment first
2. call the new `semantic_enrichment` skill
3. if AI is unavailable or low confidence, keep heuristic output
4. if AI is sufficiently strong, merge AI output with fallback output
5. continue returning the existing `SemanticEnrichment` dataclass

This preserves the current merge behavior while changing only the AI source boundary.

## Skill 2: Workflow Boundary Detection

### Purpose

Classify whether two adjacent evidence segments belong to:

- `same_workflow`
- `new_workflow`
- `uncertain`

### Current source behavior

Today this AI behavior lives in:

- `AITranscriptInterpreter.classify_workflow_boundary(...)`

And is currently used from:

- `AIWorkflowBoundaryStrategy.decide(...)`

### Input

The new `workflow_boundary_detection` skill input should include:

- serialized `left_segment`
- serialized `right_segment`

That serialized data should match the existing strategy-side boundary inputs as closely as possible.

### Output

The new skill output should include:

- `decision`
- `confidence`
- `rationale`

### Runtime behavior

The skill should:

- load prompt content from markdown
- call the shared AI client
- parse JSON through shared runtime helpers
- normalize decisions to the allowed enum
- normalize confidence values

### Integration behavior

`AIWorkflowBoundaryStrategy.decide(...)` should:

1. compute heuristic boundary decision first
2. call the new `workflow_boundary_detection` skill
3. if AI is unavailable or low confidence, keep heuristic decision
4. if AI agrees with heuristic, return an AI-sourced resolved decision
5. if AI conflicts with heuristic, keep the current conflict-resolution behavior
6. continue returning the existing `WorkflowBoundaryDecision` dataclass

This preserves the current conflict-resolution semantics while changing only the AI source boundary.

## Compatibility Strategy

This slice should not redesign the workflow-intelligence orchestration.

Compatibility rules:

- keep [worker/services/evidence_segmentation_service.py](C:/Users/work/Documents/PddGenerator/worker/services/evidence_segmentation_service.py) as the strategy orchestration layer
- keep [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py) in place
- move only the AI request/response behavior for enrichment and boundary classification into skills
- keep heuristic strategies unchanged
- keep downstream dataclass shapes unchanged

This mirrors the first slice:

- old orchestrator remains
- new skill owns the AI behavior
- compatibility stays intact

## Logging Strategy

As with `transcript_to_steps`, each migrated AI path should emit runtime proof logs.

Add logs at:

- the strategy layer, when delegating to the skill
- the skill layer, when the skill executes

Desired metadata:

- `skill_id`
- `skill_version`
- segment identifiers where available
- boundary segment ids where applicable

This will let real worker runs prove that these new skills are active.

## Testing Strategy

This slice should add three categories of tests.

### 1. Skill unit tests

For `semantic_enrichment`:

- prompt loading
- confidence normalization
- list normalization
- output parsing

For `workflow_boundary_detection`:

- decision normalization
- confidence normalization
- output parsing

### 2. Compatibility tests

Test that the current strategy classes still return:

- `SemanticEnrichment`
- `WorkflowBoundaryDecision`

with the same downstream-compatible shape expected by the existing segmentation service.

### 3. Integration-focused worker tests

Add or update tests around:

- `AISemanticEnrichmentStrategy.enrich(...)`
- `AIWorkflowBoundaryStrategy.decide(...)`

without forcing a full worker-stack dependency boot unless necessary.

## Non-Goals

This slice is not the place to:

- redesign the heuristic strategies
- redesign grouping algorithms
- redesign confidence policy broadly
- add new persisted workflow-intelligence data models
- refactor all interpreter methods at once
- solve OpenAI rate-limit handling

## Proposed Implementation Sequence

1. add `semantic_enrichment/`
2. define semantic enrichment schemas
3. add semantic enrichment markdown files
4. implement semantic enrichment skill
5. add focused tests
6. wire `AISemanticEnrichmentStrategy` to the new skill
7. add logs
8. verify tests
9. add `workflow_boundary_detection/`
10. define boundary detection schemas
11. add boundary detection markdown files
12. implement boundary detection skill
13. add focused tests
14. wire `AIWorkflowBoundaryStrategy` to the new skill
15. add logs
16. verify tests
17. run one real worker generation and confirm runtime proof logs

## Success Criteria

This slice is successful if:

- `semantic_enrichment` exists as a hybrid AI skill
- `workflow_boundary_detection` exists as a hybrid AI skill
- evidence segmentation strategies use those skills for AI behavior
- heuristic fallback behavior remains intact
- existing downstream domain dataclasses remain stable
- runtime logs prove the new skills execute in a real worker run

## Follow-On Recommendation

After this slice, the next best migration targets are:

1. `workflow_title_resolution`
2. `workflow_group_match`
3. `process_summary_generation`

That sequence continues moving the workflow-intelligence AI layer out of the interpreter-centered design and into explicit hybrid skills.
