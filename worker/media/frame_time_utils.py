from __future__ import annotations


def timestamp_to_seconds(timestamp: str) -> int:
    parts = [int(part) for part in timestamp.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    hours, minutes, seconds = parts[-3:]
    return (hours * 3600) + (minutes * 60) + seconds


def seconds_to_timestamp(total_seconds: int) -> str:
    hours = total_seconds // 3600
    remainder = total_seconds % 3600
    minutes = remainder // 60
    seconds = remainder % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
