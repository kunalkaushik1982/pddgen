# Backend and Worker Audit

This document records the current backend and worker audit focused on:

- SOLID adherence
- extensibility and plug-and-play readiness
- security and hardcoding
- design-pattern suitability for future feature growth

## Executive Summary

The backend and worker have workable service boundaries for an evolving MVP, but they are not yet enterprise-grade in architecture. The main gaps are:

- startup-time schema mutation instead of migrations
- bearer-token auth with query-token fallback for artifact access
- loose dependency governance and inconsistent runtime manifests
- oversized orchestration classes, especially in the worker
- route modules still owning domain logic
- hardcoded AI prompts and heuristic rules embedded directly in services

The code is not in a bad state, but it is not yet open-for-extension/closed-for-modification in the areas that will receive the most change pressure.

## High Severity Findings

### 1. Schema mutation at application startup

File:
- `backend/app/main.py`

Problem:
- the backend runs `Base.metadata.create_all()` on startup
- it also executes manual `ALTER TABLE` statements in `_ensure_process_step_columns()`

Why this is a problem:
- no migration history
- no versioned schema evolution
- hard to audit and test
- unsafe for multi-environment deployment

Recommendation:
- replace startup schema mutation with Alembic migrations
- remove `_ensure_process_step_columns()` once migrations are in place

### 2. Auth model is not enterprise-safe yet

Files:
- `backend/app/api/dependencies.py`
- `backend/app/api/routes/uploads.py`
- `backend/app/services/auth_service.py`

Problem:
- auth is bearer-token based
- artifact content endpoint still supports query-token fallback
- no secure cookie session model

Why this is a problem:
- query tokens leak into URLs, logs, copied links, and browser history
- frontend still has to manage bearer tokens
- difficult to harden for enterprise environments

Recommendation:
- move to secure `HttpOnly` cookie-based auth or signed one-time artifact access
- remove `token` query parameter support from artifact content endpoints

### 3. Dependency governance is weak and inconsistent

Files:
- `backend/requirements.txt`
- `worker/pyproject.toml`
- `worker/Dockerfile`

Problem:
- backend uses loose `>=` version ranges
- worker Docker image installs `backend/requirements.txt`, not `worker/pyproject.toml`
- runtime manifests are not the single source of truth

Why this is a problem:
- poor reproducibility
- weak SBOM/scanning posture
- backend and worker dependency drift is easy to introduce

Recommendation:
- pin backend dependencies
- align worker image install source with worker manifest, or adopt one shared locked workspace manifest
- add dependency audit steps in CI

### 4. Worker orchestration is a God class

File:
- `worker/services/draft_generation_worker.py`

Problem:
- one class owns session loading, cleanup, transcript interpretation, screenshot extraction, scoring, diagram generation, persistence, and failure handling

Why this is a problem:
- violates single responsibility
- hard to test in isolation
- future changes will keep modifying the same file
- not plug-and-play for future pipeline stages

Recommendation:
- split into explicit stages:
  - session loader
  - transcript stage
  - screenshot stage
  - diagram stage
  - persistence stage
  - failure handler

## Medium Severity Findings

### 5. Route modules still contain domain behavior

File:
- `backend/app/api/routes/draft_sessions.py`

Problem:
- route functions directly implement diagram persistence, screenshot promotion/removal, step editing, and candidate selection

Why this is a problem:
- routes are hard to test
- business rules are mixed with transport concerns
- extension requires editing route code directly

Recommendation:
- move these mutations into dedicated services or use-case handlers
- keep route modules as transport adapters only

### 6. Dependency composition is still manual

File:
- `backend/app/api/dependencies.py`

Problem:
- dependencies instantiate concrete classes directly

Why this is a problem:
- weak inversion of control
- hard to swap implementations cleanly
- limited plug-and-play extensibility

Recommendation:
- introduce a composition root or provider registry
- define interfaces around storage, AI, export, and orchestration services

### 7. Config contains mixed dev defaults and production concerns

File:
- `backend/app/core/config.py`

Problem:
- localhost CORS/database/redis defaults are bundled alongside production-facing settings
- AI provider defaults are embedded directly

Why this is a problem:
- unclear separation between development and required production config
- easy to accidentally rely on unsafe defaults

