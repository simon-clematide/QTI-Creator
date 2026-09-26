"""Prompting Markdown Quizzes documentation page for QTI-Creator."""

import gradio as gr

PROMPTING_MARKDOWN = """
## ✨ Prompting Markdown Quizzes

AI assistants can help you turn existing teaching materials—such as lecture slides, handouts, notes, or textbook excerpts—into a first draft of a QuizMD quiz.

Upload or provide your source material to an AI assistant, tell it what you want to assess, and ask it to return the questions in the QuizMD format understood by QTI-Creator.

> **Important:** Treat AI-generated questions as a draft. Check the factual accuracy, difficulty, wording, answer keys, and suitability for your learning objectives before importing them into QTI-Creator.
> 
> **Do not run QuizMD output through Pandoc, Prettier, or Markdown reflow formatters:** Tools like Pandoc normalize Markdown syntax (e.g. converting `[X]` to `[x]`, escaping `[+]` as `\\[+\\]`, and reflowing lines), which breaks QuizMD semantic parsing. Keep the generated Markdown strictly literal.

### A simple workflow

1. **Provide your material** → Upload your slides, notes, or other source material.
2. **Describe the quiz** → Specify the audience, topics, number and types of questions, and desired difficulty.
3. **Generate QuizMD** → Give the AI the QuizMD prompt below and ask for raw literal Markdown only.
4. **Review and revise** → Check every question and answer against your teaching material.
5. **Copy into QTI-Creator** → Paste the resulting Markdown directly into the QuizMD Source editor and use Validation and Preview before generating the QTI package.
"""

