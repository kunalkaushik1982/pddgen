"""Tests for document_export package layout, prompts, and pipeline."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.services.document_export import (
    DocumentExportPipeline,
    load_document_prompt,
    render_prompt_template,
)
from app.services.document_export.brd.context_builder import BrdDocumentExportContextBuilder
from app.services.document_export.brd.template_preparation import prepare_brd_template_if_needed
from app.services.document_export.sop.template_preparation import prepare_sop_template_if_needed


class DocumentExportPackageTests(unittest.TestCase):
    def test_load_brd_business_objective_prompt(self):
        text = load_document_prompt("brd", "business_objective")
        self.assertIsNotNone(text)
        self.assertIn("{{title}}", text)

    def test_render_prompt_template(self):
        self.assertEqual(
            render_prompt_template("Hello {{title}}", title="World"),
            "Hello World",
        )

    def test_pipeline_stages_per_type(self):
        pdd = [s.id for s in DocumentExportPipeline.stages_for("pdd")]
        brd = [s.id for s in DocumentExportPipeline.stages_for("brd")]
        self.assertIn("build_pdd_context", pdd)
        self.assertIn("build_brd_context", brd)

    def test_resolve_brd_business_objective_uses_prompt_file(self):
        out = BrdDocumentExportContextBuilder._resolve_brd_business_objective("My Process")
        self.assertIn("My Process", out)
        self.assertIn("business requirements", out.lower())

    def test_brd_sop_template_preparation_noops_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stub.docx"
            path.write_bytes(b"PK\x03\x04")
            multi = [
                SimpleNamespace(title="One"),
                SimpleNamespace(title="Two"),
            ]
            prepare_brd_template_if_needed(
                path,
                SimpleNamespace(document_type="brd", process_groups=multi),
            )
            prepare_sop_template_if_needed(
                path,
                SimpleNamespace(document_type="sop", process_groups=multi),
            )


if __name__ == "__main__":
    unittest.main()
