# Worker Contract-First Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the worker orchestration layer into interface-first, compatibility-preserving use cases while keeping existing Celery task entrypoints and worker outcomes stable.

**Architecture:** Introduce small worker contracts, a DB unit-of-work boundary, repository-backed session loading, injectable pipeline execution, and dedicated use cases for draft and screenshot generation. Keep current `DraftGenerationWorker` and `ScreenshotGenerationWorker` as thin adapters over the new use cases.

**Tech Stack:** Python, Celery, SQLAlchemy, Protocol, dataclasses, unittest, existing worker stage services

---

## File Structure

### New files

- `worker/services/worker_contracts.py`
  Defines worker-specific `Protocol` contracts and result/context DTOs used by orchestration code.
- `worker/services/worker_uow.py`
  Provides SQLAlchemy-backed unit-of-work and factory helpers for worker flows.
- `worker/services/worker_repositories.py`
  Encapsulates draft-session loading and worker persistence/failure helper queries that should not live in adapters.
- `worker/services/worker_pipeline.py`
  Provides reusable ordered stage runner utilities for draft and screenshot flows.
- `worker/services/worker_use_cases.py`
  Implements `DraftGenerationUseCase` and `ScreenshotGenerationUseCase`.
- `worker/services/screenshot_context_builder.py`
  Extracts screenshot preparation logic from `ScreenshotGenerationWorker`.
- `worker/services/worker_composition.py`
  Wires default concrete implementations and stage lists for production worker execution.
- `worker/tests/test_worker_use_cases.py`
  Verifies orchestration order, failure behavior, and screenshot lock release through fake contract implementations.
- `worker/tests/test_screenshot_context_builder.py`
  Verifies transcript lineage resolution, screenshot cleanup, and validation rules.

### Modified files

- `worker/services/draft_generation_worker.py`
  Convert to thin adapter over `DraftGenerationUseCase`.
- `worker/services/screenshot_generation_worker.py`
  Convert to thin adapter over `ScreenshotGenerationUseCase`.
- `worker/services/draft_generation_stage_services.py`
  Remove in-stage default wiring that belongs in composition; update any stage signatures needed to work with new contracts.
- `worker/bootstrap.py`
  Reuse `get_db_session()` through the new unit-of-work factory instead of direct orchestration ownership.
- `worker/tests/test_draft_generation_worker.py`
  Update tests to assert adapter delegation instead of patch-heavy internal stage wiring.
- `worker/tasks/draft_generation.py`
  Keep behavior stable; no code change expected beyond import compatibility validation.
- `worker/tasks/screenshot_generation.py`
  Keep behavior stable; no code change expected beyond import compatibility validation.

## Task 1: Define worker contracts and DTOs

**Files:**
- Create: `worker/services/worker_contracts.py`
- Test: `worker/tests/test_worker_use_cases.py`

- [ ] **Step 1: Write the failing contract-oriented orchestration test**

```python
from __future__ import annotations

from dataclasses import dataclass
import unittest

from worker.services.worker_use_cases import DraftGenerationUseCase


@dataclass
class _FakeContext:
    session_id: str


class _DraftUseCaseContractTests(unittest.TestCase):
    def test_runs_injected_draft_stages_and_returns_persisted_result(self) -> None:
        events: list[str] = []

        class FakeUow:
            def __enter__(self):
                events.append("uow_enter")
                return self

            def __exit__(self, exc_type, exc, tb):
                events.append("uow_exit")
                return False

            @property
            def session(self):
                return "db"

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

        use_case = DraftGenerationUseCase(
            uow_factory=lambda: FakeUow(),
            repository=FakeRepository(),
            context_loader=lambda db, session: _FakeContext(session_id="session-1"),
            stages=[FakeStage("segment"), FakeStage("group")],
            persister=FakePersister(),
            failure_recorder=None,
        )

        result = use_case.run(session_id="session-1")

        self.assertEqual(result["steps_created"], 3)
        self.assertEqual(events, ["uow_enter", "load:session-1", "segment", "group", "persist", "uow_exit"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest worker.tests.test_worker_use_cases -v`
Expected: FAIL with `ModuleNotFoundError` or missing `DraftGenerationUseCase` / contract definitions.

- [ ] **Step 3: Create the contract module with narrow interfaces**

