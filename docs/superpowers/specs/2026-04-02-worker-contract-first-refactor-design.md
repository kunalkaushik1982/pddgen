# Worker Contract-First Refactor Design

## Goal

Refactor the worker orchestration layer into interface-first, compatibility-preserving application services that keep current task entrypoints and behavior stable while improving separation of concerns, testability, and extension points.

## Scope

This design covers the worker orchestration layer only:

- `worker/services/draft_generation_worker.py`
- `worker/services/screenshot_generation_worker.py`
- `worker/services/draft_generation_stage_services.py`
- `worker/services/draft_generation_stage_context.py`
- worker-side dependency wiring around database lifecycle, stage execution, failure handling, and screenshot preparation

This design does not intentionally change:

- Celery task names or call sites
- expected task payload shape
- persisted business outcomes for successful runs
- the AI skill package structure beyond seams required by orchestration cleanup

## Current Problems

The current worker code has partial abstraction work already, but orchestration remains tightly coupled.

### Responsibility overlap

- `DraftGenerationWorker` coordinates pipeline order, opens the DB session, loads the session, handles failures, and constructs concrete stages itself.
- `ScreenshotGenerationWorker` coordinates flow and also contains substantial domain preparation logic for transcript linking, evidence cleanup, screenshot candidate shaping, and persistence-related cleanup.
- `draft_generation_stage_services.py` contains many responsibilities in one file: session preparation, transcript interpretation, segmentation strategy wiring, screenshot derivation, diagram generation, persistence, and failure handling.

### Dependency inversion gaps

- Coordinators create concrete collaborators directly instead of depending on contracts.
- Default strategy construction lives inside stage implementations instead of a dedicated composition root.
- DB session lifecycle is managed inline in workers rather than behind a dedicated interface.

### Weak typing at orchestration boundaries

- The pipeline passes many mutable `dict` records for steps, notes, and screenshots.
- Several worker methods mix domain decisions with persistence-ready shape mutation.
- Some protected helpers are effectively acting as hidden services.

### Open/closed pressure

- Adding a new stage or changing wiring requires editing coordinator classes.
- Reusing the same orchestration flow in tests requires patch-heavy setup because construction is inlined.

## Design Principles

The refactor will apply SOLID pragmatically rather than mechanically.

### Single Responsibility Principle

Each unit should have one reason to change:

- use cases orchestrate execution
- repositories load and persist worker data
- session providers manage DB lifecycle
- stage runners execute ordered stages
- failure recorders persist failure state
- screenshot context builders prepare screenshot-specific input state

### Open/Closed Principle

Pipelines should be extendable by registering or passing additional stage implementations rather than editing core orchestrators.

### Liskov Substitution Principle

All stage implementations must be swappable through shared worker-stage contracts with compatible input/output expectations.

### Interface Segregation Principle

The worker should use small, focused protocols instead of broad service abstractions. A screenshot-specific service should not be forced to implement draft-generation behavior, and vice versa.

### Dependency Inversion Principle

High-level worker use cases will depend on contracts for loading sessions, running stages, persisting results, and recording failure state. Concrete SQLAlchemy and current-service implementations will be provided by wiring code.

## Proposed Architecture

### 1. Thin compatibility adapters

Keep:

- `DraftGenerationWorker`
- `ScreenshotGenerationWorker`

These classes become compatibility adapters only. Their responsibilities:

- accept `task_id`
- instantiate or receive the proper use case
- call `use_case.run(session_id=...)`

They should no longer own business preparation logic, stage construction, or persistence details.

### 2. Application use cases

Introduce worker application services:

- `DraftGenerationUseCase`
- `ScreenshotGenerationUseCase`

Responsibilities:

- open a unit of work or DB session boundary
- load session aggregate through repository contracts
- prepare execution context
- invoke ordered pipeline stages
- persist final result through dedicated persistence collaborator
- record failures through failure collaborator
- release screenshot lock in the screenshot flow

The use cases are the only objects that know the high-level workflow order.

### 3. Interface-first contracts

Introduce focused protocols in a worker contracts module. Expected contract families:

- `WorkerUnitOfWork`
- `WorkerUnitOfWorkFactory`
- `DraftSessionRepository`
- `DraftPipelineStage`
- `ScreenshotPipelineStage`
- `DraftResultPersister`
- `ScreenshotResultPersister`
- `FailureRecorder`
- `ScreenshotLockManager`
- `ScreenshotContextBuilder`

These contracts should remain small and task-specific. Avoid a god-interface like `WorkerService`.

### 4. Pipeline model

Convert current stage execution into an explicit pipeline pattern.

For draft generation:

- session preparation stage
- evidence segmentation stage
- transcript interpretation stage
- process grouping stage
- canonical merge stage
- diagram assembly stage
- persistence stage

For screenshot generation:

- screenshot context preparation stage or builder
- screenshot derivation stage
- screenshot persistence stage

The ordered list of stages should be injected into the use case. That allows tests to pass fake stages and allows new stages to be added without changing use-case internals.

### 5. Repository and unit-of-work boundaries

