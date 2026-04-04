from __future__ import annotations

import ast
from pathlib import Path
import unittest


SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
SEGMENTATION_SERVICE_PATH = SERVICES_DIR / "workflow_intelligence" / "segmentation_service.py"


class ServicePackageLayoutTests(unittest.TestCase):
    def test_expected_subpackage_files_exist(self) -> None:
        expected_files = [
            SERVICES_DIR / "orchestration" / "composition.py",
            SERVICES_DIR / "orchestration" / "contracts.py",
            SERVICES_DIR / "orchestration" / "use_cases.py",
            SERVICES_DIR / "draft_generation" / "worker.py",
            SERVICES_DIR / "draft_generation" / "input_stages.py",
            SERVICES_DIR / "draft_generation" / "output_stages.py",
            SERVICES_DIR / "draft_generation" / "screenshot_derivation.py",
            SERVICES_DIR / "draft_generation" / "diagram_assembly.py",
            SERVICES_DIR / "draft_generation" / "persistence.py",
            SERVICES_DIR / "draft_generation" / "failure.py",
            SERVICES_DIR / "screenshot_generation" / "worker.py",
            SERVICES_DIR / "screenshot_generation" / "context_builder.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_service.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_heuristics.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_chunking.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_enrichment_heuristics.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_boundary_heuristics.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_ai_strategies.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_interpreter_adapters.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_ai_enrichment.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_ai_boundary.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_models.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_ai_adapters.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_assignment_flow.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_identity_flow.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_matching.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_decisions.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_profiles.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_text.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_profile_builder.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_profile_lists.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_summaries.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_summary_refresh.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_capabilities.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_title_support.py",
            SERVICES_DIR / "workflow_intelligence" / "grouping_workflow_summary.py",
            SERVICES_DIR / "ai_transcript" / "__init__.py",
            SERVICES_DIR / "ai_transcript" / "client.py",
            SERVICES_DIR / "ai_transcript" / "interpreter.py",
            SERVICES_DIR / "ai_transcript" / "models.py",
            SERVICES_DIR / "ai_transcript" / "normalization.py",
            SERVICES_DIR / "ai_transcript" / "confidence.py",
            SERVICES_DIR / "ai_transcript" / "text_normalization.py",
            SERVICES_DIR / "ai_transcript" / "record_normalization.py",
            SERVICES_DIR / "ai_transcript" / "diagrams.py",
            SERVICES_DIR / "ai_transcript" / "diagram_prompts.py",
            SERVICES_DIR / "ai_transcript" / "diagram_interpreter.py",
            SERVICES_DIR / "ai_transcript" / "transcript_adaptation.py",
            SERVICES_DIR / "ai_transcript" / "workflow_prompts.py",
            SERVICES_DIR / "ai_transcript" / "workflow_grouping.py",
            SERVICES_DIR / "ai_transcript" / "workflow_group_inference.py",
            SERVICES_DIR / "ai_transcript" / "workflow_group_ambiguity.py",
            SERVICES_DIR / "ai_transcript" / "workflow_titles.py",
            SERVICES_DIR / "ai_transcript" / "workflow_enrichment.py",
            SERVICES_DIR / "ai_transcript" / "workflow_summaries.py",
            SERVICES_DIR / "ai_transcript" / "workflows.py",
            SERVICES_DIR / "draft_generation" / "session_preparation.py",
            SERVICES_DIR / "draft_generation" / "transcript_interpretation.py",
            SERVICES_DIR / "draft_generation" / "evidence_segmentation.py",
            SERVICES_DIR / "draft_generation" / "persistence_records.py",
            SERVICES_DIR / "draft_generation" / "persistence_screenshots.py",
            SERVICES_DIR / "draft_generation" / "screenshot_timing.py",
            SERVICES_DIR / "draft_generation" / "screenshot_selection.py",
            SERVICES_DIR / "screenshot_generation" / "context_cleanup.py",
            SERVICES_DIR / "screenshot_generation" / "context_resolution.py",
            SERVICES_DIR / "media" / "video_frame_extractor.py",
            SERVICES_DIR / "media" / "ffmpeg_runtime.py",
            SERVICES_DIR / "media" / "frame_time_utils.py",
            SERVICES_DIR / "workflow_intelligence" / "canonical_merge_grouping.py",
            SERVICES_DIR / "workflow_intelligence" / "canonical_merge_matching.py",
        ]

        missing_files = [str(path) for path in expected_files if not path.exists()]

        self.assertEqual(missing_files, [])

    def test_internal_only_shims_have_been_removed(self) -> None:
        removed_internal_shims = [
            SERVICES_DIR / "worker_composition.py",
            SERVICES_DIR / "worker_contracts.py",
            SERVICES_DIR / "worker_pipeline.py",
            SERVICES_DIR / "worker_repositories.py",
            SERVICES_DIR / "worker_uow.py",
            SERVICES_DIR / "worker_use_cases.py",
            SERVICES_DIR / "canonical_process_merge.py",
            SERVICES_DIR / "draft_generation_input_stages.py",
            SERVICES_DIR / "draft_generation_output_stages.py",
            SERVICES_DIR / "draft_generation_process_stages.py",
            SERVICES_DIR / "draft_generation_stage_context.py",
            SERVICES_DIR / "draft_generation_support.py",
            SERVICES_DIR / "transcript_normalizer.py",
            SERVICES_DIR / "video_frame_extractor.py",
            SERVICES_DIR / "workflow_strategy_interfaces.py",
            SERVICES_DIR / "workflow_strategy_registry.py",
        ]

        remaining_shims = [str(path) for path in removed_internal_shims if path.exists()]

        self.assertEqual(remaining_shims, [])

    def test_second_pass_flat_service_entrypoints_have_been_removed(self) -> None:
        removed_second_pass_shims = [
            SERVICES_DIR / "draft_generation_worker.py",
            SERVICES_DIR / "screenshot_generation_worker.py",
            SERVICES_DIR / "process_grouping_service.py",
            SERVICES_DIR / "evidence_segmentation_service.py",
            SERVICES_DIR / "workflow_intelligence.py",
        ]

        remaining_shims = [str(path) for path in removed_second_pass_shims if path.exists()]

        self.assertEqual(remaining_shims, [])

    def test_segmentation_service_imports_split_modules(self) -> None:
        module = ast.parse(SEGMENTATION_SERVICE_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.grouping.segmentation_heuristics", imported_modules)
        self.assertIn("worker.grouping.segmentation_ai_strategies", imported_modules)

    def test_output_stages_imports_split_modules(self) -> None:
        output_stage_path = SERVICES_DIR / "draft_generation" / "output_stages.py"
        module = ast.parse(output_stage_path.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.pipeline.stages.screenshot_derivation", imported_modules)
        self.assertIn("worker.pipeline.stages.diagram_assembly", imported_modules)
        self.assertIn("worker.pipeline.stages.persistence", imported_modules)
        self.assertIn("worker.pipeline.stages.failure", imported_modules)

    def test_grouping_service_imports_split_modules(self) -> None:
        grouping_service_path = SERVICES_DIR / "workflow_intelligence" / "grouping_service.py"
        module = ast.parse(grouping_service_path.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.grouping.grouping_models", imported_modules)
        self.assertIn("worker.grouping.grouping_ai_adapters", imported_modules)
        self.assertIn("worker.grouping.grouping_assignment_flow", imported_modules)
        self.assertIn("worker.grouping.grouping_identity_flow", imported_modules)
        self.assertIn("worker.grouping.grouping_decisions", imported_modules)
        self.assertIn("worker.grouping.grouping_profiles", imported_modules)
        self.assertIn("worker.grouping.grouping_summaries", imported_modules)
        self.assertIn("worker.grouping.grouping_summary_refresh", imported_modules)
        self.assertIn("worker.grouping.grouping_text", imported_modules)

    def test_grouping_service_is_thin_enough(self) -> None:
        grouping_service_path = SERVICES_DIR / "workflow_intelligence" / "grouping_service.py"
        line_count = len(grouping_service_path.read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(line_count, 500)

    def test_input_stages_imports_split_modules(self) -> None:
        input_stage_path = SERVICES_DIR / "draft_generation" / "input_stages.py"
        module = ast.parse(input_stage_path.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        self.assertIn("worker.pipeline.stages.session_preparation", imported_modules)
        self.assertIn("worker.pipeline.stages.transcript_interpretation", imported_modules)
        self.assertIn("worker.pipeline.stages.evidence_segmentation", imported_modules)


if __name__ == "__main__":
    unittest.main()
