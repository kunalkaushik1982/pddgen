from __future__ import annotations

import ast
from pathlib import Path
import unittest


SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
LEGACY_OUTPUT_STAGE_PATH = SERVICES_DIR / "draft_generation_output_stages.py"
SCREENSHOT_DERIVATION_PATH = SERVICES_DIR / "draft_generation" / "screenshot_derivation.py"
DIAGRAM_ASSEMBLY_PATH = SERVICES_DIR / "draft_generation" / "diagram_assembly.py"
PERSISTENCE_PATH = SERVICES_DIR / "draft_generation" / "persistence.py"
FAILURE_PATH = SERVICES_DIR / "draft_generation" / "failure.py"

EXPECTED_STAGE_OWNERS = {
    SCREENSHOT_DERIVATION_PATH: {"ScreenshotDerivationStage"},
    DIAGRAM_ASSEMBLY_PATH: {"DiagramAssemblyStage"},
    PERSISTENCE_PATH: {"PersistenceStage"},
    FAILURE_PATH: {"FailureStage"},
}


def _defined_class_names(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in module.body
        if isinstance(node, ast.ClassDef)
    }


class StageModuleSplitTests(unittest.TestCase):
    def test_split_output_stage_modules_own_output_stage_classes(self) -> None:
        for module_path, expected_class_names in EXPECTED_STAGE_OWNERS.items():
            with self.subTest(module=module_path.name):
                output_class_names = _defined_class_names(module_path)
                self.assertTrue(expected_class_names.issubset(output_class_names))

    def test_legacy_stage_module_has_been_removed(self) -> None:
        self.assertFalse((SERVICES_DIR / "draft_generation_stage_services.py").exists())

    def test_legacy_output_stage_module_has_been_removed(self) -> None:
        self.assertFalse(LEGACY_OUTPUT_STAGE_PATH.exists())

    def test_split_output_stage_aggregate_module_has_been_removed(self) -> None:
        self.assertFalse((SERVICES_DIR / "draft_generation" / "output_stages.py").exists())


if __name__ == "__main__":
    unittest.main()
