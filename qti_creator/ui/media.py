"""Media page for QTI-Creator: ZIP management, inspection, reference analysis, and configuration."""

from __future__ import annotations

import base64
import html
import os
from pathlib import Path
from typing import Tuple

import gradio as gr

from qti_creator.media_service import analyze_session_media, safe_extract_media_zip
from qti_creator.session import MediaFile, QuizSession


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def build_media_summary_html(session: QuizSession) -> str:
    """Build the Media summary text banner."""
    total_files = len(session.media.files)
    referenced = sum(1 for f in session.media.files if f.status == "referenced")
    unused = sum(1 for f in session.media.files if f.status == "unused")
    missing = len(session.media.missing)

    if total_files == 0 and missing == 0:
        return """
        <div class="media-summary-banner" style="color: #64748b;">
          No media files uploaded yet. Upload a ZIP archive containing images/assets referenced by your QuizMD.
        </div>
        """

    parts = [
        f"<strong>{total_files} file{'s' if total_files != 1 else ''}</strong>",
        f"<span style='color: #16a34a;'>✓ {referenced} referenced</span>",
    ]
    if unused > 0:
        parts.append(f"<span style='color: #d97706;'>⚠ {unused} unused</span>")
    if missing > 0:
        parts.append(f"<span style='color: #dc2626;'>✕ {missing} missing reference{'s' if missing != 1 else ''}</span>")

    summary_line = " &bull; ".join(parts)
    zip_name_info = f" ({html.escape(session.media.zip_filename)})" if session.media.zip_filename else ""

    return f"""
    <div class="media-summary-banner">
      {summary_line}{zip_name_info}
    </div>
    """


def build_media_files_dropdown_choices(session: QuizSession) -> list[tuple[str, str]]:
    """Build choices for file selector dropdown."""
    choices = []
    for f in session.media.files:
        status_icon = "✓" if f.status == "referenced" else "○"
        label = f"{status_icon} {f.relative_path} ({format_file_size(f.size)})"
        choices.append((label, f.relative_path))
    return choices


def build_media_tree_html(session: QuizSession) -> str:
    """Build an interactive hierarchy view of extracted files and missing references."""
    if not session.media.files and not session.media.missing:
        return "<p style='color: #94a3b8; font-style: italic; padding: 12px;'>No media uploaded.</p>"

    # Build tree from relative paths
    tree: dict = {}
    for f in session.media.files:
        parts = Path(f.relative_path).parts
        curr = tree
        for part in parts[:-1]:
            curr = curr.setdefault(part, {})
        curr[parts[-1]] = f

    def render_subtree(sub: dict, level: int = 0) -> str:
        html_out = ["<ul style='list-style: none; padding-left: " + ("0" if level == 0 else "18px") + "; margin: 4px 0;'>"]
        for key, val in sorted(sub.items(), key=lambda x: (isinstance(x[1], MediaFile), x[0])):
            if isinstance(val, dict):
                # Directory
                html_out.append(f"""
                <li style='margin: 3px 0;'>
                  <span style='font-weight: 600; color: #475569;'>📁 {html.escape(key)}</span>
                  {render_subtree(val, level + 1)}
                </li>
                """)
            else:
                # File
                f: MediaFile = val
                badge = ""
                if f.status == "referenced":
                    badge = "<span style='background: #dcfce7; color: #166534; font-size: 0.72rem; padding: 1px 6px; border-radius: 4px; font-weight: 600;'>Referenced</span>"
                else:
                    badge = "<span style='background: #f1f5f9; color: #64748b; font-size: 0.72rem; padding: 1px 6px; border-radius: 4px;'>Unused</span>"

                html_out.append(f"""
                <li style='margin: 4px 0; display: flex; align-items: center; justify-content: space-between; gap: 8px;'>
                  <span style='color: #1e293b; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 0.88rem;'>
                    📄 {html.escape(f.name)}
                  </span>
                  <div>
                    <span style='color: #94a3b8; font-size: 0.78rem; margin-right: 6px;'>{format_file_size(f.size)}</span>
                    {badge}
                  </div>
                </li>
                """)
        html_out.append("</ul>")
        return "".join(html_out)

    tree_html = render_subtree(tree)

    # Missing section
    missing_html = ""
    if session.media.missing:
        items = []
        for m in session.media.missing:
            ref_str = ", ".join(m.referenced_by)
            items.append(f"""
            <li style='margin: 4px 0;'>
              <span style='color: #dc2626; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 0.88rem; font-weight: 600;'>
                ✕ {html.escape(m.relative_path)}
              </span>
              <span style='color: #64748b; font-size: 0.8rem; margin-left: 6px;'>referenced by {html.escape(ref_str)}</span>
            </li>
            """)
        missing_html = f"""
        <div style='margin-top: 16px; border-top: 1px solid #fee2e2; padding-top: 10px;'>
          <div style='font-size: 0.88rem; font-weight: 700; color: #dc2626; margin-bottom: 6px;'>
            Missing References ({len(session.media.missing)})
          </div>
          <ul style='list-style: none; padding-left: 4px; margin: 0;'>
            {''.join(items)}
          </ul>
        </div>
        """

    return f"""
    <div style='max-height: 480px; overflow-y: auto; padding: 6px;'>
      {tree_html}
      {missing_html}
    </div>
    """


