from __future__ import annotations

import json

from app.core.observability import bind_log_context, get_logger
from app.services.platform.action_log_service import ActionLogService
from sqlalchemy.orm import Session
from worker.ai_skills.diagram_generation.schemas import DiagramGenerationRequest
from worker.ai_skills.registry import AISkillRegistry
from worker.pipeline.stages.stage_context import DraftGenerationContext

logger = get_logger(__name__)


class DiagramAssemblyStage:
    """Build diagram JSON payloads for the generated draft.

    DIP fix: AISkillRegistry is injected, not constructed internally.
    The stage depends on the AISkillRegistry abstraction, not a concrete build function.
    """

    def __init__(
        self,
        *,
        action_log_service: ActionLogService,
        ai_skill_registry: AISkillRegistry,
    ) -> None:
        self.action_log_service = action_log_service
        self._ai_skill_registry = ai_skill_registry
        # Skill is eagerly resolved from the registry to avoid thread-safety issues during lazy init.
        self._diagram_generation_skill = self._ai_skill_registry.create("diagram_generation")

    def run(self, db: Session, context: DraftGenerationContext) -> None:
        with bind_log_context(stage="diagram_assembly"):
            if not context.inputs.include_diagram:
                context.overview_diagram_json = ""
                context.detailed_diagram_json = ""
                logger.info(
                    "Diagram assembly skipped by run option.",
                    extra={"event": "draft_generation.stage_skipped", "include_diagram": False},
                )
                return
            self.action_log_service.record(
                db,
                session_id=context.inputs.session_id,
                event_type="generation_stage",
                title="Building diagram",
                detail="Generating the session diagram model.",
                actor="system",
            )
            db.commit()

            diagram_interpretation = None
            try:
                logger.info(
                    "Delegating diagram generation to AI skill.",
                    extra={
                        "skill_id": "diagram_generation",
                        "skill_version": getattr(self._diagram_generation_skill, "version", "unknown"),
                        "session_title": context.inputs.session.title,
                    },
                )
                diagram_interpretation = self._diagram_generation_skill.run(
                    DiagramGenerationRequest(
                        session_title=context.inputs.session.title,
                        diagram_type=context.inputs.session.diagram_type,
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
