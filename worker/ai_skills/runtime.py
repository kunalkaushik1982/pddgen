from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_markdown_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned.removeprefix("json").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned.removesuffix("```").strip()

    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object.")
    return parsed
