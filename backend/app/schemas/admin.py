r"""
Purpose: API schemas for admin visibility over users and jobs.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\admin.py
"""

from datetime import datetime

from pydantic import BaseModel


class AdminUserListItemResponse(BaseModel):
    """Compact admin-visible user summary."""

    id: str
    username: str
    created_at: datetime
    is_admin: bool
    total_jobs: int
    active_jobs: int
