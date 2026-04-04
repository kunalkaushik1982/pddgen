from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TranscriptToStepsRequest:
    transcript_artifact_id: str
    transcript_text: str


@dataclass(slots=True)
class TranscriptStep:
    application_name: str
    action_text: str
    source_data_note: str
    start_timestamp: str
    end_timestamp: str
    display_timestamp: str
    supporting_transcript_text: str
    confidence: str


@dataclass(slots=True)
class TranscriptNote:
    text: str
    confidence: str
    inference_type: str


@dataclass(slots=True)
class TranscriptToStepsResponse:
    steps: list[TranscriptStep] = field(default_factory=list)
    notes: list[TranscriptNote] = field(default_factory=list)
