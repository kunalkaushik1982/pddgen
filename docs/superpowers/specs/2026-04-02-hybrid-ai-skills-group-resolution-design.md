# Hybrid AI Skills Group Resolution Design

## Purpose

This document defines the third implementation slice for the hybrid AI skill architecture in `PddGenerator`.

The previous slices established:

- the worker-side hybrid AI skill framework
- the first migrated skill: `transcript_to_steps`
- the workflow-core migrations:
  - `semantic_enrichment`
  - `workflow_boundary_detection`

This slice extends that architecture into workflow identity resolution by migrating:

- `workflow_title_resolution`
- `workflow_group_match`

These capabilities decide:

- what one workflow should be called
- what stable slug should identify it
- whether new evidence belongs to an existing workflow group or should form a new one

## Scope

This slice will implement:

- one new hybrid AI skill for workflow title resolution
- one new hybrid AI skill for workflow group matching
- registry wiring for both skills
- process-grouping integration so current grouping orchestration uses the new skills
- compatibility preservation through the current heuristic/grouping flow
- focused tests and runtime logs

This slice will not implement:

- process summary migration
- diagram generation migration
- session chat migration
- capability tagging migration
- database changes
- API changes
- UI changes
- HITL review workflow
- retry/rate-limit handling

## Why These Skills Next

After workflow-core segmentation, enrichment, and boundary reasoning, the next architectural bottleneck is workflow identity resolution.

That logic currently lives across:

- [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py)
- [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py)

Migrating these next will:

- reduce interpreter sprawl
- make workflow identity AI behavior explicit
- keep process grouping service focused on orchestration and heuristics
- create a clean bridge between enriched workflow evidence and persisted process groups

## Current Architecture Snapshot

### AI title resolution

Current AI title resolution lives in:

- `AITranscriptInterpreter.resolve_workflow_title(...)`

It is used from:

- `ProcessGroupingService._resolve_title_with_ai(...)`

### AI workflow-group matching

Current AI group matching lives in:

- `AITranscriptInterpreter.match_existing_workflow_group(...)`

It is used from:

- `ProcessGroupingService._match_existing_group_with_ai(...)`

### Heuristic and orchestration layer

The orchestration and fallback logic already lives in:

- [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py)

This service should remain the orchestration and conflict-resolution layer.

## Goal Of This Slice

Move the AI request/response behavior for:

- workflow title resolution
- existing-group matching

into explicit skill modules, while preserving:

- the current process grouping orchestration
- the current heuristic matching logic
- the current conflict-resolution behavior
- the current downstream `GroupResolutionDecision` behavior

## Proposed Folder Structure

Add two new skill folders:

```text
worker/services/ai_skills/
  workflow_title_resolution/
    SKILL.md
    prompt.md
    schemas.py
    skill.py
  workflow_group_match/
    SKILL.md
    prompt.md
    schemas.py
    skill.py
```

These should follow the same hybrid pattern already established by:

- [worker/services/ai_skills/transcript_to_steps/skill.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/transcript_to_steps/skill.py)
- [worker/services/ai_skills/semantic_enrichment/skill.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/semantic_enrichment/skill.py)
- [worker/services/ai_skills/workflow_boundary_detection/skill.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/workflow_boundary_detection/skill.py)

## Skill 1: Workflow Title Resolution

### Purpose

Resolve a business-readable workflow title and stable slug from workflow evidence.

### Current source behavior

Today this AI behavior lives in:

- `AITranscriptInterpreter.resolve_workflow_title(...)`

And is currently used from:

- `ProcessGroupingService._resolve_title_with_ai(...)`

### Input

The new `workflow_title_resolution` skill input should include:

- `transcript_name`
- `workflow_summary`

The `workflow_summary` should continue to carry the same grouping evidence currently assembled by `ProcessGroupingService`.

### Output

The new skill output should include:

- `workflow_title`
- `canonical_slug`
- `confidence`
- `rationale`

### Runtime behavior

The skill should:

- load prompt content from markdown
- call the shared AI client
- parse JSON through shared runtime helpers
- normalize title and slug-related fields
- normalize confidence

### Integration behavior

`ProcessGroupingService._resolve_title_with_ai(...)` should:

1. continue to build workflow summary exactly as it does now
2. call the new `workflow_title_resolution` skill
3. if AI is unavailable or weak, keep the existing fallback-title path
4. if AI is accepted, continue normalizing the title in the service layer
5. continue returning the existing `WorkflowTitleInterpretation` dataclass