```python
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class WorkerUnitOfWork(Protocol):
    session: Any

    def __enter__(self) -> "WorkerUnitOfWork": ...
    def __exit__(self, exc_type, exc, tb) -> bool | None: ...


WorkerUnitOfWorkFactory = Callable[[], WorkerUnitOfWork]


class DraftSessionRepository(Protocol):
    def load_draft_session(self, db: Any, session_id: str) -> Any: ...


class DraftContextLoader(Protocol):
    def __call__(self, db: Any, session: Any) -> Any: ...


class DraftPipelineStage(Protocol):
    def run(self, db: Any, context: Any) -> None: ...


class DraftResultPersister(Protocol):
    def persist(self, db: Any, context: Any) -> dict[str, int | str]: ...


class FailureRecorder(Protocol):
    def record_failure(self, db: Any, session_id: str, detail: str | None = None) -> None: ...


class ScreenshotContextBuilder(Protocol):
    def build(self, db: Any, session: Any) -> Any: ...


class ScreenshotPipelineStage(Protocol):
    def run(self, db: Any, context: Any) -> None: ...


class ScreenshotResultPersister(Protocol):
    def persist(self, db: Any, context: Any) -> dict[str, int | str]: ...


class ScreenshotLockManager(Protocol):
    def release(self, session_id: str) -> None: ...


@dataclass(slots=True)
class DraftPipelineDefinition:
    context_loader: DraftContextLoader
    stages: Sequence[DraftPipelineStage]
    persister: DraftResultPersister
```

- [ ] **Step 4: Create the minimal use-case module skeleton needed by the test**

```python
from __future__ import annotations

from collections.abc import Sequence

from worker.services.worker_contracts import (
    DraftContextLoader,
    DraftPipelineStage,
    DraftResultPersister,
    DraftSessionRepository,
    FailureRecorder,
    WorkerUnitOfWorkFactory,
)


class DraftGenerationUseCase:
    def __init__(
        self,
        *,
        uow_factory: WorkerUnitOfWorkFactory,
        repository: DraftSessionRepository,
        context_loader: DraftContextLoader,
        stages: Sequence[DraftPipelineStage],
        persister: DraftResultPersister,
        failure_recorder: FailureRecorder | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._repository = repository
        self._context_loader = context_loader
        self._stages = list(stages)
        self._persister = persister
        self._failure_recorder = failure_recorder

    def run(self, *, session_id: str) -> dict[str, int | str]:
        with self._uow_factory() as uow:
            session = self._repository.load_draft_session(uow.session, session_id)
            context = self._context_loader(uow.session, session)
            for stage in self._stages:
                stage.run(uow.session, context)
            return self._persister.persist(uow.session, context)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m unittest worker.tests.test_worker_use_cases -v`
Expected: PASS for the draft use-case orchestration test.

- [ ] **Step 6: Commit**

```bash
git add worker/services/worker_contracts.py worker/services/worker_use_cases.py worker/tests/test_worker_use_cases.py
git commit -m "Introduce worker orchestration contracts"
```

## Task 2: Introduce worker unit-of-work and repositories

**Files:**
- Create: `worker/services/worker_uow.py`
- Create: `worker/services/worker_repositories.py`
- Modify: `worker/services/worker_use_cases.py`
- Test: `worker/tests/test_worker_use_cases.py`

- [ ] **Step 1: Add a failing test for failure recording and repository-backed session loading**

```python
class _DraftFailureTests(unittest.TestCase):
    def test_records_failure_when_stage_raises(self) -> None:
        events: list[str] = []

        class FakeUow:
            def __enter__(self):
                self.session = "db"
                return self

            def __exit__(self, exc_type, exc, tb):
                events.append(f"uow_exit:{exc_type.__name__ if exc_type else 'none'}")
                return False

        class FakeRepository:
            def load_draft_session(self, db, session_id: str):
                return object()

        class BoomStage:
            def run(self, db, context) -> None:
                raise RuntimeError("boom")

        class FakeFailureRecorder:
            def record_failure(self, db, session_id: str, detail: str | None = None) -> None:
                events.append(f"failure:{session_id}:{detail}")

        use_case = DraftGenerationUseCase(
            uow_factory=lambda: FakeUow(),
            repository=FakeRepository(),
            context_loader=lambda db, session: _FakeContext(session_id="session-9"),
            stages=[BoomStage()],
            persister=None,
            failure_recorder=FakeFailureRecorder(),
        )

        with self.assertRaises(RuntimeError):
            use_case.run(session_id="session-9")

        self.assertEqual(events, ["failure:session-9:boom", "uow_exit:RuntimeError"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest worker.tests.test_worker_use_cases -v`
Expected: FAIL because `DraftGenerationUseCase` does not yet call `failure_recorder`.

