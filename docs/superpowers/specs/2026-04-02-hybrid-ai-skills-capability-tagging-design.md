# Hybrid AI Skills Capability Tagging Design

## Purpose

This document defines the next implementation slice for the hybrid AI skill architecture in `PddGenerator`.

The previous slices established:

- the worker-side hybrid AI skill framework
- the first migrated skill: `transcript_to_steps`
- the workflow-core migrations:
  - `semantic_enrichment`
  - `workflow_boundary_detection`
- the workflow identity migrations:
  - `workflow_title_resolution`
  - `workflow_group_match`
- the generation migrations:
  - `process_summary_generation`
  - `diagram_generation`

This slice extends the architecture into workflow capability classification by migrating:

- `workflow_capability_tagging`

This capability is responsible for:

- classifying broad reusable business capability tags for one resolved workflow

## Scope

This slice will implement:

- one new hybrid AI skill for workflow capability tagging
- registry wiring for the new skill
- process-grouping integration so capability tagging uses the new skill
- compatibility preservation through the current accepted-confidence and fallback-tag behavior
- focused tests and runtime logs

This slice will not implement:

- session chat migration
- database changes
- API changes
- UI changes
- retry or rate-limit redesign
- broader process-grouping refactoring

## Why This Skill Next

After workflow evidence extraction, group resolution, summary generation, and diagram generation, the remaining worker-side AI capability in the grouping flow is workflow capability classification.

That logic currently lives across:

- [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py)
- [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py)

Migrating this next will:

- reduce interpreter sprawl further
- make workflow capability classification explicit
- keep process grouping focused on business policy and fallback behavior
- leave only backend-side `session_grounded_qa` as the final major AI-skill migration

## Current Architecture Snapshot

### AI capability classification

Current AI capability classification lives in:

- `AITranscriptInterpreter.classify_workflow_capabilities(...)`

It is used from:

- `ProcessGroupingService._resolve_capability_tags(...)`

### Orchestration and fallback layer

The orchestration and fallback logic already lives in:

- [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py)

This should remain the orchestration and fallback layer for this slice.

## Goal Of This Slice

Move the AI request/response behavior for workflow capability classification into an explicit skill module, while preserving:

- the current accepted-confidence check
- the current capability-tag normalization logic
- the current fallback-capability-tag behavior
- the current downstream JSON shape for `capability_tags_json`

## Proposed Folder Structure

Add one new skill folder:

```text
worker/services/ai_skills/
  workflow_capability_tagging/
    README.md
    prompt.md
    schemas.py
    skill.py
```

This should follow the same hybrid pattern already established by:

- [worker/services/ai_skills/workflow_group_match/skill.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/workflow_group_match/skill.py)
- [worker/services/ai_skills/process_summary_generation/skill.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/process_summary_generation/skill.py)

## Skill: Workflow Capability Tagging

### Purpose

Classify broader business capability tags for one workflow without redefining workflow identity.

### Current source behavior

Today this AI behavior lives in:

- `AITranscriptInterpreter.classify_workflow_capabilities(...)`

And is currently used from:

- `ProcessGroupingService._resolve_capability_tags(...)`

### Input

The new `workflow_capability_tagging` skill input should include:

- `process_title`
- `workflow_summary`
- `document_type`

The `workflow_summary` should remain exactly what the grouping service currently assembles.

### Output

The new skill output should include:

- `capability_tags`
- `confidence`
- `rationale`

### Runtime behavior

The skill should:

- load prompt content from markdown
- call the shared AI client
- parse JSON through shared runtime helpers
- normalize the list of capability tags
- normalize confidence

### Integration behavior

`ProcessGroupingService._resolve_capability_tags(...)` should:

1. continue calling the AI path first
2. continue accepting AI tags only when confidence remains in the current accepted confidence set
3. continue normalizing the returned capability tags in the service layer
4. continue falling back to `_fallback_capability_tags(...)` when AI output is missing, weak, or empty
5. continue returning `[process_title]` when fallback tags are also empty

This keeps capability-tag acceptance and fallback policy in the grouping service while moving AI behavior into a skill.

## Compatibility Strategy

This slice should not redesign the grouping service.

Compatibility rules:

- keep [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py) as the orchestration and fallback layer
- keep [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py) in place
- move only the AI request/response behavior for workflow capability classification into a skill
- keep accepted-confidence behavior unchanged
- keep capability-tag normalization unchanged
- keep fallback-capability-tag behavior unchanged

This matches the previous slices:

- orchestration remains where the product workflow already expects it
- the new skill layer owns AI-specific behavior only

## Files To Modify

### New files

- `worker/services/ai_skills/workflow_capability_tagging/README.md`
- `worker/services/ai_skills/workflow_capability_tagging/prompt.md`
- `worker/services/ai_skills/workflow_capability_tagging/schemas.py`
- `worker/services/ai_skills/workflow_capability_tagging/skill.py`
- `worker/tests/test_workflow_capability_tagging_skill.py`

### Existing files to modify

- [worker/services/ai_skills/registry.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/registry.py)
- [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py)

### Reference files

- [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py)

## Logging Expectations

This slice should follow the same runtime-proof pattern as earlier slices.

Expected logs should include:

- grouping-service delegation log for `workflow_capability_tagging`
- skill execution log from the new skill module

This will make real worker verification straightforward later.

## Testing Strategy

This slice should add focused tests for:

- capability-tagging request/response schemas
- capability-tagging normalization and prompt building
- grouping-service compatibility wiring for accepted-confidence and fallback behavior
- registry creation of the new skill

The tests should follow the same direct-file pattern used by the earlier skill migrations so they remain runnable in this shell environment.

## Success Criteria

This slice is successful when:

- workflow capability classification AI behavior lives in `workflow_capability_tagging`
- grouping service still controls accepted-confidence and fallback behavior
- focused tests pass
- later worker runs can prove the new skill path through logs
