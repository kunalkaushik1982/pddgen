from __future__ import annotations

from worker.ai_skills.transcript_interpreter.interpreter import AITranscriptInterpreter


class InterpreterSemanticEnrichmentSkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.skill_id = "semantic_enrichment_interpreter_adapter"
        self.version = "interpreter-adapter"

    def run(self, input):  # type: ignore[no-untyped-def]
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

    def run(self, input):  # type: ignore[no-untyped-def]
        return self._interpreter.classify_workflow_boundary(
            left_segment=input.left_segment,
            right_segment=input.right_segment,
        )
