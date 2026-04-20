r"""Tests for batched export text enrichment (merge + JSON envelope)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from app.services.document_export.enrichment.registry import (
    BRD_ENRICHMENT_FIELD_IDS,
    ENRICHMENT_FIELD_IDS,
    field_ids_for_document_type,
)
from app.services.document_export.enrichment.service import DocumentExportEnrichmentService
from app.services.document_export.enrichment.store import (
    enrich_brd_canonical_section_bodies,
    get_enrichment_fields,
    merge_enrichment_into_brd_process_summary,
    merge_enrichment_into_pdd_overview_summary,
    merge_enrichment_into_sop_purpose,
    prefer_enrichment_field,
)


class EnrichmentStoreTests(unittest.TestCase):
    def test_get_enrichment_fields_parses_envelope(self) -> None:
        mock = MagicMock()
        mock.export_text_enrichment_json = json.dumps(
            {"version": 1, "fields": {"pdd.process_summary": " AI text "}}
        )
        fields = get_enrichment_fields(mock)
        self.assertEqual(fields, {"pdd.process_summary": "AI text"})

    def test_get_enrichment_fields_invalid_returns_none(self) -> None:
        mock = MagicMock()
        mock.export_text_enrichment_json = "not-json"
        self.assertIsNone(get_enrichment_fields(mock))

    def test_merge_pdd_prefers_ai(self) -> None:
        mock = MagicMock()
        mock.export_text_enrichment_json = json.dumps(
            {"version": 1, "fields": {"pdd.process_summary": "From model"}}
        )
        out = merge_enrichment_into_pdd_overview_summary(mock, "Deterministic")
        self.assertEqual(out, "From model")

    def test_merge_pdd_fallback(self) -> None:
        mock = MagicMock()
        mock.export_text_enrichment_json = None
        out = merge_enrichment_into_pdd_overview_summary(mock, "Deterministic")
        self.assertEqual(out, "Deterministic")

    def test_merge_brd_and_sop(self) -> None:
        mock = MagicMock()
        mock.export_text_enrichment_json = json.dumps(
            {
                "version": 1,
                "fields": {
                    "brd.current_state_summary": "BRD summary",
                    "sop.purpose": "SOP purpose",
                },
            }
        )
        self.assertEqual(
            merge_enrichment_into_brd_process_summary(mock, "x"),
            "BRD summary",
        )
        self.assertEqual(
            merge_enrichment_into_sop_purpose(mock, "y"),
            "SOP purpose",
        )

    def test_prefer_enrichment_field(self) -> None:
        mock = MagicMock()
        mock.export_text_enrichment_json = json.dumps(
            {"version": 1, "fields": {"brd.scope_of_the_project": " AI scope "}}
        )
        self.assertEqual(
            prefer_enrichment_field(mock, "brd.scope_of_the_project", "fallback"),
            "AI scope",
        )
        self.assertEqual(prefer_enrichment_field(mock, "brd.missing", "fb"), "fb")

    def test_enrich_brd_canonical_section_bodies(self) -> None:
        mock = MagicMock()
        mock.export_text_enrichment_json = json.dumps(
            {
                "version": 1,
                "fields": {
                    "brd.executive_summary": "Exec AI",
                    "brd.background_problem_statement": "Bg AI",
                    "brd.stakeholders": "Stake AI",
                },
            }
        )
        sections = [
            {"slug": "executive_summary", "body": "exec det"},
            {"slug": "background_problem_statement", "body": "bg det"},
            {"slug": "stakeholders", "body": "st det"},
        ]
        enrich_brd_canonical_section_bodies(mock, sections)
        self.assertEqual(sections[0]["body"], "Exec AI")
        self.assertEqual(sections[1]["body"], "Bg AI")
        self.assertEqual(sections[2]["body"], "Stake AI")

    def test_enrich_brd_legacy_single_key_applies_to_exec_and_background(self) -> None:
        mock = MagicMock()
        mock.export_text_enrichment_json = json.dumps(
            {"version": 1, "fields": {"brd.current_state_summary": "Legacy one-shot"}}
        )
        sections = [
            {"slug": "executive_summary", "body": "det1"},
            {"slug": "background_problem_statement", "body": "det2"},
        ]
        enrich_brd_canonical_section_bodies(mock, sections)
        self.assertEqual(sections[0]["body"], "Legacy one-shot")
        self.assertEqual(sections[1]["body"], "Legacy one-shot")


class EnrichmentServiceTests(unittest.TestCase):
    def test_registry_lists_all_fields_in_system_prompt(self) -> None:
        self.assertIn("pdd.process_summary", ENRICHMENT_FIELD_IDS)

    def test_field_ids_for_document_type(self) -> None:
        self.assertEqual(field_ids_for_document_type("pdd"), ("pdd.process_summary",))
        self.assertEqual(field_ids_for_document_type("sop"), ("sop.purpose",))
        self.assertEqual(field_ids_for_document_type("brd"), BRD_ENRICHMENT_FIELD_IDS)
        self.assertEqual(field_ids_for_document_type(None), ("pdd.process_summary",))
        self.assertEqual(field_ids_for_document_type("unknown"), ("pdd.process_summary",))

    def test_coerce_fields_extracts_only_requested_keys(self) -> None:
        svc = DocumentExportEnrichmentService()
        out = svc._coerce_fields(
            {"fields": {"pdd.process_summary": "A", "sop.purpose": "B"}},
            ("pdd.process_summary",),
        )
        self.assertEqual(out, {"pdd.process_summary": "A"})

    @patch.object(DocumentExportEnrichmentService, "is_enabled", return_value=True)
    @patch.object(DocumentExportEnrichmentService, "_post_chat")
    def test_run_skips_llm_when_no_field_ids(self, mock_post: MagicMock, _enabled: MagicMock) -> None:
        svc = DocumentExportEnrichmentService()
        out = svc.run(evidence_digest="evidence", session_id="sess-1", field_ids=())
        self.assertIsNone(out)
        mock_post.assert_not_called()

    @patch.object(DocumentExportEnrichmentService, "is_enabled", return_value=True)
    @patch.object(DocumentExportEnrichmentService, "_post_chat")
    def test_run_parses_json(self, mock_post: MagicMock, _enabled: MagicMock) -> None:
        mock_post.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "fields": {
                                    "pdd.process_summary": "A",
                                }
                            }
                        )
                    }
                }
            ]
        }
        svc = DocumentExportEnrichmentService()
        fields = svc.run(
            evidence_digest="evidence",
            session_id="sess-1",
            field_ids=("pdd.process_summary",),
        )
        self.assertEqual(fields, {"pdd.process_summary": "A"})


if __name__ == "__main__":
    unittest.main()
