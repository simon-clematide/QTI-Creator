"""QTI-Creator: Hugging Face Space Gradio Application.

Author quizzes in clean, natural Markdown and download OpenOLAT-compatible
IMS QTI 2.1 packages.

Architecture overview:
- Gradio Web UI with dual-pane layout: editor/controls on the left, live preview on the right.
- Staged parsing pipeline (`src.parser`) converting QuizMD into typed model structures (`src.model`).
- Media resolution and preflight packaging (`src.media`) for web and embedded assets.
- Standardized IMS QTI 2.1 packaging (`src.packager`, `src.qti21`) for OpenOLAT import.
"""


import os
import tempfile
import gradio as gr

from src.examples import EXAMPLES, SAMPLE_ALL_TYPES
from src.media import preflight_media
from src.packager import create_qti_package
from src.parser import parse_quizmd
from src.preview import render_quiz_preview_html
from src.validation import Severity


def update_preview_and_validate(
    text: str,
    show_relative_images: bool,
    media_zip_file,
    render_math: bool = True,
):
    """Run parsing and media validation, returning preview HTML and diagnostics Markdown."""
    if not text or not text.strip():
        return (
            "<p style='color: #64748b; font-style: italic;'>Enter questions or load an example to begin.</p>",
            "ℹ️ No content provided.",
        )

    quiz, diagnostics = parse_quizmd(text)

    # If show_relative_images is requested and media_zip_file is uploaded, extract relative images for preview
    asset_map = None
    media_zip_bytes = None
    if media_zip_file is not None:
        try:
            with open(media_zip_file.name, "rb") as f:
                media_zip_bytes = f.read()
        except Exception:
            pass

    # Perform media preflight:
    # If show_relative_images is True and we have a media zip, preflight resolves relative assets into memory
    if show_relative_images and media_zip_bytes:
        media_res = preflight_media(quiz, include_media=True, media_zip_bytes=media_zip_bytes)
        asset_map = {src: asset.data_uri for src, asset in media_res.resolved_assets.items()}
    else:
        media_res = preflight_media(quiz, include_media=False)

    preview_html = render_quiz_preview_html(
        quiz,
        asset_map=asset_map,
        render_math=render_math,
    )
    diagnostics.extend(media_res.diagnostics)

    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    warnings = [d for d in diagnostics if d.severity == Severity.WARNING]

    msg_lines = []
    if errors:
        msg_lines.append("### ⚠️ Validation")
        for err in errors:
            msg_lines.append(f"- {str(err)}")
    elif warnings:
        msg_lines.append(f"### ⚠️ Validation\n\n{len(quiz.questions)} question(s) parsed with warnings:")
        for warn in warnings:
            msg_lines.append(f"- {str(warn)}")
    else:
        msg_lines.append(f"### ✅ Validation\n\n{len(quiz.questions)} question(s) parsed with zero issues.")

    media_summary = media_res.summary_text()
    if media_summary:
        msg_lines.append(f"\n{media_summary}")

    status_md = "\n".join(msg_lines)
    return preview_html, status_md


def convert_and_download(text: str, include_media: bool, media_zip_file):
    """Generate the QTI 2.1 ZIP package and return the temporary file path for download."""
    if not text or not text.strip():
        return gr.update(visible=False), "❌ Cannot generate package: text is empty.", gr.update(visible=False), False

    quiz, diagnostics = parse_quizmd(text)
    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    if errors:
        error_details = "\n".join(f"- {str(e)}" for e in errors)
        return gr.update(visible=False), f"❌ **Fix errors before downloading:**\n{error_details}", gr.update(visible=False), False

    media_zip_bytes = None
    if media_zip_file is not None:
        try:
            with open(media_zip_file.name, "rb") as f:
                media_zip_bytes = f.read()
        except Exception as e:
            return gr.update(visible=False), f"❌ **Cannot read uploaded Media ZIP:** {e}", gr.update(visible=False), False

    # Perform media preflight (passive if include_media is False, active if True)
    media_res = preflight_media(quiz, include_media=include_media, media_zip_bytes=media_zip_bytes)
    if include_media and media_res.has_errors:
        media_errors = [d for d in media_res.diagnostics if d.severity == Severity.ERROR]
        error_details = "\n".join(f"- {str(e)}" for e in media_errors)
        return gr.update(visible=False), f"❌ **Media Preflight Failed:**\n{error_details}", gr.update(visible=False), False

    # Create temporary zip file
    safe_name = "".join(c if c.isalnum() else "_" for c in quiz.title).strip("_") or "qti_quiz"
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, f"{safe_name}_qti21.zip")

    create_qti_package(quiz, zip_path, media_preflight=media_res)
    
    media_info = f"\n{media_res.summary_text()}" if media_res.summary_text() else ""
    return (
        gr.update(value=zip_path, visible=True),
        f"🎉 **Success!** Download your OpenOLAT QTI package below.{media_info}",
        gr.update(visible=False),
        True,
    )


