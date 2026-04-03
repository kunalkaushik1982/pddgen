from __future__ import annotations

import ast
from pathlib import Path
import unittest


SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
LEGACY_STAGE_PATH = SERVICES_DIR / "draft_generation_stage_services.py"
LEGACY_OUTPUT_STAGE_PATH = SERVICES_DIR / "draft_generation_output_stages.py"
OUTPUT_STAGE_PATH = SERVICES_DIR / "draft_generation" / "output_stages.py"

OUTPUT_STAGE_CLASS_NAMES = {
    "ScreenshotDerivationStage",
    "DiagramAssemblyStage",
    "PersistenceStage",
    "FailureStage",
}


def _defined_class_names(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in module.body
        if isinstance(node, ast.ClassDef)
    }


class StageModuleSplitTests(unittest.TestCase):
    def test_output_stage_module_owns_output_stage_classes(self) -> None:
        output_class_names = _defined_class_names(OUTPUT_STAGE_PATH)

        self.assertTrue(OUTPUT_STAGE_CLASS_NAMES.issubset(output_class_names))

    def test_legacy_stage_module_does_not_define_output_stage_classes(self) -> None:
        legacy_class_names = _defined_class_names(LEGACY_STAGE_PATH)

        self.assertTrue(OUTPUT_STAGE_CLASS_NAMES.isdisjoint(legacy_class_names))

    def test_legacy_output_stage_module_is_a_shim(self) -> None:
        self.assertIn(
            "worker.services.draft_generation.output_stages",
            LEGACY_OUTPUT_STAGE_PATH.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
