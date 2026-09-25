"""QTI-Creator: Hugging Face Space Gradio Multipage Application.

Author quizzes in clean, natural Markdown and download OpenOLAT-compatible
IMS QTI 2.1 packages.
"""

from __future__ import annotations

import gradio as gr

from qti_creator.session import QuizSession, cleanup_session_callback
from qti_creator.ui.editor import render_editor_page
from qti_creator.ui.home import render_home_page
from qti_creator.ui.media import render_media_page
from qti_creator.ui.openolat import render_openolat_page
from qti_creator.ui.prompting import render_prompting_page
from qti_creator.ui.shared import THEME
from qti_creator.ui.styles import MATHJAX_HEAD, SHARED_CSS
from qti_creator.ui.syntax import render_syntax_page
from src.examples import SAMPLE_ALL_TYPES


def create_demo() -> gr.Blocks:
    """Build the multipage Gradio Blocks application."""
    demo = gr.Blocks(
        title="QTI-Creator for OpenOLAT",
        fill_width=True,
    )

    with demo:
        # Multipage navigation bar
        gr.Navbar(main_page_name="QTI-Creator")

        # Session state stored across pages for a user session
        shared_session = gr.State(
            value=lambda: QuizSession(source=SAMPLE_ALL_TYPES),
            delete_callback=cleanup_session_callback,
        )

        # Route 1: Home (/)
        render_home_page()

    # Route 2: Editor (/editor)
    with demo.route("Editor", path="/editor") as ed_route:
        render_editor_page(shared_session, route_context=ed_route)

    # Route 3: Media (/media)
    with demo.route("Media", path="/media") as med_route:
        render_media_page(shared_session, route_context=med_route)

    # Route 4: Syntax Cheat Sheet (/syntax)
    with demo.route("Syntax Cheat Sheet", path="/syntax"):
        render_syntax_page()

    # Route 5: Prompting (/prompting)
    with demo.route("Prompting", path="/prompting"):
        render_prompting_page()

    # Route 6: OpenOLAT Import (/openolat)
    with demo.route("OpenOLAT Import", path="/openolat"):
        render_openolat_page()

    return demo


demo = create_demo()

if __name__ == "__main__":
    demo.launch(
        theme=THEME,
        head=MATHJAX_HEAD,
        css=SHARED_CSS,
    )
