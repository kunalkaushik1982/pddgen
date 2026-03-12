# Architecture Notes

## Overview

`PddGenerator` is an internal enterprise application that converts RPA discovery evidence into a reviewable first-draft PDD.

The implementation currently consists of:

- `frontend`
  React + Vite + TypeScript BA workspace
- `backend`
  FastAPI application for session management, artifact upload, draft generation, review persistence, and DOCX export
- `worker`
  Celery background worker for transcript normalization and video-derived screenshot generation
- `storage`
  local filesystem contract for pilot usage

## Current Runtime Model

### Frontend

The frontend provides a single workflow page where the BA can:

1. create a draft session
2. upload video, transcript, and template files
3. trigger draft generation
4. review and edit steps
5. export the DOCX

### Backend

The backend currently provides these main API capabilities:

- create draft session
- upload artifacts to a session
- queue draft session generation
- fetch draft session state
- update process steps
- export DOCX

### Worker

The worker currently supports:

- transcript normalization for `.txt`, `.vtt`, and `.docx`
- background draft generation pipeline
- optional screenshot derivation from video frames using `ffmpeg`
- session status updates in the shared database

## Backend Architecture

### Core Layers

- `app/api`
  route handlers and dependency wiring
- `app/core`
  configuration
- `app/db`
  SQLAlchemy base and database session management
- `app/models`
  ORM models for persisted entities
- `app/schemas`
  API request and response schemas
- `app/services`
  business logic and orchestration
- `app/storage`
  storage abstraction for pilot local filesystem behavior

### Main Entities

- `DraftSessionModel`
  root entity for one PDD generation workflow
- `ArtifactModel`
  uploaded or derived artifacts such as video, transcript, template, and screenshot
- `ProcessStepModel`
  extracted or edited AS-IS steps
- `ProcessNoteModel`
  rule-like transcript-derived notes
- `OutputDocumentModel`
  exported DOCX outputs

### Main Services

- `ArtifactIngestionService`
  creates sessions and stores artifacts
- `PipelineOrchestratorService`
  generates steps and notes from transcript artifacts
- `DocumentRendererService`
  renders the final DOCX from a template
- `StorageService`
  hides the physical storage medium

## Worker Architecture

### Worker-Specific Components

- `TranscriptNormalizer`
  converts transcript artifacts into plain text
- `VideoFrameExtractor`
  derives screenshots from video timestamps using `ffmpeg`
- `DraftGenerationWorker`
  coordinates normalization, extraction, note creation, and screenshot derivation

### Shared Contracts

The worker imports backend configuration, database setup, ORM models, and extraction services so that domain logic stays centralized.

## Storage Architecture

### Pilot Storage Layout

```text
storage/
  local/
    <session-id>/
      video/
      transcript/
      template/
      sop/
      diagram/
      screenshot/
      generated-screenshots/
      exports/
```

### Storage Principle

Application code should depend on storage capabilities, not storage location. This will allow later migration to shared or object storage without changing domain logic.

## DOCX Rendering Flow

1. BA uploads the template as a `template` artifact.
2. Backend loads the template from storage.
3. Backend builds a structured render context from reviewed session data.
4. The template is rendered using deterministic template-based DOCX generation.
5. Output is stored in the session's `exports/` folder and registered in the database.

## Current Limitations

These are the main known gaps after the current Phase 3 implementation:

- worker-based screenshot derivation depends on the worker runtime and local `ffmpeg`
- transcript extraction is deterministic and transcript-driven, not yet multimodal
- no authentication or authorization layer is implemented
- no automated cleanup or retention job is implemented
- no end-to-end tests are implemented yet

## Recommended Next Integration Step

The next highest-value technical step is:

`add explicit job status metadata and richer progress reporting so the BA can see which pipeline stage is running`

Why this matters:

- improves operator trust during long-running video processing
- makes failures easier to diagnose
- supports future pipeline stage expansion

## Local Development Dependencies

Current local dependency model:

- PostgreSQL via Docker
- Redis via Docker
- backend and worker run locally
- `ffmpeg` installed locally if screenshot extraction is required

Worker dependency compose file:

- `worker/docker-compose.dependencies.yml`
