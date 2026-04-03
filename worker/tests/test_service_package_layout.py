from __future__ import annotations

from pathlib import Path
import unittest


SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"


class ServicePackageLayoutTests(unittest.TestCase):
    def test_expected_subpackage_files_exist(self) -> None:
        expected_files = [
            SERVICES_DIR / "orchestration" / "composition.py",
            SERVICES_DIR / "orchestration" / "contracts.py",
            SERVICES_DIR / "orchestration" / "use_cases.py",
            SERVICES_DIR / "draft_generation" / "worker.py",
            SERVICES_DIR / "draft_generation" / "input_stages.py",
            SERVICES_DIR / "draft_generation" / "output_stages.py",
            SERVICES_DIR / "screenshot_generation" / "worker.py",
            SERVICES_DIR / "screenshot_generation" / "context_builder.py",
            SERVICES_DIR / "workflow_intelligence" / "segmentation_service.py",
            SERVICES_DIR / "ai_transcript" / "__init__.py",
            SERVICES_DIR / "ai_transcript" / "client.py",
            SERVICES_DIR / "ai_transcript" / "models.py",
            SERVICES_DIR / "ai_transcript" / "normalization.py",
            SERVICES_DIR / "ai_transcript" / "diagrams.py",
            SERVICES_DIR / "ai_transcript" / "diagram_interpreter.py",
            SERVICES_DIR / "ai_transcript" / "transcript_adaptation.py",
            SERVICES_DIR / "ai_transcript" / "workflows.py",
            SERVICES_DIR / "media" / "video_frame_extractor.py",
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


if __name__ == "__main__":
    unittest.main()
