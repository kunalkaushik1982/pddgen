r"""
Single batched LLM call to polish export placeholder text; persists on session before DB flush in persistence.
"""

from __future__ import annotations

import json

from app.core.observability import bind_log_context, get_logger
from app.services.document_export.enrichment.registry import field_ids_for_document_type
from app.services.document_export.enrichment.service import DocumentExportEnrichmentService
from worker.pipeline.stages.stage_context import DraftGenerationContext

logger = get_logger(__name__)


def build_evidence_digest(context: DraftGenerationContext, *, max_chars: int = 12000) -> str:
    """Compact digest of steps/notes for enrichment (token budget)."""
    lines: list[str] = []
    sess = context.inputs.session
    lines.append(f"Session title: {sess.title}")
    lines.append(f"User document_type preference: {context.inputs.document_type}")
    lines.append(f"Diagram type: {getattr(sess, 'diagram_type', '') or 'flowchart'}")
    if context.process_groups:
        lines.append("Process groups:")
        for pg in context.process_groups:
            lines.append(f"  - {getattr(pg, 'title', '') or pg.id}: id={pg.id}")
    lines.append(f"Steps ({len(context.all_steps)}):")
    for step in context.all_steps[:80]:
        app_n = (getattr(step, "application_name", None) or "").strip()
        action = (getattr(step, "action_text", None) or "").strip()
        if len(action) > 400:
            action = action[:400] + "…"
        lines.append(f"  Step {getattr(step, 'step_number', '?')}: [{app_n}] {action}")
    if len(context.all_steps) > 80:
        lines.append(f"  … {len(context.all_steps) - 80} more steps omitted.")
    lines.append(f"Notes ({len(context.all_notes)}):")
    for note in context.all_notes[:40]:
        text = (getattr(note, "text", None) or "").strip()
        if len(text) > 500:
            text = text[:500] + "…"
        lines.append(f"  - {text}")
    if len(context.all_notes) > 40:
        lines.append(f"  … {len(context.all_notes) - 40} more notes omitted.")
    out = "\n".join(lines)
    if len(out) > max_chars:
        return out[: max_chars - 1] + "…"
    return out


class DocumentExportTextEnrichmentStage:
    """Run after diagram assembly; writes ``export_text_enrichment_json`` on the session model."""

    def run(self, _db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="document_export_enrichment"):
            service = DocumentExportEnrichmentService()
            if not service.is_enabled():
                logger.info(
                    "Document export enrichment skipped (disabled or AI not configured).",
                    extra={"event": "document_export_enrichment.skipped"},
                )
                return
            digest = build_evidence_digest(context)
            doc_type = getattr(context.inputs.session, "document_type", None) or context.inputs.document_type
            field_ids = field_ids_for_document_type(doc_type)
            fields = service.run(
                evidence_digest=digest,
                session_id=context.inputs.session_id,
                field_ids=field_ids,
            )
            if not fields:
                logger.info(
                    "Document export enrichment produced no fields.",
                    extra={"event": "document_export_enrichment.empty"},
                )
                return
            envelope = {"version": 1, "fields": fields}
            context.inputs.session.export_text_enrichment_json = json.dumps(envelope)
            logger.info(
                "Document export enrichment stored on session.",
                extra={
                    "event": "document_export_enrichment.stored",
                    "field_count": len(fields),
                    "document_type": doc_type,
                    "field_ids": list(field_ids),
                },
            )
