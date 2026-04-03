from __future__ import annotations

import json
from collections import Counter
from typing import Any

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger
from app.services.action_log_service import ActionLogService
from worker.services.workflow_intelligence.canonical_merge import CanonicalProcessMergeService
from worker.services.draft_generation.stage_context import DraftGenerationContext
from worker.services.workflow_intelligence.grouping_service import ProcessGroupingService

logger = get_logger(__name__)


class CanonicalMergeStage:
    """Merge meeting-specific outputs into one current canonical process."""

    def __init__(self, *, merge_service: CanonicalProcessMergeService | None = None, action_log_service: ActionLogService | None = None) -> None:
        self.merge_service = merge_service or CanonicalProcessMergeService()
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db: Any, context: DraftGenerationContext) -> None:
        with bind_log_context(stage="canonical_merge"):
            self.action_log_service.record(
                db,
                session_id=context.session_id,
                event_type="generation_stage",
                title="Merging meeting evidence",
                detail=f"Canonicalizing process evidence from {len(context.transcript_artifacts)} transcript artifact(s).",
                actor="system",
            )
            db.commit()

            merge_result = self.merge_service.merge(
                transcript_artifacts=context.transcript_artifacts,
                process_groups=context.process_groups,
                steps_by_transcript=context.steps_by_transcript,
                notes_by_transcript=context.notes_by_transcript,
            )
            context.all_steps = merge_result.steps
            context.all_notes = merge_result.notes
            context.steps_by_transcript = merge_result.steps_by_transcript
            context.notes_by_transcript = merge_result.notes_by_transcript

            logger.info(
                "Canonical merge completed",
                extra={"event": "draft_generation.stage_completed", "canonical_step_count": len(context.all_steps), "canonical_note_count": len(context.all_notes)},
            )


class ProcessGroupingStage:
    """Assign transcript outputs into logical process groups before canonical merge."""

    def __init__(self, *, grouping_service: ProcessGroupingService | None = None, action_log_service: ActionLogService | None = None) -> None:
        self.grouping_service = grouping_service or ProcessGroupingService()
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db: Any, context: DraftGenerationContext) -> None:
        with bind_log_context(stage="process_grouping"):
            action_log = self.action_log_service.record(
                db,
                session_id=context.session_id,
                event_type="generation_stage",
                title="Grouping processes",
                detail=f"Clustering transcript evidence into logical process groups for {len(context.transcript_artifacts)} transcript artifact(s).",
                actor="system",
            )
            db.commit()

            grouping_result = self.grouping_service.assign_groups(
                db=db,
                session=context.session,
                transcript_artifacts=context.transcript_artifacts,
                steps_by_transcript=context.steps_by_transcript,
                notes_by_transcript=context.notes_by_transcript,
                evidence_segments=context.evidence_segments,
                workflow_boundary_decisions=context.workflow_boundary_decisions,
            )
            context.process_groups = grouping_result.process_groups
            ambiguous_assignments = [assignment for assignment in grouping_result.assignment_details if bool(assignment.get("is_ambiguous"))]
            grouping_decision_sources = Counter(str(assignment.get("decision_source", "unknown") or "unknown") for assignment in grouping_result.assignment_details)
            grouping_conflicts = Counter("conflict" if bool(assignment.get("conflict_detected")) else "non_conflict" for assignment in grouping_result.assignment_details)
            action_log.metadata_json = json.dumps(
                {
                    "conclusion": f"Created {len(grouping_result.process_groups)} process group(s) from {len(context.transcript_artifacts)} transcript artifact(s). {len(ambiguous_assignments)} assignment(s) were marked ambiguous for later review.",
                    "document_type": context.document_type,
                    "counts": {
                        "transcript_artifacts": len(context.transcript_artifacts),
                        "segmented_transcripts": len({segment.transcript_artifact_id for segment in context.evidence_segments}),
                        "process_groups": len(grouping_result.process_groups),
                        "ambiguous_assignments": len(ambiguous_assignments),
                    },
                    "transcript_assignments": grouping_result.transcript_group_ids,
                    "ambiguity_summary": {"ambiguous_assignment_count": len(ambiguous_assignments), "has_ambiguity": bool(ambiguous_assignments)},
                    "decision_sources": dict(grouping_decision_sources),
                    "grouping_conflicts": dict(grouping_conflicts),
                    "process_group_summaries": [
                        {
                            "title": group.title,
                            "capability_tags": json.loads(getattr(group, "capability_tags_json", "[]") or "[]"),
                            "summary_text": getattr(group, "summary_text", "") or "",
                        }
                        for group in grouping_result.process_groups
                    ],
                    "assignments": grouping_result.assignment_details,
                }
            )
            logger.info(
                "Process grouping completed",
                extra={"event": "draft_generation.stage_completed", "process_group_count": len(grouping_result.process_groups), "segmented_transcript_count": len({segment.transcript_artifact_id for segment in context.evidence_segments})},
            )
