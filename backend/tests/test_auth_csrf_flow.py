from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import NoSuchModuleError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session
import app.main as main_module


class AuthCsrfFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = get_settings()
        self.original_storage_root = self.settings.local_storage_root
        self.temp_dir = TemporaryDirectory()
        self.settings.local_storage_root = Path(self.temp_dir.name)

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

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.engine.dispose()
        self.settings.local_storage_root = self.original_storage_root
        main_module.validate_database_schema = self.original_validate
        self.temp_dir.cleanup()

    def test_cookie_auth_and_csrf_are_enforced_for_unsafe_requests(self) -> None:
        response = self.client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "secret123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.settings.auth_cookie_name, self.client.cookies)
        self.assertIn(self.settings.auth_csrf_cookie_name, self.client.cookies)

        forbidden = self.client.post(
            "/api/uploads/sessions",
            json={"title": "Test Session", "diagram_type": "flowchart"},
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["detail"], "CSRF validation failed.")

        csrf_token = self.client.cookies.get(self.settings.auth_csrf_cookie_name)
        created = self.client.post(
            "/api/uploads/sessions",
            json={"title": "Test Session", "diagram_type": "flowchart"},
            headers={self.settings.auth_csrf_header_name: csrf_token},
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["owner_id"], "alice")

