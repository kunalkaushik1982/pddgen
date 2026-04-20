r"""
Batched LLM export text enrichment: one completion, many placeholder fields.

Persisted on ``DraftSessionModel.export_text_enrichment_json``; export builders merge when present.
"""

from app.services.document_export.enrichment.registry import ENRICHMENT_FIELD_IDS, field_ids_for_document_type
from app.services.document_export.enrichment.service import DocumentExportEnrichmentService
from app.services.document_export.enrichment.store import (
    get_enrichment_fields,
    merge_enrichment_into_pdd_overview_summary,
    merge_enrichment_into_brd_process_summary,
    merge_enrichment_into_sop_purpose,
)

__all__ = [
    "ENRICHMENT_FIELD_IDS",
    "field_ids_for_document_type",
    "DocumentExportEnrichmentService",
    "get_enrichment_fields",
    "merge_enrichment_into_pdd_overview_summary",
    "merge_enrichment_into_brd_process_summary",
    "merge_enrichment_into_sop_purpose",
]
