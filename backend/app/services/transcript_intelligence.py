r"""
Purpose: Service for extracting business rules and notes from transcript evidence.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\transcript_intelligence.py
"""

import json
from uuid import uuid4


class TranscriptIntelligenceService:
    """Extract rule-like notes from transcript text."""

    def extract_notes(self, *, transcript_artifact_id: str, transcript_text: str) -> list[dict]:
        """Return transcript-derived business notes."""
        notes: list[dict] = []
        rule_markers = ("if ", "when ", "unless ", "only if", "exception", "rule")

        for line in (item.strip() for item in transcript_text.splitlines()):
            if not line:
                continue
            lowered = line.lower()
            if not any(marker in lowered for marker in rule_markers):
                continue

            notes.append(
                {
                    "text": line,
                    "related_step_ids": json.dumps([]),
                    "evidence_reference_ids": json.dumps([str(uuid4())]),
                    "confidence": "medium",
                    "inference_type": "explicit" if "rule" in lowered or "if " in lowered else "inferred",
                }
            )
        return notes
