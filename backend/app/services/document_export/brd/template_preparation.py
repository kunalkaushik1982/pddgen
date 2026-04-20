r"""
BRD-only Word template adjustments before docxtpl render (optional).

Multi-process BRD is handled in the bundled template via ``brd.multi_process`` and
``brd.process_document_blocks`` from ``BrdDocumentExportContextBuilder``; this hook
remains for any future Word-XML-only tweaks (similar to PDD) if needed.
"""

from __future__ import annotations

from pathlib import Path

from app.models.draft_session import DraftSessionModel


def prepare_brd_template_if_needed(template_path: Path, draft_session: DraftSessionModel) -> None:
    """Hook for BRD multi-group templates; no-op until BRD-specific XML markers are defined."""
    if getattr(draft_session, "document_type", "pdd") != "brd":
        return
    _ = template_path
    process_groups = [g for g in getattr(draft_session, "process_groups", []) if getattr(g, "title", "")]
    if len(process_groups) <= 1:
        return
    # Future: rewrite document.xml when a bundled BRD template uses a fixed block for one section only.
