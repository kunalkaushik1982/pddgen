from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import NoSuchModuleError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.models.user import UserModel
import app.main as main_module
from app.services.password_identity_provider import PasswordIdentityProvider


class AdminConsoleOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.original_storage_root = self.settings.local_storage_root
        self.original_admin_names = list(self.settings.admin_usernames)
        self.temp_dir = TemporaryDirectory()
        self.settings.local_storage_root = Path(self.temp_dir.name)
        self.settings.admin_usernames = ["adminonly"]

        self.original_validate = main_module.validate_database_schema
        main_module.validate_database_schema = lambda: None

        try:
            self.engine = create_engine(
                "sqlite://",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        except NoSuchModuleError as exc:
            raise unittest.SkipTest(
                "SQLAlchemy SQLite dialect is unavailable in this environment; install SQLite support for SQLAlchemy."
            ) from exc
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        app = main_module.create_app()

        def override_get_db_session():
            session = self.session_local()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = override_get_db_session
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

        session = self.session_local()
        try:
            now = datetime.now(timezone.utc)
            session.add(
                UserModel(
                    id=str(uuid4()),
                    username="adminonly",
                    email="adminonly@example.com",
                    email_verified_at=now,
                    password_hash=PasswordIdentityProvider._hash_password("secret123"),
                    admin_console_only=True,
                    created_at=now,
                )
            )
            session.commit()
        finally:
            session.close()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.engine.dispose()
        self.settings.local_storage_root = self.original_storage_root
        self.settings.admin_usernames = self.original_admin_names
        main_module.validate_database_schema = self.original_validate
        self.temp_dir.cleanup()

    def test_workspace_api_returns_403_for_admin_console_only_user(self) -> None:
        login = self.client.post(
            "/api/auth/login",
            json={"username": "adminonly", "password": "secret123"},
        )
        self.assertEqual(login.status_code, 200)

        blocked = self.client.get("/api/draft-sessions")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["detail"], "This account is limited to the admin console.")

    def test_me_includes_admin_console_only(self) -> None:
        self.client.post(
            "/api/auth/login",
            json={"username": "adminonly", "password": "secret123"},
        )
        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        body = me.json()
        self.assertTrue(body["admin_console_only"])
        self.assertTrue(body["is_admin"])


if __name__ == "__main__":
    unittest.main()
