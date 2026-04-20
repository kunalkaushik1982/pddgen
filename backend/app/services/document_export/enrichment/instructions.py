r"""Load per-field instruction bodies from ``instructions/<doc>/<field>.md``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=128)
def load_field_instruction(field_id: str) -> str:
    """
    Return markdown instructions for one enrichment field id (e.g. ``pdd.process_summary``).

    Path: ``enrichment/instructions/pdd/process_summary.md``
    """
    if "." not in field_id:
        return ""
    doc, _, name = field_id.partition(".")
    path = _PACKAGE_DIR / "instructions" / doc / f"{name}.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()