def load_example(example_name: str):
    """Load sample text into the editor."""
    return EXAMPLES.get(example_name, "")


def load_file(file_obj):
    """Load uploaded file into the editor."""
    if file_obj is None:
        return ""
    with open(file_obj.name, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# UI Construction with Gradio
# ---------------------------------------------------------------------------

theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="blue",
    font=[
        gr.themes.GoogleFont("Source Sans 3"),
        "Source Sans Pro",
        "Arial",
        "sans-serif",
    ],
)

_MATHJAX_HEAD = """
<script>
window.MathJax = {
  tex: {
    inlineMath: [['$', '$']],
    displayMath: [['$$', '$$']]
  },
  options: {
    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
  },
  svg: { fontCache: 'global' }
};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
"""

APP_CSS = """
/* Surgical override for static Gradio markdown/header blocks to eliminate thin spurious scrollbar gutters */
.no-scroll-block,
.no-scroll-block > div,
.no-scroll-block .prose {
  overflow: visible !important;
  overflow-y: visible !important;
}

.no-scroll-block h1,
.no-scroll-block h2,
.no-scroll-block h3,
.no-scroll-block h4,
.no-scroll-block h5,
.no-scroll-block h6 {
  overflow: visible !important;
  margin-top: 0.25rem !important;
  margin-bottom: 0.25rem !important;
}

/* Compact upload field styling: reduce font size and padding */
.svelte-1vmd51o {
  font-size: 0.85rem !important;
}
.svelte-1vmd51o .icon-wrap {
  width: 28px !important;
  height: 28px !important;
}
.svelte-8prmba {
  min-height: 85px !important;
}

/* Outdated package banner styling: style outer block without inner double-border */
.outdated-banner.block {
  background-color: #fefce8 !important;
  border: 1px solid #fde047 !important;
  border-radius: 6px !important;
  padding: 8px 12px !important;
  color: #854d0e !important;
  margin-bottom: 8px !important;
}
.outdated-banner .prose,
.outdated-banner .prose p {
  background: transparent !important;
  border: none !important;
  color: inherit !important;
  margin: 0 !important;
  padding: 0 !important;
}
"""

# JS called after each preview update to re-typeset the newly injected HTML.
# MathJax.typesetPromise() re-scans the DOM for $...$ and $$...$$ after innerHTML changes.
_MATHJAX_TYPESET_JS = "() => { if (window.MathJax && window.MathJax.typesetPromise) { window.MathJax.typesetPromise(); } }"

