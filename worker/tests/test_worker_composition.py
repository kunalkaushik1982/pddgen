from __future__ import annotations

import unittest

from worker.tests.import_cleanup import clear_stub_modules_for_integration_tests


class WorkerCompositionTests(unittest.TestCase):
    def test_build_default_evidence_segmentation_stage_injects_segmentation_service(self) -> None:
        clear_stub_modules_for_integration_tests()
        from worker.pipeline import composition

        stage = composition.build_default_evidence_segmentation_stage()

        self.assertIsNotNone(stage.segmentation_service)
        self.assertIsNotNone(stage.transcript_normalizer)
        self.assertIsNotNone(stage.action_log_service)


if __name__ == "__main__":
    unittest.main()
