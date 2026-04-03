from __future__ import annotations

from typing import TYPE_CHECKING

from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.services.ai_skills.semantic_enrichment.schemas import SemanticEnrichmentRequest
from worker.services.ai_skills.workflow_boundary_detection.schemas import WorkflowBoundaryDetectionRequest

if TYPE_CHECKING:
    from worker.services.ai_transcript_interpreter import WorkflowBoundaryInterpretation, WorkflowSemanticEnrichmentInterpretation
    from worker.services.ai_skills.semantic_enrichment.schemas import SemanticEnrichmentResponse
    from worker.services.ai_skills.workflow_boundary_detection.schemas import WorkflowBoundaryDetectionResponse


class InterpreterSemanticEnrichmentSkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.skill_id = "semantic_enrichment_interpreter_adapter"
        self.version = "interpreter-adapter"

    def run(self, input: SemanticEnrichmentRequest) -> WorkflowSemanticEnrichmentInterpretation | SemanticEnrichmentResponse | None:
        return self._interpreter.enrich_workflow_segment(
            transcript_name=input.transcript_name,
            segment_text=input.segment_text,
            segment_context=input.segment_context,
        )


class InterpreterWorkflowBoundarySkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.skill_id = "workflow_boundary_interpreter_adapter"
        self.version = "interpreter-adapter"

    def run(self, input: WorkflowBoundaryDetectionRequest) -> WorkflowBoundaryInterpretation | WorkflowBoundaryDetectionResponse | None:
        return self._interpreter.classify_workflow_boundary(
            left_segment=input.left_segment,
            right_segment=input.right_segment,
        )


__all__ = [
    "InterpreterSemanticEnrichmentSkill",
    "InterpreterWorkflowBoundarySkill",
]
