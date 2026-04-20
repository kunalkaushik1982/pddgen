r"""
Register workflow document export context builders (PDD, SOP, BRD, …).

New document types: add a builder class and register it here only — avoid
editing DocumentTemplateRenderer when extending supported exports.
Full filepath: backend/app/services/document_context_builder_registration.py
"""

from __future__ import annotations

from app.services.documents.document_context_builder_registry import DocumentContextBuilderRegistry
from app.services.document_export import (
    BrdDocumentExportContextBuilder,
    PddDocumentExportContextBuilder,
    SopDocumentExportContextBuilder,
)
from app.services.generation.process_diagram_service import ProcessDiagramService


def register_workflow_document_builders(
    registry: DocumentContextBuilderRegistry,
    *,
    process_diagram_service: ProcessDiagramService,
) -> None:
    pd = process_diagram_service
    registry.register(
        PddDocumentExportContextBuilder.document_type,
        lambda: PddDocumentExportContextBuilder(process_diagram_service=pd),
    )
    registry.register(
        SopDocumentExportContextBuilder.document_type,
        lambda: SopDocumentExportContextBuilder(process_diagram_service=pd),
    )
    registry.register(
        BrdDocumentExportContextBuilder.document_type,
        lambda: BrdDocumentExportContextBuilder(process_diagram_service=pd),
    )
