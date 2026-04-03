from __future__ import annotations

import ast
from pathlib import Path
import unittest


INTERPRETER_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript_interpreter.py"
WORKFLOWS_PATH = Path(__file__).resolve().parents[1] / "services" / "ai_transcript" / "workflows.py"


class AITranscriptPackageLayoutTests(unittest.TestCase):
    def test_interpreter_imports_split_ai_transcript_modules(self) -> None:
        module = ast.parse(INTERPRETER_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.services.ai_transcript.client", imported_modules)
        self.assertIn("worker.services.ai_transcript.models", imported_modules)
        self.assertIn("worker.services.ai_transcript.normalization", imported_modules)
        self.assertIn("worker.services.ai_transcript.diagrams", imported_modules)
        self.assertIn("worker.services.ai_transcript.diagram_interpreter", imported_modules)
        self.assertIn("worker.services.ai_transcript.transcript_adaptation", imported_modules)
        self.assertIn("worker.services.ai_transcript.workflows", imported_modules)

    def test_workflows_imports_prompt_module(self) -> None:
        module = ast.parse(WORKFLOWS_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.services.ai_transcript.workflow_prompts", imported_modules)

    def test_workflows_imports_split_workflow_modules(self) -> None:
        module = ast.parse(WORKFLOWS_PATH.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }

        self.assertIn("worker.services.ai_transcript.workflow_grouping", imported_modules)
        self.assertIn("worker.services.ai_transcript.workflow_titles", imported_modules)
        self.assertIn("worker.services.ai_transcript.workflow_enrichment", imported_modules)
        self.assertIn("worker.services.ai_transcript.workflow_summaries", imported_modules)


if __name__ == "__main__":
    unittest.main()
