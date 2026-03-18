r"""
Purpose: Validate that the database schema is present and migrated to the current Alembic head.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\db\schema_validation.py
"""

from __future__ import annotations

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from app.core.config import BACKEND_ROOT
from app.db.session import engine


def validate_database_schema() -> None:
    """Fail fast if the database is not migrated to the current Alembic head."""
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    script_directory = ScriptDirectory.from_config(alembic_config)
    expected_revision = script_directory.get_current_head()

    with engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()

    if current_revision != expected_revision:
        raise RuntimeError(
            "Database schema is not at the expected revision. "
            f"Current revision: {current_revision or 'none'}, expected: {expected_revision}. "
            "Run 'alembic upgrade head' from the backend directory before starting the application."
        )
