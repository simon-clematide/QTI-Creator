"""In-memory ZIP packager for OpenOLAT QTI 2.1 content packages.

Rule: The imsmanifest.xml must reside at the absolute root of the ZIP archive.
Nested packaging causes OpenOLAT import failures.
"""

import io
import zipfile
from typing import Optional, Union
from src.media import MediaPreflightResult
from src.model import Quiz
from src.qti21 import generate_item_xml
from src.qti21.manifest import generate_manifest_xml
from src.qti21.package_config import generate_package_config_xml
from src.qti21.test import generate_test_xml


def create_qti_package(
    quiz: Quiz,
    output: Union[str, io.BytesIO],
    media_preflight: Optional[MediaPreflightResult] = None,
) -> None:
    """Package a Quiz into a standard OpenOLAT-compatible QTI 2.1 ZIP archive."""
    # Ensure quiz has no fatal errors
    diagnostics = quiz.validate()
    fatal_errors = [d for d in diagnostics if d.severity.value == "error"]
    if fatal_errors:
        from src.validation import QuizValidationError
        raise QuizValidationError("Cannot build package with validation errors.", fatal_errors)

    if media_preflight and media_preflight.include_media and media_preflight.has_errors:
        from src.validation import QuizValidationError
        media_errors = [d for d in media_preflight.diagnostics if d.severity.value == "error"]
        raise QuizValidationError("Cannot build package with media preflight errors.", media_errors)

    asset_map: Optional[dict] = None
    question_asset_map: Optional[dict] = None
    if media_preflight and media_preflight.include_media:
        asset_map = media_preflight.source_to_package_path
        question_asset_map = media_preflight.question_asset_map

    # If output is a filepath, open with standard zipfile; if BytesIO, write directly
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Root-level imsmanifest.xml
        manifest_xml = generate_manifest_xml(quiz, question_asset_map=question_asset_map)
        zf.writestr("imsmanifest.xml", manifest_xml.encode("utf-8"))

        # 2. Root-level Test.xml
        test_xml = generate_test_xml(quiz)
        zf.writestr("Test.xml", test_xml.encode("utf-8"))

        # 3. Root-level OpenOLAT QTI21PackageConfig.xml
        package_config_xml = generate_package_config_xml()
        zf.writestr("QTI21PackageConfig.xml", package_config_xml.encode("utf-8"))

        # 4. Assessment items
        for q in quiz.questions:
            item_xml = generate_item_xml(q, asset_map=asset_map)
            zf.writestr(f"{q.identifier}.xml", item_xml.encode("utf-8"))

        # 5. Packaged media files (if include_media is ON)
        if media_preflight and media_preflight.include_media:
            # Write unique resolved assets by filename
            written_paths = set()
            for asset in media_preflight.resolved_assets.values():
                if asset.filename not in written_paths:
                    zf.writestr(asset.filename, asset.data)
                    written_paths.add(asset.filename)


def create_qti_package_bytes(
    quiz: Quiz,
    media_preflight: Optional[MediaPreflightResult] = None,
) -> bytes:
    """Convenience helper returning the complete ZIP archive as raw bytes."""
    buffer = io.BytesIO()
    create_qti_package(quiz, buffer, media_preflight=media_preflight)
    return buffer.getvalue()
