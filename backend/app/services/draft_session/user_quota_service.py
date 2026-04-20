r"""
Purpose: Enforce per-user job quotas (lifetime + daily UTC) for workspace operations.
Full filepath: backend/app/services/user_quota_service.py
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.user import UserModel


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def is_unlimited_admin(username: str, settings: Settings) -> bool:
    return username in settings.admin_usernames


def effective_limits(settings: Settings, user: UserModel) -> tuple[int, int]:
    """Return (lifetime_cap, daily_cap) including per-user bonuses."""
    life = int(settings.user_quota_lifetime_jobs) + int(user.quota_lifetime_bonus)
    daily = int(settings.user_quota_daily_jobs) + int(user.quota_daily_bonus)
    return max(0, life), max(0, daily)


def roll_daily_counter_if_needed(user: UserModel) -> None:
    """Reset daily usage when the UTC date changes."""
    today = _utc_today()
    if user.job_usage_daily_date is None or user.job_usage_daily_date != today:
        user.job_usage_daily = 0
        user.job_usage_daily_date = today


def reserve_job_unit(db: Session, user: UserModel, settings: Settings | None = None) -> None:
    """Increment usage after checks (call before a billable operation)."""
    settings = settings or get_settings()
    if is_unlimited_admin(user.username, settings):
        return
    locked = db.execute(select(UserModel).where(UserModel.id == user.id).with_for_update()).scalar_one()
    roll_daily_counter_if_needed(locked)
    life_cap, day_cap = effective_limits(settings, locked)
    if locked.job_usage_lifetime >= life_cap:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have reached your lifetime job quota. Contact support for more capacity.",
        )
    if locked.job_usage_daily >= day_cap:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have reached your daily job quota. Try again tomorrow or contact support.",
        )
    locked.job_usage_lifetime += 1
    locked.job_usage_daily += 1
    locked.job_usage_daily_date = _utc_today()
    db.add(locked)


def refund_job_unit(db: Session, user: UserModel, settings: Settings | None = None) -> None:
    """Undo one reserved unit if the operation failed after reservation."""
    settings = settings or get_settings()
    if is_unlimited_admin(user.username, settings):
        return
    locked = db.execute(select(UserModel).where(UserModel.id == user.id).with_for_update()).scalar_one()
    roll_daily_counter_if_needed(locked)
    if locked.job_usage_lifetime > 0:
        locked.job_usage_lifetime -= 1
    if locked.job_usage_daily > 0:
        locked.job_usage_daily -= 1
    db.add(locked)


def assert_quota_available(db: Session, user: UserModel, settings: Settings | None = None) -> None:
    """Read-only check (no increment) for UX; enforcement uses reserve_job_unit."""
    settings = settings or get_settings()
    if is_unlimited_admin(user.username, settings):
        return
    locked = db.execute(select(UserModel).where(UserModel.id == user.id).with_for_update()).scalar_one()
    roll_daily_counter_if_needed(locked)
    life_cap, day_cap = effective_limits(settings, locked)
    if locked.job_usage_lifetime >= life_cap:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have reached your lifetime job quota. Contact support for more capacity.",
        )
    if locked.job_usage_daily >= day_cap:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have reached your daily job quota. Try again tomorrow or contact support.",
        )
