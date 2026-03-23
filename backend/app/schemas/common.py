r"""
Purpose: Shared API schema primitives for the backend.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\common.py
"""

from typing import Literal

from pydantic import BaseModel


ConfidenceLevel = Literal["high", "medium", "low", "unknown"]
ArtifactKind = Literal["video", "transcript", "template", "sop", "diagram", "screenshot"]
WorkflowDocumentType = Literal["pdd", "sop", "brd"]
ResolutionStatus = Literal["auto_resolved", "pending_review", "user_confirmed"]


class EvidenceReference(BaseModel):
    """Reference back to a source artifact and locator."""

    id: str
    artifact_id: str
    kind: str
    locator: str
