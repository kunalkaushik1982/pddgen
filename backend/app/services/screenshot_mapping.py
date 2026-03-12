r"""
Purpose: Service for screenshot proposal and timestamp mapping.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\screenshot_mapping.py
"""

from app.models.artifact import ArtifactModel


class ScreenshotMappingService:
    """Map uploaded screenshots to extracted steps where possible."""

    def attach_uploaded_screenshots(self, *, steps: list[dict], screenshot_artifacts: list[ArtifactModel]) -> list[dict]:
        """Attach existing screenshot artifacts to steps by position.

        The pilot version uses simple positional mapping. Later phases can
        replace this with time-based or vision-based matching.
        """

        for step, screenshot in zip(steps, screenshot_artifacts, strict=False):
            step["screenshot_id"] = screenshot.id
        return steps
