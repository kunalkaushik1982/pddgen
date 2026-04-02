# Backend Codebase Walkthrough

This document captures a plain-language walkthrough of the backend code in `backend/`.

It is intentionally structured as:

1. top-level folder map
2. layer-by-layer explanation
3. key files and what they do
4. important classes/functions
5. request-flow understanding

---

## 1. Backend Top-Level Structure

Backend root:

- `backend/alembic`
  - database migration setup and migration history
- `backend/app`
  - actual FastAPI application code
- `backend/tests`
  - backend-focused tests
- `backend/Dockerfile`
  - backend container build
- `backend/pyproject.toml`
  - backend Python dependencies and packaging metadata
- `backend/requirements.txt`
  - dependency snapshot / install convenience
- `backend/alembic.ini`
  - Alembic configuration entry file
- `backend/.env`
  - local runtime configuration
- `backend/.env.example`
  - example configuration values

---

## 2. Main Code Layers Under `backend/app`

### `app/main.py`

This is the backend entry point.

Responsibilities:

- creates the FastAPI app
- configures logging
- attaches middleware
- validates database schema on startup
- registers all API route groups

Important functions:

- `lifespan(_app: FastAPI)`
  - startup hook
  - ensures local storage exists when local storage backend is used
  - runs database schema validation before serving traffic
- `create_app()`
  - creates and configures the FastAPI application
  - attaches:
    - `RequestContextMiddleware`
    - `CSRFMiddleware`
    - `CORSMiddleware`
  - mounts route modules:
    - `uploads`
    - `auth`
    - `admin`
    - `meta`
    - `meetings`
    - `draft_sessions`
    - `exports`

Why this file matters:

- this is the composition root of the backend
- it wires together the runtime pieces, but does not contain business logic

### `app/core`

This folder contains app-wide core concerns.

Important files:

- `app/core/config.py`
  - central environment-backed settings object
  - uses `pydantic-settings`
  - defines:
    - app settings
    - DB URL
    - Redis URL
    - auth settings
    - AI settings
    - storage settings
    - screenshot-generation settings
- `app/core/observability.py`
  - logging helpers and context binding
- `app/core/release.py`
  - release/version metadata

Important function in `config.py`:

- `get_settings()`
  - cached accessor for the `Settings` object
  - most backend services depend on this indirectly or directly

Why `config.py` matters:

- this file is the configuration backbone of the backend
- almost every subsystem depends on values defined here

### `app/api`

This folder contains the HTTP API surface.

Important files:

- `app/api/dependencies.py`
  - dependency-injection helpers for FastAPI
  - provides service instances and current-user resolution
- `app/api/routes/*`
  - route modules grouped by business area

Current route modules:

- `admin.py`
- `auth.py`
- `draft_sessions.py`
- `exports.py`
- `meetings.py`
- `meta.py`
- `uploads.py`

### `app/db`

This folder contains database wiring.

Important files:

- `app/db/base.py`
  - SQLAlchemy declarative base
- `app/db/session.py`
  - SQLAlchemy engine/session setup and DB session dependency
- `app/db/schema_validation.py`
  - startup validation that checks schema health

### `app/middleware`

Cross-cutting HTTP middleware.

Important files:

- `app/middleware/csrf.py`
  - CSRF validation
- `app/middleware/request_context.py`
  - request-scoped logging/context helpers

### `app/models`

This folder defines the database entities.

Examples:

- `draft_session.py`
- `artifact.py`
- `process_group.py`
- `process_step.py`
- `process_note.py`
- `meeting.py`
- `output_document.py`
- `diagram_layout.py`
- `user.py`
- `user_auth_token.py`
- `action_log.py`

These are SQLAlchemy ORM models and represent persistent system state.

### `app/schemas`

This folder defines API-facing data contracts.

Examples:

- request payloads
- response payloads
- shared enums/literals
- nested response structures for sessions, steps, meetings, auth, workflow intelligence

This layer is the shape of data exposed to the frontend.

### `app/services`

This is the main business-logic layer of the backend.

This folder contains:

- orchestration services
- review/edit services
- auth services
- document export services
- session mapping and response shaping
- queue-dispatch helpers
- chat/evidence logic

This is the most important backend folder after `models`.

### `app/storage`

Storage abstraction layer.

