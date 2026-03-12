r"""
Purpose: Shared bootstrap helpers for importing backend code into the worker.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\bootstrap.py
"""

from functools import lru_cache
from pathlib import Path
import os
import sys


WORKER_ROOT = Path(__file__).resolve().parent
REPO_ROOT = WORKER_ROOT.parent
BACKEND_ROOT = REPO_ROOT / "backend"
WORKER_ENV_PATH = WORKER_ROOT / ".env"


def _load_worker_env() -> None:
    """Load worker-specific environment variables before importing backend settings."""
    if not WORKER_ENV_PATH.exists():
        return

    for raw_line in WORKER_ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_worker_env()

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings, get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


@lru_cache(maxsize=1)
def get_backend_settings() -> Settings:
    """Return backend settings for shared infrastructure configuration."""
    return get_settings()


def get_db_session():
    """Return a database session for background jobs."""
    return SessionLocal()