Move SQLAlchemy-facing behavior behind interfaces:

- session loading query logic
- stale generated-data cleanup
- generated screenshot cleanup
- pending bundle updates
- status transitions
- action log persistence where appropriate

DB lifecycle should be owned by a dedicated unit-of-work abstraction instead of direct `get_db_session()` management in orchestration code.

### 6. Screenshot preparation extraction

Move `_prepare_context()` and related transcript resolution helpers out of `ScreenshotGenerationWorker` into a dedicated collaborator, for example `DefaultScreenshotContextBuilder`.

Responsibilities:

- validate required transcript/video/step inputs
- strip old screenshot evidence
- clear screenshot relations and generated screenshot artifacts
- resolve transcript lineage per step
- build typed screenshot pipeline context

This is the highest-value extraction because that logic is domain-heavy and currently makes the worker class violate SRP badly.

### 7. Composition root

Add one worker composition module that wires default implementations.

Responsibilities:

- create concrete repositories and unit-of-work factories
- assemble default draft stage list
- assemble default screenshot stage list
- provide default failure recorder and screenshot lock manager
- centralize default strategy registries currently built inside stages

This separates object construction from business flow and provides a stable location for future environment-specific wiring.

## Data Model Direction

The refactor should move toward typed DTOs at orchestration seams without forcing an unsafe all-at-once rewrite.

### Immediate direction

- keep `DraftGenerationContext` as the mutable cross-stage context object
- add stronger typed fields and aliases where practical
- introduce small typed DTOs for screenshot preparation and result summaries

### Transitional rule

`dict`-based step and note payloads may remain temporarily inside stage internals where replacement cost is high, but they should not continue to spread outward into new interfaces. New contracts should use named DTOs or context objects.

### Long-term direction

After orchestration is stable, the highest-risk step/note/screenshot record dictionaries can be replaced with typed records incrementally.

## File Structure Direction

The refactor should decompose by responsibility, not by abstract technical layer names alone. A likely structure:

- `worker/services/worker_contracts.py`
- `worker/services/worker_uow.py`
- `worker/services/worker_repositories.py`
- `worker/services/worker_use_cases.py`
- `worker/services/worker_pipeline.py`
- `worker/services/screenshot_context_builder.py`
- `worker/services/worker_composition.py`

Existing stage implementations may remain where they are initially, but oversized files should be split when touched meaningfully. `draft_generation_stage_services.py` is a strong candidate for follow-up decomposition because it currently acts as a multi-service container.

## Pattern Usage

The design intentionally uses a small set of well-scoped patterns.

### Pipeline

Ordered stage execution through a shared stage contract.

### Strategy

Preserve the existing workflow-intelligence strategy model and keep strategy selection outside orchestration logic.

### Repository

Encapsulate session loading and persistence queries behind worker-specific repositories.

### Unit of Work

Own DB session lifecycle, commit, rollback, and close behavior through one abstraction.

### Adapter

Keep current worker classes as adapters over the new use cases.

### Factory / Composition Root

Centralize default implementation wiring and collaborator construction.

## Testing Strategy

The refactor should preserve behavior and improve test shape.

### Add or update tests for:

- use-case orchestration order
- failure recording on stage exception
- screenshot lock release on success and failure
- repository-backed session loading behavior
- screenshot context builder behavior
- pipeline composition with fake stage implementations

### Keep passing:

- existing worker behavior tests
- stage-level tests that should not require behavior change

### Preferred testing style

- constructor injection instead of `patch()` where practical
- fake implementations for contracts in orchestration tests
- focused tests per collaborator rather than giant end-to-end mocks

## Migration Plan

### Phase 1: Compatibility-preserving orchestration split

- introduce contracts
- introduce use cases
- move worker classes to adapter role
- preserve current entrypoints and outputs

### Phase 2: Screenshot preparation extraction

- move screenshot context logic into dedicated collaborator
- add tests for transcript lineage and evidence cleanup behavior

### Phase 3: Stage wiring cleanup

- move default collaborator construction out of stage classes
- centralize wiring in composition module

### Phase 4: Typed DTO strengthening

- introduce focused DTOs where current dictionaries are most error-prone
- keep stage internals stable until tests prove safe conversion

## Risks And Controls

### Risk: hidden behavior regression during extraction

Control:

- preserve entrypoints
- add orchestration tests before major movement
- verify current worker tests continue to pass

### Risk: over-engineering with too many abstractions

Control:

- introduce only worker-specific contracts required by use cases
- avoid framework-heavy DI patterns
- avoid large generic service interfaces

### Risk: partial refactor leaves wiring duplicated

Control:

- add a composition root in the same pass as the new use cases
- remove inlined construction from workers as part of the initial refactor

## Success Criteria

The refactor is successful when:

- current task entrypoints continue to work without caller changes
- worker orchestrators depend on contracts rather than concrete stage construction
- screenshot preparation logic no longer lives in `ScreenshotGenerationWorker`
- DB lifecycle is no longer manually managed inside business orchestration methods
- stage pipelines are injectable and testable in isolation
- targeted worker tests verify behavior remains stable
