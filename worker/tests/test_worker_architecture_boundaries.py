from __future__ import annotations

import ast
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = REPO_ROOT / "worker" / "services"
CONTRACTS_PATH = SERVICES_DIR / "orchestration" / "contracts.py"
PIPELINE_PATH = SERVICES_DIR / "orchestration" / "pipeline.py"
AI_SKILL_BASE_PATH = SERVICES_DIR / "ai_skills" / "base.py"
GROUPING_SERVICE_PATH = SERVICES_DIR / "workflow_intelligence" / "grouping_service.py"
AI_TRANSCRIPT_INTERPRETER_PATH = SERVICES_DIR / "ai_transcript_interpreter.py"

NON_RUNTIME_MODULES = [
    SERVICES_DIR / "orchestration" / "composition.py",
    SERVICES_DIR / "orchestration" / "repositories.py",
    SERVICES_DIR / "draft_generation" / "input_stages.py",
    SERVICES_DIR / "draft_generation" / "process_stages.py",
    SERVICES_DIR / "draft_generation" / "diagram_assembly.py",
    SERVICES_DIR / "draft_generation" / "screenshot_derivation.py",
    SERVICES_DIR / "draft_generation" / "persistence.py",
    SERVICES_DIR / "draft_generation" / "failure.py",
    SERVICES_DIR / "screenshot_generation" / "context_builder.py",
]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _has_worker_bootstrap_side_effect_import(path: Path) -> bool:
    module = _parse(path)
    for node in module.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "worker":
            continue
        for alias in node.names:
            if alias.name == "bootstrap":
                return True
    return False


def _annotation_name(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


class WorkerArchitectureBoundaryTests(unittest.TestCase):
    def test_non_runtime_modules_do_not_import_worker_bootstrap_for_side_effects(self) -> None:
        offending_modules = [str(path) for path in NON_RUNTIME_MODULES if _has_worker_bootstrap_side_effect_import(path)]
        self.assertEqual(offending_modules, [])

    def test_contracts_define_worker_db_session_protocol(self) -> None:
        module = _parse(CONTRACTS_PATH)
        protocol_names = {
            node.name
            for node in module.body
            if isinstance(node, ast.ClassDef)
        }
        self.assertIn("WorkerDbSession", protocol_names)

    def test_orchestration_protocols_use_worker_db_session(self) -> None:
        module = _parse(CONTRACTS_PATH)
        methods = {}
        for node in module.body:
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.args.args:
                        methods[(node.name, item.name)] = _annotation_name(item.args.args[1].annotation) if len(item.args.args) > 1 else None

        expected = {
            ("DraftSessionRepository", "load_draft_session"),
            ("DraftContextLoader", "__call__"),
            ("DraftPipelineStage", "run"),
            ("DraftResultPersister", "persist"),
            ("FailureRecorder", "record_failure"),
            ("ScreenshotContextBuilder", "build"),
            ("ScreenshotPipelineStage", "run"),
            ("ScreenshotResultPersister", "persist"),
        }
        for key in expected:
            with self.subTest(method=key):
                self.assertEqual(methods.get(key), "WorkerDbSession")

    def test_ordered_stage_runner_uses_worker_db_session(self) -> None:
        module = _parse(PIPELINE_PATH)
        run_annotation = None
        for node in module.body:
            if isinstance(node, ast.ClassDef) and node.name == "OrderedStageRunner":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "run":
                        run_annotation = _annotation_name(item.args.args[1].annotation)
        self.assertEqual(run_annotation, "WorkerDbSession")

    def test_ai_skill_protocol_is_generic(self) -> None:
        module = _parse(AI_SKILL_BASE_PATH)
        class_names = {node.name for node in module.body if isinstance(node, ast.ClassDef)}
        assign_names = {
            target.id
            for node in module.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertIn("RequestT", assign_names)
        self.assertIn("ResponseT", assign_names)
        self.assertIn("AISkill", class_names)

    def test_grouping_service_delegates_to_split_modules(self) -> None:
        module = _parse(GROUPING_SERVICE_PATH)
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        self.assertIn("worker.services.workflow_intelligence.grouping_models", imported_modules)
        self.assertIn("worker.services.workflow_intelligence.grouping_ai_adapters", imported_modules)
        self.assertIn("worker.services.workflow_intelligence.grouping_title_resolution", imported_modules)
        self.assertIn("worker.services.workflow_intelligence.grouping_identity_resolution", imported_modules)

    def test_ai_transcript_interpreter_delegates_to_split_modules(self) -> None:
        module = _parse(AI_TRANSCRIPT_INTERPRETER_PATH)
        imported_modules = {
            node.module
            for node in module.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        self.assertIn("worker.services.ai_transcript_models", imported_modules)
        self.assertIn("worker.services.ai_transcript_normalization", imported_modules)
        self.assertIn("worker.services.ai_transcript_client", imported_modules)
        self.assertIn("worker.services.ai_transcript_diagrams", imported_modules)


if __name__ == "__main__":
    unittest.main()
