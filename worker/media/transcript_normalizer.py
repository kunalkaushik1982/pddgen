r"""
Purpose: Normalize transcript artifacts from txt, vtt, and docx into plain text.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\transcript_normalizer.py
"""

from pathlib import Path
import re
from zipfile import ZipFile


VTT_TIMESTAMP_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}$")
XML_TAG_PATTERN = re.compile(r"<[^>]+>")


class TranscriptNormalizer:
    """Normalize transcript artifacts into text suitable for extraction."""

    def normalize(self, storage_path: str, filename: str) -> str:
        """Normalize transcript content based on file type."""
        suffix = Path(filename).suffix.lower()
        path = Path(storage_path)

        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".vtt":
            return self._normalize_vtt(path)
        if suffix == ".docx":
            return self._normalize_docx(path)
        return path.read_text(encoding="utf-8", errors="ignore")

    def _normalize_vtt(self, path: Path) -> str:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        normalized_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.upper() == "WEBVTT" or stripped.isdigit():
                continue
            if VTT_TIMESTAMP_PATTERN.match(stripped):
                continue
            normalized_lines.append(stripped)
        return "\n".join(normalized_lines)

    def _normalize_docx(self, path: Path) -> str:
        with ZipFile(path) as archive:
            xml_content = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        text = XML_TAG_PATTERN.sub(" ", xml_content)
        collapsed = re.sub(r"\s+", " ", text)
        return collapsed.strip()
