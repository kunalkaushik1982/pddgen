r"""
SOP-only Word template adjustments before docxtpl render (optional).

Multi-process SOP uses ``sop.multi_process`` and ``sop.process_document_blocks`` from
``SopDocumentExportContextBuilder``; this hook remains a no-op for API compatibility.
"""

from __future__ import annotations

from pathlib import Path

from app.models.draft_session import DraftSessionModel


def prepare_sop_template_if_needed(template_path: Path, draft_session: DraftSessionModel) -> None:
    """Reserved; multi-process SOP is handled in the Word template (Jinja)."""
    _ = (template_path, draft_session)
