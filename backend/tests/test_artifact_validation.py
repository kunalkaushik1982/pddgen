from __future__ import annotations

from io import BytesIO
import unittest

from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.services.artifact_validation import ArtifactValidationService


def build_upload(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


class ArtifactValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ArtifactValidationService()

    def test_rejects_invalid_file_extension(self) -> None:
        upload = build_upload("malware.exe", "application/octet-stream", b"not-allowed")

        with self.assertRaises(HTTPException) as error:
            self.service.validate_upload(upload=upload, artifact_kind="template")

        self.assertEqual(error.exception.status_code, 400)
        self.assertIn(".docx", error.exception.detail)

    def test_rejects_oversized_transcript(self) -> None:
        upload = build_upload(
            "transcript.txt",
            "text/plain",
            b"x" * (26 * 1024 * 1024),
        )

        with self.assertRaises(HTTPException) as error:
            self.service.validate_upload(upload=upload, artifact_kind="transcript")

        self.assertEqual(error.exception.status_code, 413)

    def test_accepts_valid_template_upload(self) -> None:
        upload = build_upload(
            "template.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"docx-content",
        )

        size = self.service.validate_upload(upload=upload, artifact_kind="template")
        self.assertEqual(size, len(b"docx-content"))

