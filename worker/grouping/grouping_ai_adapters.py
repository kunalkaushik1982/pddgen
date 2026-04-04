from __future__ import annotations

from worker.ai_skills.transcript_interpreter.interpreter import AITranscriptInterpreter


class InterpreterWorkflowTitleResolutionSkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.version = "interpreter-adapter"

    def run(self, input):  # type: ignore[no-untyped-def]
        return self._interpreter.resolve_workflow_title(
            transcript_name=input.transcript_name,
            workflow_summary=input.workflow_summary,
        )


class InterpreterWorkflowGroupMatchSkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.version = "interpreter-adapter"

    def run(self, input):  # type: ignore[no-untyped-def]
        return self._interpreter.match_existing_workflow_group(
            transcript_name=input.transcript_name,
            workflow_summary=input.workflow_summary,
            existing_groups=input.existing_groups,
        )


class InterpreterProcessSummarySkill:
    def __init__(self, interpreter: AITranscriptInterpreter) -> None:
        self._interpreter = interpreter
        self.version = "interpreter-adapter"

    def run(self, input):  # type: ignore[no-untyped-def]
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

    def run(self, input):  # type: ignore[no-untyped-def]
        return self._interpreter.classify_workflow_capabilities(
            process_title=input.process_title,
            workflow_summary=input.workflow_summary,
            document_type=input.document_type,
        )
