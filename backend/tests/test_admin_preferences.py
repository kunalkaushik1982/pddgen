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
from app.services.auth.password_identity_provider import PasswordIdentityProvider


class AdminPreferencesTests(unittest.TestCase):
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

        login = self.client.post(
            "/api/auth/login",
            json={"username": "adminonly", "password": "secret123"},
        )
        self.assertEqual(login.status_code, 200)

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.engine.dispose()
        self.settings.local_storage_root = self.original_storage_root
        self.settings.admin_usernames = self.original_admin_names
        main_module.validate_database_schema = self.original_validate
        self.temp_dir.cleanup()

    def test_admin_preferences_return_default_visible_columns(self) -> None:
        response = self.client.get("/api/admin/preferences")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["session_metrics_visible_columns"],
            ["session", "owner", "status", "total_estimated_cost_inr", "updated_at"],
        )

    def test_admin_preferences_persist_updated_visible_columns(self) -> None:
        csrf_token = self.client.cookies.get(self.settings.auth_csrf_cookie_name)
        self.assertIsInstance(csrf_token, str)
        save = self.client.put(
            "/api/admin/preferences",
            json={"session_metrics_visible_columns": ["session", "status", "updated_at"]},
            headers={self.settings.auth_csrf_header_name: csrf_token},
        )
        self.assertEqual(save.status_code, 200)
        self.assertEqual(
            save.json()["session_metrics_visible_columns"],
            ["session", "status", "updated_at"],
        )

        reloaded = self.client.get("/api/admin/preferences")
        self.assertEqual(reloaded.status_code, 200)
        self.assertEqual(
            reloaded.json()["session_metrics_visible_columns"],
            ["session", "status", "updated_at"],
        )


if __name__ == "__main__":
    unittest.main()