- [ ] **Step 3: Implement SQLAlchemy-backed unit-of-work and repository helpers**

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from worker.bootstrap import get_db_session


class SqlAlchemyWorkerUnitOfWork:
    def __init__(self, session_factory=get_db_session) -> None:
        self._session_factory = session_factory
        self.session = None

    def __enter__(self) -> "SqlAlchemyWorkerUnitOfWork":
        self.session = self._session_factory()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        assert self.session is not None
        self.session.close()
        return False


class SqlAlchemyDraftSessionRepository:
    def load_draft_session(self, db, session_id: str) -> DraftSessionModel:
        statement = (
            select(DraftSessionModel)
            .where(DraftSessionModel.id == session_id)
            .options(
                selectinload(DraftSessionModel.artifacts).selectinload(ArtifactModel.meeting),
                selectinload(DraftSessionModel.process_steps),
                selectinload(DraftSessionModel.process_notes),
            )
        )
        session = db.execute(statement).scalar_one_or_none()
        if session is None:
            raise ValueError(f"Draft session '{session_id}' was not found.")
        return session
```

- [ ] **Step 4: Update the use case to handle failure recording before re-raising**

```python
    def run(self, *, session_id: str) -> dict[str, int | str]:
        with self._uow_factory() as uow:
            try:
                session = self._repository.load_draft_session(uow.session, session_id)
                context = self._context_loader(uow.session, session)
                for stage in self._stages:
                    stage.run(uow.session, context)
                return self._persister.persist(uow.session, context)
            except Exception as exc:
                if self._failure_recorder is not None:
                    self._failure_recorder.record_failure(uow.session, session_id, str(exc))
                raise
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m unittest worker.tests.test_worker_use_cases -v`
Expected: PASS for orchestration and failure tests.

- [ ] **Step 6: Commit**

```bash
git add worker/services/worker_uow.py worker/services/worker_repositories.py worker/services/worker_use_cases.py worker/tests/test_worker_use_cases.py
git commit -m "Add worker unit of work and repositories"
```

## Task 3: Extract screenshot context building

**Files:**
- Create: `worker/services/screenshot_context_builder.py`
- Modify: `worker/services/screenshot_generation_worker.py`
- Test: `worker/tests/test_screenshot_context_builder.py`

- [ ] **Step 1: Write the failing screenshot-context builder tests**

```python
from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from worker.services.screenshot_context_builder import DefaultScreenshotContextBuilder


