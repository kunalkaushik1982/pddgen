r"""
Purpose: Import ORM models so SQLAlchemy metadata is fully registered.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\__init__.py
"""

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.output_document import OutputDocumentModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel

__all__ = [
    "ArtifactModel",
    "DraftSessionModel",
    "OutputDocumentModel",
    "ProcessNoteModel",
    "ProcessStepModel",
    "ProcessStepScreenshotModel",
]
