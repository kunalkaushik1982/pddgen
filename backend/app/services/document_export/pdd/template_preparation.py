r"""
PDD Word template adjustments before docxtpl render (optional hook).

Multi-process PDD exports are handled in the Word template via ``pdd.multi_process``
and ``pdd.process_sections`` (see ``docs/templates/build_flowlens_pdd_template.py``).
This function remains as a stable no-op so callers (e.g. ``DocumentTemplateRenderer``)
do not need to branch on document type.
"""

from __future__ import annotations

from pathlib import Path

from app.models.draft_session import DraftSessionModel


def prepare_pdd_multi_process_template(template_path: Path, draft_session: DraftSessionModel) -> None:
    """Reserved for future template-only tweaks; multi-process PDD uses Jinja in the ``.docx``."""
    _ = (template_path, draft_session)