This keeps naming policy centralized in the grouping service while moving AI behavior into a skill.

## Skill 2: Workflow Group Match

### Purpose

Decide whether workflow evidence matches an existing workflow group or should create a new one.

### Current source behavior

Today this AI behavior lives in:

- `AITranscriptInterpreter.match_existing_workflow_group(...)`

And is currently used from:

- `ProcessGroupingService._match_existing_group_with_ai(...)`

### Input

The new `workflow_group_match` skill input should include:

- `transcript_name`
- `workflow_summary`
- serialized `existing_groups`

This serialized data should remain compatible with the grouping service’s current AI input preparation.

### Output

The new skill output should include:

- `matched_existing_title`
- `recommended_title`
- `recommended_slug`
- `confidence`
- `rationale`

### Runtime behavior

The skill should:

- load prompt content from markdown
- call the shared AI client
- parse JSON through shared runtime helpers
- normalize matched title against existing group titles
- normalize title and slug output
- normalize confidence

### Integration behavior

`ProcessGroupingService._match_existing_group_with_ai(...)` should:

1. continue to build workflow summary and existing-group payloads
2. call the new `workflow_group_match` skill
3. preserve current heuristic-vs-AI conflict logic
4. preserve the current conservative fallback behavior
5. continue returning the existing `GroupResolutionDecision` flow

This keeps matching policy in the grouping service while moving AI behavior into a skill.

## Compatibility Strategy

This slice should not redesign the grouping service.

Compatibility rules:

- keep [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py) as the orchestration layer
- keep [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py) in place
- move only the AI request/response behavior for title resolution and group matching into skills
- keep heuristic matching and fallback title behavior unchanged
- keep downstream dataclass shapes unchanged

This matches the previous slices:

- orchestration stays where it is
- skill owns the AI behavior
- compatibility and heuristics remain intact

## Logging Strategy

As with earlier skills, add runtime proof logs at:

- the grouping service before skill delegation
- the skill layer when execution begins

Desired metadata:

- `skill_id`
- `skill_version`
- transcript or workflow identifiers where available
- candidate group information for group matching where useful

This will let real worker runs prove that the new title/group-match skills are active.

## Testing Strategy

This slice should add three categories of tests.

### 1. Skill unit tests

For `workflow_title_resolution`:

- confidence normalization
- title/slug normalization
- prompt loading and message building

For `workflow_group_match`:

- matched-title normalization
- title/slug normalization
- prompt loading and message building

### 2. Compatibility tests

Test that the grouping-service methods still preserve the current dataclass-based orchestration behavior:

- title resolution still returns `WorkflowTitleInterpretation`
- group matching still returns `GroupResolutionDecision` behavior through existing service logic

### 3. Integration-focused process-grouping tests

Add or update focused tests around:

- `_resolve_title_with_ai(...)`
- `_match_existing_group_with_ai(...)`

without forcing full environment boot unless necessary.

## Non-Goals

This slice is not the place to:

- redesign heuristic group matching
- redesign title normalization policy broadly
- change process-group persistence
- change workflow summary construction
- migrate summary or diagram generation
- solve rate-limit handling

## Proposed Implementation Sequence

1. add `workflow_title_resolution/`
2. define title-resolution schemas
3. add title-resolution markdown files
4. implement title-resolution skill
5. add focused tests
6. wire `_resolve_title_with_ai(...)` to the new skill
7. add logs
8. verify tests
9. add `workflow_group_match/`
10. define group-match schemas
11. add group-match markdown files
12. implement group-match skill
13. add focused tests
14. wire `_match_existing_group_with_ai(...)` to the new skill
15. add logs
16. verify tests
17. run one real worker generation and confirm runtime proof logs

## Success Criteria

This slice is successful if:

- `workflow_title_resolution` exists as a hybrid AI skill
- `workflow_group_match` exists as a hybrid AI skill
- process grouping uses those skills for AI behavior
- heuristic and fallback grouping behavior remain intact
- runtime logs prove the new skills execute in a real worker run

## Follow-On Recommendation

After this slice, the next best migration targets are:

1. `process_summary_generation`
2. `diagram_generation`
3. optionally `workflow_capability_tagging`

That will complete most of the remaining worker-side AI migration before backend-side `session_grounded_qa`.
