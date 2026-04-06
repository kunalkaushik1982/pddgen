from __future__ import annotations

from app.core.observability import get_logger
from app.models.action_log import ActionLogModel
from app.portability.job_messaging.redis_lock_adapter import build_redis_distributed_lock
from app.portability.job_messaging.screenshot_guard_adapter import build_screenshot_run_guard
from app.portability.job_messaging.wiring import build_default_job_enqueue_port
from app.services.action_log_service import ActionLogService
from app.services.job_dispatcher import JobDispatcherService
from app.services.process_group_service import ProcessGroupService
from app.services.step_extraction import StepExtractionService
from app.services.transcript_intelligence import TranscriptIntelligenceService
from sqlalchemy.orm import Session
from worker import bootstrap as _bootstrap  # noqa: F401
from worker.ai_skills.registry import build_default_ai_skill_registry
from worker.ai_skills.transcript_interpreter.interpreter import AITranscriptInterpreter
from worker.bootstrap import get_backend_settings
from worker.grouping.canonical_merge import CanonicalProcessMergeService
from worker.grouping.grouping_service import ProcessGroupingService
from worker.grouping.segmentation_ai_strategies import AISemanticEnrichmentStrategy, AIWorkflowBoundaryStrategy
from worker.grouping.segmentation_heuristics import (
    HeuristicSemanticEnrichmentStrategy,
    HeuristicWorkflowBoundaryStrategy,
    ParagraphTranscriptSegmentationStrategy,
)
from worker.grouping.segmentation_service import EvidenceSegmentationService
from worker.grouping.strategy_registry import WorkflowIntelligenceStrategyRegistry
from worker.media.transcript_normalizer import TranscriptNormalizer
from worker.media.video_frame_extractor import VideoFrameExtractor
from worker.pipeline.repositories import SqlAlchemyDraftSessionRepository
from worker.pipeline.stages.input_stages import EvidenceSegmentationStage, SessionPreparationStage
from worker.pipeline.stages.output_stages import DiagramAssemblyStage, FailureStage, PersistenceStage, ScreenshotDerivationStage
from worker.pipeline.stages.persistence_screenshots import persist_step_screenshots
from worker.pipeline.stages.process_stages import CanonicalMergeStage, ProcessGroupingStage
from worker.pipeline.stages.stage_context import DraftGenerationContext
from worker.pipeline.stages.transcript_interpretation import FallbackTranscriptExtractor, TranscriptInterpretationStage
from worker.pipeline.uow import SqlAlchemyWorkerUnitOfWork
from worker.pipeline.use_cases import DraftGenerationUseCase, ScreenshotGenerationUseCase
from worker.screenshot.context_builder import DefaultScreenshotContextBuilder

logger = get_logger(__name__)


def _worker_job_dispatcher_for_screenshot_lock_release() -> JobDispatcherService:
    """Dispatcher used only to release the screenshot run guard after the pipeline completes."""
    settings = get_backend_settings()
    lock = build_redis_distributed_lock(settings)
    return JobDispatcherService(
        enqueue=build_default_job_enqueue_port(settings),
        screenshot_run_guard=build_screenshot_run_guard(settings, lock=lock),
    )


def build_default_evidence_segmentation_stage() -> EvidenceSegmentationStage:
    interpreter = AITranscriptInterpreter()
    heuristic_enrich = HeuristicSemanticEnrichmentStrategy()
    heuristic_boundary = HeuristicWorkflowBoundaryStrategy()
    registry = WorkflowIntelligenceStrategyRegistry()
    registry.register_segmenter(ParagraphTranscriptSegmentationStrategy.strategy_key, ParagraphTranscriptSegmentationStrategy)
    registry.register_enricher(
        AISemanticEnrichmentStrategy.strategy_key,
        lambda: AISemanticEnrichmentStrategy(
            ai_transcript_interpreter=interpreter,
            fallback_strategy=heuristic_enrich,
        ),
    )
    registry.register_enricher(HeuristicSemanticEnrichmentStrategy.strategy_key, HeuristicSemanticEnrichmentStrategy)
    registry.register_boundary_detector(
        AIWorkflowBoundaryStrategy.strategy_key,
        lambda: AIWorkflowBoundaryStrategy(
            ai_transcript_interpreter=interpreter,
            fallback_strategy=heuristic_boundary,
        ),
    )
    segmentation_service = EvidenceSegmentationService(
        strategy_set=registry.create_strategy_set(
            segmenter_key=ParagraphTranscriptSegmentationStrategy.strategy_key,
            enricher_key=AISemanticEnrichmentStrategy.strategy_key,
            boundary_detector_key=AIWorkflowBoundaryStrategy.strategy_key,
        )
    )
    return EvidenceSegmentationStage(
        transcript_normalizer=TranscriptNormalizer(),
        segmentation_service=segmentation_service,
        action_log_service=ActionLogService(),
    )


