r"""
Purpose: Service for deriving ordered process steps from transcript evidence.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\step_extraction.py
"""

import json
import re
from uuid import uuid4


TIMESTAMP_PATTERN = re.compile(r"(?P<timestamp>\d{2}:\d{2}:\d{2})")


class StepExtractionService:
    """Extract structured steps from transcript text."""

    def extract_steps(self, *, transcript_artifact_id: str, transcript_text: str) -> list[dict]:
        """Return ordered step candidates from a transcript document.

        The pilot implementation uses a deterministic line-based parser so the
        rest of the backend can operate end to end before the dedicated
        worker-based extraction pipeline is added.
        """

        steps: list[dict] = []
        lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]

        for index, line in enumerate(lines, start=1):
            timestamp_match = TIMESTAMP_PATTERN.search(line)
            timestamp = timestamp_match.group("timestamp") if timestamp_match else ""
            normalized_text = TIMESTAMP_PATTERN.sub("", line).strip(" -:")
            if not normalized_text:
                continue

            application_name = self._infer_application_name(normalized_text)
            confidence = "high" if timestamp else "medium"
            steps.append(
                {
                    "step_number": len(steps) + 1,
                    "application_name": application_name,
                    "action_text": normalized_text,
                    "source_data_note": "",
                    "timestamp": timestamp,
                    "start_timestamp": timestamp,
                    "end_timestamp": timestamp,
                    "supporting_transcript_text": normalized_text,
                    "screenshot_id": "",
                    "confidence": confidence,
                    "evidence_references": json.dumps(
                        [
                            {
                                "id": str(uuid4()),
                                "artifact_id": transcript_artifact_id,
                                "kind": "transcript",
                                "locator": timestamp or f"line:{index}",
                            }
                        ]
                    ),
                    "edited_by_ba": False,
                }
            )
        return steps

    @staticmethod
    def _infer_application_name(text: str) -> str:
        """Infer a likely application name from transcript text."""
        known_apps = ("sap", "excel", "outlook", "chrome", "edge", "web", "portal")
        lowered = text.lower()
        for app_name in known_apps:
            if app_name in lowered:
                return app_name.upper() if app_name == "sap" else app_name.title()
        return ""
