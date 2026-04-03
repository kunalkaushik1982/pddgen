from __future__ import annotations

import json

from app.core.observability import bind_log_context, get_logger

from app.services.action_log_service import ActionLogService
from worker.services.ai_skills.diagram_generation.schemas import DiagramGenerationRequest
from worker.services.ai_skills.registry import build_default_ai_skill_registry
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.services.draft_generation.stage_context import DraftGenerationContext
from worker.services.orchestration.contracts import WorkerDbSession

logger = get_logger(__name__)


class DiagramAssemblyStage:
    """Build diagram JSON payloads for the generated draft."""

    def __init__(self, *, ai_transcript_interpreter: AITranscriptInterpreter | None = None, action_log_service: ActionLogService | None = None) -> None:
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()
        self.action_log_service = action_log_service or ActionLogService()
        self._ai_skill_registry = build_default_ai_skill_registry()
        self._diagram_generation_skill = None

    def run(self, db: WorkerDbSession, context: DraftGenerationContext) -> None:
        with bind_log_context(stage="diagram_assembly"):
            self.action_log_service.record(
                db,
                session_id=context.session_id,
                event_type="generation_stage",
                title="Building diagram",
                detail="Generating the session diagram model.",
                actor="system",
            )
            db.commit()

            diagram_interpretation = None
            try:
                if self._diagram_generation_skill is None:
                    self._diagram_generation_skill = self._ai_skill_registry.create("diagram_generation")
                logger.info(
                    "Delegating diagram generation to AI skill.",
                    extra={
                        "skill_id": "diagram_generation",
                        "skill_version": getattr(self._diagram_generation_skill, "version", "unknown"),
                        "session_title": context.session.title,
                    },
                )
                diagram_interpretation = self._diagram_generation_skill.run(
                    DiagramGenerationRequest(
                        session_title=context.session.title,
                        diagram_type=context.session.diagram_type,
                        steps=context.all_steps,
                        notes=context.all_notes,
                    )
                )
            except Exception:
                diagram_interpretation = None

            if diagram_interpretation is None:
                context.overview_diagram_json = ""
                context.detailed_diagram_json = ""
                logger.info("Diagram assembly produced no renderable output", extra={"event": "draft_generation.stage_completed"})
                return

            context.overview_diagram_json = json.dumps(diagram_interpretation.overview)
            context.detailed_diagram_json = json.dumps(diagram_interpretation.detailed)
            logger.info("Diagram assembly completed", extra={"event": "draft_generation.stage_completed"})
