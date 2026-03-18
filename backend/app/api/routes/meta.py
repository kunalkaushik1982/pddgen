r"""
Purpose: API routes for release metadata and About information.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\meta.py
"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.release import get_release_info
from app.schemas.meta import AboutResponse, ComponentVersionsResponse

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/about", response_model=AboutResponse)
def get_about() -> AboutResponse:
    """Return build and runtime metadata for the About page."""
    settings = get_settings()
    release = get_release_info()
    return AboutResponse(
        app_name=settings.app_name,
        environment=settings.app_env,
        auth_provider=settings.auth_provider,
        ai_provider=settings.ai_provider,
        versions=ComponentVersionsResponse(**release),
    )