AI_PROMPT_TEMPLATE = (
    "You are helping me draft an assessment from teaching material that I provide.\n"
    "Create a quiz based on the supplied material. Use the source material as the\n"
    "basis for factual questions and answers. Do not invent facts that are not\n"
    "supported by the material.\n\n"
    "Audience:\n"
    "[describe the students/course level]\n\n"
    "Learning goals or topics to assess:\n"
    "[describe them here]\n\n"
    "Quiz requirements:\n"
    "[number of questions, desired difficulty, question types, etc.]\n\n"
    "Return the quiz as Markdown using the QuizMD conventions below.\n\n"
    "QUIZ PARTS AND HEADERS\n\n"
    "A quiz may contain multiple parts or sections.\n\n"
    "Use a level-1 heading (#) for the quiz title and also for each quiz part:\n"
    "# Quiz title\n\n"
    "# Part or Section Title\n\n"
    "Every level-2 heading (##) starts a question.\n\n"
    "IMPORTANT:\n"
    "- Do not use level-3 or deeper headings (###, ####, etc.).\n"
    "- The text of # and ## headings must be plain text only.\n"
    "- Do not use LaTeX, Markdown formatting, inline code, links, or mathematical\n"
    "  notation inside headings.\n"
    "- Put all formulas, symbols, code, links, and formatted text in the body\n"
    "  below the heading.\n\n"
    "Example:\n\n"
    "# Matrix Multiplication\n\n"
    "## Determining the output shape\n\n"
    "Let\n\n"
    "\\[\n"
    "A\\in\\mathbb{R}^{4\\times3},\n"
    "\\qquad\n"
    "B\\in\\mathbb{R}^{3\\times2}.\n"
    "\\]\n\n"
    "What is the shape of \\(AB\\)?\n\n"
    "QUESTION TYPES\n\n"
    "Single Choice\n"
    "Use uppercase [X] for the one correct answer and [ ] for incorrect answers.\n"
    "Example:\n"
    "## Which method splits text into smaller units?\n"
    "- [ ] Parsing\n"
    "- [X] Tokenization\n"
    "- [ ] Classification\n"
    "- [ ] Generation\n\n"
    "Multiple Choice\n"
    "Use lowercase [x] for every correct answer and [ ] for incorrect answers.\n"
    "There may be one or more correct answers.\n"
    "Example:\n"
    "## Which of these are common NLP tasks?\n"
    "- [x] Tokenization\n"
    "- [x] Named entity recognition\n"
    "- [ ] Image resizing\n"
    "- [x] Part-of-speech tagging\n\n"
    "IMPORTANT:\n"
    "[X] and [x] are case-sensitive.\n"
    "Do not mix uppercase [X] and lowercase [x] within one question.\n\n"
    "True / False\n"
    "Use Single Choice syntax with exactly True and False.\n"
    "Example:\n"
    "## A tokenizer always assigns part-of-speech tags.\n"
    "- [ ] True\n"
    "- [X] False\n\n"
    "Kprim\n"
    "Write exactly four statements.\n"
    "Use [+] for a true/correct statement and [-] for a false/incorrect statement.\n"
    "Example:\n"
    "## Which statements about language models are correct?\n"
    "- [+] They can assign probabilities to sequences.\n"
    "- [-] They require every sentence to have the same length.\n"
    "- [+] They can be trained on text corpora.\n"
    "- [-] They always produce factually correct output.\n\n"
    "Fill-in-the-Blank (Text Entry)\n"
    "Put the expected answer inside double braces.\n"
    "Example:\n"
    "## Complete the sentence.\n"
    "The process of splitting text into units is called {{tokenization}}.\n"
    "Alternative accepted answers may be separated with |:\n"
    "The spelling may be {{gray | grey}}.\n\n"
    "Fill-in-the-Blank (Dropdown / Inline Choice)\n"
    "Put multiple options inside {[option 1|option 2|option 3]}.\n"
    "Mark the correct answer using Markdown bold **...**:\n"
    "Example:\n"
    "## Complete the sentence with the right terms.\n"
    "The capital of Switzerland is {[Bern|Zurich|Geneva]}, and Germany is {[Munich|**Berlin**|Hamburg]}.\n"
    "If no bold is specified, the first option is correct and options are automatically scrambled.\n"
    "IMPORTANT: Do NOT mix {{...}} and {[...]} in the same question.\n\n"
    "Hottext (Selectable Spans in Running Text)\n"
    "Mark selectable words or spans directly in text:\n"
    "- { word } for incorrect distractors (whitespace after { is required)\n"
    "- {** word **} for correct answers\n"
    "- {+ word } for explicitly correct answers\n"
    "- {- word } for explicitly incorrect distractors\n"
    "Example:\n"
    "## Identify the parts of speech\n"
    "Select all nouns in the following sentence:\n"
    "The {** cat **} { sat } on the {** mat **}.\n\n"
    "Numerical\n"
    "Give the target value with = and optionally a tolerance with ±.\n"
    "Example:\n"
    "## What is the approximate acceleration due to gravity on Earth?\n"
    "= 9.81 ± 0.05\n\n"
    "Order / Sequencing\n"
    "Use an ordered Markdown task list in the correct order.\n"
    "Example:\n"
    "## Order these stages.\n"
    "1. [ ] Tokenization\n"
    "2. [ ] Feature extraction\n"
    "3. [ ] Model inference\n"
    "4. [ ] Evaluation\n\n"
    "Match (Association Table)\n"
    "Use a two-column table with headers | Item | Match |.\n"
    "Example:\n"
    "## Match each word with its category.\n"
    "| Item | Match |\n"
    "|---|---|\n"
    "| dog | noun |\n"
    "| cat | noun |\n"
    "| run | verb |\n\n"
    "Drag & Drop (Visual Matching)\n"
    "Use a two-column table with headers | Item | Drag |.\n"
    "Example:\n"
    "## Drag words into categories.\n"
    "| Item | Drag |\n"
    "|---|---|\n"
    "| dog | noun |\n"
    "| run | verb |\n\n"
    "Essay / Free Text\n"
    "Write the question without an answer specification.\n"
    "Example:\n"
    "## Explain one limitation of evaluating a language model using accuracy alone.\n\n"
    "Markdown Tables\n"
    "Standard tables are supported in question prompts, section descriptions, hints, and feedback:\n"
    "| Col 1 | Col 2 |\n"
    "| :--- | ---: |\n"
    "| A | B |\n\n"
    "OPTIONAL QUESTION SETTINGS\n"
    "Questions are worth 1 point by default.\n"
    "Use this only when a different weight is needed:\n"
    "Points: 2\n\n"
    "CRITICAL FORMATTING & SYNTAX INVARIANTS (DO NOT POST-PROCESS OR NORMALIZE):\n"
    "- Output pure literal Markdown. Never run the output through Pandoc, Prettier, or any Markdown reflow/linter tool.\n"
    "- Single Choice: MUST use uppercase [X] for the single correct choice and [ ] for incorrect choices. NEVER lowercase [x].\n"
    "- Multiple Choice: MUST use lowercase [x] for correct choices and [ ] for incorrect choices.\n"
    "- Kprim: MUST use exactly four literal unescaped [+] or [-] markers. NEVER escape brackets (do not output \\[+\\] or \\[-\\]).\n"
    "- Headings: # is always a section, ## is always a question. Headings MUST be plain text only (never put LaTeX, math, or backticks in headings).\n"
    "- Hints and Explanations: Use '### Hint' or '### Hint: <Title>' for hints and '### Feedback' or '### Feedback: <Title>' for post-submission explanations and worked solutions. Place them after the question prompt and choices.\n"
    "- Metadata: Key-value lines (Points:, Scoring:, Topic:) MUST remain on their own separate lines, never reflowed into a paragraph.\n"
    "- Code blocks: Use standard triple backticks without a space (```python, not ``` python).\n\n"
    "OUTPUT REQUIREMENTS\n"
    "- Return only the finished QuizMD Markdown, without commentary before or after it.\n"
    "- Use question types appropriate to the material and learning objectives.\n"
    "- Write clear, unambiguous questions.\n"
    "- For Single Choice, make exactly one answer correct.\n"
    "- For Multiple Choice, identify every correct alternative.\n"
    "- For Kprim, write exactly four statements.\n"
    "- Make distractors plausible but clearly incorrect according to the source material.\n"
    "- Avoid trivia unless it is relevant to the learning objectives.\n"
    "- Avoid questions that can be answered from superficial wording cues.\n"
    "- Do not invent information absent from the supplied teaching material.\n"
    "- Do not put the answer into the wording of the question.\n"
    "- Check each answer key against the source material before returning the quiz."
)


