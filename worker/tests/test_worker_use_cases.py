from __future__ import annotations

import unittest

import worker.pipeline.use_cases as use_cases


class WorkerUseCaseTests(unittest.TestCase):
    def test_draft_use_case_runs_injected_stages_and_persists_result(self) -> None:
        events: list[str] = []

        class FakeUow:
            def __enter__(self):
                self.session = object()
                events.append("uow_enter")
                return self

            def __exit__(self, exc_type, exc, tb):
                events.append("uow_exit")
                return False

        class FakeRepository:
            def load_draft_session(self, db, session_id: str):
                events.append(f"load:{session_id}")
                return object()

        class FakeStage:
            def __init__(self, name: str) -> None:
                self.name = name

            def run(self, db, context) -> None:
                events.append(self.name)

        class FakePersister:
            def persist(self, db, context):
                events.append("persist")
                return {"session_id": context.session_id, "steps_created": 3}

        class FakeContext:
            def __init__(self, session_id: str) -> None:
                self.session_id = session_id

        use_case = use_cases.DraftGenerationUseCase(
            uow_factory=lambda: FakeUow(),
            repository=FakeRepository(),
            context_loader=lambda db, session: FakeContext("session-1"),
            stages=[FakeStage("segment"), FakeStage("group")],
            persister=FakePersister(),
            failure_recorder=None,
        )

        result = use_case.run(session_id="session-1")

        self.assertEqual(result["steps_created"], 3)
        self.assertEqual(events, ["uow_enter", "load:session-1", "segment", "group", "persist", "uow_exit"])

    def test_draft_use_case_records_failure_and_reraises(self) -> None:
        events: list[str] = []

        class FakeUow:
            def __enter__(self):
                self.session = object()
                return self

            def __exit__(self, exc_type, exc, tb):
                events.append(f"uow_exit:{exc_type.__name__ if exc_type else 'none'}")
                return False

        class FakeRepository:
            def load_draft_session(self, db, session_id: str):
                return object()

        class FakeContext:
            session_id = "session-9"

        class BoomStage:
            def run(self, db, context) -> None:
                raise RuntimeError("boom")

        class FakeFailureRecorder:
            def record_failure(self, db, session_id: str, detail: str | None = None) -> None:
                events.append(f"failure:{session_id}:{detail}")

        class FakePersister:
            def persist(self, db, context):
                raise AssertionError("persist should not be called")

        use_case = use_cases.DraftGenerationUseCase(
            uow_factory=lambda: FakeUow(),
            repository=FakeRepository(),
            context_loader=lambda db, session: FakeContext(),
            stages=[BoomStage()],
            persister=FakePersister(),
            failure_recorder=FakeFailureRecorder(),
        )

        with self.assertRaisesRegex(RuntimeError, "boom"):
            use_case.run(session_id="session-9")

        self.assertEqual(events, ["failure:session-9:boom", "uow_exit:RuntimeError"])

    def test_screenshot_use_case_releases_lock_after_run(self) -> None:
        events: list[str] = []

        class FakeUow:
            def __enter__(self):
                self.session = object()
                return self

            def __exit__(self, exc_type, exc, tb):
                events.append("uow_exit")
                return False

        class FakeRepository:
            def load_draft_session(self, db, session_id: str):
                events.append(f"load:{session_id}")
                return object()

        class FakeBuilder:
            def build(self, db, session):
                events.append("build")

                class FakeContext:
                    session_id = "session-4"

                return FakeContext()

        class FakeStage:
            def run(self, db, context):
                events.append("derive")

        class FakePersister:
            def persist(self, db, context):
                events.append("persist")
                return {"session_id": context.session_id, "screenshots_created": 2}

        class FakeLockManager:
            def release(self, session_id: str) -> None:
                events.append(f"release:{session_id}")

        use_case = use_cases.ScreenshotGenerationUseCase(
            uow_factory=lambda: FakeUow(),
            repository=FakeRepository(),
            context_builder=FakeBuilder(),
            stages=[FakeStage()],
            persister=FakePersister(),
            lock_manager=FakeLockManager(),
        )

        result = use_case.run(session_id="session-4")

        self.assertEqual(result["screenshots_created"], 2)
        self.assertEqual(events, ["load:session-4", "build", "derive", "persist", "uow_exit", "release:session-4"])


if __name__ == "__main__":
    unittest.main()
