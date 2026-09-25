"""Editor page for QTI-Creator: authoring, validation, preview, and QTI generation."""

from __future__ import annotations

import base64
from datetime import datetime
import html
import os
from pathlib import Path
import tempfile
from typing import Tuple

import gradio as gr

from qti_creator.media_service import analyze_session_media
from qti_creator.session import PackageState, QuizSession
from qti_creator.ui.styles import MATHJAX_TYPESET_JS
from src.examples import EXAMPLES, SAMPLE_ALL_TYPES
from src.media import preflight_media
from src.packager import create_qti_package
from src.parser import parse_quizmd
from src.preview import render_quiz_preview_html
from src.validation import Severity


def get_preview_asset_map(session: QuizSession) -> dict[str, str]:
    """Build base64 data URIs for relative media if resolution is enabled."""
    asset_map: dict[str, str] = {}
    if not session.media.resolve_in_preview or not session.media.extracted_root:
        return asset_map

    media_root = Path(session.media.extracted_root)
    if not media_root.exists():
        return asset_map

    for mf in session.media.files:
        if mf.status == "referenced" or mf.referenced_by:
            try:
                with open(mf.absolute_path, "rb") as f:
                    data = f.read()
                mime = mf.mime_type or "application/octet-stream"
                b64 = base64.b64encode(data).decode("ascii")
                data_uri = f"data:{mime};base64,{b64}"
                asset_map[mf.relative_path] = data_uri
                # Also map normalized form
                asset_map[os.path.normpath(mf.relative_path)] = data_uri
            except Exception:
                pass
    return asset_map


def format_editor_status_html(
    is_valid: bool,
    question_count: int,
    issue_count: int,
    media_info: str,
    package_status: str,  # "none" | "ready" | "outdated"
    package_filename: str | None = None,
) -> str:
    """Produce the compact horizontal command/status bar HTML."""
    if not is_valid:
        status_part = f"""
        <span style="color: #dc2626; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
          <span>✕</span> <span>{issue_count} validation issue{'s' if issue_count != 1 else ''}</span>
        </span>
        """
    else:
        status_part = f"""
        <span style="color: #16a34a; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
          <span>✓</span> <span>Valid · {question_count} question{'s' if question_count != 1 else ''}</span>
        </span>
        """

    media_part = ""
    if media_info:
        media_part = f"<span style='color: #64748b;'>· {html.escape(media_info)}</span>"

    pkg_part = ""
    if package_status == "ready" and package_filename:
        pkg_part = f"""
        <span style="background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: 500;">
          ✓ Package ready: <strong>{html.escape(package_filename)}</strong>
        </span>
        """
    elif package_status == "outdated":
        pkg_part = """
        <span style="background: #fefce8; color: #854d0e; border: 1px solid #fde047; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: 500;">
          ⚠ Package outdated (source or media changed)
        </span>
        """

    return f"""
    <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
      {status_part}
      {media_part}
      {pkg_part}
    </div>
    """


