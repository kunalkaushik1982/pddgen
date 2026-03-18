r"""
Purpose: Convert rendered DOCX files into PDF outputs.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\document_pdf_converter.py
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path

from fastapi import HTTPException, status


class DocumentPdfConverter:
    """Convert exported DOCX files into PDF documents."""

    _pdf_conversion_lock = threading.Lock()

    def convert(self, source_docx_path: Path, output_pdf_path: Path) -> None:
        conversion_errors: list[str] = []
        if self._convert_with_docx2pdf(source_docx_path, output_pdf_path, conversion_errors):
            return
        if self._convert_with_libreoffice(source_docx_path, output_pdf_path, conversion_errors):
            return

        error_suffix = f" Conversion details: {' | '.join(conversion_errors)}" if conversion_errors else ""
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "PDF export requires DOCX-to-PDF conversion support. "
                "Install Microsoft Word with the 'docx2pdf' package, or install LibreOffice and expose 'soffice' in PATH."
                f"{error_suffix}"
            ).strip(),
        )

    def _convert_with_docx2pdf(
        self,
        source_docx_path: Path,
        output_pdf_path: Path,
        conversion_errors: list[str],
    ) -> bool:
        try:
            from docx2pdf import convert
        except ImportError as error:
            conversion_errors.append(f"docx2pdf import failed: {error}")
            return False

        pythoncom = None
        com_initialized = False
        try:
            import pythoncom  # type: ignore

            pythoncom.CoInitialize()
            com_initialized = True
        except ImportError:
            pythoncom = None
        except Exception as error:
            conversion_errors.append(f"COM initialization failed: {error}")
            return False

        attempts = 2
        try:
            with self._pdf_conversion_lock:
                for attempt in range(1, attempts + 1):
                    try:
                        if output_pdf_path.exists():
                            output_pdf_path.unlink()
                        convert(str(source_docx_path), str(output_pdf_path))
                        if output_pdf_path.exists():
                            return True
                        conversion_errors.append(
                            f"docx2pdf attempt {attempt} completed without producing '{output_pdf_path.name}'"
                        )
                    except Exception as error:
                        conversion_errors.append(f"docx2pdf attempt {attempt} failed: {error}")
                    if attempt < attempts:
                        time.sleep(1.0)
            return False
        finally:
            if pythoncom is not None and com_initialized:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

    @staticmethod
    def _convert_with_libreoffice(
        source_docx_path: Path,
        output_pdf_path: Path,
        conversion_errors: list[str],
    ) -> bool:
        soffice_path = shutil.which("soffice")
        if not soffice_path:
            conversion_errors.append("LibreOffice 'soffice' not found in PATH")
            return False

        try:
            subprocess.run(
                [
                    soffice_path,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_pdf_path.parent),
                    str(source_docx_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as error:
            conversion_errors.append(f"LibreOffice conversion failed: {error}")
            return False

        generated_pdf = output_pdf_path.parent / f"{source_docx_path.stem}.pdf"
        if generated_pdf.exists() and generated_pdf != output_pdf_path:
            generated_pdf.replace(output_pdf_path)
        if not output_pdf_path.exists():
            conversion_errors.append("LibreOffice completed without producing the expected PDF output")
        return output_pdf_path.exists()