with gr.Blocks(title="QTI-Creator for OpenOLAT (Beta)", css=APP_CSS) as demo:
    gr.Markdown(
        "# QTI-Creator: Markdown to OpenOLAT QTI 2.1 (Beta)",
        elem_classes=["no-scroll-block"],
    )

    with gr.Accordion("Write quizzes in natural Markdown and export them directly to OpenOLAT.", open=False):
        gr.Markdown(
            """
            Export standardized 1EdTech Question & Test Interoperability (QTI) 2.1 ZIP packages ready for direct import into the OpenOLAT Question Bank or Course Tests. No XML or complex syntax required.

            **Specifications & Guides:**
            - [1EdTech QTI 2.1 specification](https://www.imsglobal.org/question/qtiv2p1/index.html)
            - [OpenOLAT eTesting](https://www.openolat.com/etesting)
            """
        )

    with gr.Tabs():
        # TAB 1: Editor & Converter
        with gr.TabItem("✏️ Quiz Editor & Converter"):
            with gr.Row():
                # LEFT COLUMN: Editor
                with gr.Column(scale=5):
                    with gr.Row():
                        example_dropdown = gr.Dropdown(
                            choices=list(EXAMPLES.keys()),
                            value="All Question Types (Showcase)",
                            label="Load Example",
                            scale=3,
                        )
                        file_upload = gr.File(
                            label="Upload .md / .txt",
                            file_types=[".md", ".txt"],
                            type="filepath",
                            scale=2,
                            height=105,
                        )

                    gr.Markdown("### 📝 QuizMD Source", elem_classes=["no-scroll-block"])
                    quiz_input = gr.Textbox(
                        value=SAMPLE_ALL_TYPES,
                        show_label=False,
                        placeholder="Write your quiz here in Markdown...",
                        lines=22,
                    )

                    with gr.Accordion("🖼️ Media Packaging", open=False):
                        include_media_cb = gr.Checkbox(
                            value=False,
                            label="Include media in QTI package",
                            info="Download remote images and include uploaded relative images to make the QTI package self-contained.",
                        )
                        show_relative_images_cb = gr.Checkbox(
                            value=False,
                            label="Show relative images in preview",
                            info="Extract and display images referenced by relative paths from the uploaded Media ZIP.",
                        )
                        media_zip_upload = gr.File(
                            label="Media ZIP",
                            file_types=[".zip"],
                            type="filepath",
                        )
                        gr.Markdown(
                            "<p style='color: #64748b; font-size: 0.85em; margin-top: -4px;'>Required only when referencing images by relative paths.</p>",
                            elem_classes=["no-scroll-block"],
                        )

                    with gr.Row():
                        btn_preview = gr.Button("🔄 Refresh Preview", variant="secondary")
                        btn_convert = gr.Button("📦 Generate OpenOLAT QTI Package", variant="secondary")

                # RIGHT COLUMN: Preview & Download
                with gr.Column(scale=5):
                    status_box = gr.Markdown("Ready.", elem_classes=["no-scroll-block"])
                    has_package_state = gr.State(value=False)
                    outdated_warning = gr.Markdown(
                        "⚠️ **Outdated Package:** Quiz source or media settings have changed since this package was generated. Click **'📦 Generate OpenOLAT QTI Package'** to re-generate with latest changes.",
                        visible=False,
                        elem_classes=["no-scroll-block", "outdated-banner"],
                    )
                    download_output = gr.File(
                        label="Download QTI 2.1 ZIP Package",
                        interactive=False,
                        visible=False,
                    )
                    with gr.Row():
                        gr.Markdown("### 👁️ Preview", scale=2, elem_classes=["no-scroll-block"])
                        render_math_cb = gr.Checkbox(
                            value=True,
                            label="Render math with MathJax (matches OpenOLAT)",
                            scale=3,
                        )
                    preview_display = gr.HTML()

            def on_source_or_media_changed(has_pkg: bool):
                """Show outdated warning if a package was previously generated."""
                if has_pkg:
                    return gr.update(visible=True)
                return gr.update(visible=False)

            # Event wiring
            example_dropdown.change(
                fn=load_example,
                inputs=[example_dropdown],
                outputs=[quiz_input],
                api_name=False,
            )

            file_upload.change(
                fn=load_file,
                inputs=[file_upload],
                outputs=[quiz_input],
                api_name=False,
            )

            # Changes to quiz source or media invalidate previously generated package
            for trigger in (
                quiz_input.change,
                include_media_cb.change,
                show_relative_images_cb.change,
                media_zip_upload.change,
            ):
                trigger(
                    fn=on_source_or_media_changed,
                    inputs=[has_package_state],
                    outputs=[outdated_warning],
                    api_name=False,
                )

            btn_preview.click(
                fn=update_preview_and_validate,
                inputs=[quiz_input, show_relative_images_cb, media_zip_upload, render_math_cb],
                outputs=[preview_display, status_box],
                api_name="preview",
            ).then(js=_MATHJAX_TYPESET_JS)

            show_relative_images_cb.change(
                fn=update_preview_and_validate,
                inputs=[quiz_input, show_relative_images_cb, media_zip_upload, render_math_cb],
                outputs=[preview_display, status_box],
                api_name=False,
            ).then(js=_MATHJAX_TYPESET_JS)

            media_zip_upload.change(
                fn=update_preview_and_validate,
                inputs=[quiz_input, show_relative_images_cb, media_zip_upload, render_math_cb],
                outputs=[preview_display, status_box],
                api_name=False,
            ).then(js=_MATHJAX_TYPESET_JS)

            render_math_cb.change(
                fn=update_preview_and_validate,
                inputs=[quiz_input, show_relative_images_cb, media_zip_upload, render_math_cb],
                outputs=[preview_display, status_box],
                api_name=False,
            ).then(js=_MATHJAX_TYPESET_JS)

            btn_convert.click(
                fn=convert_and_download,
                inputs=[quiz_input, include_media_cb, media_zip_upload],
                outputs=[download_output, status_box, outdated_warning, has_package_state],
                api_name="convert",
            )

            # Initial preview load
            demo.load(
                fn=update_preview_and_validate,
                inputs=[quiz_input, show_relative_images_cb, media_zip_upload, render_math_cb],
                outputs=[preview_display, status_box],
                api_name=False,
            ).then(js=_MATHJAX_TYPESET_JS)

        # TAB 2: Syntax Cheat Sheet
        with gr.TabItem("📖 Syntax Cheat Sheet"):
            gr.Markdown(
                """
                ### QuizMD Cheat Sheet
                Question types are inferred automatically from their Markdown syntax.

                > **Choice markers are case-sensitive:** Use uppercase `[X]` for Single Choice and lowercase `[x]` for Multiple Choice. Do not mix `[X]` and `[x]` within a question.

                <div style="overflow-x: auto; margin-top: 1rem; margin-bottom: 1rem;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.95em;">
                  <thead>
                    <tr style="border-bottom: 2px solid #cbd5e1;">
                      <th style="padding: 8px 12px;">Question Type</th>
                      <th style="padding: 8px 12px;">Syntax Pattern</th>
                      <th style="padding: 8px 12px;">Inference Rule</th>
                      <th style="padding: 8px 12px;">Default Scoring (1 pt)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                      <td style="padding: 8px 12px;"><strong>Single Choice</strong></td>
                      <td style="padding: 8px 12px;"><code>- [ ] Option<br>- [X] Correct Option</code></td>
                      <td style="padding: 8px 12px;">Exactly one uppercase <code>[X]</code></td>
                      <td style="padding: 8px 12px;">All or nothing</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                      <td style="padding: 8px 12px;"><strong>True / False</strong></td>
                      <td style="padding: 8px 12px;"><code>- [X] True<br>- [ ] False</code></td>
                      <td style="padding: 8px 12px;">Single Choice with exactly True and False</td>
                      <td style="padding: 8px 12px;">All or nothing</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                      <td style="padding: 8px 12px;"><strong>Multiple Choice</strong></td>
                      <td style="padding: 8px 12px;"><code>- [x] Option 1<br>- [x] Option 2</code></td>
                      <td style="padding: 8px 12px;">One or more lowercase <code>[x]</code></td>
                      <td style="padding: 8px 12px;">Partial credit for correct and incorrect selections</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                      <td style="padding: 8px 12px;"><strong>Kprim (Matrix)</strong></td>
                      <td style="padding: 8px 12px;"><code>- [+] True statement<br>- [-] False statement</code></td>
                      <td style="padding: 8px 12px;">Exactly 4 statements marked <code>[+]</code> or <code>[-]</code></td>
                      <td style="padding: 8px 12px;">4/4 = full, 3/4 = half, ≤2/4 = zero</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                      <td style="padding: 8px 12px;"><strong>Fill in the Blank</strong></td>
                      <td style="padding: 8px 12px;"><code>The word is {{gray | grey}}.</code></td>
                      <td style="padding: 8px 12px;">Answer embedded as <code>{{answer | alternative}}</code></td>
                      <td style="padding: 8px 12px;">Points divided equally across blanks</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                      <td style="padding: 8px 12px;"><strong>Numerical</strong></td>
                      <td style="padding: 8px 12px;"><code>= 9.81 ± 0.05</code></td>
                      <td style="padding: 8px 12px;">Answer line starts with <code>= number (optional ± tolerance)</code></td>
                      <td style="padding: 8px 12px;">All or nothing within tolerance</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                      <td style="padding: 8px 12px;"><strong>Order / Sequencing</strong></td>
                      <td style="padding: 8px 12px;"><code>1. [ ] First<br>1. [ ] Second<br>1. [ ] Third</code></td>
                      <td style="padding: 8px 12px;">Ordered list with empty <code>[ ]</code> (minimum 2 items)</td>
                      <td style="padding: 8px 12px;">All or nothing</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                      <td style="padding: 8px 12px;"><strong>Essay / Free Text</strong></td>
                      <td style="padding: 8px 12px;"><em>Question prompt with no answers</em></td>
                      <td style="padding: 8px 12px;">No answer syntax</td>
                      <td style="padding: 8px 12px;">Manual grading</td>
                    </tr>
                  </tbody>
                </table>
                </div>

                *All questions are worth 1 point by default. Use `Points: <number>` to change a question's weight.*
                """
            )

            with gr.Accordion("Quiz-level settings", open=False):
                gr.Markdown(
                    """
                    You can specify global quiz settings and defaults using either **Top-Level Header Metadata** (Way A) or **YAML Frontmatter** (Way B):

                    **Way A: Top-Level Header Metadata**
                    ```markdown
                    # Biology Exam
                    Version: 1.2.0
                    Language: en
                    Shuffle: yes
                    Topic: Molecular Biology
                    Keywords: cells, genetics, dna
                    ```

                    **Way B: YAML Frontmatter**
                    ```markdown
                    ---
                    title: Biology Exam
                    version: 1.2.0
                    language: en
                    shuffle: yes
                    topic: Molecular Biology
                    keywords: [cells, genetics, dna]
                    ---
                    ```
                    """
                )

            with gr.Accordion("Test Structure & Sections", open=False):
                gr.Markdown(
                    """
                    Long tests can be structured into multiple sections, generating OpenOLAT's native hierarchical navigation tree:
                    - **YAML `title:`** defines the overall test title.
                    - **`#` always starts an Assessment Section** (e.g. `# Section 1: Listening Comprehension`).
                    - **`##` always starts an Assessment Question** (e.g. `## Question Title`).
                    - **Section instructions / description**: Any content written between `# Section` and its first `## Question` is rendered as an OpenOLAT candidate rubric (`<rubricBlock>`), presented to the student at the beginning of that section.
                    - **Default fallback**: If no test title is given in YAML, the first `#` section title is automatically used as the test title. If questions appear without any `#` heading, an implicit default section is created.
                    - *Headings are strictly deterministic: `#` is always a section, `##` is always a question.*
                    """
                )

            with gr.Accordion("Multiple Choice Scoring", open=False):
                gr.Markdown(
                    r"""
                    Multiple Choice uses OpenOLAT partial scoring by default. Use `Scoring: all-correct` when full credit should require an exact response.

                    - **Partial credit (default)**: `Scoring: partial`
                      OpenOLAT's native proportional model:
                      - Each selected correct alternative adds $+\text{points} / N_{\text{correct}}$.
                      - Each selected distractor subtracts $-\text{points} / N_{\text{incorrect}}$.
                      - The question score is clamped between $0.0$ and $\text{Points}$ (never negative).
                      - If all options are correct, each selected option earns its equal share ($1/N$).
                    - **All or nothing**: `Scoring: all-correct`
                      Full points only if all correct answers and no incorrect answers are selected; otherwise 0.0 points.
                    - **Kprim evaluation**: If a question has exactly 4 statements to evaluate as true/false, use Kprim format (`- [+]` and `- [-]`) to get standard 4/4 = full, 3/4 = half, ≤2/4 = 0 scoring.
                    """
                )

            with gr.Accordion("Question Types & Formatting", open=False):
                gr.Markdown(
                    r"""
                    This guide covers details, edge cases, and syntax rules beyond the summary table above:

                    #### 1. Single Choice & Multiple Choice Details
                    - Do not mix `[X]` and `[x]` within the same question.
                    - True / False questions are parsed as Single Choice with `True` and `False` as the only choices.

                    #### 2. Kprim (4-Statement Matrix)
                    - Must contain exactly 4 statements, each marked with `- [+]` (true) or `- [-]` (false).

                    #### 3. Fill in the Blank with Alternatives
                    - Wrap target blanks in `{{...}}`.
                    - Provide acceptable synonyms or alternate spellings with pipe `|`: `{{gray | grey}}`.
                    - The first value is canonical; all alternatives receive equal full credit.
                    - **Escaping syntax characters**: Within `{{...}}`, use a backslash to escape syntax characters: `\\|` (literal `|`), `\\}` (literal `}`), and `\\\\` (literal `\\`), e.g., `{{answer containing \\}\\} braces | alternative}}`.

                    #### 4. Numerical Questions
                    - Specify the expected answer and optional tolerance: `= 9.81 ± 0.05` or `= 42` or `= 0.125 +- 0.001`.

                    #### 5. Order / Sequencing Questions
                    - Write an ordered list with empty boxes: `1. [ ] Step A`, `1. [ ] Step B`, `1. [ ] Step C` (minimum 2 items).
                    - **The order written in Markdown is the correct solution.**
                    - Learner-facing tiles are automatically scrambled (`shuffle="true"`).
                    - *Regular numbered lists (`1. Foo`, `2. Bar`) without `[ ]` remain standard Markdown text.*

                    #### 6. Essay / Free Text
                    - Write the prompt without any answer markers. OpenOLAT creates an open text response area for manual grading.

                    #### 7. Formulas & Code Blocks
                    - **Math Formulas**: Use MathJax-compatible TeX syntax — e.g. `$E = mc^2$`, `$$\frac{a}{b}$$`, `\sum`, `\text{...}`. OpenOLAT renders math natively via MathJax 3 (OpenOLAT ≥ 16.2). Arbitrary LaTeX packages and document-level commands are not supported.
                    - **Display Math**: `$$ \int_0^1 x^2 \, dx $$` on its own line.
                    - **Code**: Backticks `` `code` `` or fenced blocks ```` ```python ... ``` ````. Lines in code blocks are protected from quiz syntax parsing.
                    """
                )

            with gr.Accordion("Question-level settings", open=False):
                gr.Markdown(
                    """
                    Question metadata can be placed **before or after** choices/statements to override global quiz settings (case-insensitive):
                    - `Points: <number>` (default: 1)
                    - `Hint: <text>` (pre-submission hint shown during test-taking; supports Markdown & math)
                    - `Feedback: <text>` (post-submission explanation shown after test submission; supports Markdown & math)
                    - `Scoring: partial` or `all-correct` (for Multiple Choice questions; default: `partial`)
                    - `Shuffle: yes / no` (controls answer scrambling; default: `yes`)
                    - `Topic: <text>` (overrides quiz-level Topic in OpenOLAT)
                    - `Keywords: <kw1, kw2>` (overrides quiz-level Keywords in OpenOLAT)
                    - `Additional_Info: <text>` (overrides OpenOLAT Zusatzinformationen)
                    - `Language: <iso-code>` (e.g. `en`, `de`, `fr`)
                    - `Type: <type-name>` (optional explicit question type override)
                    - `Identifier: <custom_id>` (optional, default: auto-generated)

                    ```markdown
                    ## Order the biological taxonomy ranks
                    Points: 2
                    Topic: Taxonomy
                    Keywords: biology, classification
                    1. [ ] Domain
                    1. [ ] Kingdom
                    1. [ ] Phylum
                    1. [ ] Class
                    Feedback: Remember "Dear King Philip Came Over For Good Soup".
                    ```
                    """
                )

            with gr.Accordion("Media & Images", open=False):
                gr.Markdown(
                    """
                    Embed images anywhere in question prompts, choices, or feedback using standard Markdown:
                    - **Remote URL**: `![Diagram](https://example.org/diagram.png)`
                    - **Relative Path**: `![Tree](tree.png)` or `![Chart](images/chart.png)`
                    - **Image Sizing (HackMD Syntax)**:
                      - Fixed width: `![Diagram](diagram.png =300x)`
                      - Proportional width: `![Chart](chart.png =30%x)`
                      - Width and height: `![Photo](photo.png =400x250)`
                      - *(Note: A space before `=` is required; aspect ratio is preserved when omitting height or width).*

                    **Packaging Behavior:**
                    - By default (*Include media* OFF), image references remain external URLs / relative links in the QTI package.
                    - When *Include media* is enabled, remote images are downloaded and relative images are extracted from the uploaded **Media ZIP** to create a fully self-contained QTI package for OpenOLAT.
                    """
                )

        # TAB 3: OpenOLAT Import Guide
        with gr.TabItem("🚀 How to Import into OpenOLAT"):
            gr.Markdown(
                """
                ## 🚀 Using your QTI test in OpenOlat

                QTI-Creator generates an **IMS QTI 2.1 test package** that can be imported directly into OpenOlat.

                The simplest way to use it is to import the generated ZIP directly into a **Test** or **Self-test** course element.

                ### Quickest route: add the test directly to a course

                1. In QTI-Creator, click **📦 Generate OpenOLAT QTI Package** and download the generated `.zip` file.
                2. Open your course in OpenOlat and enter the **Course editor**.
                3. Add a **Test** or **Self-test** course element.
                4. Open its **Test configuration**.
                5. Choose the option to **select or import a test** and import the `.zip` generated by QTI-Creator.
                6. Configure the test options you need.
                7. **Preview the test**, then publish the course when you are ready to make it available to participants.

                📖 OpenOlat documentation: <a href="https://docs.openolat.org/manual_user/learningresources/Course_Element_Test/" target="_blank" rel="noopener noreferrer">Course element "Test"</a>
                """
            )

            with gr.Accordion("▶ Test or Self-test?", open=False):
                gr.Markdown(
                    """
                    Both course elements use an OpenOlat **Test learning resource**, so you can use the same QTI-Creator package for either one. The difference is how the test is used and how OpenOlat handles the results.

                    | | Test | Self-test |
                    |---|---|---|
                    | **Typical use** | Assessment | Practice and self-assessment |
                    | **Results** | Associated with participants | Stored anonymously |
                    | **Attempts** | Configurable | Can be repeated as often as needed |
                    | **Teacher assessment** | Results can be assessed | No personalized learner results |

                    **Rule of thumb:** Use **Test** when results should be associated with individual participants. Use **Self-test** when learners should be able to practice without personalized results being stored for teachers.

                    📖 OpenOlat documentation: <a href="https://docs.openolat.org/manual_user/learningresources/Course_Element_Test/" target="_blank" rel="noopener noreferrer">Test and Self-test</a>
                    """
                )

            with gr.Accordion("▶ Import as a reusable Test learning resource", open=False):
                gr.Markdown(
                    """
                    If you want to keep the test independently of a particular course or reuse it in multiple courses, import the generated package into the OpenOlat **Authoring** area.

                    1. Open **Authoring** in OpenOlat.
                    2. Choose **Import file**.
                    3. Upload the `.zip` generated by QTI-Creator.
                    4. OpenOlat imports the compatible package as a learning resource.
                    5. You can then select the imported test when configuring a **Test** or **Self-test** course element.

                    This route is useful when you want the test to exist as a reusable learning resource rather than importing it while configuring one particular course.

                    📖 OpenOlat documentation: <a href="https://docs.openolat.org/manual_user/area_modules/authoring_new_course/" target="_blank" rel="noopener noreferrer">Create and import learning resources</a> · <a href="https://docs.openolat.org/manual_user/area_modules/Authoring/" target="_blank" rel="noopener noreferrer">Authoring overview</a>
                    """
                )

            with gr.Accordion("▶ Import questions into the Question Bank", open=False):
                gr.Markdown(
                    """
                    Use the **Question Bank** when you want to manage and reuse the **individual questions**, rather than simply use the generated test as a whole.

                    1. Open the **Question Bank** in OpenOlat.
                    2. Click **Import**.
                    3. Choose **ZIP-file from local computer**.
                    4. Upload the `.zip` generated by QTI-Creator.
                    5. OpenOlat imports the QTI 2.1 questions from the package into the Question Bank.

                    The Question Bank is useful when you want to organize questions into pools or lists, edit individual questions, or reuse them when constructing other tests.

                    OpenOlat also supports importing questions from an existing Test learning resource in the Authoring area.

                    📖 OpenOlat documentation: <a href="https://docs.openolat.org/manual_user/area_modules/Question_Bank_Import_Questions/" target="_blank" rel="noopener noreferrer">Import questions into the Question Bank</a>
                    """
                )

            with gr.Accordion("▶ Understanding tests in OpenOlat", open=False):
                gr.Markdown(
                    """
                    There are three useful ways to think about the generated QTI package:

                    ### Test / Self-test course element
                    A **course element** is where learners encounter the test inside a course. For the quickest workflow, add a Test or Self-test course element and import the QTI-Creator package there.

                    ### Test learning resource
                    The **Test learning resource** contains the test itself. Learning resources can be managed independently in the Authoring area and reused in courses.

                    ### Question Bank
                    The **Question Bank** manages individual questions. Use it when you want to reuse, organize, or edit questions independently of the complete test.

                    | Your goal | Recommended route |
                    |---|---|
                    | Put this quiz into a course | **Course → Test / Self-test → Import** |
                    | Keep a reusable complete test | **Authoring → Import file** |
                    | Manage or reuse individual questions | **Question Bank → Import** |

                    ```text
                    QTI-Creator
                         │
                         ▼
                    QTI 2.1 ZIP
                         │
                         ├──► Course → Test / Self-test
                         │         quickest route
                         │
                         ├──► Authoring → Test learning resource
                         │         reusable complete test
                         │
                         └──► Question Bank
                                   reusable individual questions
                    ```

                    📖 OpenOlat documentation: <a href="https://docs.openolat.org/manual_user/learningresources/" target="_blank" rel="noopener noreferrer">OpenOlat learning resources</a>
                    """
                )

            with gr.Accordion("▶ Troubleshooting imports", open=False):
                gr.Markdown(
                    """
                    ### OpenOlat rejects the ZIP
                    Return to QTI-Creator and check the **Validation** result. Fix any reported errors and generate the package again.

                    Upload the `.zip` file generated by QTI-Creator directly. **Do not unpack the ZIP before importing it into OpenOlat.**

                    ### The test imports, but does not behave as expected
                    Preview the test in OpenOlat before publishing the course.

                    Also check the settings of the **Test** or **Self-test** course element. OpenOlat provides course-level settings for test behavior and result display in addition to the information stored in the QTI package.

                    ### The test is not visible to learners
                    Make sure the course and the relevant course element have been published and that the intended participants have access to the course.

                    📖 OpenOlat documentation: <a href="https://docs.openolat.org/manual_user/learningresources/Tests_at_course_level/" target="_blank" rel="noopener noreferrer">Tests at course level</a>
                    """
                )

if __name__ == "__main__":
    demo.launch(theme=theme, head=_MATHJAX_HEAD, css=APP_CSS)
