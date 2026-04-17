# Developer Onboarding

This document is the fastest way to get productive in the current `PddGenerator` codebase without reading the entire repository first.

## What This Repo Is

`PddGenerator` is no longer just a pilot uploader plus extractor. The current system is a full application with:

- a React workspace for uploads, review, diagrams, billing, and admin
- a FastAPI backend for sessions, artifacts, auth, exports, billing, and admin operations
- a Celery worker for long-running draft generation and screenshot generation
- PostgreSQL for persisted state
- Redis for queueing and distributed run guards

The product flow is:

1. user creates a draft session
2. user uploads transcripts, templates, and optionally videos
3. backend queues background generation
4. worker interprets transcripts, groups workflows, assembles diagrams, and derives screenshots
5. frontend loads the review workspace for BA edits
6. backend renders DOCX or PDF exports from reviewed session data

## Read This First

If you only have 30-60 minutes, read in this order:

1. [architecture.md](/abs/path/c:/Users/work/Documents/PddGenerator/docs/architecture.md)
2. [backend/app/main.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/main.py:1)
3. [backend/app/core/config.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/core/config.py:1)
4. [backend/app/api/dependencies.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/dependencies.py:1)
5. [backend/app/api/routes/uploads.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/uploads.py:1)
6. [backend/app/api/routes/draft_sessions.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/draft_sessions.py:1)
7. [backend/app/services/pipeline_orchestrator.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/pipeline_orchestrator.py:1)
8. [backend/app/services/job_dispatcher.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/job_dispatcher.py:1)
9. [worker/pipeline/composition.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/pipeline/composition.py:1)
10. [worker/tasks/draft_generation.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/tasks/draft_generation.py:1)
11. [frontend/src/router.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/router.tsx:1)
12. [frontend/src/routes/WorkspaceRoute.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/routes/WorkspaceRoute.tsx:1)
13. [frontend/src/routes/SessionRoute.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/routes/SessionRoute.tsx:1)
14. [frontend/src/pages/StepReviewPage.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/pages/StepReviewPage.tsx:1)

That path covers the real composition roots and the main user workflow.

## Repo Layout

### `frontend/`

This is the user-facing application.

What lives here:

- route containers under `src/routes`
- page components under `src/pages`
- backend client wrappers under `src/services`
- session and review hooks under `src/hooks`
- review, diagram, admin, and layout UI under `src/components`
- app-wide state providers under `src/providers`

Start with:

- [frontend/src/main.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/main.tsx:1)
- [frontend/src/router.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/router.tsx:1)
- [frontend/src/providers/AppProviders.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/providers/AppProviders.tsx:1)
- [frontend/src/routes/WorkspaceRoute.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/routes/WorkspaceRoute.tsx:1)
- [frontend/src/routes/SessionRoute.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/routes/SessionRoute.tsx:1)

Most important hooks:

- [frontend/src/hooks/useWorkspaceFlow.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useWorkspaceFlow.ts:1)
- [frontend/src/hooks/useSessionActions.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useSessionActions.ts:1)
- [frontend/src/hooks/useReviewWorkspace.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useReviewWorkspace.ts:1)
- [frontend/src/hooks/useStepEditor.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useStepEditor.ts:1)
- [frontend/src/hooks/useAskSession.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useAskSession.ts:1)

### `backend/`

This is the API and application core.

What lives here:

- FastAPI route handlers under `app/api/routes`
- dependency wiring under `app/api/dependencies.py`
- configuration under `app/core`
- ORM models under `app/models`
- API schemas under `app/schemas`
- business logic under `app/services`
- platform seams under `app/portability`
- DB session and schema validation under `app/db`

Start with:

- [backend/app/main.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/main.py:1)
- [backend/app/api/dependencies.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/dependencies.py:1)
- [backend/app/api/routes/uploads.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/uploads.py:1)
- [backend/app/api/routes/draft_sessions.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/draft_sessions.py:1)
- [backend/app/api/routes/exports.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/exports.py:1)

Core models:

- [backend/app/models/draft_session.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/draft_session.py:1)
- [backend/app/models/artifact.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/artifact.py:1)
- [backend/app/models/process_group.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/process_group.py:1)
- [backend/app/models/process_step.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/process_step.py:1)
- [backend/app/models/user.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/user.py:1)

Core services:

- [backend/app/services/pipeline_orchestrator.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/pipeline_orchestrator.py:1)
- [backend/app/services/job_dispatcher.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/job_dispatcher.py:1)
- [backend/app/services/draft_session_review_service.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/draft_session_review_service.py:1)
- [backend/app/services/draft_session_diagram_service.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/draft_session_diagram_service.py:1)
- [backend/app/services/document_renderer.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/document_renderer.py:1)

