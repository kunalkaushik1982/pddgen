# Hybrid AI Skills Generation Design

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

This slice extends the architecture into downstream AI-generated workflow outputs by migrating:

- `process_summary_generation`
- `diagram_generation`

These capabilities are responsible for:

- generating a concise business summary for one resolved workflow group
- generating overview and detailed flowchart graph models for the session

## Scope

This slice will implement:

- one new hybrid AI skill for process summary generation
- one new hybrid AI skill for diagram generation
- registry wiring for both skills
- process-grouping integration so workflow summary generation uses the new skill
- diagram-stage integration so diagram assembly uses the new skill
- compatibility preservation through the current fallback and empty-output behavior
- focused tests and runtime logs

This slice will not implement:

- capability-tagging migration
- session chat migration
- database changes
- API changes
- UI changes
- retry or rate-limit redesign
- broader stage orchestration refactoring

## Why These Skills Next

After workflow evidence extraction, boundary reasoning, and group resolution, the next AI-heavy bottleneck is downstream workflow output generation.

That logic currently lives across:

- [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py)
- [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py)
- [worker/services/draft_generation_stage_services.py](C:/Users/work/Documents/PddGenerator/worker/services/draft_generation_stage_services.py)

Migrating these next will:

- reduce interpreter sprawl further
- make workflow-summary and diagram-generation AI behavior explicit
- keep grouping and draft stages focused on orchestration and fallback behavior
- create a cleaner bridge between resolved workflow evidence and generated outputs

## Current Architecture Snapshot

### AI process summary generation

Current AI summary generation lives in:

- `AITranscriptInterpreter.summarize_process_group(...)`

It is used from:

- `ProcessGroupingService._refresh_group_summaries(...)`

### AI diagram generation

Current AI diagram generation lives in:

- `AITranscriptInterpreter.interpret_diagrams(...)`

It is used from:

- `DiagramAssemblyStage.run(...)`

### Orchestration and fallback layers

The orchestration and fallback logic already lives in:

- [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py)
- [worker/services/draft_generation_stage_services.py](C:/Users/work/Documents/PddGenerator/worker/services/draft_generation_stage_services.py)

These should remain the orchestration and fallback layers for this slice.

## Goal Of This Slice

Move the AI request/response behavior for:

- process summary generation
- diagram generation

into explicit skill modules, while preserving:

- the current grouping service summary fallback behavior
- the current diagram-stage empty-output behavior
- the current downstream dataclass and JSON payload shapes

## Proposed Folder Structure

Add two new skill folders:

```text
worker/services/ai_skills/
  process_summary_generation/
    SKILL.md
    prompt.md
    schemas.py
    skill.py
  diagram_generation/
    SKILL.md
    prompt.md
    schemas.py
    skill.py
```

These should follow the same hybrid pattern already established by:

- [worker/services/ai_skills/transcript_to_steps/skill.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/transcript_to_steps/skill.py)
- [worker/services/ai_skills/semantic_enrichment/skill.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/semantic_enrichment/skill.py)
- [worker/services/ai_skills/workflow_group_match/skill.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/workflow_group_match/skill.py)

## Skill 1: Process Summary Generation

### Purpose

Generate a concise business summary for one resolved workflow group.

### Current source behavior

Today this AI behavior lives in:

- `AITranscriptInterpreter.summarize_process_group(...)`

And is currently used from:

- `ProcessGroupingService._refresh_group_summaries(...)`

### Input

The new `process_summary_generation` skill input should include:

- `process_title`
- `workflow_summary`
- `steps`
- `notes`
- `document_type`

The `workflow_summary` should remain exactly what the grouping service currently assembles.

### Output

The new skill output should include:

- `summary_text`
- `confidence`
- `rationale`

### Runtime behavior

The skill should:

- load prompt content from markdown
- call the shared AI client
- parse JSON through shared runtime helpers
- normalize `summary_text`
- normalize confidence

### Integration behavior

`ProcessGroupingService._refresh_group_summaries(...)` should:

1. continue to build the fallback summary exactly as it does now
2. continue to build the workflow summary exactly as it does now
3. call the new `process_summary_generation` skill
4. accept AI summary text only when confidence remains in the current accepted confidence set
5. otherwise keep the existing fallback summary path

