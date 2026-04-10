r"""
Purpose: Persist LLM usage and background job metrics for admin dashboards.
Full filepath: backend/app/services/usage_metrics_service.py
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.artifact import ArtifactModel
from app.models.background_job_run import BackgroundJobRunModel
from app.models.draft_session import DraftSessionModel
from app.models.llm_usage_event import LlmUsageEventModel
from app.schemas.admin import AdminSessionMetricsResponse


def estimate_cost_usd(
    *,
    settings: Settings,
    prompt_tokens: int,
    completion_tokens: int,
) -> Decimal | None:
    """Rough USD estimate from configured per-1k rates; None if rates are unset."""
    p_rate = float(settings.ai_prompt_usd_per_1k_tokens or 0.0)
    c_rate = float(settings.ai_completion_usd_per_1k_tokens or 0.0)
    if p_rate <= 0 and c_rate <= 0:
        return None
    return Decimal(str((prompt_tokens / 1000.0) * p_rate + (completion_tokens / 1000.0) * c_rate))


def persist_llm_usage_from_response_body(
    db: Session,
    *,
    session_id: str,
    owner_id: str,
    skill_id: str,
    response_body: dict[str, Any],
    settings: Settings,
) -> None:
    """Insert one llm_usage_events row from an OpenAI-compatible chat completion JSON body."""
    usage = response_body.get("usage")
    if not isinstance(usage, dict):
        return
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total_raw = usage.get("total_tokens")
    total_tokens = int(total_raw) if total_raw is not None else None
    model_raw = response_body.get("model")
    model = str(model_raw) if isinstance(model_raw, str) else None
    cost = estimate_cost_usd(settings=settings, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    row = LlmUsageEventModel(
        id=str(uuid4()),
        session_id=session_id,
        owner_id=owner_id,
        skill_id=skill_id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=cost,
    )
    db.add(row)
    db.commit()


def persist_llm_usage_from_response_body_standalone(
    *,
    session_id: str | None,
    skill_id: str,
    response_body: dict[str, Any],
) -> None:
    """Worker path: own DB session; resolves owner_id from draft_sessions."""
    if not session_id:
        return
    from app.core.config import get_settings
    from app.db.session import SessionLocal

    settings = get_settings()
    db = SessionLocal()
    try:
        draft = db.get(DraftSessionModel, session_id)
        owner_id = draft.owner_id if draft is not None else "unknown"
        persist_llm_usage_from_response_body(
            db,
            session_id=session_id,
            owner_id=owner_id,
            skill_id=skill_id,
            response_body=response_body,
            settings=settings,
        )
    finally:
        db.close()


def persist_background_job_run(
    *,
    session_id: str,
    job_type: str,
    celery_task_id: str | None,
    duration_seconds: float,
) -> None:
    """Worker path: record one completed Celery job duration."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        draft = db.get(DraftSessionModel, session_id)
        owner_id = draft.owner_id if draft is not None else "unknown"
        row = BackgroundJobRunModel(
            id=str(uuid4()),
            session_id=session_id,
            owner_id=owner_id,
            job_type=job_type,
            celery_task_id=celery_task_id,
            duration_seconds=float(duration_seconds),
        )
        db.add(row)
        db.commit()
    finally:
        db.close()