Important file:

- `app/storage/storage_service.py`

This hides whether storage is:

- local filesystem
- object storage

So higher layers do not need to know storage implementation details.

---

## 3. First Critical File Walkthrough

### `app/api/routes/draft_sessions.py`

This is one of the most important route modules because it drives the main product workflow.

Responsibilities:

- list sessions
- queue draft generation
- queue screenshot generation
- fetch one session for review
- delete a session
- ask grounded Q&A against a session
- fetch and save diagram model/layout
- update reviewed process steps and screenshot selections

Important route handlers from the top of the file:

- `list_draft_sessions(...)`
  - returns the current user’s historical sessions
- `generate_draft_session(...)`
  - marks session as processing
  - writes action log
  - enqueues background draft generation through `JobDispatcherService`
- `generate_session_screenshots(...)`
  - validates that draft steps and videos exist
  - acquires screenshot-generation lock
  - writes action log
  - enqueues screenshot generation
- `get_draft_session(...)`
  - returns the structured session for frontend review
- `delete_draft_session(...)`
  - deletes a draft-only session
- `ask_session(...)`
  - runs grounded Q&A over session evidence

Why this file matters:

- this is the primary HTTP interface used by the review workspace frontend
- it coordinates many backend services without containing much core business logic directly

---

## 4. Architectural Reading Order Recommendation

If someone wants to understand this backend quickly, this is the best reading order:

1. `app/main.py`
2. `app/core/config.py`
3. `app/api/routes/draft_sessions.py`
4. `app/api/dependencies.py`
5. `app/services/pipeline_orchestrator.py`
6. `app/services/job_dispatcher.py`
7. `app/models/draft_session.py`
8. `app/models/process_group.py`
9. `app/models/process_step.py`
10. `app/services/mappers.py`

This reading order gives:

- app entry
- configuration
- main API
- DI wiring
- orchestration
- background dispatch
- persistence model
- response shaping

---

## 5. Current Status Of This Walkthrough

So far this document covers:

- backend top-level structure
- purpose of each major folder
- startup/app entry
- configuration layer
- one key route module
- recommended reading order

Next sections should cover in detail:

- `app/api/dependencies.py`
- all route modules one by one
- `app/models/*`
- `app/schemas/*`
- `app/services/*`
- end-to-end request flow from upload to export

---

## 6. What Is Happening Inside The First Important Files

This section explains not just what the file is for, but what actually happens inside it.

### `app/main.py`

This file is the backend bootstrapper.

Flow inside the file:

1. import FastAPI and middleware dependencies
2. import all route modules
3. import settings, logging, schema validation, and middleware classes
4. define a `lifespan()` function for startup work
5. define `create_app()` to assemble the FastAPI app
6. create the final exported app instance at the bottom with `app = create_app()`

#### `lifespan(_app: FastAPI)`

This function runs automatically when the app starts and stops.

What happens inside:

- reads settings
- if local storage is enabled:
  - ensures the local storage root exists on disk
- validates that the DB schema matches the expected application schema
- writes a startup log
- yields control back to FastAPI

Why this matters:

- startup safety checks are centralized here
- the app refuses to run with an invalid schema shape

Code references:

- import of schema validator:
  - [backend/app/main.py:13](C:\Users\work\Documents\PddGenerator\backend\app\main.py:13)
- actual schema-validation call:
  - [backend/app/main.py:24](C:\Users\work\Documents\PddGenerator\backend\app\main.py:24)
- FastAPI app wiring that uses the lifespan hook:
  - [backend/app/main.py:34](C:\Users\work\Documents\PddGenerator\backend\app\main.py:34)

#### `create_app()`

This function builds the FastAPI object.

What happens inside:

- loads settings
- configures logging level
- creates `FastAPI(...)`
- attaches middleware in order:
  - `RequestContextMiddleware`
  - `CSRFMiddleware`
  - `CORSMiddleware`
- includes all route groups with the configured API prefix

Important design point:

- this file wires the app together, but does not contain request business logic
- that is a good separation of concerns

### `app/api/dependencies.py`

This file is the dependency-injection hub for route handlers.

The route files do not directly construct services everywhere.
Instead, they ask FastAPI for dependencies from this file.

That gives:

