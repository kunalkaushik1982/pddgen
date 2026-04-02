# Hybrid AI Skills Design

## Purpose

This document defines the first implementation slice for introducing a hybrid AI skill architecture into `PddGenerator`.

The current codebase has a clear split between:

- standard software-engineering infrastructure
  - frontend
  - backend routes and services
  - worker orchestration
  - database and storage
  - export pipeline
- AI-driven interpretation behavior
  - transcript-to-step extraction
  - semantic enrichment
  - workflow-boundary reasoning
  - workflow grouping and naming
  - summary generation
  - diagram generation
  - grounded session Q&A

The current AI logic is functional, but too concentrated inside a small number of large Python services, especially:

- [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py)

That structure makes the AI layer harder to reason about, harder to test in bounded slices, and harder to evolve into a reusable, skill-oriented architecture.

This design introduces a hybrid approach:

- markdown files for skill intent and prompt content
- Python files for runtime execution, validation, normalization, and compatibility

## Scope

This branch will implement:

- the hybrid AI skill framework
- one migrated skill: `transcript_to_steps`
- compatibility wiring so the current worker pipeline continues to work

This branch will not implement:

- migration of all AI capabilities
- large route or API contract changes
- a full worker-pipeline rewrite
- UI changes specific to the new architecture

## Why Hybrid Instead Of Pure Markdown Or Pure Python

Pure markdown is useful for:

- readable instructions
- prompt editing
- documentation-like skill definitions

But pure markdown is too weak for runtime product behavior because this system also needs:

- typed contracts
- output validation
- confidence normalization
- fallback handling
- compatibility transforms
- transport-level error handling

Pure Python is useful for:

- runtime safety
- validation
- tests
- integration with existing worker/backend code

But pure Python makes prompts and capability boundaries harder to read and maintain cleanly. It also keeps AI behavior too embedded in implementation code.

The hybrid model is the correct fit for this repository because:

- the project already has Python-centric orchestration and service boundaries
- the AI layer needs stronger modularity
- prompts and business rules should remain readable and explicit
- structured runtime behavior must remain testable and controlled

## Skill Definition

In this repository, a skill should mean:

- one bounded AI capability
- one stable input contract
- one stable output contract
- one explicit prompt and instruction surface
- one runtime execution path
- one normalization and validation boundary

A skill is not:

- a route handler
- a Celery task
- a database model
- a storage service
- the entire worker pipeline

Those remain software-engineering infrastructure.

## First Skill Selection

The first migrated skill will be:

- `transcript_to_steps`

This skill is the best first slice because:

- it is concrete and easy to reason about
- it already has a bounded purpose
- the current code already has both AI and deterministic paths
- it can be migrated without redesigning the whole pipeline
- it creates a reusable template for later skills

Later candidates include:

- `semantic_enrichment`
- `workflow_boundary_detection`
- `workflow_title_resolution`
- `workflow_group_match`
- `process_summary_generation`
- `diagram_generation`
- `session_grounded_qa`

## Proposed Folder Structure

The first framework slice should live under the worker because the first migrated skill belongs to worker-side transcript interpretation.

```text
worker/services/ai_skills/
  base.py
  registry.py
  runtime.py
  client.py
  transcript_to_steps/
    SKILL.md
    prompt.md
    schemas.py
    skill.py
```

### `base.py`

Defines the core skill contract and shared skill metadata types.

Responsibilities:

- define what a skill is
- define the minimum runtime interface
- keep the contract stable for future skills

### `registry.py`

Provides explicit registration and resolution of skills by stable key.

Responsibilities:

- register skill factories
- resolve a skill by key
- avoid ad hoc imports scattered through orchestrators

### `runtime.py`

Provides shared runtime utilities used by skills.

Responsibilities:

- load prompt content from markdown
- parse model JSON safely
- normalize common output fields
- raise clean runtime errors for invalid skill responses

### `client.py`

Provides the OpenAI-compatible transport boundary for skills.

Responsibilities:

- send requests to the configured AI provider
- apply timeout behavior
- normalize provider HTTP failures
- extract model message content from the response

This keeps provider transport separate from individual skill behavior.

### `transcript_to_steps/SKILL.md`

Human-readable description of the skill.

It should contain:

- purpose
- what evidence it consumes
- what output it must produce
- what it must not invent
- confidence rules
- examples and edge cases

This file is for maintainability and clarity, not for direct execution by the worker.

### `transcript_to_steps/prompt.md`

Model-facing prompt content.

It should contain:

- the system instruction body
- response-shape expectations
- key constraints on step and note generation

This keeps prompts outside Python code while still loading them at runtime.

### `transcript_to_steps/schemas.py`

Typed request and response models for the skill.

It should define:

- request model for transcript input
- response model for structured steps and notes
- step model
- note model

### `transcript_to_steps/skill.py`

The runtime implementation for the skill.

Responsibilities:

- accept typed input
- load the prompt
- call the shared AI client
- parse and validate JSON response
- normalize confidence and timestamps
- return a typed output model