def render_file_detail_html(session: QuizSession, selected_path: str) -> str:
    """Build the details panel HTML for a selected file."""
    if not selected_path:
        return """
        <div style="color: #94a3b8; font-style: italic; padding: 24px; text-align: center;">
          Select a file from the dropdown to inspect details and preview content.
        </div>
        """

    # Locate media file
    f: MediaFile | None = None
    for item in session.media.files:
        if item.relative_path == selected_path:
            f = item
            break

    if not f:
        return f"<div style='color: #dc2626;'>File not found: {html.escape(selected_path)}</div>"

    # Preview element
    preview_tag = ""
    ext = f.extension.lower()
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        try:
            with open(f.absolute_path, "rb") as img_file:
                b64 = base64.b64encode(img_file.read()).decode("ascii")
            data_uri = f"data:{f.mime_type or 'image/png'};base64,{b64}"
            preview_tag = f"""
            <div style="margin: 12px 0; text-align: center; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px;">
              <img src="{data_uri}" alt="{html.escape(f.name)}" style="max-height: 260px; max-width: 100%; object-fit: contain; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);" />
            </div>
            """
        except Exception as e:
            preview_tag = f"<div style='color: #dc2626;'>Error rendering image: {e}</div>"
    elif ext in (".mp3", ".wav", ".ogg"):
        try:
            with open(f.absolute_path, "rb") as aud_file:
                b64 = base64.b64encode(aud_file.read()).decode("ascii")
            data_uri = f"data:{f.mime_type or 'audio/mpeg'};base64,{b64}"
            preview_tag = f"""
            <div style="margin: 12px 0; padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;">
              <audio controls style="width: 100%;">
                <source src="{data_uri}" type="{f.mime_type or 'audio/mpeg'}">
                Your browser does not support the audio element.
              </audio>
            </div>
            """
        except Exception as e:
            preview_tag = f"<div style='color: #dc2626;'>Error rendering audio: {e}</div>"
    elif ext == ".svg":
        preview_tag = """
        <div style="margin: 12px 0; padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; color: #475569; font-size: 0.9rem;">
          SVG file (rendered directly inside the test when exported).
        </div>
        """
    else:
        preview_tag = f"""
        <div style="margin: 12px 0; padding: 16px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; color: #64748b; font-size: 0.9rem; text-align: center;">
          No inline preview available for {html.escape(ext.upper())} files.
        </div>
        """

    # Reference information
    if f.referenced_by:
        ref_items = "".join(f"<li style='margin-bottom: 2px;'>{html.escape(r)}</li>" for r in f.referenced_by)
        refs_html = f"""
        <div style="margin-top: 12px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 8px 12px; font-size: 0.88rem; color: #166534;">
          <strong>Referenced by:</strong>
          <ul style="margin: 4px 0 0 16px; padding: 0;">{ref_items}</ul>
        </div>
        """
    else:
        refs_html = """
        <div style="margin-top: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 12px; font-size: 0.88rem; color: #64748b;">
          <em>Not currently referenced by any question in QuizMD.</em>
        </div>
        """

    return f"""
    <div>
      <h3 style="margin: 0 0 4px 0; font-size: 1.15rem; color: #0f172a; word-break: break-all;">
        {html.escape(f.relative_path)}
      </h3>
      <div style="font-size: 0.85rem; color: #64748b; margin-bottom: 8px;">
        {f.extension.upper().lstrip('.')} &bull; {f.mime_type or 'unknown'} &bull; {format_file_size(f.size)}
      </div>

      {preview_tag}
      {refs_html}
    </div>
    """