def render_editor_view(
    session: QuizSession,
    render_math: bool = True,
) -> Tuple[str, str, str, gr.update, gr.update]:
    """Generate editor view updates: preview_html, status_bar_html, diagnostics_markdown, download_btn, generate_btn."""
    analyze_session_media(session)
    source = session.source

    if not source or not source.strip():
        empty_preview = "<p style='color: #64748b; font-style: italic;'>Enter questions or load an example to begin.</p>"
        status_bar = format_editor_status_html(
            is_valid=True,
            question_count=0,
            issue_count=0,
            media_info="",
            package_status="none",
        )
        return (
            empty_preview,
            status_bar,
            "",
            gr.update(visible=False),
            gr.update(value="📦 Generate package", variant="secondary"),
        )

    quiz, diagnostics = parse_quizmd(source)
    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    warnings = [d for d in diagnostics if d.severity == Severity.WARNING]

    # Preflight media if any relative or remote media exists
    asset_map = get_preview_asset_map(session)

    # Check media preflight diagnostics
    media_res = preflight_media(quiz, include_media=session.media.include_in_package)
    diagnostics.extend(media_res.diagnostics)
    all_errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    all_warnings = [d for d in diagnostics if d.severity == Severity.WARNING]

    # Build media info snippet
    media_parts = []
    if session.media.files:
        media_parts.append(f"{len(session.media.files)} media files")
    if session.media.missing:
        media_parts.append(f"⚠ {len(session.media.missing)} missing media ref(s)")
    media_info = " · ".join(media_parts)

    is_valid = len(all_errors) == 0
    preview_html = render_quiz_preview_html(
        quiz,
        asset_map=asset_map,
        render_math=render_math,
    )

    # Check package state
    pkg_status = "none"
    pkg_filename = None
    if session.package.output_path and os.path.exists(session.package.output_path):
        if session.is_package_fresh():
            pkg_status = "ready"
            pkg_filename = session.package.filename or os.path.basename(session.package.output_path)
        else:
            pkg_status = "outdated"

    status_bar_html = format_editor_status_html(
        is_valid=is_valid,
        question_count=len(quiz.questions),
        issue_count=len(all_errors),
        media_info=media_info,
        package_status=pkg_status,
        package_filename=pkg_filename,
    )

    diag_lines = []
    if all_errors:
        diag_lines.append("⚠️ **Validation Errors:**")
        for err in all_errors:
            diag_lines.append(f"- {str(err)}")
    elif all_warnings:
        diag_lines.append(f"⚠️ **Validation Warnings** ({len(all_warnings)}):")
        for warn in all_warnings:
            diag_lines.append(f"- {str(warn)}")

    if session.media.missing:
        diag_lines.append("\n⚠️ **Missing Media References (check Media page):**")
        for m in session.media.missing:
            refs = ", ".join(m.referenced_by)
            diag_lines.append(f"- `{m.relative_path}` referenced by {refs}")

    diag_md = "\n".join(diag_lines)

    download_update = (
        gr.update(value=session.package.output_path, visible=True)
        if (pkg_status == "ready")
        else gr.update(visible=False)
    )

    gen_btn_text = "🔄 Regenerate" if pkg_status == "outdated" else "📦 Generate package"
    gen_btn_variant = "primary" if is_valid else "secondary"
    gen_update = gr.update(value=gen_btn_text, variant=gen_btn_variant)

    return preview_html, status_bar_html, diag_md, download_update, gen_update


def handle_generate_package(
    session: QuizSession,
) -> Tuple[QuizSession, gr.update, str, str, gr.update]:
    """Generate the QTI 2.1 package for the current session."""
    source = session.source
    if not source or not source.strip():
        preview, status_bar, diag, dl, gen = render_editor_view(session)
        return session, dl, status_bar, "❌ Cannot generate: QuizMD source is empty.", gen

    quiz, diagnostics = parse_quizmd(source)
    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    if errors:
        preview, status_bar, diag, dl, gen = render_editor_view(session)
        return session, dl, status_bar, f"❌ Cannot generate package: {len(errors)} validation errors must be fixed.", gen

    # Read media zip bytes if available and enabled
    media_zip_bytes = None
    if session.media.include_in_package and session.media.zip_path and os.path.exists(session.media.zip_path):
        try:
            with open(session.media.zip_path, "rb") as f:
                media_zip_bytes = f.read()
        except Exception:
            pass

    media_res = preflight_media(
        quiz,
        include_media=session.media.include_in_package,
        media_zip_bytes=media_zip_bytes,
    )
    if session.media.include_in_package and media_res.has_errors:
        preview, status_bar, diag, dl, gen = render_editor_view(session)
        return session, dl, status_bar, "❌ Media preflight failed. Check the Media page for missing assets.", gen

    # Destination inside session packages dir
    packages_dir = Path(session.session_id) / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c if c.isalnum() else "_" for c in quiz.title).strip("_") or "qti_quiz"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{safe_name}_{timestamp}_qti21.zip"
    zip_path = str(packages_dir / zip_filename)

    create_qti_package(quiz, zip_path, media_preflight=media_res)

    # Update package state
    session.package = PackageState(
        output_path=zip_path,
        filename=zip_filename,
        source_revision=session.source_revision,
        media_revision=session.media_revision,
        generated_at=datetime.now(),
    )

    preview, status_bar, diag, dl, gen = render_editor_view(session)
    return session, dl, status_bar, diag, gen


