"""QTI-Creator: Hugging Face Space Gradio Application.

Author quizzes in clean, natural Markdown and download OpenOLAT-compatible
IMS QTI 2.1 packages.
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


def update_preview_and_validate(text: str, show_relative_images: bool = False, media_zip_file = None):
    """Parse the text, resolve images if requested, render preview, and format status."""
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

    preview_html = render_quiz_preview_html(quiz, asset_map=asset_map)
    diagnostics.extend(media_res.diagnostics)

    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    warnings = [d for d in diagnostics if d.severity == Severity.WARNING]

    msg_lines = []
    if errors:
        msg_lines.append("⚠️ **Validation Errors:**")
        for err in errors:
            msg_lines.append(f"- {str(err)}")
    elif warnings:
        msg_lines.append(f"✅ **{len(quiz.questions)} question(s) parsed.** (With warnings:)\n")
        for warn in warnings:
            msg_lines.append(f"- {str(warn)}")
    else:
        msg_lines.append(f"✅ **{len(quiz.questions)} question(s) successfully parsed with zero errors.**")

    media_summary = media_res.summary_text()
    if media_summary:
        msg_lines.append(f"\n{media_summary}")

    status_md = "\n".join(msg_lines)
    return preview_html, status_md


def convert_and_download(text: str, include_media: bool, media_zip_file):
    """Generate the QTI 2.1 ZIP package and return the temporary file path for download."""
    if not text or not text.strip():
        return None, "❌ Cannot generate package: text is empty."

    quiz, diagnostics = parse_quizmd(text)
    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    if errors:
        error_details = "\n".join(f"- {str(e)}" for e in errors)
        return None, f"❌ **Fix errors before downloading:**\n{error_details}"

    media_zip_bytes = None
    if media_zip_file is not None:
        try:
            with open(media_zip_file.name, "rb") as f:
                media_zip_bytes = f.read()
        except Exception as e:
            return None, f"❌ **Cannot read uploaded Media ZIP:** {e}"

    # Perform media preflight (passive if include_media is False, active if True)
    media_res = preflight_media(quiz, include_media=include_media, media_zip_bytes=media_zip_bytes)
    if include_media and media_res.has_errors:
        media_errors = [d for d in media_res.diagnostics if d.severity == Severity.ERROR]
        error_details = "\n".join(f"- {str(e)}" for e in media_errors)
        return None, f"❌ **Media Preflight Failed:**\n{error_details}"

    # Create temporary zip file
    safe_name = "".join(c if c.isalnum() else "_" for c in quiz.title).strip("_") or "qti_quiz"
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, f"{safe_name}_qti21.zip")

    create_qti_package(quiz, zip_path, media_preflight=media_res)
    
    media_info = f"\n{media_res.summary_text()}" if media_res.summary_text() else ""
    return zip_path, f"🎉 **Success!** Download your OpenOLAT QTI package below.{media_info}"


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

with gr.Blocks(title="QTI-Creator for OpenOLAT") as demo:
    gr.Markdown(
        """
        # 📝 QTI-Creator: Markdown to OpenOLAT QTI 2.1
        Write quizzes in natural Markdown. No XML or complex syntax required.
        Export standardized **IMS QTI 2.1 ZIP packages** ready for direct import into **OpenOLAT**.
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
                        )

                    quiz_input = gr.Textbox(
                        value=SAMPLE_ALL_TYPES,
                        label="QuizMD Source",
                        placeholder="Write your quiz here in Markdown...",
                        lines=22,
                    )

                    with gr.Accordion("🖼️ Media & Image Packaging (Optional)", open=False):
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
                            label="Media ZIP (Required when including images referenced by relative paths)",
                            file_types=[".zip"],
                            type="filepath",
                        )

                    with gr.Row():
                        btn_preview = gr.Button("🔄 Refresh Preview", variant="secondary")
                        btn_convert = gr.Button("📦 Generate OpenOLAT QTI Package", variant="primary")

                # RIGHT COLUMN: Preview & Download
                with gr.Column(scale=5):
                    status_box = gr.Markdown("Ready.")
                    download_output = gr.File(
                        label="Download QTI 2.1 ZIP Package",
                        interactive=False,
                    )
                    gr.Markdown("### 👁️ Question Preview")
                    preview_display = gr.HTML()

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

            btn_preview.click(
                fn=update_preview_and_validate,
                inputs=[quiz_input, show_relative_images_cb, media_zip_upload],
                outputs=[preview_display, status_box],
                api_name="preview",
            )

            show_relative_images_cb.change(
                fn=update_preview_and_validate,
                inputs=[quiz_input, show_relative_images_cb, media_zip_upload],
                outputs=[preview_display, status_box],
                api_name=False,
            )

            media_zip_upload.change(
                fn=update_preview_and_validate,
                inputs=[quiz_input, show_relative_images_cb, media_zip_upload],
                outputs=[preview_display, status_box],
                api_name=False,
            )

            btn_convert.click(
                fn=convert_and_download,
                inputs=[quiz_input, include_media_cb, media_zip_upload],
                outputs=[download_output, status_box],
                api_name="convert",
            )

            # Initial preview load
            demo.load(
                fn=update_preview_and_validate,
                inputs=[quiz_input, show_relative_images_cb, media_zip_upload],
                outputs=[preview_display, status_box],
                api_name=False,
            )

        # TAB 2: Syntax Cheat Sheet
        with gr.TabItem("📖 Syntax Cheat Sheet"):
            gr.Markdown(
                """
                ### QuizMD Cheat Sheet
                QuizMD uses standard Markdown whenever possible. Question types are detected automatically from the syntax:

                | Question Type | Syntax Pattern | Inference Rule | Default Scoring (1 point per question) |
                | :--- | :--- | :--- | :--- |
                | **Single Choice** | `- [ ] Option`<br>`- [X] Correct Option` | Exactly one option marked `[X]` | All or nothing |
                | **True / False** | `- [X] True`<br>`- [ ] False` | Single Choice with exactly True and False | All or nothing |
                | **Multiple Choice** | `- [x] Option 1`<br>`- [x] Option 2` | One or more options marked `[x]` | Partial credit for correct and incorrect selections |
                | **Kprim (Matrix)** | `- [+] True statement`<br>`- [-] False statement` | Exactly 4 statements marked `[+]` or `[-]` | 4/4 = full, 3/4 = half, ≤2/4 = zero |
                | **Fill in the Blank** | `The word is {{gray \\| grey}}.` | Answer embedded as `{{answer \\| alternative}}` | Points divided equally across blanks |
                | **Numerical** | `= 9.81 ± 0.05` | Answer line starts with `= number (optional ± tolerance)` | All or nothing within tolerance |
                | **Order / Sequencing** | `1. [ ] First`<br>`1. [ ] Second`<br>`1. [ ] Third` | Ordered list with empty `[ ]` (minimum 2 items) | All or nothing |
                | **Essay / Free Text** | Question prompt with no answers | No answer syntax | Manual grading |

                *All questions are worth 1 point by default. Use `Points: <number>` to change a question's weight.*

                ---

                ### Quiz Metadata & Shuffling
                You can specify quiz-level settings using either **Top-Level Header Metadata** (Way A) or **YAML Frontmatter** (Way B):

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
                ---

                ### Multiple Choice Scoring Options
                By default, Multiple Choice questions use OpenOLAT's native **partial credit** (`Scoring: partial`). You can configure alternative scoring methods globally in the quiz header/frontmatter or per question:

                - **Partial credit (default)**: `Scoring: partial`
                  OpenOLAT's native proportional model:
                  - Each selected correct alternative adds $+\text{points} / N_{\text{correct}}$.
                  - Each selected distractor subtracts $-\text{points} / N_{\text{incorrect}}$.
                  - The question score is clamped between $0.0$ and $\text{Points}$ (never negative).
                  - If all options are correct, each selected option earns its equal share ($1/N$).
                - **All or nothing**: `Scoring: all-correct`
                  Full points only if all correct answers and no incorrect answers are selected; otherwise 0.0 points.
                - **Kprim evaluation**: If a question has exactly 4 statements to evaluate as true/false, use Kprim format (`- [+]` and `- [-]`) to get standard 4/4 = full, 3/4 = half, ≤2/4 = 0 scoring.

                ---

                ### Question Types & Formatting Guide

                #### 1. Single Choice, True / False, and Multiple Choice
                - **Single Choice**: Mark exactly one correct option with uppercase `[X]`.
                - **True / False**: A Single Choice question with exactly two options, `True` and `False`.
                - **Multiple Choice**: Mark each correct option with lowercase `[x]`. Even one `[x]` makes the question Multiple Choice.
                - *Do not mix `[X]` and `[x]` in the same question.*

                #### 2. Kprim (4-Statement Matrix)
                - Write exactly 4 statements, marking each as true with `- [+]` or false with `- [-]`.
                - Scoring in OpenOLAT: 4/4 correct = full points, 3/4 correct = half points, ≤2/4 = 0 points.

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
                - **Inline Math**: `$E = mc^2$` (rendered natively via MathJax in OpenOLAT).
                - **Display Math**: `$$ \int_0^1 x^2 \, dx $$` on its own line.
                - **Code**: Backticks `` `code` `` or fenced blocks ```` ```python ... ``` ````. Lines in code blocks are protected from quiz syntax parsing.

                ---

                ### Question Metadata & Local Overrides
                Question metadata can be placed **before or after** choices/statements (case-insensitive):
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

                ---

                ### Media & Images
                Embed images anywhere in question prompts, choices, or feedback using standard Markdown:
                - **Remote URL**: `![Diagram](https://example.org/diagram.png)`
                - **Relative Path**: `![Tree](tree.png)` or `![Chart](images/chart.png)`

                **Packaging Behavior:**
                - By default (*Include media* OFF), image references remain external URLs / relative links in the QTI package.
                - When *Include media* is enabled, remote images are downloaded and relative images are extracted from the uploaded **Media ZIP** to create a fully self-contained QTI package for OpenOLAT.
                """
            )

        # TAB 3: OpenOLAT Import Guide
        with gr.TabItem("🚀 How to Import into OpenOLAT"):
            gr.Markdown(
                """
                ### Step-by-Step OpenOLAT Import Guide

                1. **Generate the Package**:
                   - Click **"Generate OpenOLAT QTI Package"** on the editor tab and download the `.zip` archive.
                
                2. **Import into OpenOLAT Question Bank**:
                   - Log into OpenOLAT.
                   - Open the **Question Bank** from the main navigation menu.
                   - Click the **Import** button in the top action bar.
                   - Select **"ZIP-file from local computer"**.
                   - Select your downloaded `.zip` file and click **Upload**.
                   - OpenOLAT will parse the `imsmanifest.xml` and add all questions directly to your pool!

                3. **Use in a Course Test**:
                   - In your course editor, add a **Test** course element.
                   - In the **Test configuration** tab, click **Select or create test**.
                   - You can either import the `.zip` directly as a learning resource or pull questions from your Question Bank.
                   - Publish your course and run the test!
                """
            )

if __name__ == "__main__":
    demo.launch(theme=theme)
