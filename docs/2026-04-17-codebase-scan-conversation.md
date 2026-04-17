# 2026-04-17 Codebase Scan Conversation

This document records the repo scan and architectural summary from the 2026-04-17 discussion.

## User Request

> Please scan the codebase and let me know once you have full understaning of the code

## Scan Summary

I completed an architectural scan of the repo and reached a solid working understanding of how it is structured and how the main flows operate.

At a high level, this is a 3-part application:

- `frontend/`: React + Vite workspace UI with auth, workspace setup, session review/editing, diagram editing, billing, and admin views
- `backend/`: FastAPI API that owns auth, uploads, session state, review mutations, exports, admin metrics, quotas, billing, and portability wiring
- `worker/`: Celery-based background pipeline that performs transcript interpretation, workflow grouping, canonicalization, diagram assembly, and screenshot generation

The core flow is:

1. create a draft session and default meeting/process group
2. upload transcript, video, and template artifacts
3. queue background work with run guards
4. run worker pipeline stages for interpretation, grouping, diagram generation, and screenshots
5. review and edit the resulting session in the frontend
6. export DOCX or PDF from reviewed session data

## Important Correction To Older Docs

The older pilot-oriented docs do not fully describe the current repo. The codebase now includes:

- authenticated users and session cookies
- password and Google auth
- quotas and usage tracking
- admin console and operational metrics
- billing catalog, Stripe and Razorpay checkout, and GST invoice support
- AI-backed session-grounded Q&A
- multi-process grouping and diagram persistence

## Working Conclusion

The scan established a strong understanding of:

- architecture and composition roots
- main domain entities
- request and background-processing flows
- boundaries between frontend, backend, and worker responsibilities

It did not imply a line-by-line understanding of every file or every edge case in every service.

## Requested Follow-Up

The follow-up request was:

> Please do that.

That request asked for a concise codebase map and reading order.

## Codebase Map

### Runtime entry points

- Backend app bootstrapping: [backend/app/main.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/main.py:1)
- Backend dependency wiring: [backend/app/api/dependencies.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/dependencies.py:1)
- Frontend entry: [frontend/src/main.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/main.tsx:1)
- Frontend routing: [frontend/src/router.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/router.tsx:1)
- Worker Celery app: [worker/celery_app.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/celery_app.py:1)
- Worker pipeline composition root: [worker/pipeline/composition.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/pipeline/composition.py:1)

### Main product flow

- Session creation and artifact upload: [backend/app/api/routes/uploads.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/uploads.py:1)
- Draft generation, screenshots, and review mutations: [backend/app/api/routes/draft_sessions.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/draft_sessions.py:1)
- Export DOCX/PDF: [backend/app/api/routes/exports.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/exports.py:1)
- Frontend workspace setup: [frontend/src/routes/WorkspaceRoute.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/routes/WorkspaceRoute.tsx:1)
- Frontend session and review surface: [frontend/src/routes/SessionRoute.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/routes/SessionRoute.tsx:1)
- Review page: [frontend/src/pages/StepReviewPage.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/pages/StepReviewPage.tsx:1)
- Upload page: [frontend/src/pages/UploadPage.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/pages/UploadPage.tsx:1)

### Backend structure

- `app/api/routes`: HTTP surface grouped by business area
- `app/services`: business logic and orchestration
- `app/models`: SQLAlchemy persistence layer
- `app/schemas`: API contracts exposed to frontend
- `app/core/config.py`: env-backed runtime settings and feature toggles
- `app/storage/storage_service.py`: storage abstraction
- `app/portability/*`: seams for auth, payments, job enqueueing, and related integrations

Most important backend services:

- [backend/app/services/pipeline_orchestrator.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/pipeline_orchestrator.py:1)
- [backend/app/services/job_dispatcher.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/job_dispatcher.py:1)
- [backend/app/services/draft_session_review_service.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/draft_session_review_service.py:1)
- [backend/app/services/draft_session_diagram_service.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/draft_session_diagram_service.py:1)
- [backend/app/services/document_renderer.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/services/document_renderer.py:1)

Core models:

- [backend/app/models/draft_session.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/draft_session.py:1)
- [backend/app/models/process_group.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/process_group.py:1)
- [backend/app/models/process_step.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/process_step.py:1)
- [backend/app/models/artifact.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/artifact.py:1)
- [backend/app/models/user.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/models/user.py:1)

### Worker structure

- Task entrypoints: [worker/tasks/draft_generation.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/tasks/draft_generation.py:1), [worker/tasks/screenshot_generation.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/tasks/screenshot_generation.py:1)
- Use-case layer: [worker/pipeline/use_cases.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/pipeline/use_cases.py:1)
- Stage definitions: `worker/pipeline/stages/*`
- AI skill registry: [worker/ai_skills/registry.py](/abs/path/c:/Users/work/Documents/PddGenerator/worker/ai_skills/registry.py:1)
- Transcript interpreter stack: `worker/ai_skills/transcript_interpreter/*`
- Workflow grouping and segmentation logic: `worker/grouping/*`
- Media utilities: `worker/media/*`
- Screenshot context and derivation: `worker/screenshot/*`

### Frontend structure

- Providers and app-wide state: [frontend/src/providers/AppProviders.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/providers/AppProviders.tsx:1)
- Auth state: [frontend/src/providers/AuthProvider.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/providers/AuthProvider.tsx:1)
- Route-level containers: `frontend/src/routes/*`
- Page components: `frontend/src/pages/*`
- API client and services: `frontend/src/services/*`
- Domain types: `frontend/src/types/*`
- Review, diagram, and session UI: `frontend/src/components/review/*`, `frontend/src/components/diagram/*`

Most important hooks:

- [frontend/src/hooks/useWorkspaceFlow.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useWorkspaceFlow.ts:1)
- [frontend/src/hooks/useSessionActions.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useSessionActions.ts:1)
- [frontend/src/hooks/useReviewWorkspace.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useReviewWorkspace.ts:1)
- [frontend/src/hooks/useStepEditor.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useStepEditor.ts:1)
- [frontend/src/hooks/useAskSession.ts](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/hooks/useAskSession.ts:1)

### Platform features outside the core PDD flow

- Auth API: [backend/app/api/routes/auth.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/auth.py:1)
- Billing API: [backend/app/api/routes/payments.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/payments.py:1)
- Admin API: [backend/app/api/routes/admin.py](/abs/path/c:/Users/work/Documents/PddGenerator/backend/app/api/routes/admin.py:1)
- Billing page: [frontend/src/pages/BillingPage.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/pages/BillingPage.tsx:1)
- Admin page: [frontend/src/pages/AdminPage.tsx](/abs/path/c:/Users/work/Documents/PddGenerator/frontend/src/pages/AdminPage.tsx:1)

## Recommended Reading Order

1. [docs/architecture.md](/abs/path/c:/Users/work/Documents/PddGenerator/docs/architecture.md)
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
