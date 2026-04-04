from __future__ import annotations

from app.core.observability import get_logger
from app.models.action_log import ActionLogModel
from app.services.job_dispatcher import JobDispatcherService
from worker import bootstrap as _bootstrap  # noqa: F401
from worker.pipeline.stages.input_stages import EvidenceSegmentationStage, SessionPreparationStage, TranscriptInterpretationStage
from worker.pipeline.stages.output_stages import DiagramAssemblyStage, FailureStage, PersistenceStage, ScreenshotDerivationStage
from worker.pipeline.stages.persistence_screenshots import persist_step_screenshots
from worker.pipeline.stages.process_stages import CanonicalMergeStage, ProcessGroupingStage
from worker.grouping.segmentation_service import (
    AISemanticEnrichmentStrategy,
    AIWorkflowBoundaryStrategy,
    EvidenceSegmentationService,
    HeuristicSemanticEnrichmentStrategy,
    ParagraphTranscriptSegmentationStrategy,
)
from worker.screenshot.context_builder import DefaultScreenshotContextBuilder
from worker.pipeline.repositories import SqlAlchemyDraftSessionRepository
from worker.pipeline.uow import SqlAlchemyWorkerUnitOfWork
from worker.pipeline.use_cases import DraftGenerationUseCase, ScreenshotGenerationUseCase
from worker.grouping.strategy_registry import WorkflowIntelligenceStrategyRegistry

logger = get_logger(__name__)


def build_default_evidence_segmentation_stage() -> EvidenceSegmentationStage:
    registry = WorkflowIntelligenceStrategyRegistry()
    registry.register_segmenter(ParagraphTranscriptSegmentationStrategy.strategy_key, ParagraphTranscriptSegmentationStrategy)
    registry.register_enricher(AISemanticEnrichmentStrategy.strategy_key, AISemanticEnrichmentStrategy)
    registry.register_enricher(HeuristicSemanticEnrichmentStrategy.strategy_key, HeuristicSemanticEnrichmentStrategy)
    registry.register_boundary_detector(AIWorkflowBoundaryStrategy.strategy_key, AIWorkflowBoundaryStrategy)
    segmentation_service = EvidenceSegmentationService(
        strategy_set=registry.create_strategy_set(
            segmenter_key=ParagraphTranscriptSegmentationStrategy.strategy_key,
            enricher_key=AISemanticEnrichmentStrategy.strategy_key,
            boundary_detector_key=AIWorkflowBoundaryStrategy.strategy_key,
        )
    )
    return EvidenceSegmentationStage(segmentation_service=segmentation_service)


class DraftPersistenceAdapter:
    def __init__(self, stage: PersistenceStage | None = None) -> None:
        self._stage = stage or PersistenceStage()

    def persist(self, db, context) -> dict[str, int | str]:  # type: ignore[no-untyped-def]
        return self._stage.run(db, context)


class FailureRecorderAdapter:
    def __init__(self, stage: FailureStage | None = None) -> None:
        self._stage = stage or FailureStage()

    def record_failure(self, db, session_id: str, detail: str | None = None) -> None:  # type: ignore[no-untyped-def]
        self._stage.mark_failed(db, session_id, detail)


class ScreenshotLockManagerAdapter:
    def __init__(self, dispatcher: JobDispatcherService | None = None) -> None:
        self._dispatcher = dispatcher or JobDispatcherService()

    def release(self, session_id: str) -> None:
        self._dispatcher.release_screenshot_generation_lock(session_id)


class ScreenshotPersistenceAdapter:
    """Persist screenshot outputs for the screenshot-only pipeline.

    SRP fix: action logging extracted to ScreenshotActionLogStage.
    This class has exactly one job: call persist_step_screenshots.
    """

    def __init__(self, stage: PersistenceStage | None = None) -> None:
        self._stage = stage or PersistenceStage()

    def persist(self, db, context) -> dict[str, int | str]:  # type: ignore[no-untyped-def]
        persist_step_screenshots(db, step_models=context.persisted_step_models, step_candidates=context.all_steps)
        selected_screenshot_count = sum(len(step.get("_derived_screenshots", [])) for step in context.all_steps)
        result = {
            "session_id": context.session_id,
            "screenshots_created": selected_screenshot_count,
            "steps_updated": len(context.persisted_step_models),
        }
        logger.info("Persisted generated screenshots", extra={"event": "screenshot_generation.persisted", **result})
        return result


class ScreenshotActionLogStage:
    """Post-persistence audit log stage for the screenshot pipeline.

    SRP: writes one ActionLogModel entry and commits. Separated from
    ScreenshotPersistenceAdapter so each class has exactly one concern.
    """

    def run(self, db, context) -> None:  # type: ignore[no-untyped-def]
        selected_screenshot_count = sum(len(step.get("_derived_screenshots", [])) for step in context.all_steps)
        db.add(
            ActionLogModel(
                session_id=context.session_id,
                event_type="screenshots_generated",
                title="Screenshots ready",
                detail=f"{selected_screenshot_count} screenshots generated for canonical steps.",
                actor="system",
            )
        )
        db.commit()


def build_draft_generation_use_case(*, task_id: str | None) -> DraftGenerationUseCase:
    return DraftGenerationUseCase(
        uow_factory=SqlAlchemyWorkerUnitOfWork,
        repository=SqlAlchemyDraftSessionRepository(),
        context_loader=SessionPreparationStage().load_and_prepare,
        stages=[
            build_default_evidence_segmentation_stage(),
            TranscriptInterpretationStage(),
            ProcessGroupingStage(),
            CanonicalMergeStage(),
            DiagramAssemblyStage(),
        ],
        persister=DraftPersistenceAdapter(),
        failure_recorder=FailureRecorderAdapter(),
    )


def build_screenshot_generation_use_case(*, task_id: str | None) -> ScreenshotGenerationUseCase:
    return ScreenshotGenerationUseCase(
        uow_factory=SqlAlchemyWorkerUnitOfWork,
        repository=SqlAlchemyDraftSessionRepository(),
        context_builder=DefaultScreenshotContextBuilder(),
        stages=[ScreenshotDerivationStage(), ScreenshotActionLogStage()],
        persister=ScreenshotPersistenceAdapter(),
        lock_manager=ScreenshotLockManagerAdapter(),
    )
