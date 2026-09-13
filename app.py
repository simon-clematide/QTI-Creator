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


def update_preview_and_validate(text: str, include_media: bool = False):
    """Parse the text, perform passive media preflight, render preview, and format status."""
    if not text or not text.strip():
        return (
            "<p style='color: #64748b; font-style: italic;'>Enter questions or load an example to begin.</p>",
            "ℹ️ No content provided.",
            None,
        )

    quiz, diagnostics = parse_quizmd(text)
    preview_html = render_quiz_preview_html(quiz)

    # Passive media preflight (zero network requests, provides inventory & scheme warnings)
    media_res = preflight_media(quiz, include_media=False)
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
                inputs=[quiz_input, include_media_cb],
                outputs=[preview_display, status_box],
                api_name="preview",
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
                inputs=[quiz_input, include_media_cb],
                outputs=[preview_display, status_box],
                api_name=False,
            )

        # TAB 2: Syntax Cheat Sheet
        with gr.TabItem("📖 Syntax Cheat Sheet"):
            gr.Markdown(
                """
                ### Minimal QuizMD Cheat Sheet
                QuizMD uses standard Markdown whenever possible. The question type is inferred automatically:

                | Question Type | Syntax Pattern | Inference Rule | Default Scoring (all questions = 1 pt) |
                | :--- | :--- | :--- | :--- |
                | **Single Choice** | `- [ ] Option`<br>`- [X] Correct Option` | Exactly 1 checked with `[X]` | All or nothing |
                | **Multiple Choice** | `- [x] Option 1`<br>`- [x] Option 2` | One or more checked with `[x]` | Partial credit based on correct and incorrect selections |
                | **True / False** | `- [X] True`<br>`- [ ] False` | Exactly 2 choices with "True" and "False" | All or nothing |
                | **Fill in the Blank** | `The word is {{gray \\| grey}}.` | Prompt contains `{{canonical \\| alt1 \\| alt2}}` | Points divided equally across blanks |
                | **Order / Sequencing** | `1. [ ] First`<br>`1. [ ] Second`<br>`1. [ ] Third` | Ordered task list with empty `[ ]` (min 2 items, source order is target sequence) | All or nothing |
                | **Numerical** | `= 9.81 ± 0.05` | Line starting with `= number (± tol)` | All or nothing within tolerance |
                | **Essay / Free Text** | Question prompt with no answers | No answer tokens | Manual grading |
                | **Kprim (Matrix)** | `- [+] True statement`<br>`- [-] False statement` | 4 statements marked `[+]` or `[-]` | 4/4 = full, 3/4 = half, ≤2/4 = zero |

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
                By default, Multiple Choice questions use OpenOLAT's native **partial credit** (`Scoring: partial`). You can configure alternative scoring methods globally or per question:

                - **Partial credit (default)**: `Scoring: partial`
                  Points are awarded proportionally for correct choices and deducted for incorrect choices (floored at 0).
                - **All or nothing**: `Scoring: all-correct`
                  Full points only if all correct answers and no incorrect answers are selected; otherwise 0 points.
                - **Kprim evaluation**: If a question has exactly 4 statements to evaluate as true/false, use Kprim format (`- [+]` and `- [-]`) to get standard 4/4 = full, 3/4 = half, ≤2/4 = 0 scoring.

                ---

                ### Question Metadata & Local Overrides
                Question metadata can be placed **before or after** choices/statements (case-insensitive):
                - `Points: 3` (default: 1)
                - `Scoring: partial` or `all-correct` (for Multiple Choice questions; default: `partial`)
                - `Feedback: Explanatory text shown to learners after submission` (supports Markdown & LaTeX math `$x^2$`)
                - `Shuffle: false` (disables QuizMD's default answer shuffling for this question)
                - `Topic: Genetics` (overrides quiz-level Topic in OpenOLAT)
                - `Keywords: rna, translation` (overrides quiz-level Keywords in OpenOLAT)
                - `Additional_Info: Custom note` (overrides OpenOLAT Zusatzinformationen)
                - `Language: en` (overrides question language)
                - `Type: multiple-choice` (optional type override)
                - `Identifier: custom_id` (optional, default: auto-generated)

                ```markdown
                ## Order the biological taxonomy ranks
                Points: 2
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
