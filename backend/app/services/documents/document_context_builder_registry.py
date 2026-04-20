r"""
Purpose: Registry and resolver for document-specific export context builders.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_context_builder_registry.py
"""

from __future__ import annotations

from collections.abc import Callable

from app.services.documents.document_context_builder_interfaces import DocumentContextBuilder


class DocumentContextBuilderRegistry:
    """Resolve export context builders by document type."""

    def __init__(self) -> None:
        self._builders: dict[str, Callable[[], DocumentContextBuilder]] = {}

    def register(self, document_type: str, factory: Callable[[], DocumentContextBuilder]) -> None:
        self._builders[document_type] = factory

    def create(self, document_type: str) -> DocumentContextBuilder:
        try:
            return self._builders[document_type]()
        except KeyError as exc:
            available = ", ".join(sorted(self._builders)) or "none"
            raise ValueError(f"Unsupported document type '{document_type}'. Available builders: {available}.") from exc
