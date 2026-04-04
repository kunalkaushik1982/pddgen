from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

DRAFT_TASK_PATH = Path(__file__).resolve().parents[1] / "tasks" / "draft_generation.py"
SCREENSHOT_TASK_PATH = Path(__file__).resolve().parents[1] / "tasks" / "screenshot_generation.py"


class _FakeCeleryApp:
    def task(self, **kwargs):
        def decorator(func):
            func._task_kwargs = kwargs
            return func

        return decorator


class _BindContext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeLogger:
    def info(self, *args, **kwargs):
        return None

    def exception(self, *args, **kwargs):
        return None


def _install_task_test_stubs() -> None:
    app_module = types.ModuleType("app")
    app_module.__path__ = []  # type: ignore[attr-defined]
    core_module = types.ModuleType("app.core")
    observability_module = types.ModuleType("app.core.observability")
    observability_module.bind_log_context = lambda **kwargs: _BindContext()
    observability_module.get_logger = lambda name: _FakeLogger()

    worker_module = types.ModuleType("worker")
    worker_module.__path__ = []  # type: ignore[attr-defined]
    bootstrap_module = types.ModuleType("worker.bootstrap")
    worker_module.bootstrap = bootstrap_module
    celery_app_module = types.ModuleType("worker.celery_app")
    celery_app_module.celery_app = _FakeCeleryApp()
    services_module = types.ModuleType("worker.services")
    services_module.__path__ = []  # type: ignore[attr-defined]
    draft_generation_package = types.ModuleType("worker.services.draft_generation")
    draft_generation_package.__path__ = []  # type: ignore[attr-defined]
    screenshot_generation_package = types.ModuleType("worker.services.screenshot_generation")
    screenshot_generation_package.__path__ = []  # type: ignore[attr-defined]
    draft_worker_module = types.ModuleType("worker.pipeline.stages.worker")
    draft_worker_module.DraftGenerationWorker = type("DraftGenerationWorker", (), {})
    screenshot_worker_module = types.ModuleType("worker.screenshot.worker")
    screenshot_worker_module.ScreenshotGenerationWorker = type("ScreenshotGenerationWorker", (), {})

    sys.modules["app"] = app_module
    sys.modules["app.core"] = core_module
    sys.modules["app.core.observability"] = observability_module
    sys.modules["worker"] = worker_module
    sys.modules["worker.bootstrap"] = bootstrap_module
    sys.modules["worker.celery_app"] = celery_app_module
    sys.modules["worker.services"] = services_module
    sys.modules["worker.services.draft_generation"] = draft_generation_package
    sys.modules["worker.services.screenshot_generation"] = screenshot_generation_package
    sys.modules["worker.pipeline.stages.worker"] = draft_worker_module
    sys.modules["worker.screenshot.worker"] = screenshot_worker_module


def load_draft_task_module():
    _install_task_test_stubs()
    spec = importlib.util.spec_from_file_location("draft_generation_task_test", DRAFT_TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_screenshot_task_module():
    _install_task_test_stubs()
    spec = importlib.util.spec_from_file_location("screenshot_generation_task_test", SCREENSHOT_TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WorkerTaskTests(unittest.TestCase):
    def test_draft_task_delegates_to_worker(self) -> None:
        module = load_draft_task_module()
        worker = type("Worker", (), {"run": lambda self, session_id: {"session_id": session_id, "steps_created": 2}})()
        module.DraftGenerationWorker = lambda task_id=None: worker
        request = type("Request", (), {"id": "task-1"})()
        task_self = type("TaskSelf", (), {"request": request})()

        result = module.run_draft_generation(task_self, "session-1")

        self.assertEqual(result["steps_created"], 2)
        self.assertEqual(module.run_draft_generation._task_kwargs["name"], "draft_generation.run")

    def test_draft_task_wraps_value_error_as_runtime_error(self) -> None:
        module = load_draft_task_module()

        class Worker:
            def run(self, session_id: str):
                raise ValueError("missing session")

        module.DraftGenerationWorker = lambda task_id=None: Worker()
        request = type("Request", (), {"id": "task-2"})()
        task_self = type("TaskSelf", (), {"request": request})()

        with self.assertRaisesRegex(RuntimeError, "missing session"):
            module.run_draft_generation(task_self, "session-2")

    def test_screenshot_task_delegates_to_worker(self) -> None:
        module = load_screenshot_task_module()
        worker = type("Worker", (), {"run": lambda self, session_id: {"session_id": session_id, "screenshots_created": 4}})()
        module.ScreenshotGenerationWorker = lambda task_id=None: worker
        request = type("Request", (), {"id": "task-3"})()
        task_self = type("TaskSelf", (), {"request": request})()

        result = module.run_screenshot_generation(task_self, "session-3")

        self.assertEqual(result["screenshots_created"], 4)
        self.assertEqual(module.run_screenshot_generation._task_kwargs["name"], "screenshot_generation.run")

    def test_screenshot_task_wraps_value_error_as_runtime_error(self) -> None:
        module = load_screenshot_task_module()

        class Worker:
            def run(self, session_id: str):
                raise ValueError("no screenshots")

        module.ScreenshotGenerationWorker = lambda task_id=None: Worker()
        request = type("Request", (), {"id": "task-4"})()
        task_self = type("TaskSelf", (), {"request": request})()

        with self.assertRaisesRegex(RuntimeError, "no screenshots"):
            module.run_screenshot_generation(task_self, "session-4")


if __name__ == "__main__":
    unittest.main()
