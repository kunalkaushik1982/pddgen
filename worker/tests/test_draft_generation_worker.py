from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock

DRAFT_WORKER_PATH = Path(__file__).resolve().parents[1] / "services" / "draft_generation_worker.py"
SCREENSHOT_WORKER_PATH = Path(__file__).resolve().parents[1] / "services" / "screenshot_generation_worker.py"
WORKER_ROOT = Path(__file__).resolve().parents[1]
SERVICES_ROOT = WORKER_ROOT / "services"


def _install_worker_test_stubs() -> None:
    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    core_module = types.ModuleType("app.core")
    observability_module = types.ModuleType("app.core.observability")

    class FakeLogger:
        def info(self, *args, **kwargs):
            return None

    class BindContext:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    observability_module.bind_log_context = lambda **kwargs: BindContext()
    observability_module.get_logger = lambda name: FakeLogger()

    worker_module = types.ModuleType("worker")
    worker_module.__path__ = [str(WORKER_ROOT)]  # type: ignore[attr-defined]
    worker_services_module = types.ModuleType("worker.services")
    worker_services_module.__path__ = [str(SERVICES_ROOT)]  # type: ignore[attr-defined]
    bootstrap_module = types.ModuleType("worker.bootstrap")
    composition_module = types.ModuleType("worker.services.worker_composition")
    composition_module.build_draft_generation_use_case = lambda **kwargs: None
    composition_module.build_screenshot_generation_use_case = lambda **kwargs: None

    worker_module.bootstrap = bootstrap_module
    sys.modules["app"] = app_module
    sys.modules["app.core"] = core_module
    sys.modules["app.core.observability"] = observability_module
    sys.modules["worker"] = worker_module
    sys.modules["worker.bootstrap"] = bootstrap_module
    sys.modules["worker.services"] = worker_services_module
    sys.modules["worker.services.worker_composition"] = composition_module


def load_draft_worker_module():
    _install_worker_test_stubs()
    spec = importlib.util.spec_from_file_location("draft_generation_worker_test", DRAFT_WORKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_screenshot_worker_module():
    _install_worker_test_stubs()
    spec = importlib.util.spec_from_file_location("screenshot_generation_worker_test", SCREENSHOT_WORKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WorkerAdapterTests(unittest.TestCase):
    def test_draft_worker_delegates_to_composed_use_case(self) -> None:
        module = load_draft_worker_module()
        use_case = Mock()
        use_case.run.return_value = {"session_id": "session-1", "steps_created": 2}
        package_worker_module = sys.modules["worker.services.draft_generation.worker"]
        module.build_draft_generation_use_case = Mock(return_value=use_case)
        package_worker_module.build_draft_generation_use_case = module.build_draft_generation_use_case

        worker = module.DraftGenerationWorker(task_id="task-1")
        result = worker.run("session-1")

        module.build_draft_generation_use_case.assert_called_once_with(task_id="task-1")
        use_case.run.assert_called_once_with(session_id="session-1")
        self.assertEqual(result["session_id"], "session-1")

    def test_screenshot_worker_delegates_to_composed_use_case(self) -> None:
        module = load_screenshot_worker_module()
        use_case = Mock()
        use_case.run.return_value = {"session_id": "session-2", "screenshots_created": 4}
        package_worker_module = sys.modules["worker.services.screenshot_generation.worker"]
        module.build_screenshot_generation_use_case = Mock(return_value=use_case)
        package_worker_module.build_screenshot_generation_use_case = module.build_screenshot_generation_use_case

        worker = module.ScreenshotGenerationWorker(task_id="task-2")
        result = worker.run("session-2")

        module.build_screenshot_generation_use_case.assert_called_once_with(task_id="task-2")
        use_case.run.assert_called_once_with(session_id="session-2")
        self.assertEqual(result["screenshots_created"], 4)


if __name__ == "__main__":
    unittest.main()
