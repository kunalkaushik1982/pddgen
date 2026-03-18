# PddGenerator

AI-assisted PDD drafting for RPA discovery workflows. The application is designed for Business Analysts who need to convert discovery artifacts into a trustworthy first-draft PDD.

## Current Scope

The current implementation supports:

- creating a draft session
- uploading process videos, transcripts, and a DOCX template
- queueing background draft generation for transcript-driven AS-IS steps
- reviewing and editing extracted steps
- exporting a DOCX using the uploaded template

The first pilot path assumes:

- required inputs are `video + transcript + template`
- screenshots are derived from video frames
- local filesystem storage is acceptable for pilot testing

## Project Structure

- `frontend`
  React + Vite + TypeScript BA workspace
- `backend`
  FastAPI service for session management, uploads, generation, review updates, and export
- `worker`
  Celery worker for transcript normalization and video-based screenshot generation
- `storage`
  pilot storage contract and migration guidance
- `docs`
  implementation-aware architecture documentation

## Technology Stack

- Frontend: React + Vite + TypeScript
- Backend: FastAPI
- Database: PostgreSQL
- Queue and worker: Celery + Redis
- Storage: local filesystem for pilot, with planned migration to shared or object-backed storage
- Document generation: Python template-based DOCX rendering

## Local Development Setup

### Infrastructure

Use Docker for:

- PostgreSQL
- Redis

The worker dependency file is:

- `worker/docker-compose.dependencies.yml`

### Application Runtime

- run backend locally
- run worker locally
- run frontend locally
- install `ffmpeg` locally if derived screenshots are required

## First Local Run

### 1. Create environment files

Create these files from the examples:

- `backend/.env`
- `worker/.env`
- `frontend/.env`

The example files are:

- [backend/.env.example](C:\Users\work\Documents\PddGenerator\backend\.env.example)
- [worker/.env.example](C:\Users\work\Documents\PddGenerator\worker\.env.example)
- [frontend/.env.example](C:\Users\work\Documents\PddGenerator\frontend\.env.example)

### 2. Start PostgreSQL and Redis

From `C:\Users\work\Documents\PddGenerator\worker`:

```powershell
docker compose -f docker-compose.dependencies.yml up -d
```

### 3. Install backend dependencies

From `C:\Users\work\Documents\PddGenerator\backend`:

```powershell
python -m pip install -e .
```

### 4. Install worker dependencies

From `C:\Users\work\Documents\PddGenerator\worker`:

```powershell
python -m pip install -e .
```

### 5. Start backend

From `C:\Users\work\Documents\PddGenerator\backend`:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Start worker

From `C:\Users\work\Documents\PddGenerator`:

```powershell
python -m celery -A worker.celery_app worker --loglevel=info
```

### 7. Install frontend dependencies

From `C:\Users\work\Documents\PddGenerator\frontend`:

```powershell
npm install
```

### 8. Start frontend

From `C:\Users\work\Documents\PddGenerator\frontend`:

```powershell
npm run dev
```

### 9. Test with a real session

Use one real pilot case with:

- at least one process video
- at least one transcript in `.txt`, `.vtt`, or `.docx`
- one DOCX template

Flow:

1. create session
2. upload artifacts
3. click generate
4. wait for status to move from `processing` to `review`
5. review/edit steps
6. export DOCX

## Important Implementation Note

The backend now queues draft generation through Celery and the frontend polls session status while processing. The current end-to-end flow can therefore:

- create sessions
- upload artifacts
- queue background generation
- refresh into review state automatically
- export DOCX

Derived screenshots still depend on:

- worker availability
- Redis availability
- PostgreSQL availability
- `ffmpeg` being installed locally

## Current Machine Gaps

On this machine, I confirmed:

- `Python` is installed
- `Docker` is installed
- `Node.js` is not installed
- `ffmpeg` is not installed

So the immediate blockers for the first full local run are:

- install `Node.js`
- install `ffmpeg`

## Documentation

- architecture details: [docs/architecture.md](C:\Users\work\Documents\PddGenerator\docs\architecture.md)
- product blueprint: [masterplan.md](C:\Users\work\Documents\PddGenerator\masterplan.md)
