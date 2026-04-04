from __future__ import annotations

import ast
from pathlib import Path
import unittest


SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
LEGACY_OUTPUT_STAGE_PATH = SERVICES_DIR / "draft_generation_output_stages.py"
OUTPUT_STAGE_PATH = SERVICES_DIR / "draft_generation" / "output_stages.py"

OUTPUT_STAGE_EXPORT_NAMES = {
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


def _imported_names(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in module.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


class StageModuleSplitTests(unittest.TestCase):
    def test_output_stage_module_exports_output_stage_classes(self) -> None:
        imported_names = _imported_names(OUTPUT_STAGE_PATH)

        self.assertTrue(OUTPUT_STAGE_EXPORT_NAMES.issubset(imported_names))

    def test_legacy_stage_module_has_been_removed(self) -> None:
        self.assertFalse((SERVICES_DIR / "draft_generation_stage_services.py").exists())

    def test_legacy_output_stage_module_has_been_removed(self) -> None:
        self.assertFalse(LEGACY_OUTPUT_STAGE_PATH.exists())


if __name__ == "__main__":
    unittest.main()