### `worker/`

This is the long-running processing engine.

What lives here:

- Celery bootstrap and tasks
- pipeline composition and stage orchestration
- transcript interpretation and AI-skill runtime
- workflow grouping and canonical merge logic
- screenshot derivation and frame extraction

Start with:

- [worker/celery_app.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/celery_app.py:1)
- [worker/tasks/draft_generation.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/tasks/draft_generation.py:1)
- [worker/tasks/screenshot_generation.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/tasks/screenshot_generation.py:1)
- [worker/pipeline/composition.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/pipeline/composition.py:1)
- [worker/pipeline/use_cases.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/pipeline/use_cases.py:1)

Important directories:

- `worker/pipeline/stages`: explicit pipeline stages
- `worker/grouping`: workflow segmentation, grouping, and merge logic
- `worker/ai_skills`: skill registry and prompt-driven interpretation modules
- `worker/media`: transcript normalization and video frame extraction
- `worker/screenshot`: screenshot context building and screenshot-only worker logic

## Main Runtime Responsibilities

### Frontend

The frontend owns:

- auth state and route gating
- session creation and artifact upload UX
- polling and refresh behavior while jobs run
- review and edit workflows for steps, screenshots, and diagrams
- admin and billing surfaces

### Backend

The backend owns:

- authentication and CSRF
- artifact intake and storage references
- session loading and response mapping
- queueing jobs and preventing duplicate runs
- review mutations and diagram persistence
- exports, billing, quotas, and admin visibility

### Worker

The worker owns:

- expensive transcript interpretation
- process segmentation and grouping
- canonical process merge
- diagram assembly
- screenshot derivation from videos
- failure handling and completion persistence

## Common Task Guide

### If you need to change upload behavior

Look at:

- [frontend/src/hooks/useWorkspaceFlow.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useWorkspaceFlow.ts:1)
- [frontend/src/pages/UploadPage.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/pages/UploadPage.tsx:1)
- [backend/app/api/routes/uploads.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/uploads.py:1)
- [backend/app/services/artifact_ingestion.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/artifact_ingestion.py:1)

### If you need to change review/edit behavior

Look at:

- [frontend/src/routes/SessionRoute.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/routes/SessionRoute.tsx:1)
- [frontend/src/pages/StepReviewPage.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/pages/StepReviewPage.tsx:1)
- [frontend/src/components/review](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/components/review)
- [backend/app/api/routes/draft_sessions.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/draft_sessions.py:1)
- [backend/app/services/draft_session_review_service.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/draft_session_review_service.py:1)

### If you need to change background generation

Look at:

- [backend/app/services/job_dispatcher.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/job_dispatcher.py:1)
- [worker/tasks/draft_generation.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/tasks/draft_generation.py:1)
- [worker/pipeline/composition.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/pipeline/composition.py:1)
- [worker/pipeline/stages](/abs/path/c:/Users/work/Documents/PddGenerator/worker/pipeline/stages)
- [worker/grouping](/abs/path/c:/Users/work/Documents/PddGenerator/worker/grouping)

### If you need to change exports

Look at:

- [backend/app/api/routes/exports.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/exports.py:1)
- [backend/app/services/document_renderer.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/document_renderer.py:1)
- [backend/app/services/document_template_renderer.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/document_template_renderer.py:1)

### If you need to change auth, admin, quotas, or billing

Look at:

- [backend/app/api/routes/auth.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/auth.py:1)
- [backend/app/api/routes/admin.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/admin.py:1)
- [backend/app/api/routes/payments.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/payments.py:1)
- [frontend/src/providers/AuthProvider.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/providers/AuthProvider.tsx:1)
- [frontend/src/pages/AdminPage.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/pages/AdminPage.tsx:1)
- [frontend/src/pages/BillingPage.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/pages/BillingPage.tsx:1)

## What To Ignore At First

Do not try to understand everything before making a useful change.

You can usually defer:

- older roadmap/spec documents under `docs/superpowers`
- billing internals unless you are touching checkout or invoices
- portability adapters you are not using
- individual AI skill prompt files unless your change affects interpretation behavior

Read those only when your change crosses those boundaries.

## Known Documentation Gap

Some older docs still describe the repo as a smaller pilot system. The current codebase includes materially more functionality than those documents imply. Prefer the code and the route/composition roots when docs disagree.

## Suggested First Local Checks

When orienting yourself after dependency install:

1. start backend and worker
2. open the frontend
3. create a draft session
4. upload a transcript and template
5. queue generation
6. inspect one session in the review UI
7. trace the corresponding API route and worker task

That gives the quickest end-to-end mental model.
