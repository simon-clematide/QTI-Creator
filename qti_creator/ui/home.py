"""Home page for QTI-Creator: orientation and onboarding."""

import gradio as gr
from qti_creator.ui.help_content import AUTHORING_WORKFLOW, VALIDATION_GUIDE
from qti_creator.examples import UI_EXAMPLES, HOTSPOT_EXAMPLE_NAME, HOTSPOT_MEDIA_ZIP, load_example
from src.version import __version__, __release_date__


def render_home_page(shared_session: gr.State) -> None:
    """Render the calm, focused Home page."""
    with gr.Column(elem_classes=["home-container"]):
        # Header
        gr.HTML(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
              <h1 style="margin: 0; font-size: 2rem; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 10px;">
                <span>QTI-Creator</span>
                <span style="background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; font-size: 0.45em; font-weight: 600; padding: 2px 8px; border-radius: 9999px; vertical-align: middle;" title="QTI-Creator preview release">Beta</span>
              </h1>
              <div style="font-size: 0.85em; color: #64748b; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
                <span style="background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; border: 1px solid #e2e8f0;" title="QTI-Creator version {__version__}">v{__version__}</span>
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
            btn_open_editor = gr.Button("🚀 Open Quiz Editor", variant="primary", scale=1, elem_id="btn_open_editor")

        # Connect button to navigate to /editor
        btn_open_editor.click(
            None,
            js="() => { window.location.pathname = '/editor'; }",
        )

        gr.HTML("<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 1.75rem 0;'>")

        # How it works
        gr.Markdown("### How it works\n\n" + AUTHORING_WORKFLOW)
        gr.Markdown("""### Need help getting started?

- **[Syntax Cheat Sheet](/syntax)**: Complete examples and supported question syntax.
- **[Prompting Guide](/prompting)**: AI drafting template and review checklist.
- **[OpenOLAT Import](/openolat)**: Import, learner-preview checks, and publication.
""")

        gr.HTML("<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 1.75rem 0;'>")

        with gr.Accordion("Validation, preview, and export status", open=False):
            gr.Markdown(VALIDATION_GUIDE)

        # Explore examples
        gr.Markdown("### Explore Examples")
        example_select = gr.Dropdown(
            choices=list(UI_EXAMPLES.keys()),
            value="All Question Types (Showcase)",
            label="Select an example to inspect its Markdown syntax:",
        )
        gr.Markdown("Loading an example replaces the current QuizMD and media in this browser session. Save your working source first. The hotspot example includes its image archive and enables media packaging.")
        with gr.Row():
            btn_load_example = gr.Button("Load selected example in Editor", variant="primary")
            example_media_download = gr.DownloadButton(
                "Download hotspot media ZIP",
                value=str(HOTSPOT_MEDIA_ZIP),
                visible=False,
            )
        btn_load_example.click(
            fn=load_example,
            inputs=[example_select, shared_session],
            outputs=[shared_session],
            api_name=False,
        ).success(None, js="() => { window.location.pathname = '/editor'; }")

        example_view = gr.Textbox(
            value=UI_EXAMPLES.get("All Question Types (Showcase)", ""),
            lines=14,
            show_label=False,
            interactive=False,
            elem_classes=["quiz-source-editor"],
        )

        example_select.change(
            fn=lambda name: (UI_EXAMPLES.get(name, ""), gr.update(visible=name == HOTSPOT_EXAMPLE_NAME)),
            inputs=[example_select],
            outputs=[example_view, example_media_download],
        )
