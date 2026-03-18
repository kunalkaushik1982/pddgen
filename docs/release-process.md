# Release Process

Use the shared release script from the repo root:

```bash
python scripts/bump_release.py patch
python scripts/bump_release.py minor
python scripts/bump_release.py major
python scripts/bump_release.py set 1.0.0
```

The script updates these files together:

- `release.json`
- `frontend/package.json`
- `frontend/package-lock.json`
- `backend/pyproject.toml`
- `worker/pyproject.toml`

Versioning policy:

- `patch`: bug fixes only
- `minor`: backward-compatible features
- `major`: breaking changes
