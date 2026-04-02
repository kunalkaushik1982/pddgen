import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.document_export_context_builder import BrdDocumentExportContextBuilder, SopDocumentExportContextBuilder
from app.services.document_template_renderer import DocumentTemplateRenderer


class _StubProcessDiagramService:
    def build_to_be_suggestions(self, draft_session):
        return []

    def build_diagram_source(self, draft_session):
        return "flowchart TD; A-->B;"

    def render_sequence_diagram(self, draft_session, output_path):
        return ""

    def render_flowchart_view(self, draft_session, view_type, output_path, saved_positions=None, process_group_id=None):
        return ""

    def _scope_session(self, draft_session, process_group_id):
        return draft_session


class _LocalCopyStorageService:
    def copy_to_local_path(self, storage_path, destination_path):
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(Path(storage_path), destination)
        return destination


class DocumentTemplateRendererTests(unittest.TestCase):
    def test_sop_renderer_creates_sop_specific_export(self):
        template_path = Path(__file__).resolve().parents[2] / "docs" / "templates" / "flowlens-sop-template.docx"
        self.assertTrue(template_path.exists(), "Expected SOP sample template to exist.")

        renderer = DocumentTemplateRenderer(
            context_builder=SopDocumentExportContextBuilder(_StubProcessDiagramService())
        )
        draft_session = SimpleNamespace(
            id="session-1",
            title="Vendor Master Update",
            owner_id="tester",
            status="review",
            document_type="sop",
            diagram_type="sequence",
            artifacts=[
                SimpleNamespace(
                    kind="template",
                    storage_path=str(template_path),
                    name="flowlens-sop-template.docx",
                )
            ],
            process_groups=[],
            process_steps=[
                SimpleNamespace(
                    process_group_id=None,
                    step_number=1,
                    application_name="SAP GUI",
                    action_text="Open the vendor master transaction",
                    source_data_note="Vendor ID and company code required",
                    timestamp="00:00:12",
                    start_timestamp="00:00:12",
                    end_timestamp="00:00:45",
                    supporting_transcript_text="Open the transaction and prepare the vendor record.",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
                SimpleNamespace(
                    process_group_id=None,
                    step_number=2,
                    application_name="SAP GUI",
                    action_text="Validate the data and save the record",
                    source_data_note="Review payment terms before save",
                    timestamp="00:00:46",
                    start_timestamp="00:00:46",
                    end_timestamp="00:01:20",
                    supporting_transcript_text="Validate fields and save the record.",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
            ],
            process_notes=[
                SimpleNamespace(
                    process_group_id=None,
                    text="Confirm payment terms before saving the vendor record.",
                    confidence="medium",
                    inference_type="business_rule",
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "sop-output.docx"
            renderer.render_docx_file(
                MagicMock(),
                draft_session,
                output_path,
                storage_service=_LocalCopyStorageService(),
            )
            self.assertTrue(output_path.exists(), "Expected SOP export to be created.")

            with zipfile.ZipFile(output_path) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")

            self.assertIn("FlowLens Standard Operating Procedure", document_xml)
            self.assertIn("Vendor Master Update", document_xml)
            self.assertIn("Process operator", document_xml)
            self.assertIn("Confirm payment terms before saving the vendor record.", document_xml)
            self.assertIn("Open the vendor master transaction", document_xml)
            self.assertNotIn("pdd.overview.process_name", document_xml)

    def test_brd_renderer_creates_brd_specific_export(self):
        template_path = Path(__file__).resolve().parents[2] / "docs" / "templates" / "flowlens-brd-template.docx"
        self.assertTrue(template_path.exists(), "Expected BRD sample template to exist.")

        renderer = DocumentTemplateRenderer(
            context_builder=BrdDocumentExportContextBuilder(_StubProcessDiagramService())
        )
        draft_session = SimpleNamespace(
            id="session-2",
            title="Sales Order Creation",
            owner_id="tester",
            status="review",
            document_type="brd",
            diagram_type="sequence",
            artifacts=[
                SimpleNamespace(
                    kind="template",
                    storage_path=str(template_path),
                    name="flowlens-brd-template.docx",
                )
            ],
            process_groups=[],
            process_steps=[
                SimpleNamespace(
                    process_group_id=None,
                    step_number=1,
                    application_name="SAP GUI",
                    action_text="Open the sales order transaction",
                    source_data_note="Sales area and customer required",
                    timestamp="00:00:10",
                    start_timestamp="00:00:10",
                    end_timestamp="00:00:32",
                    supporting_transcript_text="Start the sales order process in SAP.",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
                SimpleNamespace(
                    process_group_id=None,
                    step_number=2,
                    application_name="SAP GUI",
                    action_text="Enter order details and validate the item data",
                    source_data_note="Material and quantity must be accurate",
                    timestamp="00:00:33",
                    start_timestamp="00:00:33",
                    end_timestamp="00:01:05",
                    supporting_transcript_text="Enter the customer and item details.",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
            ],
            process_notes=[
                SimpleNamespace(
                    process_group_id=None,
                    text="Order data must be validated before save.",
                    confidence="medium",
                    inference_type="business_rule",
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "brd-output.docx"
            renderer.render_docx_file(
                MagicMock(),
                draft_session,
                output_path,
                storage_service=_LocalCopyStorageService(),
            )
            self.assertTrue(output_path.exists(), "Expected BRD export to be created.")

            with zipfile.ZipFile(output_path) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")

            self.assertIn("FlowLens Business Requirements Document", document_xml)
            self.assertIn("Sales Order Creation", document_xml)
            self.assertIn("Business Requirements", document_xml)
            self.assertIn("BR-001", document_xml)
            self.assertIn("Order data must be validated before save.", document_xml)
            self.assertNotIn("sop.purpose", document_xml)


if __name__ == "__main__":
    unittest.main()
