r"""
Purpose: Shared release metadata loader for backend runtime surfaces.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\core\release.py
"""

from functools import lru_cache
import json
from pathlib import Path
from typing import TypedDict


class ReleaseInfo(TypedDict):
    release: str
    frontend: str
    backend: str
    worker: str


RELEASE_FILE = Path(__file__).resolve().parents[3] / "release.json"


@lru_cache(maxsize=1)
def get_release_info() -> ReleaseInfo:
    """Load the shared release manifest for frontend, backend, and worker."""
    default_release: ReleaseInfo = {
        "release": "0.0.0",
        "frontend": "0.0.0",
        "backend": "0.0.0",
        "worker": "0.0.0",
    }
    if not RELEASE_FILE.exists():
        return default_release

    try:
        payload = json.loads(RELEASE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_release

    return {
        "release": str(payload.get("release", default_release["release"])),
        "frontend": str(payload.get("frontend", default_release["frontend"])),
        "backend": str(payload.get("backend", default_release["backend"])),
        "worker": str(payload.get("worker", default_release["worker"])),
    }
