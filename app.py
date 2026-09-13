"""QTI-Creator: Hugging Face Space Gradio Application.

Author quizzes in clean, natural Markdown and download OpenOLAT-compatible
IMS QTI 2.1 packages.
"""

import os
import tempfile
import gradio as gr

from src.examples import EXAMPLES, SAMPLE_ALL_TYPES
from src.packager import create_qti_package
from src.parser import parse_quizmd
from src.preview import render_quiz_preview_html
from src.validation import Severity


def update_preview_and_validate(text: str):
    """Parse the text, validate invariants, render HTML preview, and format diagnostics."""
    if not text or not text.strip():
        return (
            "<p style='color: #64748b; font-style: italic;'>Enter questions or load an example to begin.</p>",
            "ℹ️ No content provided.",
            None,
        )

    quiz, diagnostics = parse_quizmd(text)
    preview_html = render_quiz_preview_html(quiz)

    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    warnings = [d for d in diagnostics if d.severity == Severity.WARNING]

    if errors:
        msg_lines = ["⚠️ **Validation Errors:**"]
        for err in errors:
            msg_lines.append(f"- {str(err)}")
        status_md = "\n".join(msg_lines)
    elif warnings:
        msg_lines = [f"✅ **{len(quiz.questions)} question(s) parsed.** (With warnings:)\n"]
        for warn in warnings:
            msg_lines.append(f"- {str(warn)}")
        status_md = "\n".join(msg_lines)
    else:
        status_md = f"✅ **{len(quiz.questions)} question(s) successfully parsed with zero errors.**"

    return preview_html, status_md


def convert_and_download(text: str):
    """Generate the QTI 2.1 ZIP package and return the temporary file path for download."""
    if not text or not text.strip():
        return None, "❌ Cannot generate package: text is empty."

    quiz, diagnostics = parse_quizmd(text)
    errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    if errors:
        error_details = "\n".join(f"- {str(e)}" for e in errors)
        return None, f"❌ **Fix errors before downloading:**\n{error_details}"

    # Create temporary zip file
    safe_name = "".join(c if c.isalnum() else "_" for c in quiz.title).strip("_") or "qti_quiz"
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, f"{safe_name}_qti21.zip")

    create_qti_package(quiz, zip_path)
    return zip_path, f"🎉 **Success!** Download your OpenOLAT QTI package below."


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
            )

            file_upload.change(
                fn=load_file,
                inputs=[file_upload],
                outputs=[quiz_input],
            )

            btn_preview.click(
                fn=update_preview_and_validate,
                inputs=[quiz_input],
                outputs=[preview_display, status_box],
            )

            btn_convert.click(
                fn=convert_and_download,
                inputs=[quiz_input],
                outputs=[download_output, status_box],
            )

            # Initial preview load
            demo.load(
                fn=update_preview_and_validate,
                inputs=[quiz_input],
                outputs=[preview_display, status_box],
            )

        # TAB 2: Syntax Cheat Sheet
        with gr.TabItem("📖 Syntax Cheat Sheet"):
            gr.Markdown(
                """
                ### Minimal QuizMD Cheat Sheet
                QuizMD uses standard Markdown whenever possible. The question type is inferred automatically:

                | Question Type | Syntax Pattern | Inference Rule |
                | :--- | :--- | :--- |
                | **Single Choice** | `- [ ] Option`<br>`- [X] Correct Option` | Exactly 1 checked with `[X]` |
                | **Multiple Choice** | `- [x] Option 1`<br>`- [x] Option 2` | One or more checked with `[x]` |
                | **True / False** | `- [X] True`<br>`- [ ] False` | Exactly 2 choices with "True" and "False" |
                | **Fill in the Blank** | `The capital of France is {{Paris}}.` | Prompt contains `{{gap}}` |
                | **Numerical** | `= 9.81 ± 0.05` | Line starting with `= number (± tol)` |
                | **Essay / Free Text** | Question prompt with no answers | No answer tokens |
                | **Kprim (Matrix)** | `- [+] True statement`<br>`- [-] False statement` | 4 statements marked `[+]` or `[-]` |

                ---

                ### Quiz Metadata & Versioning
                You can specify quiz-level version, language, or title using either **Top-Level Header Metadata** (Way A) or **YAML Frontmatter** (Way B):

                **Way A: Top-Level Header Metadata**
                ```markdown
                # Biology Exam
                Version: 1.2.0
                Language: en
                ```

                **Way B: YAML Frontmatter**
                ```markdown
                ---
                title: Biology Exam
                version: 1.2.0
                language: en
                ---
                ```
                *(If both are provided, they must be consistent; contradictory values will trigger a warning diagnostic).*

                ---

                ### Question Metadata
                Question metadata is only needed when changing defaults (default is 1 point, auto ID):
                ```markdown
                ## Question Title
                Points: 3
                Feedback: Good job!
                Type: multiple-choice
                ```
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
