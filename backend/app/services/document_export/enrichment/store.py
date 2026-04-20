r"""Parse persisted enrichment JSON and helpers for context builders."""

from __future__ import annotations

import json
from typing import Any

from app.models.draft_session import DraftSessionModel

# Older exports stored a single BRD narrative under this key; still honored as fallback.
LEGACY_BRD_FIELD_CURRENT_STATE = "brd.current_state_summary"


def get_enrichment_fields(draft_session: DraftSessionModel) -> dict[str, str] | None:
    """Return flat field_id -> text map, or None if missing/invalid."""
    raw = getattr(draft_session, "export_text_enrichment_json", None)
    if not raw or not str(raw).strip():
        return None
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    fields = payload.get("fields")
    if not isinstance(fields, dict):
        return None
    out: dict[str, str] = {}
    for key, value in fields.items():
        if isinstance(key, str) and isinstance(value, str) and value.strip():
            out[key] = value.strip()
    return out or None


def prefer_enrichment_field(
    draft_session: DraftSessionModel,
    field_id: str,
    fallback: str,
) -> str:
    """Use AI text for ``field_id`` when present; otherwise ``fallback``."""
    fields = get_enrichment_fields(draft_session)
    if fields and (ai := fields.get(field_id)) and ai.strip():
        return ai.strip()
    return fallback


def prefer_first_enrichment_field(
    draft_session: DraftSessionModel,
    field_ids: tuple[str, ...],
    fallback: str,
) -> str:
    """Return the first non-empty enrichment value for any of ``field_ids``, else ``fallback``."""
    fields = get_enrichment_fields(draft_session)
    if not fields:
        return fallback
    for fid in field_ids:
        val = fields.get(fid)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return fallback


def enrich_brd_canonical_section_bodies(
    draft_session: DraftSessionModel,
    sections: list[dict[str, str]],
) -> None:
    """
    Overlay persisted enrichment onto each ``canonical_sections`` row ``body`` (mutates ``sections``).

    Executive summary and background sections also accept the legacy single-key payload
    ``brd.current_state_summary`` when newer per-slug keys are absent.
    """
    for row in sections:
        slug = str(row.get("slug") or "")
        det = str(row.get("body") or "")
        field_id = f"brd.{slug}"
        if slug == "executive_summary":
            row["body"] = prefer_first_enrichment_field(
                draft_session,
                (field_id, LEGACY_BRD_FIELD_CURRENT_STATE),
                det,
            )
        elif slug == "background_problem_statement":
            row["body"] = prefer_first_enrichment_field(
                draft_session,
                (field_id, LEGACY_BRD_FIELD_CURRENT_STATE),
                det,
            )
        else:
            row["body"] = prefer_enrichment_field(draft_session, field_id, det)


def merge_enrichment_into_pdd_overview_summary(
    draft_session: DraftSessionModel,
    deterministic_summary: str,
) -> str:
    return prefer_enrichment_field(draft_session, "pdd.process_summary", deterministic_summary)


def merge_enrichment_into_brd_process_summary(
    draft_session: DraftSessionModel,
    deterministic_summary: str,
) -> str:
    """Backward-compatible single-string merge (used by tests and any legacy callers)."""
    return prefer_first_enrichment_field(
        draft_session,
        (
            "brd.background_problem_statement",
            "brd.executive_summary",
            LEGACY_BRD_FIELD_CURRENT_STATE,
        ),
        deterministic_summary,
    )


def merge_enrichment_into_sop_purpose(
    draft_session: DraftSessionModel,
    deterministic_purpose: str,
) -> str:
    return prefer_enrichment_field(draft_session, "sop.purpose", deterministic_purpose)
