from __future__ import annotations

import ast
from pathlib import Path
import unittest


SERVICES_DIR = Path(__file__).resolve().parents[1]
GROUPING_DIR = SERVICES_DIR / "grouping"
PIPELINE_DIR = SERVICES_DIR / "pipeline"
STAGES_DIR = PIPELINE_DIR / "stages"
AI_SKILLS_DIR = SERVICES_DIR / "ai_skills"


class ServicePackageLayoutTests(unittest.TestCase):
    def test_expected_subpackage_files_exist(self) -> None:
        expected_files = [
            PIPELINE_DIR / "composition.py",
            PIPELINE_DIR / "contracts.py",
            PIPELINE_DIR / "use_cases.py",
            STAGES_DIR / "worker.py",
            STAGES_DIR / "input_stages.py",
            STAGES_DIR / "output_stages.py",
            STAGES_DIR / "screenshot_derivation.py",
            STAGES_DIR / "diagram_assembly.py",
            STAGES_DIR / "persistence.py",
            STAGES_DIR / "failure.py",
            SERVICES_DIR / "screenshot" / "worker.py",
            SERVICES_DIR / "screenshot" / "context_builder.py",
            GROUPING_DIR / "segmentation_service.py",
            GROUPING_DIR / "segmentation_heuristics.py",
            GROUPING_DIR / "segmentation_chunking.py",
            GROUPING_DIR / "segmentation_enrichment_heuristics.py",
            GROUPING_DIR / "segmentation_boundary_heuristics.py",
            GROUPING_DIR / "segmentation_ai_strategies.py",
            GROUPING_DIR / "segmentation_interpreter_adapters.py",
            GROUPING_DIR / "segmentation_ai_enrichment.py",
            GROUPING_DIR / "segmentation_ai_boundary.py",
            GROUPING_DIR / "grouping_models.py",
            GROUPING_DIR / "grouping_ai_adapters.py",
            GROUPING_DIR / "grouping_assignment_flow.py",
            GROUPING_DIR / "grouping_identity_flow.py",
            GROUPING_DIR / "grouping_matching.py",
            GROUPING_DIR / "grouping_decisions.py",
            GROUPING_DIR / "grouping_profiles.py",
            GROUPING_DIR / "grouping_text.py",
            GROUPING_DIR / "grouping_profile_builder.py",
            GROUPING_DIR / "grouping_profile_lists.py",
            GROUPING_DIR / "grouping_summaries.py",
            GROUPING_DIR / "grouping_summary_refresh.py",
            GROUPING_DIR / "grouping_titles.py",
            GROUPING_DIR / "grouping_workflow_summary.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "__init__.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "client.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "interpreter.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "models.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "normalization.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "confidence.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "text_normalization.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "record_normalization.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "diagrams.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "diagram_prompts.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "diagram_interpreter.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "transcript_adaptation.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "workflow_prompts.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "workflow_grouping.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "workflow_group_inference.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "workflow_group_ambiguity.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "workflow_titles.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "workflow_enrichment.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "workflow_summaries.py",
            AI_SKILLS_DIR / "transcript_interpreter" / "workflows.py",
            STAGES_DIR / "session_preparation.py",
            STAGES_DIR / "transcript_interpretation.py",
            STAGES_DIR / "evidence_segmentation.py",
            STAGES_DIR / "persistence_records.py",
            STAGES_DIR / "persistence_screenshots.py",
            STAGES_DIR / "screenshot_timing.py",
            STAGES_DIR / "screenshot_selection.py",
            SERVICES_DIR / "screenshot" / "context_cleanup.py",
            SERVICES_DIR / "screenshot" / "context_resolution.py",
            SERVICES_DIR / "media" / "video_frame_extractor.py",
            SERVICES_DIR / "media" / "ffmpeg_runtime.py",
            SERVICES_DIR / "media" / "frame_time_utils.py",
            GROUPING_DIR / "canonical_merge_grouping.py",
            GROUPING_DIR / "canonical_merge_matching.py",
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
            SERVICES_DIR / "ai_transcript",  # Directory was removed
        ]

        remaining_shims = [str(path) for path in removed_second_pass_shims if path.exists()]

        self.assertEqual(remaining_shims, [])

    def test_segmentation_service_imports_split_modules(self) -> None:
        segmentation_service_path = GROUPING_DIR / "segmentation_service.py"
        module = ast.parse(segmentation_service_path.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.grouping.segmentation_heuristics", imported_modules)
        self.assertIn("worker.grouping.segmentation_ai_strategies", imported_modules)

    def test_output_stages_imports_split_modules(self) -> None:
        output_stage_path = STAGES_DIR / "output_stages.py"
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
        grouping_service_path = GROUPING_DIR / "grouping_service.py"
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
        self.assertIn("worker.grouping.grouping_titles", imported_modules)

    def test_grouping_service_is_thin_enough(self) -> None:
        grouping_service_path = GROUPING_DIR / "grouping_service.py"
        line_count = len(grouping_service_path.read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(line_count, 500)

    def test_input_stages_imports_split_modules(self) -> None:
        input_stage_path = STAGES_DIR / "input_stages.py"
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
