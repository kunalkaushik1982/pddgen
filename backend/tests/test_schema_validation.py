from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.db.schema_validation import validate_database_schema


class SchemaValidationTests(unittest.TestCase):
    @patch("app.db.schema_validation.ScriptDirectory.from_config")
    @patch("app.db.schema_validation.MigrationContext.configure")
    @patch("app.db.schema_validation.engine.connect")
    def test_accepts_database_at_head(
        self,
        connect_mock,
        migration_context_mock,
        script_directory_mock,
    ) -> None:
        script_directory_mock.return_value.get_current_head.return_value = "20260318_0001"
        migration_context_mock.return_value.get_current_revision.return_value = "20260318_0001"
        connection = MagicMock()
        connect_mock.return_value.__enter__.return_value = connection

        validate_database_schema()

    @patch("app.db.schema_validation.ScriptDirectory.from_config")
    @patch("app.db.schema_validation.MigrationContext.configure")
    @patch("app.db.schema_validation.engine.connect")
    def test_rejects_database_behind_head(
        self,
        connect_mock,
        migration_context_mock,
        script_directory_mock,
    ) -> None:
        script_directory_mock.return_value.get_current_head.return_value = "20260318_0001"
        migration_context_mock.return_value.get_current_revision.return_value = None
        connection = MagicMock()
        connect_mock.return_value.__enter__.return_value = connection

        with self.assertRaises(RuntimeError) as error:
            validate_database_schema()

        self.assertIn("Run 'alembic upgrade head'", str(error.exception))

