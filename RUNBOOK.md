# PDD Generator Runbook

## Repo Setup

Clone the repository, then create local env files from the examples:

- `backend/.env` from `backend/.env.example`
- `worker/.env` from `worker/.env.example`
- `frontend/.env` from `frontend/.env.example`

Do not commit the `.env` files.

## Prerequisites

You need these runtimes available on the machine:

- Python 3.11 or newer
- Node.js LTS
- npm
- `ffmpeg` in PATH

Verify the runtimes:

```powershell
python --version
node --version
npm --version
ffmpeg -version
```

## Backend Setup

From `backend`:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

Run the API:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Setup

From `frontend`:

```powershell
npm install
```

Create the frontend env file if needed:

```powershell
Copy-Item .\.env.example .\.env
```

Recommended frontend `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Run the React app:

```powershell
npm run dev
```

Default UI URL:

```text
http://localhost:5173
```

## Worker Setup

From `worker`:

```powershell
python -m pip install -e .
python -m celery -A worker.celery_app worker --loglevel=info
```

On Windows the worker is configured to use the `solo` pool.

## Database and Redis

The app expects:

- PostgreSQL
- Redis

Your current local setup uses:

- PostgreSQL on `127.0.0.1:5432`
- Redis on `localhost:6379`

If you reuse an existing PostgreSQL/Redis instance, keep a separate database and Redis DB index for this app.

## Demo Mode For Restricted Machines

If a machine cannot run PostgreSQL, Redis, or Docker Desktop, use demo mode.

Recommended backend `.env` values:

```env
PDD_GENERATOR_DEMO_MODE=true
PDD_GENERATOR_DATABASE_URL=sqlite:///C:/Users/work/Documents/PddGenerator/backend/pdd_generator_demo.db
PDD_GENERATOR_REDIS_URL=
```

Demo mode behavior:

- uses SQLite for persistence
- runs generation inline in the backend
- does not require Redis
- does not require the Celery worker process

In demo mode you only need:

1. backend
2. frontend
3. `ffmpeg`

The worker terminal is not required.

## Corporate Demo Machine Setup

Use this path if the machine cannot run Docker Desktop, PostgreSQL, or Redis.

### 1. Clone the repo

```powershell
git clone <your-repo-url> C:\Users\work\Documents\PddGenerator
cd C:\Users\work\Documents\PddGenerator
```

### 2. Create env files

```powershell
Copy-Item .\backend\.env.example .\backend\.env
Copy-Item .\frontend\.env.example .\frontend\.env
```

### 3. Configure backend demo mode

Put these values in `backend\.env`:

```env
PDD_GENERATOR_APP_NAME=PDD Generator API
PDD_GENERATOR_APP_ENV=development
PDD_GENERATOR_APP_DEBUG=true
PDD_GENERATOR_API_PREFIX=/api
PDD_GENERATOR_DEMO_MODE=true
PDD_GENERATOR_DATABASE_URL=sqlite:///C:/Users/work/Documents/PddGenerator/backend/pdd_generator_demo.db
PDD_GENERATOR_REDIS_URL=
PDD_GENERATOR_AI_ENABLED=true
PDD_GENERATOR_AI_PROVIDER=openai_compatible
PDD_GENERATOR_AI_API_KEY=YOUR_OPENAI_API_KEY
PDD_GENERATOR_AI_MODEL=gpt-4.1-mini
PDD_GENERATOR_AI_BASE_URL=https://api.openai.com/v1
PDD_GENERATOR_STORAGE_BACKEND=local
PDD_GENERATOR_LOCAL_STORAGE_ROOT=C:\Users\work\Documents\PddGenerator\storage\local
PDD_GENERATOR_MAX_UPLOAD_SIZE_MB=1024
PDD_GENERATOR_DOCX_OUTPUT_FOLDER=exports
```

Important:

- do not put the API key in quotes
- Redis is intentionally blank in demo mode

### 4. Configure frontend

Put this in `frontend\.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### 5. Install backend

```powershell
cd C:\Users\work\Documents\PddGenerator\backend
python -m pip install -r requirements.txt
python -m pip install -e .
```

### 6. Start backend

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Install frontend

```powershell
cd C:\Users\work\Documents\PddGenerator\frontend
npm install
```

### 8. Start frontend

```powershell
npm run dev
```

### 9. Open the app

```text
http://localhost:5173
```

### 10. What not to start in demo mode

Do not start:

- PostgreSQL
- Redis
- Celery worker
- Docker Desktop

## Restart Sequence

If code changes are pulled on a new machine or after a branch switch:

1. Restart backend
2. Restart worker
3. Restart frontend
4. Hard refresh the browser

## First Test Flow

1. Start backend
2. Start worker
3. Start frontend
4. Create a new session
5. Upload video, transcript, and DOCX template
6. Generate the draft
7. Review steps and screenshots
8. Export DOCX

## Git Notes

Ignored from git:

- all `.env` files
- `frontend/node_modules`
- Python cache files
- local storage output under `storage/local`

Safe to commit:

- source code
- templates under `test-assets`
- docs
- `package-lock.json`
- `pyproject.toml`
- `requirements.txt`
