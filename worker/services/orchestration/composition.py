from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.observability import get_logger
from app.models.action_log import ActionLogModel
from app.services.job_dispatcher import JobDispatcherService
from worker.services.draft_generation.input_stages import EvidenceSegmentationStage, SessionPreparationStage, TranscriptInterpretationStage
from worker.services.draft_generation.diagram_assembly import DiagramAssemblyStage
from worker.services.draft_generation.failure import FailureStage
from worker.services.draft_generation.persistence import PersistenceStage
from worker.services.draft_generation.screenshot_derivation import ScreenshotDerivationStage
from worker.services.draft_generation.process_stages import CanonicalMergeStage, ProcessGroupingStage
from worker.services.workflow_intelligence.segmentation_service import (
    AISemanticEnrichmentStrategy,
    AIWorkflowBoundaryStrategy,
    EvidenceSegmentationService,
    HeuristicSemanticEnrichmentStrategy,
    ParagraphTranscriptSegmentationStrategy,
)
from worker.services.screenshot_generation.context_builder import DefaultScreenshotContextBuilder
from worker.services.orchestration.contracts import WorkerDbSession
from worker.services.orchestration.repositories import SqlAlchemyDraftSessionRepository
from worker.services.orchestration.uow import SqlAlchemyWorkerUnitOfWork
from worker.services.orchestration.use_cases import DraftGenerationUseCase, ScreenshotGenerationUseCase
from worker.services.workflow_intelligence.strategy_registry import WorkflowIntelligenceStrategyRegistry

if TYPE_CHECKING:
    from worker.services.draft_generation.stage_context import DraftGenerationContext

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

    def persist(self, db: WorkerDbSession, context: DraftGenerationContext) -> dict[str, int | str]:
        return self._stage.run(db, context)


class FailureRecorderAdapter:
    def __init__(self, stage: FailureStage | None = None) -> None:
        self._stage = stage or FailureStage()

    def record_failure(self, db: WorkerDbSession, session_id: str, detail: str | None = None) -> None:
        self._stage.mark_failed(db, session_id, detail)


class ScreenshotLockManagerAdapter:
    def __init__(self, dispatcher: JobDispatcherService | None = None) -> None:
        self._dispatcher = dispatcher or JobDispatcherService()

    def release(self, session_id: str) -> None:
        self._dispatcher.release_screenshot_generation_lock(session_id)


class ScreenshotPersistenceAdapter:
    def __init__(self, stage: PersistenceStage | None = None) -> None:
        self._stage = stage or PersistenceStage()

    def persist(self, db: WorkerDbSession, context: DraftGenerationContext) -> dict[str, int | str]:
        self._stage._persist_step_screenshots(db, context.persisted_step_models, context.all_steps)
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
        result = {
            "session_id": context.session_id,
            "screenshots_created": selected_screenshot_count,
            "steps_updated": len(context.persisted_step_models),
        }
        logger.info("Persisted generated screenshots", extra={"event": "screenshot_generation.persisted", **result})
        return result


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
        stages=[ScreenshotDerivationStage()],
        persister=ScreenshotPersistenceAdapter(),
        lock_manager=ScreenshotLockManagerAdapter(),
    )
