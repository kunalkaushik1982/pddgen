from __future__ import annotations

import re
from uuid import uuid4

from worker.pipeline.stages.support import TIMESTAMP_PATTERN
from worker.services.workflow_intelligence import EvidenceSegment


class ParagraphTranscriptSegmentationStrategy:
    """Default transcript chunking strategy based on paragraph and timestamp continuity."""

    strategy_key = "paragraph_v1"

    def segment(
        self,
        *,
        transcript_artifact_id: str,
        meeting_id: str | None,
        transcript_text: str,
    ) -> list[EvidenceSegment]:
        chunks = [chunk.strip() for chunk in re.split(r"(?:\r?\n){2,}", transcript_text) if chunk.strip()]
        if not chunks:
            chunks = [line.strip() for line in transcript_text.splitlines() if line.strip()]

        segments: list[EvidenceSegment] = []
        for index, chunk in enumerate(chunks, start=1):
            timestamps = self._extract_timestamps(chunk)
            segments.append(
                EvidenceSegment(
                    id=str(uuid4()),
                    transcript_artifact_id=transcript_artifact_id,
                    meeting_id=meeting_id,
                    segment_order=index,
                    text=chunk,
                    start_timestamp=timestamps[0] if timestamps else None,
                    end_timestamp=timestamps[-1] if timestamps else None,
                    segmentation_method="timestamp_paragraph" if timestamps else "paragraph_fallback",
                    confidence="medium" if timestamps else "low",
                )
            )
        return segments

    @staticmethod
    def _extract_timestamps(text: str) -> list[str]:
        timestamps: list[str] = []
        for match in TIMESTAMP_PATTERN.finditer(text):
            hours_group, minutes_group, seconds_group = match.groups()
            hours = int(hours_group or 0)
            minutes = int(minutes_group)
            seconds = int(seconds_group)
            timestamps.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        return timestamps