def render_media_page(shared_session: gr.State, route_context: gr.Blocks | None = None) -> None:
    """Build the Media management and inspection workspace."""
    with gr.Column(elem_classes=["media-page-container"]):
        # Top Header
        with gr.Row(elem_classes=["media-header-bar"]):
            with gr.Column(scale=3):
                gr.HTML(
                    """
                    <h2 style="margin: 0; font-size: 1.4rem; font-weight: 700; color: #0f172a;">Media Workspace</h2>
                    <p style="margin: 2px 0 0 0; color: #64748b; font-size: 0.95rem;">
                      Upload and inspect assets referenced by your QuizMD source.
                    </p>
                    """
                )
            with gr.Column(scale=1, min_width=200):
                btn_upload_media_zip = gr.UploadButton(
                    "📎 Upload Media ZIP",
                    file_types=[".zip"],
                    file_count="single",
                    type="filepath",
                    size="sm",
                    variant="primary",
                )

        # Summary Banner
        summary_banner = gr.HTML(
            value=build_media_summary_html(QuizSession()),
            elem_classes=["no-scroll-block"],
        )

        # Workspace: Left File Hierarchy | Right File Details
        with gr.Row(elem_classes=["quiz-workspace-container"], equal_height=True):
            # Left: File Hierarchy
            with gr.Column(scale=5, min_width=380, elem_classes=["quiz-pane"]):
                gr.Markdown("**📂 Files & References**", elem_classes=["no-scroll-block"])
                tree_display = gr.HTML(
                    value=build_media_tree_html(QuizSession()),
                )

            # Right: File Detail Panel
            with gr.Column(scale=5, min_width=380, elem_classes=["quiz-pane"]):
                gr.Markdown("**🔍 File Details & Preview**", elem_classes=["no-scroll-block"])
                file_selector = gr.Dropdown(
                    choices=[],
                    value=None,
                    label="Select file to inspect",
                    container=False,
                )
                detail_display = gr.HTML(
                    value=render_file_detail_html(QuizSession(), ""),
                )

        # Package settings row
        with gr.Row(elem_classes=["quiz-media-settings-bar"]):
            include_media_cb = gr.Checkbox(
                value=False,
                label="Include media in exported QTI package",
            )
            resolve_preview_cb = gr.Checkbox(
                value=True,
                label="Resolve relative media in preview",
            )

        # Event: Upload Media ZIP
        def on_upload_media_zip(
            filepath: str,
            session: QuizSession,
        ) -> Tuple[QuizSession, str, str, gr.update, str]:
            if not filepath or not os.path.exists(filepath):
                return (
                    session,
                    build_media_summary_html(session),
                    build_media_tree_html(session),
                    gr.update(choices=build_media_files_dropdown_choices(session), value=None),
                    render_file_detail_html(session, ""),
                )

            # Extract to session-specific media root
            media_extract_root = str(Path(session.session_id) / "media")
            ok, msg, extracted = safe_extract_media_zip(filepath, media_extract_root)
            if ok:
                session.media.zip_path = filepath
                session.media.zip_filename = os.path.basename(filepath)
                session.media.extracted_root = media_extract_root
                analyze_session_media(session)

            choices = build_media_files_dropdown_choices(session)
            first_val = choices[0][1] if choices else None

            return (
                session,
                build_media_summary_html(session),
                build_media_tree_html(session),
                gr.update(choices=choices, value=first_val),
                render_file_detail_html(session, first_val or ""),
            )

        btn_upload_media_zip.upload(
            fn=on_upload_media_zip,
            inputs=[btn_upload_media_zip, shared_session],
            outputs=[shared_session, summary_banner, tree_display, file_selector, detail_display],
            api_name=False,
        )

        # Event: Select File from dropdown
        def on_file_selected(
            selected_path: str,
            session: QuizSession,
        ) -> str:
            return render_file_detail_html(session, selected_path)

        file_selector.change(
            fn=on_file_selected,
            inputs=[file_selector, shared_session],
            outputs=[detail_display],
            api_name=False,
        )

        # Checkbox settings handlers
        def on_include_media_changed(val: bool, session: QuizSession) -> QuizSession:
            session.media.include_in_package = bool(val)
            return session

        include_media_cb.change(
            fn=on_include_media_changed,
            inputs=[include_media_cb, shared_session],
            outputs=[shared_session],
            api_name=False,
        )

        def on_resolve_preview_changed(val: bool, session: QuizSession) -> QuizSession:
            session.media.resolve_in_preview = bool(val)
            return session

        resolve_preview_cb.change(
            fn=on_resolve_preview_changed,
            inputs=[resolve_preview_cb, shared_session],
            outputs=[shared_session],
            api_name=False,
        )

        def on_media_loaded(session: QuizSession):
            analyze_session_media(session)
            choices = build_media_files_dropdown_choices(session)
            first_val = choices[0][1] if choices else None
            return (
                build_media_summary_html(session),
                build_media_tree_html(session),
                gr.update(choices=choices, value=first_val),
                render_file_detail_html(session, first_val or ""),
                session.media.include_in_package,
                session.media.resolve_in_preview,
            )

        if route_context is not None and hasattr(route_context, "load"):
            route_context.load(
                fn=on_media_loaded,
                inputs=[shared_session],
                outputs=[summary_banner, tree_display, file_selector, detail_display, include_media_cb, resolve_preview_cb],
                api_name=False,
            )
