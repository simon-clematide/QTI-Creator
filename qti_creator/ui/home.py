"""Home page for QTI-Creator: orientation and onboarding."""

import gradio as gr
from src.examples import EXAMPLES
from src.version import __version__, __release_date__


def render_home_page() -> None:
    """Render the calm, focused Home page."""
    with gr.Column(elem_classes=["home-container"]):
        # Header
        gr.HTML(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
              <h1 style="margin: 0; font-size: 2rem; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 10px;">
                <span>QTI-Creator</span>
                <span style="background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; font-size: 0.45em; font-weight: 600; padding: 2px 8px; border-radius: 9999px; vertical-align: middle;">Beta</span>
              </h1>
              <div style="font-size: 0.85em; color: #64748b; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
                <span style="background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; border: 1px solid #e2e8f0;">v{__version__}</span>
                <span>&bull;</span>
                <span>{__release_date__}</span>
              </div>
            </div>
            <p style="font-size: 1.15rem; color: #475569; margin-top: 0; margin-bottom: 1.25rem;">
              <strong>Markdown to OpenOLAT QTI 2.1</strong> &mdash; Write quizzes in natural Markdown and export them directly as OpenOLAT-compatible QTI 2.1 packages.
            </p>
            """
        )

        with gr.Row():
            btn_open_editor = gr.Button("🚀 Open Quiz Editor", variant="primary", scale=1)

        # Connect button to navigate to /editor
        btn_open_editor.click(
            None,
            js="() => { window.location.pathname = '/editor'; }",
        )

        gr.HTML("<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 1.75rem 0;'>")

        # How it works
        gr.Markdown(
            """
            ### How it works

            ```text
            Write or paste QuizMD  →  Preview & validate  →  Optionally manage Media  →  Export QTI 2.1
            ```

            ### Need help getting started?

            - **[Syntax Cheat Sheet](/syntax)**: Comprehensive overview of supported question types and syntax conventions.
            - **[Prompting Guide](/prompting)**: Ready-to-use AI prompts for converting teaching materials into QuizMD.
            - **[OpenOLAT Import](/openolat)**: Step-by-step guide to importing the generated packages into OpenOLAT courses or question banks.
            """
        )

        gr.HTML("<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 1.75rem 0;'>")

        # Explore examples
        gr.Markdown("### Explore Examples")
        example_select = gr.Dropdown(
            choices=list(EXAMPLES.keys()),
            value="All Question Types (Showcase)",
            label="Select an example to inspect its Markdown syntax:",
        )
        example_view = gr.Textbox(
            value=EXAMPLES.get("All Question Types (Showcase)", ""),
            lines=14,
            show_label=False,
            interactive=False,
            elem_classes=["quiz-source-editor"],
        )

        example_select.change(
            fn=lambda name: EXAMPLES.get(name, ""),
            inputs=[example_select],
            outputs=[example_view],
        )