This keeps summary acceptance policy in the grouping service while moving AI behavior into a skill.

## Skill 2: Diagram Generation

### Purpose

Generate overview and detailed flowchart graph models for the session.

### Current source behavior

Today this AI behavior lives in:

- `AITranscriptInterpreter.interpret_diagrams(...)`

And is currently used from:

- `DiagramAssemblyStage.run(...)`

### Input

The new `diagram_generation` skill input should include:

- `session_title`
- `diagram_type`
- serialized `steps`
- serialized `notes`

This payload should remain compatible with the current diagram prompt inputs.

### Output

The new skill output should include:

- `overview`
- `detailed`

Each view should preserve the current normalized graph shape:

- `title`
- `nodes`
- `edges`

### Runtime behavior

The skill should:

- load prompt content from markdown
- call the shared AI client
- parse JSON through shared runtime helpers
- normalize overview and detailed diagram views
- preserve current connected-graph and valid-edge constraints

### Integration behavior

`DiagramAssemblyStage.run(...)` should:

1. continue checking whether diagram generation should run
2. call the new `diagram_generation` skill
3. preserve the current `try/except` behavior that treats AI failures as no renderable output
4. preserve the current empty-string fallback when no diagram output exists
5. continue serializing overview and detailed JSON into the context exactly as it does now

This keeps stage-level resilience policy in the stage layer while moving AI behavior into a skill.

## Compatibility Strategy

This slice should not redesign either orchestration layer.

Compatibility rules:

- keep [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py) as the summary orchestration layer
- keep [worker/services/draft_generation_stage_services.py](C:/Users/work/Documents/PddGenerator/worker/services/draft_generation_stage_services.py) as the diagram stage and fallback layer
- keep [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py) in place
- move only the AI request/response behavior for process summary generation and diagram generation into skills
- keep summary fallback and confidence acceptance unchanged
- keep diagram empty-output behavior unchanged
- keep downstream dataclass and JSON shapes unchanged

This matches the previous slices:

- orchestration remains where the product workflow already expects it
- the new skill layer owns AI-specific behavior only

## Files To Modify

### New files

- `worker/services/ai_skills/process_summary_generation/SKILL.md`
- `worker/services/ai_skills/process_summary_generation/prompt.md`
- `worker/services/ai_skills/process_summary_generation/schemas.py`
- `worker/services/ai_skills/process_summary_generation/skill.py`
- `worker/services/ai_skills/diagram_generation/SKILL.md`
- `worker/services/ai_skills/diagram_generation/prompt.md`
- `worker/services/ai_skills/diagram_generation/schemas.py`
- `worker/services/ai_skills/diagram_generation/skill.py`
- `worker/tests/test_process_summary_generation_skill.py`
- `worker/tests/test_diagram_generation_skill.py`

### Existing files to modify

- [worker/services/ai_skills/registry.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_skills/registry.py)
- [worker/services/process_grouping_service.py](C:/Users/work/Documents/PddGenerator/worker/services/process_grouping_service.py)
- [worker/services/draft_generation_stage_services.py](C:/Users/work/Documents/PddGenerator/worker/services/draft_generation_stage_services.py)

### Reference files

- [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py)

## Logging Expectations

This slice should follow the same runtime-proof pattern as earlier slices.

Expected logs should include:

- grouping-service delegation log for `process_summary_generation`
- diagram-stage delegation log for `diagram_generation`
- skill execution log from each new skill module

This will make real worker verification straightforward later.

## Testing Strategy

This slice should add focused tests for:

- process summary request/response schemas
- process summary normalization and prompt building
- grouping-service compatibility wiring for summary generation
- diagram request/response schemas
- diagram normalization and prompt building
- diagram-stage compatibility wiring for AI and no-output paths
- registry creation of both new skills

The tests should follow the same direct-file pattern used by the earlier skill migrations so they remain runnable in this shell environment.

## Success Criteria

This slice is successful when:

- summary generation AI behavior lives in `process_summary_generation`
- diagram generation AI behavior lives in `diagram_generation`
- grouping service still controls summary fallback and acceptance
- diagram stage still controls empty-output fallback behavior
- focused tests pass
- later worker runs can prove both new skill paths through logs
