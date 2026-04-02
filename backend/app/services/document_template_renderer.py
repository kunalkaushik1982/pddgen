r"""
Purpose: Render DOCX templates to output files for document exports.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_template_renderer.py
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from docxtpl import DocxTemplate
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.draft_session import DraftSessionModel
from app.services.document_context_builder_interfaces import DocumentContextBuilder
from app.services.document_context_builder_registry import DocumentContextBuilderRegistry
from app.services.document_export_context_builder import (
    BrdDocumentExportContextBuilder,
    PddDocumentExportContextBuilder,
    SopDocumentExportContextBuilder,
)
from app.storage.storage_service import StorageService


class DocumentTemplateRenderer:
    """Render DOCX output files from a draft session and a template artifact."""

    def __init__(self, context_builder: DocumentContextBuilder | None = None) -> None:
        self.context_builder = context_builder
        self.builder_registry = self._build_default_registry()

    def render_docx_file(
        self,
        db: Session,
        draft_session: DraftSessionModel,
        output_path: Path,
        storage_service: StorageService,
    ) -> None:
        template_artifact = self._get_template_artifact(draft_session)
        with TemporaryDirectory(prefix=f"pdd_export_assets_{draft_session.id}_") as asset_dir:
            asset_root = Path(asset_dir)
            template_path = storage_service.copy_to_local_path(
                template_artifact.storage_path,
                asset_root / "template" / template_artifact.name,
            )
            self._prepare_template_for_rendering(template_path, draft_session)
            doc = DocxTemplate(str(template_path))
            context_builder = self.context_builder or self.builder_registry.create(getattr(draft_session, "document_type", "pdd"))
            doc.render(context_builder.build(db, draft_session, doc, asset_root=asset_root, storage_service=storage_service))
            doc.save(str(output_path))

    @staticmethod
    def _build_default_registry() -> DocumentContextBuilderRegistry:
        registry = DocumentContextBuilderRegistry()
        registry.register(PddDocumentExportContextBuilder.document_type, PddDocumentExportContextBuilder)
        registry.register(SopDocumentExportContextBuilder.document_type, SopDocumentExportContextBuilder)
        registry.register(BrdDocumentExportContextBuilder.document_type, BrdDocumentExportContextBuilder)
        return registry

    @staticmethod
    def _get_template_artifact(draft_session: DraftSessionModel):
        template_artifact = next((artifact for artifact in draft_session.artifacts if artifact.kind == "template"), None)
        if template_artifact is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A template artifact is required before export.",
            )
        return template_artifact

    def _prepare_template_for_rendering(self, template_path: Path, draft_session: DraftSessionModel) -> None:
        if getattr(draft_session, "document_type", "pdd") != PddDocumentExportContextBuilder.document_type:
            return
        process_groups = [group for group in getattr(draft_session, "process_groups", []) if getattr(group, "title", "")]
        if len(process_groups) <= 1:
            return

        with zipfile.ZipFile(template_path, "r") as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")

        rebuilt_xml = self._build_multi_process_document_xml(document_xml)
        if rebuilt_xml == document_xml:
            return

        temp_path = template_path.with_suffix(".tmp.docx")
        with zipfile.ZipFile(template_path, "r") as source, zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == "word/document.xml":
                    data = rebuilt_xml.encode("utf-8")
                target.writestr(item, data)
        temp_path.replace(template_path)

    def _build_multi_process_document_xml(self, document_xml: str) -> str:
        start_marker = "3. AS-IS Steps"
        end_marker = "<w:sectPr"
        start_index = document_xml.find(start_marker)
        if start_index < 0:
            return document_xml
        start_index = document_xml.rfind("<w:p ", 0, start_index)
        end_index = document_xml.find(end_marker, start_index)
        if start_index < 0 or end_index < 0:
            return document_xml

        replacement = self._multi_process_sections_xml()
        return document_xml[:start_index] + replacement + document_xml[end_index:]

    @staticmethod
    def _multi_process_sections_xml() -> str:
        heading = lambda text: (
            '<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>'
            '<w:r><w:rPr><w:b/><w:bCs/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>'
            f"<w:t>{text}</w:t></w:r><w:r><w:rPr><w:b/><w:bCs/><w:sz w:val=\"28\"/><w:szCs w:val=\"28\"/></w:rPr><w:t>:</w:t></w:r></w:p>"
        )
        subheading = lambda text: (
            '<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>'
            '<w:r><w:rPr><w:b/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
            f"<w:t>{text}</w:t></w:r></w:p>"
        )
        text_paragraph = lambda text: (
            '<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
        )
        bullet_paragraph = lambda text: (
            '<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
            '<w:spacing w:after="0"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
        )
        page_break = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'

        parts = [
            heading("3. Process Sections"),
            text_paragraph("{% for section in pdd.process_sections %}"),
            subheading("{{ section.title }}"),
            text_paragraph("{{ section.summary }}"),
            subheading("AS-IS Steps"),
            text_paragraph("{% for step in section.steps %}"),
            bullet_paragraph("{{ step.bullet_entry }}"),
            text_paragraph("{% if step.primary_screenshot_image %}"),
            text_paragraph("{{ step.primary_screenshot_image }}"),
            text_paragraph("{% endif %}"),
            text_paragraph("{% endfor %}"),
            subheading("Process Flow Diagram"),
            text_paragraph("{% if section.diagram_image %}"),
            text_paragraph("{{ section.diagram_image }}"),
            text_paragraph("{% else %}"),
            text_paragraph("{{ section.diagram_source }}"),
            text_paragraph("{% endif %}"),
            subheading("Business Rules and Notes"),
            text_paragraph("{% for rule in section.notes %}"),
            bullet_paragraph("{{ rule.text }}"),
            text_paragraph("{% endfor %}"),
            text_paragraph("{% if not loop.last %}"),
            page_break,
            text_paragraph("{% endif %}"),
            text_paragraph("{% endfor %}"),
            heading("4. TO-BE Suggestions"),
            text_paragraph("{% for item in pdd.to_be_recommendations %}"),
            bullet_paragraph("{{ item.title }}: {{ item.recommendation }}"),
            text_paragraph("{% endfor %}"),
        ]
        return "".join(parts)