- centralized wiring
- easier testing
- fewer repeated constructors inside route files

#### Service provider functions

Examples:

- `get_storage_service()`
- `get_artifact_ingestion_service()`
- `get_pipeline_orchestrator_service()`
- `get_document_renderer_service()`
- `get_draft_session_diagram_service()`
- `get_draft_session_review_service()`
- `get_session_chat_service()`
- `get_job_dispatcher_service()`
- `get_meeting_service()`
- `get_process_group_service()`

What these do:

- create and return service objects
- in a few cases, inject nested service dependencies into them

Example:

- `get_artifact_ingestion_service()`
  - creates `ArtifactIngestionService`
  - injects:
    - `StorageService`
    - `ArtifactValidationService`

This means the route file only says:

- give me an `ArtifactIngestionService`

It does not care how it is constructed.

#### `get_auth_service()`

This is more interesting than the others.

What happens inside:

- loads settings
- builds the configured identity provider through `AuthProviderRegistry`
- optionally builds `DatabaseSessionService` depending on the configured session backend
- returns `AuthService(...)`

This gives a clean auth façade while keeping provider/session decisions configurable.

#### `get_current_user(...)`

This is one of the most important dependencies in the backend.

What happens inside:

- reads the configured auth session cookie
- gets a DB session
- gets the configured `AuthService`
- if the cookie exists:
  - authenticates the token
  - sets logging actor context
  - returns the `UserModel`
- otherwise:
  - raises HTTP 401

Why this matters:

- almost all protected routes depend on this
- it is the gatekeeper for authenticated access

#### `get_current_admin_user(...)`

What happens inside:

- depends on `get_current_user`
- checks whether the user is in configured admin usernames
- raises HTTP 403 if not admin

So:

- `get_current_user` = authentication
- `get_current_admin_user` = authorization for admin-only routes

### `app/api/routes/auth.py`

This file defines login, registration, user lookup, and logout endpoints.

It is intentionally thin.
It mostly:

- validates request data through schemas
- calls `AuthService`
- sets or clears cookies

#### File-level setup

At the top:

- creates `router = APIRouter(prefix="/auth", tags=["auth"])`
- loads global `settings`
- creates `csrf_service = CsrfService(settings)`

That means this file is prepared once and then reused per request.

#### `register(...)`

What happens inside:

- receives username/password payload
- gets DB session and `AuthService`
- calls `service.register(...)`
- sets auth cookie
- sets CSRF cookie
- returns `AuthResponse`

So registration both creates the user and logs them in immediately.

#### `login(...)`

What happens inside:

- receives username/password
- calls `service.login(...)`
- sets auth cookie
- sets CSRF cookie
- returns `AuthResponse`

So login flow mirrors register flow.

#### `get_me(...)`

What happens inside:

- depends on `get_current_user`
- if CSRF cookie is missing, it issues a fresh one
- returns current user info

Why that extra CSRF logic exists:

- frontend needs the CSRF cookie for protected write requests
- this endpoint helps ensure it exists after login/session restore

#### `logout(...)`

What happens inside:

- reads session cookie
- if token exists, invalidates it through `AuthService`
- builds a clean 204 response
- clears auth cookie
- clears CSRF cookie
- returns the cleared response

#### Private helper functions in this file

- `_set_auth_cookie(response, token)`
- `_set_csrf_cookie(response)`
- `_clear_auth_cookie(response)`
- `_clear_csrf_cookie(response)`
- `_build_user_response(user)`

These helpers keep route functions small and readable.

### `app/api/routes/uploads.py`

This file handles session creation and artifact intake.

This is the main entry point before generation starts.

#### File-level setup

At the top:

- creates upload router
- creates shared `ActionLogService`

#### `create_upload_session(...)`

What happens inside:

- receives session creation payload
- calls `ArtifactIngestionService.create_session(...)`
- ensures default meeting exists
- ensures default process group exists
- records an action log entry:
  - `Session created`
- commits DB transaction
- refreshes the session
- returns mapped session response

Important meaning:

- a draft session is the root workspace entity
- meeting and process-group defaults are created early so the rest of the pipeline has stable anchors

#### `upload_artifact(...)`

What happens inside:

- receives:
  - session id
  - artifact kind
  - uploaded file
  - optional meeting and upload-batch metadata
