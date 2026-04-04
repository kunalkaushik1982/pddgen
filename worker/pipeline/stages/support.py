r"""
Purpose: Shared constants and deterministic helpers for draft generation.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\draft_generation_support.py
"""

import re


TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")
ACTION_VERB_PATTERNS = {
    "navigate": ("open", "navigate", "launch", "go to", "switch to", "login", "log in"),
    "data_entry": ("enter", "paste", "type", "update", "fill", "input"),
    "copy": ("copy",),
    "submit": ("submit", "save", "confirm", "create", "send"),
}
ACTION_OFFSET_WINDOWS = {
    "navigate": [0, 1, 2, 3, 4, -1, -2],
    "data_entry": [-1, 0, 1, 2, 3, -2],
    "copy": [-2, -1, 0, 1],
    "submit": [1, 2, 3, 4, 0, -1],
    "default": [-2, -1, 0, 1, 2, 3],
}
SCREENSHOT_ROLE_ORDER = ("before", "during", "after")
SCREENSHOT_ROLE_LOCAL_OFFSETS = {
    "before": [-1, 0, 1],
    "during": [-1, 0, 1],
    "after": [0, 1, 2],
}


def timestamp_to_seconds(timestamp: str) -> int:
    """Convert HH:MM:SS into total seconds."""
    parts = [int(part) for part in (timestamp or "00:00:00").split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    hours, minutes, seconds = parts[-3:]
    return (hours * 3600) + (minutes * 60) + seconds


def seconds_to_timestamp(total_seconds: int) -> str:
    """Convert total seconds into HH:MM:SS."""
    hours = total_seconds // 3600
    remainder = total_seconds % 3600
    minutes = remainder // 60
    seconds = remainder % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def extract_transcript_timestamps(transcript_text: str) -> list[str]:
    """Extract normalized timestamps from transcript text in source order."""
    timestamps: list[str] = []
    for match in TIMESTAMP_PATTERN.finditer(transcript_text):
        hours_group, minutes_group, seconds_group = match.groups()
        hours = int(hours_group or 0)
        minutes = int(minutes_group)
        seconds = int(seconds_group)
        timestamps.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    return timestamps


def classify_action_type(action_text: str) -> str:
    """Infer a coarse action type from step text."""
    lowered = action_text.lower()
    for action_type, patterns in ACTION_VERB_PATTERNS.items():
        if any(pattern in lowered for pattern in patterns):
            return action_type
    return "default"


def build_pairing_detail(transcript_artifacts, video_artifacts) -> str:  # type: ignore[no-untyped-def]
    if not transcript_artifacts or not video_artifacts:
        return "No video/transcript pairing available."
    if len(video_artifacts) == 1 and len(transcript_artifacts) > 1:
        return "Using the first uploaded video for all transcripts because only one video is available."
    if len(video_artifacts) < len(transcript_artifacts):
        return (
            f"Pairing by upload order for the first {len(video_artifacts)} transcript/video set(s); "
            "remaining transcripts reuse the last uploaded video."
        )
    pair_count = min(len(transcript_artifacts), len(video_artifacts))
    return f"Pairing transcripts to videos by upload order for {pair_count} set(s)."
