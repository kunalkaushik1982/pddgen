import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from jinja2.exceptions import TemplateError

from app.services.documents.document_export_context_builder import (
    BrdDocumentExportContextBuilder,
    PddDocumentExportContextBuilder,
    SopDocumentExportContextBuilder,
)
from app.services.documents.document_template_renderer import DocumentTemplateRenderer


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


def _db_with_no_diagram_layout():
    """Avoid MagicMock truthy one_or_none() breaking JSON load in diagram render path."""
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = None
    return db


class DocumentTemplateRendererTests(unittest.TestCase):
    def test_pdd_renderer_single_process_exports_as_is_path(self):
        template_path = Path(__file__).resolve().parents[2] / "docs" / "templates" / "flowlens-pdd-template.docx"
        self.assertTrue(template_path.exists(), "Expected flowlens PDD sample template to exist.")

        stub = _StubProcessDiagramService()
        renderer = DocumentTemplateRenderer(
            process_diagram_service=stub,
            context_builder=PddDocumentExportContextBuilder(process_diagram_service=stub),
        )
        draft_session = SimpleNamespace(
            id="pdd-1",
            title="Invoice Entry",
            owner_id="owner",
            status="draft",
            document_type="pdd",
            diagram_type="flowchart",
            artifacts=[
                SimpleNamespace(
                    kind="template",
                    storage_path=str(template_path),
                    name="flowlens-pdd-template.docx",
                )
            ],
            process_groups=[],
            process_steps=[
                SimpleNamespace(
                    process_group_id=None,
                    step_number=1,
                    application_name="SAP",
                    action_text="Post the invoice",
                    source_data_note="",
                    timestamp="00:00:01",
                    start_timestamp="00:00:01",
                    end_timestamp="00:00:10",
                    supporting_transcript_text="",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
            ],
            process_notes=[],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "pdd-single.docx"
            renderer.render_docx_file(
                _db_with_no_diagram_layout(),
                draft_session,
                output_path,
                storage_service=_LocalCopyStorageService(),
            )
            with zipfile.ZipFile(output_path) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("3. AS-IS Steps", document_xml)
            self.assertIn("Post the invoice", document_xml)
            self.assertIn("5. Process Flow Diagram", document_xml)

    def test_pdd_renderer_multi_process_exports_process_sections(self):
        template_path = Path(__file__).resolve().parents[2] / "docs" / "templates" / "flowlens-pdd-template.docx"
        self.assertTrue(template_path.exists(), "Expected flowlens PDD sample template to exist.")

        stub = _StubProcessDiagramService()
        renderer = DocumentTemplateRenderer(
            process_diagram_service=stub,
            context_builder=PddDocumentExportContextBuilder(process_diagram_service=stub),
        )
        draft_session = SimpleNamespace(
            id="pdd-mp",
            title="End-to-End",
            owner_id="owner",
            status="draft",
            document_type="pdd",
            diagram_type="flowchart",
            artifacts=[
                SimpleNamespace(
                    kind="template",
                    storage_path=str(template_path),
                    name="flowlens-pdd-template.docx",
                )
            ],
            process_groups=[
                SimpleNamespace(id="g1", title="Create Order", display_order=0),
                SimpleNamespace(id="g2", title="Fulfill Order", display_order=1),
            ],
            process_steps=[
                SimpleNamespace(
                    process_group_id="g1",
                    step_number=1,
                    application_name="SAP",
                    action_text="Enter the order header",
                    source_data_note="",
                    timestamp="00:00:01",
                    start_timestamp="00:00:01",
                    end_timestamp="00:00:10",
                    supporting_transcript_text="",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
                SimpleNamespace(
                    process_group_id="g2",
                    step_number=2,
                    application_name="SAP",
                    action_text="Pick and confirm delivery",
                    source_data_note="",
                    timestamp="00:01:00",
                    start_timestamp="00:01:00",
                    end_timestamp="00:02:00",
                    supporting_transcript_text="",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
            ],
            process_notes=[],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "pdd-multi.docx"
            renderer.render_docx_file(
                _db_with_no_diagram_layout(),
                draft_session,
                output_path,
                storage_service=_LocalCopyStorageService(),
            )
            with zipfile.ZipFile(output_path) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("3. Process Sections", document_xml)
            self.assertIn("Create Order", document_xml)
            self.assertIn("Fulfill Order", document_xml)
            self.assertIn("Enter the order header", document_xml)
            self.assertIn("Pick and confirm delivery", document_xml)
            self.assertNotIn("3. AS-IS Steps", document_xml)

    def test_sop_renderer_creates_sop_specific_export(self):
        template_path = Path(__file__).resolve().parents[2] / "docs" / "templates" / "flowlens-sop-template.docx"
        self.assertTrue(template_path.exists(), "Expected SOP sample template to exist.")

        stub = _StubProcessDiagramService()
        renderer = DocumentTemplateRenderer(
            process_diagram_service=stub,
            context_builder=SopDocumentExportContextBuilder(process_diagram_service=stub),
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
                _db_with_no_diagram_layout(),
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

    def test_sop_renderer_multi_process_repeats_body_per_group(self):
        template_path = Path(__file__).resolve().parents[2] / "docs" / "templates" / "flowlens-sop-template.docx"
        self.assertTrue(template_path.exists(), "Expected SOP sample template to exist.")

        stub = _StubProcessDiagramService()
        renderer = DocumentTemplateRenderer(
            process_diagram_service=stub,
            context_builder=SopDocumentExportContextBuilder(process_diagram_service=stub),
        )
        draft_session = SimpleNamespace(
            id="session-sop-mp",
            title="Order-to-Cash",
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
            process_groups=[
                SimpleNamespace(id="g-a", title="Order capture", display_order=0),
                SimpleNamespace(id="g-b", title="Billing", display_order=1),
            ],
            process_steps=[
                SimpleNamespace(
                    process_group_id="g-a",
                    step_number=1,
                    application_name="SAP GUI",
                    action_text="Enter the customer order",
                    source_data_note="",
                    timestamp="00:00:10",
                    start_timestamp="00:00:10",
                    end_timestamp="00:00:32",
                    supporting_transcript_text="",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
                SimpleNamespace(
                    process_group_id="g-b",
                    step_number=2,
                    application_name="SAP GUI",
                    action_text="Generate and post the invoice",
                    source_data_note="",
                    timestamp="00:01:00",
                    start_timestamp="00:01:00",
                    end_timestamp="00:01:30",
                    supporting_transcript_text="",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
            ],
            process_notes=[],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "sop-multi.docx"
            renderer.render_docx_file(
                _db_with_no_diagram_layout(),
                draft_session,
                output_path,
                storage_service=_LocalCopyStorageService(),
            )
            self.assertTrue(output_path.exists(), "Expected SOP export to be created.")

            with zipfile.ZipFile(output_path) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")

            self.assertIn("Order-to-Cash", document_xml)
            self.assertIn("Order capture", document_xml)
            self.assertIn("Billing", document_xml)
            self.assertIn("Enter the customer order", document_xml)
            self.assertIn("Generate and post the invoice", document_xml)
            self.assertGreaterEqual(document_xml.count("Purpose"), 2)

    def test_brd_renderer_creates_brd_specific_export(self):
        template_path = Path(__file__).resolve().parents[2] / "docs" / "templates" / "flowlens-brd-template.docx"
        self.assertTrue(template_path.exists(), "Expected BRD sample template to exist.")

        stub = _StubProcessDiagramService()
        renderer = DocumentTemplateRenderer(
            process_diagram_service=stub,
            context_builder=BrdDocumentExportContextBuilder(process_diagram_service=stub),
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
            self.assertNotIn("AS-IS", document_xml)
            self.assertIn("business context", document_xml.lower())

    def test_brd_renderer_multi_process_repeats_body_per_group(self):
        template_path = Path(__file__).resolve().parents[2] / "docs" / "templates" / "flowlens-brd-template.docx"
        self.assertTrue(template_path.exists(), "Expected BRD sample template to exist.")

        stub = _StubProcessDiagramService()
        renderer = DocumentTemplateRenderer(
            process_diagram_service=stub,
            context_builder=BrdDocumentExportContextBuilder(process_diagram_service=stub),
        )
        draft_session = SimpleNamespace(
            id="session-mp",
            title="Combined Initiative",
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
            process_groups=[
                SimpleNamespace(id="g-a", title="Order Entry", display_order=0),
                SimpleNamespace(id="g-b", title="Billing", display_order=1),
            ],
            process_steps=[
                SimpleNamespace(
                    process_group_id="g-a",
                    step_number=1,
                    application_name="SAP GUI",
                    action_text="Create the sales order",
                    source_data_note="",
                    timestamp="00:00:10",
                    start_timestamp="00:00:10",
                    end_timestamp="00:00:32",
                    supporting_transcript_text="",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
                SimpleNamespace(
                    process_group_id="g-b",
                    step_number=2,
                    application_name="SAP GUI",
                    action_text="Post invoice to accounting",
                    source_data_note="",
                    timestamp="00:01:00",
                    start_timestamp="00:01:00",
                    end_timestamp="00:01:30",
                    supporting_transcript_text="",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                ),
            ],
            process_notes=[],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "brd-multi.docx"
            renderer.render_docx_file(
                MagicMock(),
                draft_session,
                output_path,
                storage_service=_LocalCopyStorageService(),
            )
            self.assertTrue(output_path.exists(), "Expected BRD export to be created.")

            with zipfile.ZipFile(output_path) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")

            self.assertIn("Combined Initiative", document_xml)
            self.assertIn("Order Entry", document_xml)
            self.assertIn("Billing", document_xml)
            self.assertGreaterEqual(document_xml.count("Standard BRD sections"), 2)

    def test_brd_canonical_sections_matches_index_shape(self):
        rows = BrdDocumentExportContextBuilder._build_brd_canonical_sections(
            overview={"process_summary": "Executive summary narrative."},
            business_objective="Business objectives paragraph.",
            scope="Scope paragraph.",
            current_state_summary="Background narrative.",
            stakeholders=[{"name": "Owner", "role": "Process owner", "interest": "Approves requirements."}],
            applications=["SAP GUI"],
            requirements=[
                {"category": "Functional", "statement": "The solution must support users to open the order."},
                {"category": "System", "statement": "Preserve SAP GUI access."},
            ],
            assumptions=["Walkthrough reflects current practice."],
            risks=["Validate implicit rules before build."],
            process_flow={"diagram_source": "flowchart TD; A-->B;", "rendered": True},
            workflow_sections=[{"title": "Sales order"}],
            process_steps=[{"action_text": "Open the sales order transaction"}],
        )
        self.assertEqual(len(rows), 22)
        self.assertEqual(rows[0]["ref"], "1")
        self.assertEqual(rows[0]["slug"], "executive_summary")
        self.assertIn("Executive summary narrative.", rows[0]["body"])
        self.assertEqual(rows[4]["ref"], "4.1")
        self.assertEqual(rows[4]["slug"], "in_scope")
        self.assertIn("Sales order", rows[4]["body"])
        self.assertEqual(rows[-1]["ref"], "20")
        self.assertEqual(rows[-1]["slug"], "approval_sign_off")

    def test_render_docx_raises_422_when_template_render_fails(self):
        template_path = Path(__file__).resolve().parents[2] / "docs" / "templates" / "flowlens-pdd-template.docx"
        self.assertTrue(template_path.exists(), "Expected flowlens PDD sample template to exist.")

        stub = _StubProcessDiagramService()
        renderer = DocumentTemplateRenderer(
            process_diagram_service=stub,
            context_builder=PddDocumentExportContextBuilder(process_diagram_service=stub),
        )
        draft_session = SimpleNamespace(
            id="pdd-422",
            title="Test",
            owner_id="owner",
            status="review",
            document_type="pdd",
            diagram_type="flowchart",
            artifacts=[
                SimpleNamespace(
                    kind="template",
                    storage_path=str(template_path),
                    name="flowlens-pdd-template.docx",
                )
            ],
            process_groups=[],
            process_steps=[
                SimpleNamespace(
                    process_group_id=None,
                    step_number=1,
                    application_name="SAP",
                    action_text="Step one",
                    source_data_note="",
                    timestamp="00:00:01",
                    start_timestamp="00:00:01",
                    end_timestamp="00:00:10",
                    supporting_transcript_text="",
                    confidence="high",
                    evidence_references="[]",
                    step_screenshots=[],
                    screenshot_id="",
                )
            ],
            process_notes=[],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "fail.docx"
            with patch("app.services.documents.document_template_renderer.DocxTemplate") as mock_docx_cls:
                mock_docx_cls.return_value.render.side_effect = TemplateError("undefined variable")
                with self.assertRaises(HTTPException) as ctx:
                    renderer.render_docx_file(
                        _db_with_no_diagram_layout(),
                        draft_session,
                        output_path,
                        storage_service=_LocalCopyStorageService(),
                    )
                self.assertEqual(ctx.exception.status_code, 422)
                self.assertIn("document type", str(ctx.exception.detail).lower())


if __name__ == "__main__":
    unittest.main()
