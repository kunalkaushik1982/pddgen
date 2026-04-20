r"""
Load editable prompt text by document type and section id.

Prompts live under ``document_export/<type>/prompts/<section_id>.md``.
Adjust copy without touching Python; missing files return ``None`` so callers can fall back.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_ALLOWED_DOC = frozenset({"pdd", "sop", "brd"})
_SAFE_SECTION = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-."
)


def _package_dir() -> Path:
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=256)
def load_document_prompt(document_type: str, section_id: str) -> str | None:
    """
    Return prompt file body for ``document_type`` + ``section_id``, or None if missing.

    ``section_id`` uses slug form, e.g. ``executive_summary``, ``diagram_nodes``.
    """
    if document_type not in _ALLOWED_DOC:
        return None
    if not section_id or any(c not in _SAFE_SECTION for c in section_id):
        return None
    path = _package_dir() / document_type / "prompts" / f"{section_id}.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def render_prompt_template(template: str, **variables: str) -> str:
    """Simple ``{{name}}`` replacement for prompt bodies."""
    out = template
    for key, value in variables.items():
        out = out.replace("{{" + key + "}}", value)
    return out
