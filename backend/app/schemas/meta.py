r"""
Purpose: API schemas for release metadata and About surfaces.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\meta.py
"""

from pydantic import BaseModel


class ComponentVersionsResponse(BaseModel):
    release: str
    frontend: str
    backend: str
    worker: str


class AboutResponse(BaseModel):
    app_name: str
    environment: str
    auth_provider: str
    ai_provider: str
    versions: ComponentVersionsResponse
