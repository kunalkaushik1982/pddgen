# PDD Generator Runbook

## Repo Setup

Clone the repository, then create local env files from the examples:

- `backend/.env` from `backend/.env.example`
- `worker/.env` from `worker/.env.example`
- `frontend/.env` from `frontend/.env.example`

Do not commit the `.env` files.

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

## Worker Setup

From `worker`:

```powershell
python -m pip install -e .
python -m celery -A worker.celery_app worker --loglevel=info
```

On Windows the worker is configured to use the `solo` pool.

## Frontend Setup

From `frontend`:

```powershell
npm install
npm run dev
```

Default UI URL:

```text
http://localhost:5173
```

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
