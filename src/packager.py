"""In-memory ZIP packager for OpenOLAT QTI 2.1 content packages.

Rule: The imsmanifest.xml must reside at the absolute root of the ZIP archive.
Nested packaging causes OpenOLAT import failures.
"""

import io
import zipfile
from typing import Union
from src.model import Quiz
from src.qti21 import generate_item_xml
from src.qti21.manifest import generate_manifest_xml
from src.qti21.package_config import generate_package_config_xml
from src.qti21.test import generate_test_xml


def create_qti_package(quiz: Quiz, output: Union[str, io.BytesIO]) -> None:
    """Package a Quiz into a standard OpenOLAT-compatible QTI 2.1 ZIP archive."""
    # Ensure quiz has no fatal errors
    diagnostics = quiz.validate()
    fatal_errors = [d for d in diagnostics if d.severity.value == "error"]
    if fatal_errors:
        from src.validation import QuizValidationError
        raise QuizValidationError("Cannot build package with validation errors.", fatal_errors)

    # If output is a filepath, open with standard zipfile; if BytesIO, write directly
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Root-level imsmanifest.xml
        manifest_xml = generate_manifest_xml(quiz)
        zf.writestr("imsmanifest.xml", manifest_xml.encode("utf-8"))

        # 2. Root-level Test.xml
        test_xml = generate_test_xml(quiz)
        zf.writestr("Test.xml", test_xml.encode("utf-8"))

        # 3. Root-level OpenOLAT QTI21PackageConfig.xml
        package_config_xml = generate_package_config_xml()
        zf.writestr("QTI21PackageConfig.xml", package_config_xml.encode("utf-8"))

        # 4. Assessment items
        for q in quiz.questions:
            item_xml = generate_item_xml(q)
            zf.writestr(f"{q.identifier}.xml", item_xml.encode("utf-8"))


def create_qti_package_bytes(quiz: Quiz) -> bytes:
    """Convenience helper returning the complete ZIP archive as raw bytes."""
    buffer = io.BytesIO()
    create_qti_package(quiz, buffer)
    return buffer.getvalue()