def render_prompting_page() -> None:
    """Render the Prompting Guide page."""
    with gr.Column(elem_classes=["docs-content"]):
        gr.Markdown(PROMPTING_MARKDOWN)

        with gr.Accordion("▶ Prompt template for AI assistants", open=False):
            gr.Markdown(
                "Copy this prompt template, fill in your audience and topic requirements, and attach your teaching material in your preferred AI tool:"
            )
            prompt_textbox = gr.Textbox(
                value=AI_PROMPT_TEMPLATE,
                lines=18,
                show_label=False,
                interactive=False,
            )
            with gr.Row():
                btn_copy_prompt = gr.Button("📋 Copy Prompt Template", variant="secondary")
                copy_status = gr.Markdown("", elem_classes=["no-scroll-block"])

            btn_copy_prompt.click(
                None,
                inputs=[prompt_textbox],
                outputs=[copy_status],
                js="""(val) => {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(val);
                    }
                    return "✅ Prompt template copied to clipboard!";
                }""",
            )

        with gr.Accordion("▶ Customize your request", open=False):
            gr.Markdown(
                """
                You can append short, focused requirement blocks to the prompt template. Here are two practical examples:

                **Example 1: Concept-focused linguistics quiz**
                ```text
                Create 10 questions for first-year linguistics students.
                Focus on tokenization, morphology, and part-of-speech tagging.
                Use 4 Single Choice, 3 Multiple Choice, 2 True/False, and 1 Essay question.
                Prefer conceptual understanding over memorizing terminology.
                ```

                **Example 2: Formative quiz from lecture slides**
                ```text
                Create a short formative quiz from the attached lecture slides.
                Use 6 questions with mixed question types.
                Target concepts students commonly misunderstand.
                Keep the difficulty appropriate for a second-year university course.
                ```
                """
            )

        with gr.Accordion("▶ Reviewing AI-generated quizzes", open=False):
            gr.Markdown(
                """
                Before using the quiz in an assessment or course, check:

                - **Source accuracy:** Are all questions and answers actually supported by your supplied teaching material?
                - **Correct answer keys:** Are the designated correct answers factually and pedagogically accurate?
                - **Single vs. Multiple Choice:** Is each Single Choice (`[X]`) unambiguously single-answer? Does each Multiple Choice (`[x]`) identify all correct alternatives?
                - **Plausible distractors:** Are distractors plausible without being unfairly misleading or ambiguous?
                - **Learning alignment:** Does the quiz assess your intended learning objectives rather than incidental trivia?
                - **Difficulty & tone:** Is the difficulty appropriate for your students?
                - **Validation check:** When pasted into QTI-Creator, does the **Validation** panel report zero issues?

                *AI can accelerate drafting, but the instructor remains responsible for the assessment content.*
                """
            )