## Data Flow

This branch must preserve the current end-to-end behavior while changing the AI boundary.

The new flow for transcript interpretation should be:

1. existing worker/orchestrator requests transcript interpretation
2. [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py) delegates transcript-to-steps generation to the new skill
3. the new skill loads `prompt.md`
4. the skill calls the shared AI client
5. the shared runtime parses and validates the JSON response
6. the skill returns typed step/note output
7. the existing interpreter compatibility layer converts that output into the current worker-compatible shape if needed
8. the rest of the pipeline remains unchanged

This preserves downstream behavior while establishing the new skill architecture.

## Compatibility Strategy

This branch should not break the rest of the system.

Compatibility rules:

- keep [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py) present
- keep the current `interpret(...)` public behavior intact
- migrate only the transcript-to-steps logic into the new skill
- let the old interpreter act as a compatibility facade for now
- avoid changing unrelated AI methods in the same branch

This means the old service becomes thinner without forcing a multi-area refactor immediately.

## Skill Contract Shape

The framework should use a simple, explicit contract.

Example shape:

```python
class AISkill(Protocol):
    skill_id: str
    version: str

    def run(self, input: Any) -> Any:
        ...
```

The first slice does not need a large generic abstraction hierarchy.

It does need:

- a stable skill id
- a stable version marker
- typed input and output models
- a single runtime entrypoint

The system should prefer a small, readable contract over an over-general plugin framework.

## Transcript-To-Steps Skill Contract

### Input

The first skill input should contain:

- `transcript_artifact_id`
- `transcript_text`

Future fields may include:

- `meeting_id`
- `document_type`
- `domain_key`

But those are out of scope for this first slice unless required by the current interpreter logic.

### Output

The first skill output should contain:

- `steps`
- `notes`

Each step should contain normalized fields equivalent to the current AI interpretation path:

- `application_name`
- `action_text`
- `source_data_note`
- `start_timestamp`
- `end_timestamp`
- `display_timestamp`
- `supporting_transcript_text`
- `confidence`

Each note should contain:

- `text`
- `confidence`
- `inference_type`

## Error Handling

The new skill layer must fail clearly and predictably.

Requirements:

- provider timeout should become a bounded runtime error
- provider HTTP failure should become a clean runtime error
- invalid or non-JSON model output should become a parse/validation error
- invalid confidence values should be normalized
- malformed timestamps should be normalized or emptied

The goal is to keep errors localized and easier to diagnose than the current mixed approach.

## Fallback Behavior

This branch should preserve current system behavior when AI is disabled.

Important boundary:

- the worker-side AI skill architecture should not remove deterministic fallback paths that already exist elsewhere in the system

This branch does not need to move deterministic fallback logic into the new skill framework unless that is needed for clean compatibility.

For now:

- AI-enabled transcript interpretation uses the new skill
- non-AI behavior remains with the existing fallback path already present in the codebase

## Testing Strategy

This branch should add tests at three levels.

### 1. Skill unit tests

Test:

- prompt loading
- JSON parsing
- response normalization
- invalid JSON handling
- confidence normalization
- timestamp normalization

### 2. Compatibility tests

Test:

- the old interpreter interface still returns the same downstream shape expected by current worker code

### 3. Regression tests

Run or update:

- worker tests that depend on transcript-driven generation behavior

The design goal is to prove:

- the new architecture exists
- the migrated skill behaves correctly
- the current product pipeline remains stable

## Non-Goals

This branch is not the place to:

- migrate every AI capability
- redesign all workflow intelligence contracts
- move backend grounded chat into the same first slice
- fully replace the old interpreter
- introduce broad UI changes

Keeping the branch small is a feature, not a limitation.

## Implementation Plan For This Branch

The implementation sequence should be:

1. create `worker/services/ai_skills/`
2. add `base.py`, `registry.py`, `runtime.py`, and `client.py`
3. add `transcript_to_steps/`
4. write `SKILL.md`
5. write `prompt.md`
6. define request/response models in `schemas.py`
7. implement execution in `skill.py`
8. update [worker/services/ai_transcript_interpreter.py](C:/Users/work/Documents/PddGenerator/worker/services/ai_transcript_interpreter.py) to delegate only transcript-to-steps
9. add tests
10. verify existing worker behavior still holds

## Success Criteria

This branch is successful if:

- a new hybrid AI skill framework exists under `worker/services/ai_skills/`
- `transcript_to_steps` exists as the first real skill
- prompt content is no longer hardcoded inside the main interpreter for this capability
- typed schemas exist for the skill input and output
- the existing worker pipeline still uses the same external behavior
- the branch creates a clean template for later skills

## Recommendation For Next Branches

After this branch is complete, the next best migrations are:

1. `semantic_enrichment`
2. `workflow_boundary_detection`
3. `workflow_title_resolution`

That sequence will extend the same pattern into the deeper workflow-intelligence layer without forcing a full architecture rewrite in one step.
