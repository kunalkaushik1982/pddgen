r"""
Purpose: BA review mutations for steps and screenshot selections.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\draft_session_review_service.py
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.artifact import ArtifactModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.services.action_log_service import ActionLogService


class DraftSessionReviewService:
    """Encapsulate mutable BA review actions for draft sessions."""

    def __init__(self, *, action_log_service: ActionLogService | None = None) -> None:
        self.action_log_service = action_log_service or ActionLogService()

    def update_process_step(self, db: Session, *, session, step_id: str, payload, actor: str):  # type: ignore[no-untyped-def]
        step = next((item for item in session.process_steps if item.id == step_id), None)
        if step is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Process step not found.")

        updates = payload.model_dump(exclude_none=True)
        for field_name, field_value in updates.items():
            setattr(step, field_name, field_value)

        session.status = "review"
        db.add(step)
        self.action_log_service.record(
            db,
            session_id=session.id,
            event_type="step_edited",
            title=f"Step {step.step_number} edited",
            detail=step.action_text,
            actor=actor,
        )
        db.commit()
        db.refresh(step)
        return step

    def update_step_screenshot(
        self,
        db: Session,
        *,
        session,
        step_id: str,
        step_screenshot_id: str,
        payload,
        actor: str,
    ):  # type: ignore[no-untyped-def]
        step = next((item for item in session.process_steps if item.id == step_id), None)
        if step is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Process step not found.")

        step_screenshot = next((item for item in step.step_screenshots if item.id == step_screenshot_id), None)
        if step_screenshot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step screenshot not found.")

        updates = payload.model_dump(exclude_none=True)
        if updates.get("is_primary"):
            for item in step.step_screenshots:
                item.is_primary = item.id == step_screenshot.id
            step.screenshot_id = step_screenshot.artifact_id
        if "role" in updates:
            step_screenshot.role = updates["role"] or step_screenshot.role

        self.action_log_service.record(
            db,
            session_id=session.id,
            event_type="screenshot_updated",
            title=f"Step {step.step_number} screenshot updated",
            detail=step_screenshot.timestamp or step_screenshot.artifact.name,
            actor=actor,
        )
        db.commit()
        db.refresh(step)
        return step

    def select_candidate_screenshot(
        self,
        db: Session,
        *,
        session,
        step_id: str,
        candidate_screenshot_id: str,
        payload,
        actor: str,
    ):  # type: ignore[no-untyped-def]
        step = next((item for item in session.process_steps if item.id == step_id), None)
        if step is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Process step not found.")

        candidate = next((item for item in step.step_screenshot_candidates if item.id == candidate_screenshot_id), None)
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate screenshot not found.")

        existing = next((item for item in step.step_screenshots if item.artifact_id == candidate.artifact_id), None)
        if existing is None:
            next_sequence = max((item.sequence_number for item in step.step_screenshots), default=0) + 1
            existing = ProcessStepScreenshotModel(
                step_id=step.id,
                artifact_id=candidate.artifact_id,
                role=payload.role or candidate.source_role or "during",
                sequence_number=next_sequence,
                timestamp=candidate.timestamp,
                selection_method="manual-candidate",
                is_primary=bool(payload.is_primary) or not step.step_screenshots,
            )
            db.add(existing)
            db.flush()
        elif payload.role:
            existing.role = payload.role

        if payload.is_primary or not any(item.is_primary for item in step.step_screenshots):
            for item in step.step_screenshots:
                item.is_primary = item.id == existing.id
            step.screenshot_id = existing.artifact_id
        elif not step.screenshot_id:
            step.screenshot_id = existing.artifact_id

        self.action_log_service.record(
            db,
            session_id=session.id,
            event_type="candidate_screenshot_selected",
            title=f"Candidate screenshot selected for step {step.step_number}",
            detail=candidate.artifact.name,
            actor=actor,
        )
        db.commit()
        db.refresh(step)
        return step

    def delete_step_screenshot(self, db: Session, *, session, step_id: str, step_screenshot_id: str, actor: str):  # type: ignore[no-untyped-def]
        step = next((item for item in session.process_steps if item.id == step_id), None)
        if step is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Process step not found.")

        step_screenshot = next((item for item in step.step_screenshots if item.id == step_screenshot_id), None)
        if step_screenshot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step screenshot not found.")

        removed_artifact_id = step_screenshot.artifact_id
        db.delete(step_screenshot)
        db.flush()

        remaining = sorted(step.step_screenshots, key=lambda item: item.sequence_number)
        if remaining:
            has_primary = any(item.is_primary for item in remaining)
            if not has_primary:
                remaining[0].is_primary = True
            primary = next((item for item in remaining if item.is_primary), remaining[0])
            step.screenshot_id = primary.artifact_id
        else:
            step.screenshot_id = ""

        artifact_reference_count = db.query(ProcessStepScreenshotModel).filter(
            ProcessStepScreenshotModel.artifact_id == removed_artifact_id
        ).count()
        candidate_reference_count = db.query(ProcessStepScreenshotCandidateModel).filter(
            ProcessStepScreenshotCandidateModel.artifact_id == removed_artifact_id
        ).count()
        if artifact_reference_count == 0 and candidate_reference_count == 0:
            artifact = db.get(ArtifactModel, removed_artifact_id)
            if artifact is not None:
                db.delete(artifact)

        self.action_log_service.record(
            db,
            session_id=session.id,
            event_type="screenshot_removed",
            title=f"Screenshot removed from step {step.step_number}",
            detail=removed_artifact_id,
            actor=actor,
        )
        db.commit()
        db.refresh(step)
        return step
