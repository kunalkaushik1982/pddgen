r"""
Purpose: SQLAlchemy declarative base for backend persistence models.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\db\base.py
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
