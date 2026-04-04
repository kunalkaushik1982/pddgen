from __future__ import annotations

import re
from typing import Any


def normalize_slug(value: str, *, fallback: str) -> str:
    normalized_source = value.strip() or fallback
    normalized = re.sub(r"[^a-z0-9\s-]+", " ", normalized_source.lower())
    collapsed = re.sub(r"\s+", "-", normalized.strip())
    return re.sub(r"-{2,}", "-", collapsed).strip("-") or "process"


def normalize_existing_title(value: str, *, existing_titles: list[str]) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None
    return candidate if candidate in existing_titles else None


def normalize_label(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    return normalized[:120].strip()


def normalize_textish(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_label_list(values: Any, *, max_items: int, exclude: set[str] | None = None) -> list[str]:
    if not isinstance(values, list):
        return []
    excluded = {normalize_textish(item) for item in (exclude or set()) if normalize_textish(item)}
    normalized_items: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = normalize_label(value)
        if not cleaned:
            continue
        normalized_key = normalize_textish(cleaned)
        if not normalized_key or normalized_key in seen or normalized_key in excluded:
            continue
        seen.add(normalized_key)
        normalized_items.append(cleaned)
        if len(normalized_items) >= max_items:
            break
    return normalized_items


def normalize_optional_text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None
