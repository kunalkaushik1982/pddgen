r"""
Common export pipeline shell: document-type-specific stages register dynamically.

Use this to document or extend the sequence of export-related steps without
putting all logic in one class. Rendering still flows: registry → builder.build().
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExportStage:
    """Named stage for observability or future orchestration hooks."""

    id: str
    description: str


# Stages describe the conceptual pipeline for each document output type.
# Add or reorder entries here as behavior splits per type.

_PDD_STAGES: tuple[ExportStage, ...] = (
    ExportStage("load_session_evidence", "Load steps, notes, screenshots, diagrams from session"),
    ExportStage("build_pdd_context", "Map evidence into PDD template context"),
)

_SOP_STAGES: tuple[ExportStage, ...] = (
    ExportStage("load_session_evidence", "Load shared session primitives"),
    ExportStage("build_sop_context", "Map evidence into SOP procedure context"),
)

_BRD_STAGES: tuple[ExportStage, ...] = (
    ExportStage("load_session_evidence", "Load shared session primitives"),
    ExportStage("build_brd_context", "Map evidence into BRD / canonical sections"),
)


class DocumentExportPipeline:
    """Resolve ordered export stages for a workflow document type."""

    _by_type: dict[str, tuple[ExportStage, ...]] = {
        "pdd": _PDD_STAGES,
        "sop": _SOP_STAGES,
        "brd": _BRD_STAGES,
    }

    @classmethod
    def stages_for(cls, document_type: str) -> Sequence[ExportStage]:
        return cls._by_type.get(document_type, _PDD_STAGES)

    @classmethod
    def register_document_type(
        cls,
        document_type: str,
        stages: tuple[ExportStage, ...],
        *,
        overwrite: bool = False,
    ) -> None:
        """Allow tests or plugins to register a new document pipeline."""
        if document_type in cls._by_type and not overwrite:
            raise ValueError(f"Document type {document_type!r} already registered")
        cls._by_type[document_type] = stages


def run_export_stages(
    document_type: str,
    runner: Callable[[ExportStage], Any],
) -> list[Any]:
    """Run each stage through an optional callback (e.g. metrics); returns runner outputs."""
    results: list[Any] = []
    for stage in DocumentExportPipeline.stages_for(document_type):
        results.append(runner(stage))
    return results