def render_editor_page(shared_session: gr.State, route_context: gr.Blocks | None = None) -> None:
    """Build the clean, compact Editor workspace."""
    with gr.Column(elem_classes=["quiz-editor-page-container"]):
        # Top row: Title + Actions (UploadButton, Example Dropdown)
        with gr.Row(elem_classes=["editor-header-row"]):
            gr.HTML(
                """
                <h2 style="margin: 0; font-size: 1.4rem; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 8px;">
                  <span>Quiz Editor</span>
                </h2>
                """
            )
            with gr.Row():
                example_dd = gr.Dropdown(
                    choices=list(EXAMPLES.keys()),
                    value="All Question Types (Showcase)",
                    show_label=False,
                    container=False,
                    scale=0,
                    min_width=220,
                )
                btn_upload_file = gr.UploadButton(
                    "📄 Upload .md / .txt",
                    file_types=[".md", ".txt"],
                    file_count="single",
                    type="filepath",
                    size="sm",
                    variant="secondary",
                )

        # Status & Export Bar: Command row
        with gr.Row(elem_classes=["quiz-command-bar"], elem_id="quiz_command_bar"):
            status_bar_html = gr.HTML(
                value="""
                <div style="color: #64748b; font-size: 0.92rem; font-weight: 500;">
                  Ready to parse QuizMD.
                </div>
                """,
                elem_classes=["quiz-status-pill"],
            )
            with gr.Row():
                btn_generate = gr.Button("📦 Generate package", variant="primary", size="sm")
                btn_download = gr.DownloadButton("📥 Download ZIP", visible=False, size="sm", variant="primary")

        # Validation diagnostics (collapsible / alert when errors exist)
        diagnostics_box = gr.Markdown("", elem_classes=["no-scroll-block"])

        # Workspace: Source (Left) | Preview (Right)
        with gr.Row(elem_classes=["quiz-workspace-container"], equal_height=True):
            # Left: Source
            with gr.Column(scale=1, min_width=480, elem_id="quiz_source_container", elem_classes=["quiz-pane"]):
                with gr.Row(elem_classes=["quiz-fullscreen-header"]):
                    gr.Markdown("**📝 QuizMD Source**", elem_classes=["no-scroll-block"])
                    btn_refresh = gr.Button("🔄 Refresh", variant="secondary", size="sm", elem_classes=["quiz-fullscreen-btn"])
                    btn_editor_fs = gr.Button("⛶", size="sm", elem_id="btn_editor_fs", elem_classes=["quiz-fullscreen-btn"])

                quiz_source = gr.Textbox(
                    value=SAMPLE_ALL_TYPES,
                    show_label=False,
                    placeholder="Write or paste your QuizMD here...",
                    lines=28,
                    elem_classes=["quiz-source-editor"],
                )

            # Right: Preview
            with gr.Column(scale=1, min_width=480, elem_id="quiz_preview_container", elem_classes=["quiz-pane"]):
                with gr.Row(elem_classes=["quiz-fullscreen-header"]):
                    gr.Markdown("**👁️ Preview**", elem_classes=["no-scroll-block"])
                    render_math_cb = gr.Checkbox(
                        value=True,
                        label="Render math",
                        container=False,
                        elem_classes=["quiz-header-checkbox"],
                    )
                    btn_preview_fs = gr.Button("⛶", size="sm", elem_id="btn_preview_fs", elem_classes=["quiz-fullscreen-btn"])

                preview_display = gr.HTML(elem_id="quiz_preview_display")

        # Fullscreen button handlers (Generic JS helper)
        btn_editor_fs.click(
            None,
            js="() => { window.toggleFullscreen('quiz_source_container', 'btn_editor_fs'); }",
        )
        btn_preview_fs.click(
            None,
            js="() => { window.toggleFullscreen('quiz_preview_container', 'btn_preview_fs'); }",
        )

        # Helper: Sync source change to session and re-render
        def on_source_changed(
            new_text: str,
            session: QuizSession,
            render_math: bool,
        ) -> Tuple[QuizSession, str, str, str, gr.update, gr.update]:
            session.source = new_text or ""
            preview, status_bar, diag, dl, gen = render_editor_view(session, render_math=render_math)
            return session, preview, status_bar, diag, dl, gen

        quiz_source.input(
            fn=on_source_changed,
            inputs=[quiz_source, shared_session, render_math_cb],
            outputs=[shared_session, preview_display, status_bar_html, diagnostics_box, btn_download, btn_generate],
            api_name=False,
        ).then(js=MATHJAX_TYPESET_JS)

        btn_refresh.click(
            fn=on_source_changed,
            inputs=[quiz_source, shared_session, render_math_cb],
            outputs=[shared_session, preview_display, status_bar_html, diagnostics_box, btn_download, btn_generate],
            api_name="refresh_preview",
        ).then(js=MATHJAX_TYPESET_JS)

        render_math_cb.change(
            fn=on_source_changed,
            inputs=[quiz_source, shared_session, render_math_cb],
            outputs=[shared_session, preview_display, status_bar_html, diagnostics_box, btn_download, btn_generate],
            api_name=False,
        ).then(js=MATHJAX_TYPESET_JS)

        # Example loading
        def on_load_example(name: str, session: QuizSession, render_math: bool):
            text = EXAMPLES.get(name, "")
            session.source = text
            preview, status_bar, diag, dl, gen = render_editor_view(session, render_math=render_math)
            return text, session, preview, status_bar, diag, dl, gen

        example_dd.change(
            fn=on_load_example,
            inputs=[example_dd, shared_session, render_math_cb],
            outputs=[quiz_source, shared_session, preview_display, status_bar_html, diagnostics_box, btn_download, btn_generate],
            api_name=False,
        ).then(js=MATHJAX_TYPESET_JS)

        # File upload via UploadButton
        def on_upload_file(filepath: str, session: QuizSession, render_math: bool):
            if not filepath or not os.path.exists(filepath):
                preview, status_bar, diag, dl, gen = render_editor_view(session, render_math=render_math)
                return session.source, session, preview, status_bar, diag, dl, gen
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                content = ""
            session.source = content
            preview, status_bar, diag, dl, gen = render_editor_view(session, render_math=render_math)
            return content, session, preview, status_bar, diag, dl, gen

        btn_upload_file.upload(
            fn=on_upload_file,
            inputs=[btn_upload_file, shared_session, render_math_cb],
            outputs=[quiz_source, shared_session, preview_display, status_bar_html, diagnostics_box, btn_download, btn_generate],
            api_name=False,
        ).then(js=MATHJAX_TYPESET_JS)

        # Package generation
        btn_generate.click(
            fn=handle_generate_package,
            inputs=[shared_session],
            outputs=[shared_session, btn_download, status_bar_html, diagnostics_box, btn_generate],
            api_name="generate_package",
        )

        def on_editor_loaded(session: QuizSession, render_math: bool):
            preview, status_bar, diag, dl, gen = render_editor_view(session, render_math=render_math)
            return session.source, preview, status_bar, diag, dl, gen

        if route_context is not None and hasattr(route_context, "load"):
            route_context.load(
                fn=on_editor_loaded,
                inputs=[shared_session, render_math_cb],
                outputs=[quiz_source, preview_display, status_bar_html, diagnostics_box, btn_download, btn_generate],
                api_name=False,
            ).then(js=MATHJAX_TYPESET_JS)
