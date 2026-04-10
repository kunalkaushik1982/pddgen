from __future__ import annotations

from datetime import datetime, timezone
import unittest
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.models.user import UserModel
from app.services.password_identity_provider import PasswordIdentityProvider
from app.services.user_quota_service import reserve_job_unit


class UserQuotaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.original_life = self.settings.user_quota_lifetime_jobs
        self.original_daily = self.settings.user_quota_daily_jobs
        self.original_admin = list(self.settings.admin_usernames)
        self.settings.user_quota_lifetime_jobs = 2
        self.settings.user_quota_daily_jobs = 2
        self.settings.admin_usernames = []

        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        session = self.session_local()
        try:
            now = datetime.now(timezone.utc)
            session.add(
                UserModel(
                    id=str(uuid4()),
                    username="quotauser",
                    email="quotauser@example.com",
                    email_verified_at=now,
                    password_hash=PasswordIdentityProvider._hash_password("secret123"),
                    admin_console_only=False,
                    created_at=now,
                )
            )
            session.commit()
        finally:
            session.close()

    def tearDown(self) -> None:
        self.engine.dispose()
        self.settings.user_quota_lifetime_jobs = self.original_life
        self.settings.user_quota_daily_jobs = self.original_daily
        self.settings.admin_usernames = self.original_admin

    def _user(self, session):
        return session.execute(select(UserModel).where(UserModel.username == "quotauser")).scalar_one()

    def test_reserve_blocks_after_lifetime_cap(self) -> None:
        s = self.session_local()
        try:
            u = self._user(s)
            reserve_job_unit(s, u, self.settings)
            s.commit()
            u = self._user(s)
            reserve_job_unit(s, u, self.settings)
            s.commit()
            u = self._user(s)
            with self.assertRaises(HTTPException) as ctx:
                reserve_job_unit(s, u, self.settings)
            self.assertEqual(ctx.exception.status_code, 403)
        finally:
            s.close()

    def test_admin_username_skips_increment(self) -> None:
        self.settings.admin_usernames = ["adminquota"]
        s = self.session_local()
        try:
            now = datetime.now(timezone.utc)
            s.add(
                UserModel(
                    id=str(uuid4()),
                    username="adminquota",
                    email="adminquota@example.com",
                    email_verified_at=now,
                    password_hash=PasswordIdentityProvider._hash_password("secret123"),
                    admin_console_only=False,
                    created_at=now,
                )
            )
            s.commit()
            u = self._user_by_username(s, "adminquota")
            for _ in range(10):
                reserve_job_unit(s, u, self.settings)
            s.commit()
            u = self._user_by_username(s, "adminquota")
            self.assertEqual(u.job_usage_lifetime, 0)
            self.assertEqual(u.job_usage_daily, 0)
        finally:
            s.close()

    def _user_by_username(self, session, username: str):
        return session.execute(select(UserModel).where(UserModel.username == username)).scalar_one()


if __name__ == "__main__":
    unittest.main()