class ScreenshotContextBuilderTests(unittest.TestCase):
    def test_raises_when_no_persisted_steps_exist(self) -> None:
        builder = DefaultScreenshotContextBuilder()
        session = SimpleNamespace(id="session-1", artifacts=[SimpleNamespace(kind="transcript"), SimpleNamespace(kind="video")], process_steps=[])

        with self.assertRaisesRegex(ValueError, "No generated process steps"):
            builder.build(db=SimpleNamespace(), session=session)

    def test_removes_screenshot_evidence_from_step_records(self) -> None:
        builder = DefaultScreenshotContextBuilder()
        step = SimpleNamespace(
            id="step-1",
            process_group_id="group-1",
            meeting_id="meeting-1",
            step_number=1,
            application_name="App",
            action_text="Click Save",
            source_data_note="",
            timestamp="00:00:05",
            start_timestamp="00:00:05",
            end_timestamp="00:00:06",
            supporting_transcript_text="Click Save",
            screenshot_id="old",
            confidence=0.9,
            evidence_references=json.dumps(
                [
                    {"kind": "transcript", "artifact_id": "tx-1"},
                    {"kind": "screenshot", "artifact_id": "ss-1"},
                ]
            ),
            edited_by_ba=False,
            source_transcript_artifact_id=None,
        )
        session = SimpleNamespace(
            id="session-1",
            artifacts=[
                SimpleNamespace(id="tx-1", kind="transcript", meeting_id="meeting-1", created_at=1),
                SimpleNamespace(id="vid-1", kind="video", meeting_id="meeting-1", created_at=1),
            ],
            process_steps=[step],
            process_notes=[],
        )

        context = builder.build(db=SimpleNamespace(execute=lambda *args, **kwargs: None, commit=lambda: None), session=session)

        self.assertEqual(json.loads(step.evidence_references), [{"kind": "transcript", "artifact_id": "tx-1"}])
        self.assertEqual(context.all_steps[0]["_transcript_artifact_id"], "tx-1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest worker.tests.test_screenshot_context_builder -v`
Expected: FAIL with missing builder module.

- [ ] **Step 3: Move `_prepare_context()` and helper methods into a dedicated builder**

```python
from __future__ import annotations

import json

from worker.services.draft_generation_stage_context import DraftGenerationContext


class DefaultScreenshotContextBuilder:
    def build(self, db, session) -> DraftGenerationContext:
        transcript_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "transcript"]
        video_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "video"]
        if not transcript_artifacts:
            raise ValueError("No transcript artifacts found for screenshot generation.")
        if not video_artifacts:
            raise ValueError("No video artifacts found for screenshot generation.")
        if not session.process_steps:
            raise ValueError("No generated process steps are available for screenshot generation.")

        step_candidates: list[dict] = []
        steps_by_transcript: dict[str, list[dict]] = {}
        transcripts_by_meeting = self._transcripts_by_meeting(transcript_artifacts)
        preferred_transcripts_by_group_meeting = self._preferred_transcripts_by_group_meeting(session.process_steps)

        for step in sorted(session.process_steps, key=lambda item: item.step_number):
            evidence_references = self._strip_screenshot_evidence(step.evidence_references)
            step.evidence_references = json.dumps(evidence_references)
            step.screenshot_id = ""
            transcript_artifact_id = self._resolve_transcript_artifact_id(
                persisted_source_transcript_artifact_id=getattr(step, "source_transcript_artifact_id", None),
                evidence_references=evidence_references,
                meeting_id=step.meeting_id,
                process_group_id=step.process_group_id,
                transcripts_by_meeting=transcripts_by_meeting,
                preferred_transcripts_by_group_meeting=preferred_transcripts_by_group_meeting,
            )
            candidate = {
                "id": step.id,
                "process_group_id": step.process_group_id,
                "meeting_id": step.meeting_id,
                "step_number": step.step_number,
                "application_name": step.application_name,
                "action_text": step.action_text,
                "_transcript_artifact_id": transcript_artifact_id,
                "evidence_references": json.dumps(evidence_references),
            }
            step_candidates.append(candidate)
            if transcript_artifact_id:
                steps_by_transcript.setdefault(transcript_artifact_id, []).append(candidate)

        db.commit()
        context = DraftGenerationContext(
            session_id=session.id,
            session=session,
            transcript_artifacts=transcript_artifacts,
            video_artifacts=video_artifacts,
            all_steps=step_candidates,
            all_notes=[],
            steps_by_transcript=steps_by_transcript,
        )
        context.persisted_step_models = list(sorted(session.process_steps, key=lambda item: item.step_number))
        return context
```

- [ ] **Step 4: Run the builder tests to verify they pass**

Run: `python -m unittest worker.tests.test_screenshot_context_builder -v`
Expected: PASS for validation and evidence-cleanup coverage.

- [ ] **Step 5: Commit**

```bash
git add worker/services/screenshot_context_builder.py worker/tests/test_screenshot_context_builder.py
git commit -m "Extract screenshot context builder"
```

## Task 4: Add pipeline runners and complete both use cases

**Files:**
- Create: `worker/services/worker_pipeline.py`
- Modify: `worker/services/worker_use_cases.py`
- Test: `worker/tests/test_worker_use_cases.py`

- [ ] **Step 1: Add failing tests for screenshot lock release and screenshot stage orchestration**

```python
class _ScreenshotUseCaseTests(unittest.TestCase):
    def test_releases_lock_after_screenshot_run(self) -> None:
        events: list[str] = []

        class FakeUow:
            def __enter__(self):
                self.session = "db"
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
                return _FakeContext(session_id="session-4")

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

        use_case = ScreenshotGenerationUseCase(
            uow_factory=lambda: FakeUow(),
            repository=FakeRepository(),
            context_builder=FakeBuilder(),
            stages=[FakeStage()],
            persister=FakePersister(),
            lock_manager=FakeLockManager(),
        )

        result = use_case.run(session_id="session-4")

        self.assertEqual(result["screenshots_created"], 2)
        self.assertEqual(events, ["load:session-4", "build", "derive", "persist", "release:session-4", "uow_exit"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest worker.tests.test_worker_use_cases -v`
Expected: FAIL because `ScreenshotGenerationUseCase` does not exist yet.

- [ ] **Step 3: Add a reusable pipeline runner and screenshot use case**

```python
from __future__ import annotations

from collections.abc import Sequence


class OrderedStageRunner:
    def __init__(self, stages: Sequence[object]) -> None:
        self._stages = list(stages)

    def run(self, db, context) -> None:
        for stage in self._stages:
            stage.run(db, context)
```

```python
class ScreenshotGenerationUseCase:
    def __init__(
        self,
        *,
        uow_factory: WorkerUnitOfWorkFactory,
        repository: DraftSessionRepository,
        context_builder: ScreenshotContextBuilder,
        stages: Sequence[ScreenshotPipelineStage],
        persister: ScreenshotResultPersister,
        lock_manager: ScreenshotLockManager,
    ) -> None:
        self._uow_factory = uow_factory
        self._repository = repository
        self._context_builder = context_builder
        self._stages = OrderedStageRunner(stages)
        self._persister = persister
        self._lock_manager = lock_manager

    def run(self, *, session_id: str) -> dict[str, int | str]:
        try:
            with self._uow_factory() as uow:
                session = self._repository.load_draft_session(uow.session, session_id)
                context = self._context_builder.build(uow.session, session)
                self._stages.run(uow.session, context)
                return self._persister.persist(uow.session, context)
        finally:
            self._lock_manager.release(session_id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest worker.tests.test_worker_use_cases -v`
Expected: PASS for draft and screenshot orchestration tests.

- [ ] **Step 5: Commit**

```bash
git add worker/services/worker_pipeline.py worker/services/worker_use_cases.py worker/tests/test_worker_use_cases.py
git commit -m "Implement worker use case orchestration"
```

## Task 5: Add composition root and convert worker adapters

**Files:**
- Create: `worker/services/worker_composition.py`
- Modify: `worker/services/draft_generation_worker.py`
- Modify: `worker/services/screenshot_generation_worker.py`
- Modify: `worker/tests/test_draft_generation_worker.py`

- [ ] **Step 1: Write failing adapter tests that assert delegation to composed use cases**

```python
from unittest.mock import Mock, patch
import unittest

from worker.services.draft_generation_worker import DraftGenerationWorker


class DraftGenerationWorkerTests(unittest.TestCase):
    @patch("worker.services.draft_generation_worker.build_draft_generation_use_case")
    def test_delegates_run_to_composed_use_case(self, build_use_case_mock) -> None:
        use_case = Mock()
        use_case.run.return_value = {"session_id": "session-1", "steps_created": 2}
        build_use_case_mock.return_value = use_case

        worker = DraftGenerationWorker(task_id="task-1")
        result = worker.run("session-1")

        build_use_case_mock.assert_called_once_with(task_id="task-1")
        use_case.run.assert_called_once_with(session_id="session-1")
        self.assertEqual(result["session_id"], "session-1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest worker.tests.test_draft_generation_worker -v`
Expected: FAIL because the worker still manages stages directly.

- [ ] **Step 3: Add the composition root and thin worker adapters**

```python
from worker.services.draft_generation_stage_services import (
    CanonicalMergeStage,
    DiagramAssemblyStage,
    EvidenceSegmentationStage,
    FailureStage,
    PersistenceStage,
    ProcessGroupingStage,
    SessionPreparationStage,
    TranscriptInterpretationStage,
)
from worker.services.screenshot_context_builder import DefaultScreenshotContextBuilder
from worker.services.worker_repositories import SqlAlchemyDraftSessionRepository
from worker.services.worker_uow import SqlAlchemyWorkerUnitOfWork
from worker.services.worker_use_cases import DraftGenerationUseCase, ScreenshotGenerationUseCase


def build_draft_generation_use_case(*, task_id: str | None) -> DraftGenerationUseCase:
    return DraftGenerationUseCase(
        uow_factory=SqlAlchemyWorkerUnitOfWork,
        repository=SqlAlchemyDraftSessionRepository(),
        context_loader=SessionPreparationStage().load_and_prepare,
        stages=[
            EvidenceSegmentationStage(),
            TranscriptInterpretationStage(),
            ProcessGroupingStage(),
            CanonicalMergeStage(),
            DiagramAssemblyStage(),
        ],
        persister=DraftPersistenceAdapter(PersistenceStage()),
        failure_recorder=FailureRecorderAdapter(FailureStage()),
    )
```

```python
class DraftGenerationWorker:
    def __init__(self, task_id: str | None = None, use_case=None) -> None:
        self.task_id = task_id
        self._use_case = use_case or build_draft_generation_use_case(task_id=task_id)

    def run(self, session_id: str) -> dict[str, int | str]:
        return self._use_case.run(session_id=session_id)
```

```python
class ScreenshotGenerationWorker:
    def __init__(self, task_id: str | None = None, use_case=None) -> None:
        self.task_id = task_id
        self._use_case = use_case or build_screenshot_generation_use_case(task_id=task_id)

    def run(self, session_id: str) -> dict[str, int | str]:
        return self._use_case.run(session_id=session_id)
```

- [ ] **Step 4: Run the adapter tests to verify they pass**

Run: `python -m unittest worker.tests.test_draft_generation_worker -v`
Expected: PASS with delegation-based assertions.

- [ ] **Step 5: Commit**

```bash
git add worker/services/worker_composition.py worker/services/draft_generation_worker.py worker/services/screenshot_generation_worker.py worker/tests/test_draft_generation_worker.py
git commit -m "Convert workers to use case adapters"
```

## Task 6: Remove default stage wiring from stage implementations

**Files:**
- Modify: `worker/services/draft_generation_stage_services.py`
- Modify: `worker/services/worker_composition.py`
- Test: `worker/tests/test_worker_use_cases.py`
- Test: `worker/tests/test_draft_generation_worker.py`

- [ ] **Step 1: Add a failing test to assert composition root owns default stage wiring**

```python
class CompositionTests(unittest.TestCase):
    def test_builds_draft_use_case_with_injected_stage_instances(self) -> None:
        use_case = build_draft_generation_use_case(task_id="task-7")
        self.assertGreater(len(use_case._stages._stages), 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest worker.tests.test_worker_use_cases worker.tests.test_draft_generation_worker -v`
Expected: FAIL because stage defaults are still partially hidden inside stage implementations.

- [ ] **Step 3: Move default collaborator creation out of stages and into composition**

```python
def build_default_evidence_segmentation_stage() -> EvidenceSegmentationStage:
    registry = WorkflowIntelligenceStrategyRegistry()
    registry.register_segmenter(ParagraphTranscriptSegmentationStrategy.strategy_key, ParagraphTranscriptSegmentationStrategy)
    registry.register_enricher(AISemanticEnrichmentStrategy.strategy_key, AISemanticEnrichmentStrategy)
    registry.register_enricher(HeuristicSemanticEnrichmentStrategy.strategy_key, HeuristicSemanticEnrichmentStrategy)
    registry.register_boundary_detector(AIWorkflowBoundaryStrategy.strategy_key, AIWorkflowBoundaryStrategy)
    service = EvidenceSegmentationService(
        strategy_set=registry.create_strategy_set(
            segmenter_key=ParagraphTranscriptSegmentationStrategy.strategy_key,
            enricher_key=AISemanticEnrichmentStrategy.strategy_key,
            boundary_detector_key=AIWorkflowBoundaryStrategy.strategy_key,
        )
    )
    return EvidenceSegmentationStage(segmentation_service=service)
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run: `python -m unittest worker.tests.test_worker_use_cases worker.tests.test_draft_generation_worker -v`
Expected: PASS with composition-controlled dependency wiring.

- [ ] **Step 5: Commit**

```bash
git add worker/services/draft_generation_stage_services.py worker/services/worker_composition.py worker/tests/test_worker_use_cases.py worker/tests/test_draft_generation_worker.py
git commit -m "Move worker stage wiring into composition root"
```

## Task 7: Final regression verification

**Files:**
- Modify: `worker/tests/test_worker_use_cases.py`
- Modify: `worker/tests/test_screenshot_context_builder.py`
- Modify: `worker/tests/test_draft_generation_worker.py`

- [ ] **Step 1: Run focused unit tests**

Run: `python -m unittest worker.tests.test_worker_use_cases worker.tests.test_screenshot_context_builder worker.tests.test_draft_generation_worker -v`
Expected: PASS.

- [ ] **Step 2: Run existing worker regression tests touched by orchestration dependencies**

Run: `python -m unittest worker.tests.test_evidence_segmentation_service worker.tests.test_process_grouping_service worker.tests.test_workflow_strategy_interfaces -v`
Expected: PASS.

- [ ] **Step 3: Run type-oriented verification already used in the repo**

Run: `python -m compileall worker`
Expected: `Listing 'worker'...` with no syntax errors.

- [ ] **Step 4: Review git diff for compatibility constraints**

Run: `git diff -- worker/services worker/tests worker/tasks`
Expected: Thin adapters, new contracts/use cases, extracted screenshot builder, and no Celery task-name changes.

- [ ] **Step 5: Commit**

```bash
git add worker/services worker/tests
git commit -m "Refactor worker orchestration around contracts"
```
