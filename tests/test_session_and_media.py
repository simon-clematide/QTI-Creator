"""Unit tests for QTI-Creator session and media service models."""

import os
from pathlib import Path
import tempfile
import zipfile

from qti_creator.media_service import analyze_session_media, safe_extract_media_zip
from qti_creator.session import MediaSession, PackageState, QuizSession


def test_session_lifecycle_and_freshness():
    session = QuizSession(source="# Sample\n\n## Q1\n- [X] A\n- [ ] B\n")
    initial_src_rev = session.source_revision
    initial_media_rev = session.media_revision

    assert not session.is_package_fresh()

    # Simulate generating a package
    session.package = PackageState(
        output_path="/tmp/fake_pkg.zip",
        filename="fake_pkg.zip",
        source_revision=initial_src_rev,
        media_revision=initial_media_rev,
    )
    assert session.is_package_fresh()

    # Editing source makes it outdated
    session.source += "\n## Q2\n- [X] True\n- [ ] False\n"
    assert not session.is_package_fresh()

    # Changing media settings makes it outdated
    session.source = "# Sample\n\n## Q1\n- [X] A\n- [ ] B\n"
    assert session.is_package_fresh()
    session.media.include_in_package = True
    assert not session.is_package_fresh()

    # Cleanup removes directory
    sess_dir = Path(session.session_id)
    assert sess_dir.exists()
    session.cleanup()
    assert not sess_dir.exists()


def test_safe_media_zip_extraction_and_analysis():
    session = QuizSession()
    session.source = """# Geography Quiz

## Identify the capital
![Map](images/capital.png)
- [X] Paris
- [ ] Lyon

## Flag of the country
![Flag](flag.svg)
- [X] Blue white red
"""
    # Create a test media zip
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
        zip_path = tmp_zip.name

    try:
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("images/capital.png", b"PNG dummy data")
            zf.writestr("unused_image.jpg", b"JPG dummy data")

        extract_root = str(Path(session.session_id) / "media")
        ok, msg, extracted = safe_extract_media_zip(zip_path, extract_root)
        assert ok, msg
        assert len(extracted) == 2

        session.media.zip_path = zip_path
        session.media.zip_filename = os.path.basename(zip_path)
        session.media.extracted_root = extract_root

        # Analyze
        analyze_session_media(session)

        # Check manifest
        file_map = {f.relative_path: f for f in session.media.files}
        assert "images/capital.png" in file_map
        assert file_map["images/capital.png"].status == "referenced"
        assert len(file_map["images/capital.png"].referenced_by) == 1

        assert "unused_image.jpg" in file_map
        assert file_map["unused_image.jpg"].status == "unused"

        # Check missing references
        missing_names = [m.relative_path for m in session.media.missing]
        assert "flag.svg" in missing_names
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        session.cleanup()


def test_safe_extract_zip_guards_traversal():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
        zip_path = tmp_zip.name

    target_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Dangerous path traversal
            zf.writestr("../evil.txt", b"evil content")

        ok, msg, extracted = safe_extract_media_zip(zip_path, target_dir)
        assert not ok
        assert "unsafe path" in msg.lower()
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(target_dir):
            import shutil
            shutil.rmtree(target_dir, ignore_errors=True)
