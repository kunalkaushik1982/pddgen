# Backend Migrations

The backend now expects the database schema to be managed by Alembic.

## New environments

From the `backend` directory:

```bash
alembic upgrade head
```

## Existing environments created before Alembic

If the database already contains the current application tables from the older runtime `create_all()` flow, do a one-time baseline stamp instead of running the baseline migration again:

```bash
alembic stamp 20260318_0001
```

After that, future schema changes should use normal upgrades:

```bash
alembic upgrade head
```

## Startup behavior

The backend no longer creates or mutates schema at startup.

Startup now only:

- prepares storage directories
- validates that the database is already at the Alembic head revision

If the schema is not current, the backend will fail fast and instruct you to run:

```bash
alembic upgrade head
```
