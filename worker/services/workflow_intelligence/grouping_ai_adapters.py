from __future__ import annotations

from typing import TYPE_CHECKING

from worker.services.ai_skills.process_summary_generation.schemas import ProcessSummaryGenerationRequest
from worker.services.ai_skills.workflow_capability_tagging.schemas import WorkflowCapabilityTaggingRequest
from worker.services.ai_skills.workflow_group_match.schemas import WorkflowGroupMatchRequest
from worker.services.ai_skills.workflow_title_resolution.schemas import WorkflowTitleResolutionRequest
from worker.services.ai_transcript.interpreter import (
    AITranscriptInterpreter,
    WorkflowGroupMatchInterpretation,
    WorkflowTitleInterpretation,
)

if TYPE_CHECKING:
    from worker.services.ai_skills.process_summary_generation.schemas import ProcessSummaryGenerationResponse
    from worker.services.ai_skills.workflow_capability_tagging.schemas import WorkflowCapabilityTaggingResponse
    from worker.services.ai_skills.workflow_group_match.schemas import WorkflowGroupMatchResponse
    from worker.services.ai_skills.workflow_title_resolution.schemas import WorkflowTitleResolutionResponse
    from worker.services.ai_transcript.interpreter import ProcessSummaryInterpretation, WorkflowCapabilityInterpretation


class InterpreterWorkflowTitleResolutionSkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.version = "interpreter-adapter"

    def run(self, input: WorkflowTitleResolutionRequest) -> WorkflowTitleInterpretation | WorkflowTitleResolutionResponse | None:
        return self._interpreter.resolve_workflow_title(
            transcript_name=input.transcript_name,
            workflow_summary=input.workflow_summary,
        )


class InterpreterWorkflowGroupMatchSkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.version = "interpreter-adapter"

    def run(self, input: WorkflowGroupMatchRequest) -> WorkflowGroupMatchInterpretation | WorkflowGroupMatchResponse | None:
        return self._interpreter.match_existing_workflow_group(
            transcript_name=input.transcript_name,
            workflow_summary=input.workflow_summary,
            existing_groups=input.existing_groups,
        )


class InterpreterProcessSummarySkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.version = "interpreter-adapter"

    def run(self, input: ProcessSummaryGenerationRequest) -> ProcessSummaryInterpretation | ProcessSummaryGenerationResponse | None:
        return self._interpreter.summarize_process_group(
            process_title=input.process_title,
            workflow_summary=input.workflow_summary,
            steps=input.steps,
            notes=input.notes,
            document_type=input.document_type,
        )


class InterpreterWorkflowCapabilityTaggingSkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.version = "interpreter-adapter"

    def run(self, input: WorkflowCapabilityTaggingRequest) -> WorkflowCapabilityInterpretation | WorkflowCapabilityTaggingResponse | None:
        return self._interpreter.classify_workflow_capabilities(
            process_title=input.process_title,
            workflow_summary=input.workflow_summary,
            document_type=input.document_type,
        )


__all__ = [
    "InterpreterProcessSummarySkill",
    "InterpreterWorkflowCapabilityTaggingSkill",
    "InterpreterWorkflowGroupMatchSkill",
    "InterpreterWorkflowTitleResolutionSkill",
]
