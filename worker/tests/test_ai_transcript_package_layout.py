from __future__ import annotations

import ast
from pathlib import Path
import unittest


INTERPRETER_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript_interpreter.py"
PACKAGE_INTERPRETER_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "interpreter.py"
WORKFLOWS_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "workflows.py"
DIAGRAM_INTERPRETER_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "diagram_interpreter.py"


class AITranscriptPackageLayoutTests(unittest.TestCase):
    def test_interpreter_shim_reexports_package_interpreter(self) -> None:
        module = ast.parse(INTERPRETER_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        self.assertIn("worker.ai_skills.transcript_interpreter.interpreter", imported_modules)

    def test_package_interpreter_imports_split_ai_transcript_modules(self) -> None:
        module = ast.parse(PACKAGE_INTERPRETER_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        self.assertIn("worker.ai_skills.transcript_interpreter.client", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.models", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.normalization", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.diagrams", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.diagram_interpreter", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.transcript_adaptation", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.workflows", imported_modules)

    def test_workflows_imports_prompt_module(self) -> None:
        module = ast.parse(WORKFLOWS_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.ai_skills.transcript_interpreter.workflow_prompts", imported_modules)

    def test_workflows_imports_split_workflow_modules(self) -> None:
        module = ast.parse(WORKFLOWS_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.ai_skills.transcript_interpreter.workflow_grouping", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.workflow_titles", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.workflow_enrichment", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.workflow_summaries", imported_modules)

    def test_diagram_interpreter_imports_prompt_and_runtime_modules(self) -> None:
        module = ast.parse(DIAGRAM_INTERPRETER_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.ai_skills.transcript_interpreter.diagram_prompts", imported_modules)
        self.assertIn("worker.ai_skills.transcript_interpreter.workflow_runtime", imported_modules)


if __name__ == "__main__":
    unittest.main()