class DraftPersistenceAdapter:
    def __init__(self, stage: PersistenceStage) -> None:
        self._stage = stage

    def persist(self, db: Session, context: DraftGenerationContext) -> dict[str, int | str]:
        return self._stage.run(db, context)


class FailureRecorderAdapter:
    def __init__(self, stage: FailureStage) -> None:
        self._stage = stage

    def record_failure(self, db: Session, session_id: str, detail: str | None = None) -> None:
        self._stage.mark_failed(db, session_id, detail)


class ScreenshotLockManagerAdapter:
    def __init__(self, dispatcher: JobDispatcherService) -> None:
        self._dispatcher = dispatcher

    def release(self, session_id: str) -> None:
        self._dispatcher.release_screenshot_generation_lock(session_id)


class ScreenshotPersistenceAdapter:
    """Persist screenshot outputs for the screenshot-only pipeline.

    Commits step↔screenshot rows and step field updates. Artifact rows are
    committed earlier inside ScreenshotDerivationStage; without a commit here,
    the session closes and those relation inserts roll back (UI shows no
    screenshots). Optional ``action_log_stage`` runs after commit so the audit
    log reflects persisted evidence links.
    """

    def __init__(self, *, action_log_stage: ScreenshotActionLogStage | None = None) -> None:
        self._action_log_stage = action_log_stage

    def persist(self, db: Session, context: DraftGenerationContext) -> dict[str, int | str]:
        persist_step_screenshots(db, step_models=context.persisted_step_models, step_candidates=context.all_steps)
        context.inputs.session.status = "review"
        db.commit()
        selected_screenshot_count = context.selected_screenshot_count
        result = {
            "session_id": context.inputs.session_id,
            "screenshots_created": selected_screenshot_count,
            "steps_updated": len(context.persisted_step_models),
        }
        logger.info("Persisted generated screenshots", extra={"event": "screenshot_generation.persisted", **result})
        if self._action_log_stage is not None:
            self._action_log_stage.run(db, context)
        return result


class ScreenshotActionLogStage:
    """Post-persistence audit log stage for the screenshot pipeline.

    SRP: writes one ActionLogModel entry and commits. Separated from
    ScreenshotPersistenceAdapter so each class has exactly one concern.
    """

    def run(self, db: Session, context: DraftGenerationContext) -> None:
        selected_screenshot_count = context.selected_screenshot_count
        db.add(
            ActionLogModel(
                session_id=context.inputs.session_id,
                event_type="screenshots_generated",
                title="Screenshots ready",
                detail=f"{selected_screenshot_count} screenshots generated for canonical steps.",
                actor="system",
            )
        )
        db.commit()


def build_draft_generation_use_case(*, task_id: str | None) -> DraftGenerationUseCase:
    ai_interpreter = AITranscriptInterpreter()
    action_log = ActionLogService()
    skill_registry = build_default_ai_skill_registry()
    return DraftGenerationUseCase(
        uow_factory=SqlAlchemyWorkerUnitOfWork,
        repository=SqlAlchemyDraftSessionRepository(),
        context_loader=SessionPreparationStage().load_and_prepare,
        stages=[
            build_default_evidence_segmentation_stage(),
            TranscriptInterpretationStage(
                transcript_normalizer=TranscriptNormalizer(),
                ai_transcript_interpreter=ai_interpreter,
                fallback_extractor=FallbackTranscriptExtractor(
                    step_extractor=StepExtractionService(),
                    note_extractor=TranscriptIntelligenceService(),
                ),
                action_log_service=action_log,
            ),
            ProcessGroupingStage(
                grouping_service=ProcessGroupingService(
                    process_group_service=ProcessGroupService(),
                    ai_transcript_interpreter=ai_interpreter,
                    ai_skill_registry=skill_registry,
                ),
                action_log_service=action_log,
            ),
            CanonicalMergeStage(
                merge_service=CanonicalProcessMergeService(),
                action_log_service=action_log,
            ),
            DiagramAssemblyStage(
                action_log_service=action_log,
                ai_skill_registry=skill_registry,
            ),
        ],
        persister=DraftPersistenceAdapter(PersistenceStage()),
        failure_recorder=FailureRecorderAdapter(FailureStage()),
    )


def build_screenshot_generation_use_case(*, task_id: str | None) -> ScreenshotGenerationUseCase:
    settings = get_backend_settings()
    return ScreenshotGenerationUseCase(
        uow_factory=SqlAlchemyWorkerUnitOfWork,
        repository=SqlAlchemyDraftSessionRepository(),
        context_builder=DefaultScreenshotContextBuilder(),
        stages=[
            ScreenshotDerivationStage(
                frame_extractor=VideoFrameExtractor(timeout_seconds=settings.screenshot_ffmpeg_timeout_seconds),
                action_log_service=ActionLogService(),
            ),
        ],
        persister=ScreenshotPersistenceAdapter(action_log_stage=ScreenshotActionLogStage()),
        lock_manager=ScreenshotLockManagerAdapter(
            _worker_job_dispatcher_for_screenshot_lock_release()
        ),
    )
