from __future__ import annotations

import json
import re

from worker.grouping.grouping_profiles import normalize_text


def to_capability_label(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())


def normalize_capability_tags(tags: list[str], *, process_title: str) -> list[str]:
    normalized_process_title = normalize_text(process_title)
    normalized_tags: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = re.sub(r"\s+", " ", str(tag or "").strip())
        if not cleaned:
            continue
        normalized_key = normalize_text(cleaned)
        if not normalized_key or normalized_key == normalized_process_title or normalized_key in seen:
            continue
        seen.add(normalized_key)
        normalized_tags.append(cleaned)
        if len(normalized_tags) >= 3:
            break
    return normalized_tags


def parse_capability_tags(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, str)]
