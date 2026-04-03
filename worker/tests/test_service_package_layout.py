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
            SERVICES_DIR / "media" / "video_frame_extractor.py",
        ]

        missing_files = [str(path) for path in expected_files if not path.exists()]

        self.assertEqual(missing_files, [])

    def test_legacy_entry_modules_are_compatibility_shims(self) -> None:
        legacy_files = {
            SERVICES_DIR / "worker_composition.py": "worker.services.orchestration.composition",
            SERVICES_DIR / "draft_generation_worker.py": "worker.services.draft_generation.worker",
            SERVICES_DIR / "screenshot_generation_worker.py": "worker.services.screenshot_generation.worker",
            SERVICES_DIR / "draft_generation_input_stages.py": "worker.services.draft_generation.input_stages",
            SERVICES_DIR / "evidence_segmentation_service.py": "worker.services.workflow_intelligence.segmentation_service",
            SERVICES_DIR / "video_frame_extractor.py": "worker.services.media.video_frame_extractor",
        }

        for path, target_import in legacy_files.items():
            self.assertIn(target_import, path.read_text(encoding="utf-8"), msg=str(path))


if __name__ == "__main__":
    unittest.main()