Recommendation:
- keep development defaults explicit, but validate critical prod settings
- consider separate dev/prod config profiles or stricter validation rules

### 8. AI prompts are hardcoded inside services

Files:
- `backend/app/services/session_chat_service.py`
- `worker/services/ai_transcript_interpreter.py`

Problem:
- prompt bodies are embedded inline in service classes

Why this is a problem:
- no prompt versioning
- hard to test/evaluate changes
- difficult to support multiple providers or tenant-specific variants

Recommendation:
- move prompt specs into dedicated prompt modules or strategy objects
- separate provider transport from prompt construction

### 9. Artifact ingestion lacks strict file validation

Files:
- `backend/app/services/artifact_ingestion.py`
- `backend/app/api/routes/uploads.py`

Problem:
- uploads are persisted with minimal validation

Missing controls:
- extension allowlists
- content-type validation
- service-level size validation
- malformed file rejection

Recommendation:
- add per-artifact-kind validation policies
- enforce size/content-type limits before persistence

### 10. Document rendering service is too broad

File:
- `backend/app/services/document_renderer.py`

Problem:
- DOCX rendering, PDF conversion, diagram rendering fallback, summary generation, image fitting, and export context mapping all live in one class

Why this is a problem:
- extension requires modifying one large class
- hard to test isolated export concerns

Recommendation:
- split into:
  - export context builder
  - DOCX renderer
  - PDF conversion strategy
  - diagram export helper

### 11. Worker imports backend internals via path injection

File:
- `worker/bootstrap.py`

Problem:
- worker mutates `sys.path` to import backend modules and settings

Why this is a problem:
- weak package boundary
- brittle reuse story

Recommendation:
- extract shared models/config into a proper shared package or workspace package

### 12. Screenshot heuristics are hardcoded at module scope

File:
- `worker/services/draft_generation_worker.py`

Problem:
- verb patterns, timing windows, role offsets, and selection heuristics are module constants

Why this is a problem:
- difficult to tune per domain
- not configurable or strategy-based

Recommendation:
- move heuristics into configurable strategy objects or settings-backed profiles

## Low Severity / Positive Foundations

### 13. Storage abstraction is a solid starting point

File:
- `backend/app/storage/storage_service.py`

What is good:
- `StorageBackend` protocol exists
- `LocalStorageBackend` is isolated
- `StorageService` is already a facade

Why this matters:
- this is a good seam for S3/R2/B2 or another object store later

### 14. There are already meaningful service seams

Files:
- `backend/app/services/step_extraction.py`
- `backend/app/services/transcript_intelligence.py`
- `backend/app/services/screenshot_mapping.py`
- `backend/app/services/job_dispatcher.py`

What is good:
- some responsibilities are already separated

What is missing:
- those boundaries are not yet enforced consistently at route and worker orchestration levels

## Hardcoding Snapshot

Notable hardcoded values or policies still present:

- dev infra defaults in `backend/app/core/config.py`
- prompt bodies in AI services
- fixed diagram artifact filename `detailed-process-flow.png`
- export folder name `exports`
- screenshot heuristics and action windows in the worker

These are not all equally bad, but they should be reviewed if the goal is strict configurability and extension.

## Plug-and-Play Readiness

Current state:
- not yet plug-and-play

Main blockers:
- concrete class instantiation everywhere
- no provider/strategy registry for AI/export/auth/storage
- oversized route and worker coordinator layers
- no formal pipeline stage abstraction

## Recommended Refactor Order

### Phase 1: security and infrastructure

1. introduce migrations
2. harden auth/session handling
3. remove query-token artifact access
4. add upload validation
5. pin dependencies and align manifests

### Phase 2: service and orchestration decomposition

1. split `draft_generation_worker.py`
2. split `document_renderer.py`
3. move route business logic into services/use cases

### Phase 3: extension architecture

1. add interfaces/strategies for:
   - auth/session provider
   - artifact access provider
   - AI provider
   - transcript interpreter
   - diagram generator
   - export renderer
   - storage backend
2. create a proper composition root

## Immediate Next Recommendation

If the goal is enterprise hardening, the next best implementation slice is:

1. auth and artifact access hardening
2. migrations
3. dependency pinning and runtime manifest cleanup

Only after that should the larger orchestration refactors start.
