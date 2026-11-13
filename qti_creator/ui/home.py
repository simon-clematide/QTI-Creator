"""Home page: entry points, examples, and progressively disclosed guidance."""

import gradio as gr
from qti_creator.ui.help_content import AUTHORING_WORKFLOW, VALIDATION_GUIDE
from qti_creator.examples import UI_EXAMPLES, HOTSPOT_EXAMPLE_NAME, HOTSPOT_MEDIA_ZIP, load_example
from qti_creator.core.version import __version__, __release_date__


def render_home_page(shared_session: gr.State) -> None:
    with gr.Column(elem_classes=["home-container"]):
        gr.HTML(f"""
            <div class="home-heading">
              <h1>QTI-Creator</h1>
              <span class="release-version">v{__version__} · {__release_date__}</span>
            </div>
            <p class="home-intro">Author quizzes in Markdown. Preview your questions and export a QTI 2.1 package for OpenOLAT.</p>
        """)
        with gr.Row(elem_classes=["home-actions"]):
            btn_open_editor = gr.Button("Open Editor", variant="primary", scale=0, min_width=140, elem_id="btn_open_editor")
        btn_open_editor.click(None, js="() => { window.location.pathname = '/editor'; }")

        gr.Markdown("### Try an example", elem_classes=["no-scroll-block"])
        example_select = gr.Dropdown(
            choices=list(UI_EXAMPLES.keys()), value="All Question Types (Showcase)",
            label="Example", show_label=False, container=False, elem_id="example_select",
        )
        gr.Markdown("Loading an example replaces your current source and media. Save your work first. The hotspot example includes its image archive.", elem_classes=["example-note", "no-scroll-block"])
        with gr.Row(elem_classes=["home-actions"]):
            btn_load_example = gr.Button("Load example in Editor", variant="secondary", scale=0, min_width=170)
            example_media_download = gr.DownloadButton(
                "Download hotspot media ZIP", value=str(HOTSPOT_MEDIA_ZIP),
                visible=False, scale=0, min_width=180, elem_id="btn_download_example_media",
            )
        btn_load_example.click(
            fn=load_example, inputs=[example_select, shared_session],
            outputs=[shared_session], api_name=False,
        ).success(None, js="() => { window.location.pathname = '/editor'; }")
        with gr.Accordion("Inspect example source", open=False):
            example_view = gr.Textbox(
                value=UI_EXAMPLES["All Question Types (Showcase)"], lines=10,
                show_label=False, interactive=False, elem_classes=["example-source"],
            )
        example_select.change(
            fn=lambda name: (UI_EXAMPLES.get(name, ""), gr.update(visible=name == HOTSPOT_EXAMPLE_NAME)),
            inputs=[example_select], outputs=[example_view, example_media_download],
        )

        gr.Markdown("""### From source to course
1. **Author.** Paste your QuizMD, upload a source file, or load an example.
2. **Inspect.** Review questions, answer keys, validation, and any media.
3. **Export.** Generate and download the ZIP, then preview it in OpenOLAT before publication.

[Syntax reference](/syntax) · [AI drafting guide](/prompting) · [OpenOLAT import](/openolat)
""", elem_classes=["no-scroll-block"])
        with gr.Accordion("Detailed authoring and export workflow", open=False):
            gr.Markdown(AUTHORING_WORKFLOW)
        with gr.Accordion("Validation, preview, and export status", open=False):
            gr.Markdown(VALIDATION_GUIDE)
