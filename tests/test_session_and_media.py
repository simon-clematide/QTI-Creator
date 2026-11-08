"""Unit tests for QTI-Creator session and media service models."""

import os
from pathlib import Path
import tempfile
import zipfile

from qti_creator.media_service import analyze_session_media, safe_extract_media_zip
from qti_creator.session import (
    MediaSession,
    PackageState,
    QuizSession,
    cleanup_session_callback,
    resolve_session,
)


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


def test_render_editor_view_diagnostics_jump_buttons():
    from qti_creator.ui.editor import render_editor_view

    session = QuizSession()
    session.source = """## Question 1
Feedback: First line of feedback.

Second line of feedback leaking into question prompt.
- [X] Choice 1
- [ ] Choice 2
"""
    preview_html, status_bar_html, diag_html, dl_update, gen_update = render_editor_view(session)

    assert "Validation Warnings" in diag_html
    assert 'class="quiz-diag-jump-btn"' in diag_html
    assert 'data-line="2"' in diag_html
    assert "window.quizJumpToLine" in diag_html


def test_cross_tab_session_persistence_and_media_upload():
    """Verify editor source and media uploads persist across multipage route loads."""
    from types import SimpleNamespace
    from app import demo

    # Ensure no rogue <lambda> load listeners exist on any route
    load_fns = [
        f.fn.__name__
        for f in demo.fns.values()
        if any(evt == "load" for _, evt in f.targets) and f.fn is not None
    ]
    assert "<lambda>" not in load_fns
    assert load_fns == ["on_editor_loaded", "on_media_loaded"]

    # Locate the actual route handlers registered in demo.fns
    fn_by_name = {f.fn.__name__: f.fn for f in demo.fns.values() if f.fn is not None}
    on_editor_loaded = fn_by_name["on_editor_loaded"]
    on_source_changed = fn_by_name["on_source_changed"]
    on_media_loaded = fn_by_name["on_media_loaded"]
    on_upload_media_zip = fn_by_name["on_upload_media_zip"]

    fake_req = SimpleNamespace(
        cookies={"qti_creator_sid": "test_browser_sid_123"},
        headers={"user-agent": "pytest-browser/1.0"},
        client=SimpleNamespace(host="127.0.0.1"),
    )

    # 1. Load /editor (gr.State is None on initial page load)
    sess1, src1, *_ = on_editor_loaded(None, True, fake_req)
    assert isinstance(sess1, QuizSession)

    # 2. Edit source on /editor
    custom_md = (
        "# Hotspot Test\n\n## Q1\n![Diagram](quadrants.png)\n"
        "- [X] circle(25%, 25%, 15%) Target\n"
        "- [ ] rect(60%, 60%, 90%, 90%) Distractor\n"
    )
    sess2, *_ = on_source_changed(custom_md, sess1, True, fake_req)
    assert sess2 is sess1
    assert sess2.source == custom_md

    # 3. Navigate to /media (new page load -> gr.State is None, Gradio calls cleanup on old page state)
    cleanup_session_callback(sess1)
    assert Path(sess1.session_id).exists(), "Active shared session dir must not be deleted on tab switch"

    sess3, summary_html, tree_html, *_ = on_media_loaded(None, fake_req)
    assert sess3 is sess1
    assert sess3.source == custom_md
    assert "quadrants.png" in tree_html  # Missing reference detected from editor source

    # 4. Upload Media ZIP on /media and delete the original upload tempfile afterwards
    from tests.test_hotspot import make_png_bytes

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_up:
        tmp_upload_path = tmp_up.name
    with zipfile.ZipFile(tmp_upload_path, "w") as zf:
        zf.writestr("quadrants.png", make_png_bytes(400, 400))

    try:
        sess4, summary_after, tree_after, _, _, include_cb = on_upload_media_zip(
            tmp_upload_path, None, fake_req
        )
    finally:
        # Simulate Gradio cleaning up temporary upload file
        if os.path.exists(tmp_upload_path):
            os.remove(tmp_upload_path)

    assert sess4 is sess1
    assert include_cb is True
    assert sess4.media.include_in_package is True
    assert sess4.media.zip_path is not None and os.path.exists(sess4.media.zip_path)
    assert any(f.relative_path == "quadrants.png" and f.status == "referenced" for f in sess4.media.files)

    # 5. Navigate back to /editor (new page load -> gr.State is None)
    sess5, loaded_src, preview_html, status_html, diag_html, *_ = on_editor_loaded(
        None, True, fake_req
    )
    assert sess5 is sess1
    assert loaded_src == custom_md
    assert "Valid · 1 question" in status_html
    assert "Validation Errors" not in diag_html
