r"""
Purpose: Import ORM models so SQLAlchemy metadata is fully registered.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\__init__.py
"""

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.output_document import OutputDocumentModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.user import UserModel
from app.models.user_auth_token import UserAuthTokenModel

__all__ = [
    "ArtifactModel",
    "DraftSessionModel",
    "OutputDocumentModel",
    "ProcessNoteModel",
    "ProcessStepModel",
    "ProcessStepScreenshotCandidateModel",
    "ProcessStepScreenshotModel",
    "UserModel",
    "UserAuthTokenModel",
]