def list_admin_session_metrics(db: Session) -> list[AdminSessionMetricsResponse]:
    """Aggregate LLM usage and background job durations per draft session (newest first)."""
    settings = get_settings()
    sessions = list(db.execute(select(DraftSessionModel).order_by(DraftSessionModel.updated_at.desc())).scalars().all())
    if not sessions:
        return []
    ids = [s.id for s in sessions]
    llm_rows = db.execute(
        select(
            LlmUsageEventModel.session_id,
            func.coalesce(func.sum(LlmUsageEventModel.prompt_tokens), 0),
            func.coalesce(func.sum(LlmUsageEventModel.completion_tokens), 0),
            func.sum(LlmUsageEventModel.total_tokens),
            func.sum(LlmUsageEventModel.estimated_cost_usd),
            func.count(LlmUsageEventModel.id),
        )
        .where(LlmUsageEventModel.session_id.in_(ids))
        .group_by(LlmUsageEventModel.session_id)
    ).all()
    llm_map: dict[str, dict[str, object]] = {}
    for row in llm_rows:
        llm_map[row[0]] = {
            "prompt": int(row[1] or 0),
            "completion": int(row[2] or 0),
            "total_tokens_sum": row[3],
            "cost": row[4],
            "count": int(row[5] or 0),
        }

    job_rows = db.execute(
        select(
            BackgroundJobRunModel.session_id,
            BackgroundJobRunModel.job_type,
            func.coalesce(func.sum(BackgroundJobRunModel.duration_seconds), 0.0),
            func.count(BackgroundJobRunModel.id),
        )
        .where(BackgroundJobRunModel.session_id.in_(ids))
        .group_by(BackgroundJobRunModel.session_id, BackgroundJobRunModel.job_type)
    ).all()
    job_map: dict[str, dict[str, tuple[float, int]]] = {}
    for sid, jtype, dur_sum, cnt in job_rows:
        job_map.setdefault(str(sid), {})[str(jtype)] = (float(dur_sum or 0.0), int(cnt or 0))

    storage_rows = db.execute(
        select(
            ArtifactModel.session_id,
            func.coalesce(func.sum(ArtifactModel.size_bytes), 0),
        )
        .where(ArtifactModel.session_id.in_(ids))
        .group_by(ArtifactModel.session_id)
    ).all()
    storage_map = {str(session_id): int(size_bytes or 0) for session_id, size_bytes in storage_rows}

    out: list[AdminSessionMetricsResponse] = []
    for s in sessions:
        lm = llm_map.get(s.id, {})
        tp = int(lm.get("prompt", 0) or 0)
        tc = int(lm.get("completion", 0) or 0)
        tts = lm.get("total_tokens_sum")
        total_rep = int(tts) if tts is not None else None
        cost_val = lm.get("cost")
        cost_float = float(cost_val) if cost_val is not None else None
        if cost_float is None and (tp > 0 or tc > 0):
            recomputed = estimate_cost_usd(settings=settings, prompt_tokens=tp, completion_tokens=tc)
            if recomputed is not None:
                cost_float = float(recomputed)
        actual_inr: float | None = None
        charge_inr: float | None = None
        if cost_float is not None and float(settings.usd_to_inr_rate) > 0:
            actual_inr = round(cost_float * float(settings.usd_to_inr_rate), 4)
            charge_inr = round(actual_inr * float(settings.admin_ai_cost_margin_multiplier), 4)
        j = job_map.get(s.id, {})
        d_sum, d_cnt = j.get("draft_generation", (0.0, 0))
        ss_sum, ss_cnt = j.get("screenshot_generation", (0.0, 0))
        processing_cost_inr = round(
            ((d_sum / 60.0) * float(settings.admin_processing_inr_per_minute_draft))
            + ((ss_sum / 60.0) * float(settings.admin_processing_inr_per_minute_screenshot)),
            4,
        )
        storage_bytes_total = int(storage_map.get(s.id, 0) or 0)
        gb_months = (storage_bytes_total / float(1024**3)) * (float(settings.admin_storage_retention_days) / 30.0)
        storage_cost_inr = round(gb_months * float(settings.admin_storage_inr_per_gb_month), 4)
        total_estimated_cost_inr = round((actual_inr or 0.0) + processing_cost_inr + storage_cost_inr, 4)
        out.append(
            AdminSessionMetricsResponse(
                session_id=s.id,
                title=s.title,
                owner_id=s.owner_id,
                status=s.status,
                updated_at=s.updated_at,
                llm_call_count=int(lm.get("count", 0) or 0),
                total_prompt_tokens=tp,
                total_completion_tokens=tc,
                total_tokens_reported=total_rep,
                estimated_cost_usd=cost_float,
                actual_ai_cost_inr=actual_inr,
                charge_inr_with_margin=charge_inr,
                processing_cost_inr=processing_cost_inr,
                storage_bytes_total=storage_bytes_total,
                storage_cost_inr=storage_cost_inr,
                total_estimated_cost_inr=total_estimated_cost_inr,
                draft_generation_seconds_total=d_sum,
                draft_generation_runs=d_cnt,
                screenshot_generation_seconds_total=ss_sum,
                screenshot_generation_runs=ss_cnt,
            )
        )
    return out
