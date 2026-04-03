# AI Architecture Contract-First Refactor Design

## Goal

Refactor worker-side and backend-side AI integration into a contract-first architecture that follows SOLID principles, reduces legacy coupling, and keeps orchestration, domain logic, AI execution, and infrastructure concerns cleanly separated.

## Problem Statement

The codebase has already migrated most AI behavior into `ai_skills`, but the surrounding architecture is still transitional:

- orchestration code still directly constructs some concrete AI classes
- `ai_transcript_interpreter.py` still acts as a mixed legacy facade
- worker-side and backend-side AI integration patterns are similar but not fully unified
- some large service/stage files still combine orchestration with implementation detail

The goal of this refactor is not to rewrite the product behavior. The goal is to make the architecture cleaner, safer to extend, easier to test, and easier to maintain.

## Design Principles

This refactor must follow these principles throughout:

- **Single Responsibility Principle**
  - each class/file should have one clear reason to change
- **Open/Closed Principle**
  - new AI capabilities should be added through contracts and registration, not orchestration rewrites
- **Liskov Substitution Principle**
  - AI and heuristic implementations must be swappable behind the same contract
- **Interface Segregation Principle**
  - use small responsibility-specific contracts rather than one large generic AI interface
- **Dependency Inversion Principle**
  - orchestration depends on contracts, not concrete AI implementations
- **Composition over inheritance**
  - prefer registries, factories, strategy composition, and adapters over deep base-class hierarchies

## Target Layers

The target architecture is split into four layers.

### 1. Domain Layer

This layer contains business objects and pure workflow concepts.

Current examples:

- `worker/services/workflow_intelligence.py`

Responsibilities:

- evidence segment model
- semantic enrichment model
- workflow-boundary decision model
- process/workflow profile concepts
- grounded citation/evidence concepts where applicable

Rules:

- no AI client logic
- no persistence logic
- no orchestration logic

### 2. Application / Orchestration Layer

This layer coordinates workflows and applies business policy.

Current examples:

- `worker/services/draft_generation_worker.py`
- `worker/services/draft_generation_stage_services.py`
- `worker/services/evidence_segmentation_service.py`
- `worker/services/process_grouping_service.py`
- `worker/services/screenshot_generation_worker.py`
- `backend/app/services/session_chat_service.py`

Responsibilities:

- stage coordination
- pipeline sequencing
- fallback selection
- conflict resolution
- policy decisions
- persistence coordination

Rules:

- should depend on contracts/interfaces
- should not depend directly on concrete AI implementation classes unless acting as composition root

### 3. AI Capability Layer

This layer contains skills and AI-facing request/response behavior.

Current examples:

- `worker/services/ai_skills/...`
- `backend/app/services/ai_skills/session_grounded_qa/...`

Responsibilities:

- prompt loading
- request shaping
- model call execution
- response parsing
- output validation
- skill-specific normalization

Rules:

- no workflow orchestration
- no grouping policy
- no persistence decisions

### 4. Infrastructure Layer

This layer contains external system integrations.

Current examples:

- `worker/services/ai_skills/client.py`
- `worker/services/ai_skills/runtime.py`
- storage service
- Celery task entrypoints
- DB/repository integration

Responsibilities:

- OpenAI-compatible HTTP calls
- storage access
- background task integration
- config/environment integration

## Contract-First Model

The central refactor direction is to make orchestration depend on explicit contracts.

Recommended contract set:

- transcript interpretation contract
- semantic enrichment contract
- workflow boundary detection contract
- workflow title resolution contract
- workflow group match contract
- process summary generation contract
- workflow capability tagging contract
- diagram generation contract
- session grounded QA contract

These contracts should live in a dedicated area such as:

- `worker/services/contracts/`
- `backend/app/services/contracts/`

or a shared internal contract package if that proves cleaner later.

Each contract should define:

- request type
- response type
- one clear method per responsibility

Example direction:

- orchestration asks for `semantic enrichment`
- AI skill implementation satisfies that contract
- heuristic implementation can also satisfy that contract
- tests can inject a fake implementation of the same contract

This allows strict dependency inversion and clean substitution.

## Worker-Side Target Structure

### Keep as permanent orchestration/domain layer

These files are still necessary and should remain after refactor, though some may be split for size:

- `worker/services/draft_generation_worker.py`
- `worker/services/draft_generation_stage_services.py`
- `worker/services/evidence_segmentation_service.py`
- `worker/services/process_grouping_service.py`
- `worker/services/screenshot_generation_worker.py`
- `worker/services/workflow_intelligence.py`
- `worker/services/workflow_strategy_interfaces.py`
- `worker/services/workflow_strategy_registry.py`
- `worker/services/transcript_normalizer.py`
- `worker/services/video_frame_extractor.py`

### Transitional legacy file

Main cleanup target:

- `worker/services/ai_transcript_interpreter.py`

Current status:

- still required for transcript interpretation compatibility
- still used for ambiguous group resolution
- no longer the correct long-term home for most AI responsibilities

Long-term goal:

- reduce this file to temporary adapter behavior only
- then remove it when the last live compatibility path is migrated

## Backend-Side Target Structure

Backend should follow the same model as worker-side refactor.

Current example:

- `backend/app/services/session_chat_service.py`
- `backend/app/services/ai_skills/session_grounded_qa/...`

Long-term structure:

- service remains orchestration/policy layer
- contract defines grounded QA responsibility
- concrete skill implements the contract
- shared runtime patterns align with worker-side expectations

## Design Patterns to Use

Use these deliberately:

- **Strategy**
  - AI implementation vs heuristic implementation
- **Registry / Factory**
  - skill resolution and strategy construction
- **Adapter**
  - for transitional legacy compatibility
- **Facade**
  - worker entrypoints and backend entrypoints
- **Template Method**
  - common skill runtime behavior
- **Composition Root**
  - task entrypoints / service assembly points instantiate concrete implementations

Avoid:

- god services
- giant “AI manager” abstractions
- hidden dict contracts
- orchestration classes that construct every dependency internally

## Refactor Phases

### Phase 1: Contract Baseline

Goal:

- define explicit contracts for all AI responsibilities

Deliverables:

- worker-side contracts for transcript interpretation, enrichment, boundary detection, title resolution, group match, summary generation, capability tagging, diagram generation
- backend-side contract for session grounded QA
- contract ownership and usage boundaries documented

Exit criteria:

- orchestration code can reference contracts instead of implicit concrete AI classes

### Phase 2: Runtime Standardization

Goal:

- unify all AI implementations under one runtime model

Deliverables:

- consistent base skill pattern
- uniform request/response validation
- uniform logging and error handling
- standardized registry/factory behavior

Exit criteria:

- all skills use one execution pattern

### Phase 3: Orchestration Decoupling

Goal:

- make services/stages depend on contracts, not concrete AI classes

Deliverables:

- dependency injection into draft generation stages
- dependency injection into evidence segmentation service
- dependency injection into process grouping service
- dependency injection into session chat service

Exit criteria:

- orchestration can be tested using fake contract implementations without relying on concrete AI objects

### Phase 4: Legacy Facade Reduction

Goal:

- isolate and shrink `ai_transcript_interpreter.py`

Deliverables:

- only truly live compatibility methods remain
- superseded legacy methods are removed or deprecated
- adapter responsibilities are made explicit

Exit criteria:

- `ai_transcript_interpreter.py` is no longer a multi-purpose AI service

### Phase 5: Strategy Layer Hardening

Goal:

- make AI vs heuristic composition explicit and fully substitutable

Deliverables:

- strategy composition aligned to contracts
- conflict-resolution logic isolated and tested
- fallback behavior clearly separated from AI execution

Exit criteria:

- strategy implementations are safely swappable

### Phase 6: Pipeline Composition Cleanup

Goal:

- reduce oversized orchestration files into smaller focused collaborators

Deliverables:

- stage coordinators separated where responsibility boundaries are clear
- worker coordinators become composition roots
- screenshot and persistence boundaries become cleaner

Exit criteria:

- large workflow files are easier to understand and modify independently

### Phase 7: Cross-Boundary Unification

Goal:

- align worker and backend AI architecture

Deliverables:

- naming and contract conventions aligned
- runtime conventions aligned
- logging/error handling aligned

Exit criteria:

- worker-side and backend-side AI code follow one mental model

### Phase 8: Legacy Removal and Final Simplification

Goal:

- remove duplicate paths and finalize the new architecture

Deliverables:

- dead code deletion
- redundant compatibility layers removed
- final architecture documentation updated

Exit criteria:

- one canonical execution path per AI responsibility

## File Classification

### Permanent orchestration/domain files

- `worker/services/draft_generation_worker.py`
- `worker/services/draft_generation_stage_services.py`
- `worker/services/evidence_segmentation_service.py`
- `worker/services/process_grouping_service.py`
- `worker/services/screenshot_generation_worker.py`
- `worker/services/workflow_intelligence.py`
- `worker/services/workflow_strategy_interfaces.py`
- `worker/services/workflow_strategy_registry.py`
- `backend/app/services/session_chat_service.py`

### Transitional cleanup target

- `worker/services/ai_transcript_interpreter.py`

### AI implementation files

- all worker `ai_skills/*/skill.py`
- backend `session_grounded_qa/skill.py`

## Recommended Execution Order

Recommended order for implementation:

1. Phase 1: Contract Baseline
2. Phase 3: Orchestration Decoupling
3. Phase 4: Legacy Facade Reduction
4. Phase 5: Strategy Layer Hardening
5. Phase 6: Pipeline Composition Cleanup
6. Phase 7: Cross-Boundary Unification
7. Phase 8: Legacy Removal and Final Simplification

Phase 2 is partly complete already because a shared skill runtime exists, so it should be treated as a normalization pass rather than a net-new architecture phase.

## Non-Goals

This refactor should not:

- change user-facing product behavior unnecessarily
- redesign the database model
- redesign API contracts without clear need
- merge unrelated feature work into the refactor

## Success Criteria

The refactor is successful when:

- AI responsibilities are accessed through explicit contracts
- orchestration depends on contracts instead of concrete AI classes
- heuristic and AI implementations are interchangeable where intended
- `ai_transcript_interpreter.py` is reduced or removed
- worker and backend AI integration patterns are aligned
- new AI capabilities can be added with minimal changes outside contract registration