- resolves target meeting
- calls `ArtifactIngestionService.ingest_artifact(...)`
- records action log:
  - `<artifact kind> uploaded`
- commits transaction
- refreshes artifact
- returns API schema for uploaded artifact

This is one of the key backend ingestion endpoints.

#### `get_artifact_content(...)`

What happens inside:

- loads artifact by id
- verifies ownership through the parent session owner
- prepares content-disposition header
- asks storage service for an internal artifact path
- if internal path exists:
  - returns `X-Accel-Redirect` response for nginx to serve directly
- otherwise:
  - reads bytes from storage and streams them back

Why this matters:

- it supports secure protected artifact access
- it lets nginx serve large files efficiently when possible

#### `delete_uploaded_artifact(...)`

What happens inside:

- validates artifact ownership via service
- deletes artifact from session
- returns `204`

This keeps deletion logic in the service layer rather than directly in the route.

---

## 7. First Set Of Backend Design Observations

From these files, the backend structure is already following a reasonably clean pattern:

- `main.py`
  - composition root
- `api/routes/*`
  - HTTP transport layer
- `api/dependencies.py`
  - dependency provider layer
- `services/*`
  - business logic
- `models/*`
  - persistence model
- `schemas/*`
  - API contracts

That means route files are mostly orchestration points, not business-logic dumps.

This is the correct direction for maintainability.

---

## 8. What `app/core/observability.py` Is Used For

File:

- [backend/app/core/observability.py](C:\Users\work\Documents\PddGenerator\backend\app\core\observability.py)

This file is the backend logging utility layer.

Its job is:

- configure application logging once
- make logs structured JSON instead of loose plain text
- attach shared context to logs
  - request id
  - path
  - method
  - actor
  - session id
  - task id

### Why this file exists

Without this file, logs would usually become inconsistent:

- one module logs one way
- another module logs another way
- request id is missing in some logs
- actor/session context is missing in others

This file standardizes that.

### Important pieces inside it

#### `StructuredJsonFormatter`

This converts Python log records into JSON log lines.

What it includes:

- timestamp
- level
- logger name
- message
- current shared log context
- any `extra={...}` values supplied by the caller
- exception and stack info when present

Meaning:

- logs become machine-readable and searchable

#### `configure_logging(level)`

This configures root logging once for the process.

What it does:

- creates a stream handler
- applies `StructuredJsonFormatter`
- clears existing handlers
- sets root logger level
- normalizes logging for:
  - `uvicorn`
  - `celery`

This is why both backend and worker logs can follow the same style.

#### `get_logger(name)`

Simple helper that returns a module logger.

This is why many files do:

- `logger = get_logger(__name__)`

#### Context helpers

These functions manage shared log context:

- `get_log_context()`
- `set_log_context(**values)`
- `reset_log_context(token)`
- `bind_log_context(**values)`

### How shared log context works

Example:

If a request comes in for session `abc123` from user `kunal`, backend can bind:

- `request_id`
- `path`
- `method`
- `actor`
- `session_id`

Then every log written during that request can automatically include those values.

That makes debugging much easier.

### Where this is used

Examples in the current backend:

- [backend/app/main.py](C:\Users\work\Documents\PddGenerator\backend\app\main.py)
  - calls `configure_logging(...)`
- [backend/app/middleware/request_context.py](C:\Users\work\Documents\PddGenerator\backend\app\middleware\request_context.py)
  - binds request id, method, and path for each request
- [backend/app/api/dependencies.py](C:\Users\work\Documents\PddGenerator\backend\app\api\dependencies.py)
  - binds `actor=user.username` after authentication
- [backend/app/api/routes/draft_sessions.py](C:\Users\work\Documents\PddGenerator\backend\app\api\routes\draft_sessions.py)
  - uses `bind_log_context(session_id=...)` around generation requests
- [backend/app/services/job_dispatcher.py](C:\Users\work\Documents\PddGenerator\backend\app\services\job_dispatcher.py)
  - logs queueing events with task id and session id

### Simple interpretation

This file is not business logic.

It is the backend’s:

- logging standardizer
- request/task trace context carrier
- JSON log formatter

So when something goes wrong, this file helps answer:

- which request caused it
- which user caused it
- which session it belonged to
- which task/job it belonged to
