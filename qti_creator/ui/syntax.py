"""Syntax Cheat Sheet documentation page for QTI-Creator."""

import gradio as gr

SYNTAX_MARKDOWN = """
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
      <td style="padding: 8px 12px;"><strong>Fill in the Blank (Text)</strong></td>
      <td style="padding: 8px 12px;"><code>The word is {{gray | grey}}.</code></td>
      <td style="padding: 8px 12px;">Answer embedded as <code>{{answer | alternative}}</code></td>
      <td style="padding: 8px 12px;">Points divided equally across blanks</td>
    </tr>
    <tr style="border-bottom: 1px solid #e2e8f0;">
      <td style="padding: 8px 12px;"><strong>Fill in the Blank (Dropdown)</strong></td>
      <td style="padding: 8px 12px;"><code>The capital is {[Munich|**Berlin**|Hamburg]}.</code></td>
      <td style="padding: 8px 12px;">Choices embedded as <code>{[opt 1|**opt 2**|opt 3]}</code> (bold marks correct answer; if no bold, first option is correct and options are scrambled)</td>
      <td style="padding: 8px 12px;">Points divided equally across dropdowns</td>
    </tr>
    <tr style="border-bottom: 1px solid #e2e8f0;">
      <td style="padding: 8px 12px;"><strong>Hottext</strong></td>
      <td style="padding: 8px 12px;"><code>The {** cat **} { sat } on the {** mat **}.</code></td>
      <td style="padding: 8px 12px;">Selectable spans embedded in text: <code>{ text }</code> (incorrect), <code>{** text **}</code> (correct), <code>{+ text }</code> (correct), <code>{- text }</code> (incorrect)</td>
      <td style="padding: 8px 12px;">Partial credit for correct and incorrect selections</td>
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
      <td style="padding: 8px 12px;"><strong>Match</strong></td>
      <td style="padding: 8px 12px;"><code>| Item | Match |<br>|---|---|<br>| dog | noun |<br>| cat | noun |</code></td>
      <td style="padding: 8px 12px;">2-column table with <code>Item</code> and <code>Match</code> headers. Single Choice if each item has 1 target; Multiple Choice if any item has 2+ targets (empty cells repeat previous)</td>
      <td style="padding: 8px 12px;">Partial credit (OpenOLAT negative point system)</td>
    </tr>
    <tr style="border-bottom: 1px solid #e2e8f0;">
      <td style="padding: 8px 12px;"><strong>Drag &amp; Drop</strong></td>
      <td style="padding: 8px 12px;"><code>| Item | Drag |<br>|---|---|<br>| dog | noun |<br>| run | verb |</code></td>
      <td style="padding: 8px 12px;">2-column table with <code>Item</code> and <code>Drag</code> headers. Renders native OpenOLAT drag-and-drop interaction</td>
      <td style="padding: 8px 12px;">Partial credit (OpenOLAT negative point system)</td>
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


def render_syntax_page() -> None:
    """Render the Syntax Cheat Sheet page."""
    with gr.Column(elem_classes=["docs-content"]):
        gr.Markdown(SYNTAX_MARKDOWN)

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

                #### 3. Fill in the Blank (Text Entry) with Alternatives
                - Wrap target blanks in `{{...}}`.
                - Provide acceptable synonyms or alternate spellings with pipe `|`: `{{gray | grey}}`.
                - The first value is canonical; all alternatives receive equal full credit.
                - **Escaping syntax characters**: Within `{{...}}`, use a backslash to escape syntax characters: `\\|` (literal `|`), `\\}` (literal `}`), and `\\\\` (literal `\\`), e.g., `{{answer containing \\}\\} braces | alternative}}`.

                #### 4. Fill in the Blank with Dropdown (Inline Choice)
                - Embed dropdown options directly in text: `{[option 1|option 2|option 3]}`.
                - Mark the correct answer using Markdown bold: `{[Munich|**Berlin**|Hamburg]}`.
                - If no option has bold markup, the first option is the correct answer and option scrambling is automatically enforced (`shuffle="true"`).
                - *Note: OpenOLAT does not allow mixing open text entry gaps and dropdown gaps within the same question.*

                #### 5. Hottext (Selectable Spans in Running Text)
                - Embed selectable words or phrases directly in text:
                  - `{ text }` — Selectable distractor (incorrect). Note: whitespace after `{` is strictly required.
                  - `{** text **}` — Selectable correct answer. The outer `**` is an author-facing solution marker stripped from learner text.
                  - `{- text }` — Explicitly incorrect selectable distractor.
                  - `{+ text }` — Explicitly correct selectable answer (preserves any internal markdown, code, or math, e.g. `{+ The **must** rule }`, `{+ `print()` }`, `{+ $x^2$ }`).
                - Hottext questions support OpenOLAT partial credit scoring by default, as well as `Scoring: all-correct`.
                - *Note: Cannot be combined with cloze gaps (`{{...}}`, `{[...]}`), choice markers (`[X]`), or order items within the same question.*

                #### 6. Numerical Questions
                - Specify the expected answer and optional tolerance: `= 9.81 ± 0.05` or `= 42` or `= 0.125 +- 0.001`.

                #### 6. Order / Sequencing Questions
                - Write an ordered list with empty boxes: `1. [ ] Step A`, `1. [ ] Step B`, `1. [ ] Step C` (minimum 2 items).
                - **The order written in Markdown is the correct solution.**
                - Learner-facing tiles are automatically scrambled (`shuffle="true"`).
                - *Regular numbered lists (`1. Foo`, `2. Bar`) without `[ ]` remain standard Markdown text.*

                #### 7. Essay / Free Text
                - Write the prompt without any answer markers. OpenOLAT creates an open text response area for manual grading.

                #### 8. Formulas & Code Blocks
                - **Math Formulas**: Use MathJax-compatible TeX syntax — e.g. `$E = mc^2$`, `$$\frac{a}{b}$$`, `\sum`, `\text{...}`. OpenOLAT renders math natively via MathJax 3 (OpenOLAT ≥ 16.2). Arbitrary LaTeX packages and document-level commands are not supported.
                - **Display Math**: `$$ \int_0^1 x^2 \, dx $$` on its own line.
                - **Code**: Backticks `` `code` `` or fenced blocks ```` ```python ... ``` ````. Lines in code blocks are protected from quiz syntax parsing.

                #### 8. Markdown Tables (GFM Pipe Syntax)
                - Tables are supported in question prompts, section descriptions, hints, and feedback (everywhere apart from headings/titles).
                - Use standard Markdown pipe syntax:
                  ```markdown
                  | Column 1 | Column 2 | Column 3 |
                  | :--- | :---: | ---: |
                  | Left | Centered | Right |
                  ```
                - Cells can contain math (`$...$`), code spans, bold, italic, and links.
                """
            )

        with gr.Accordion("Question-level settings", open=False):
            gr.Markdown(
                """
                Question metadata and sections can be placed to configure question settings or add hints and post-submission explanations:
                - `Points: <number>` (default: 1)
                - `### Hint` or `### Hint: <Title>` (pre-submission hint section; captures all lines/paragraphs, math, and code until the next heading)
                - `### Feedback` or `### Feedback: <Title>` (post-submission explanation and solution section; captures all lines/paragraphs, math, and code until the next heading)
                - `Scoring: partial` or `all-correct` (for Multiple Choice questions; default: `partial`)
                - `Shuffle: yes / no` (controls answer scrambling; default: `yes`)
                - `Topic: <text>` (overrides quiz-level Topic in OpenOLAT)
                - `Keywords: <kw1, kw2>` (overrides quiz-level Keywords in OpenOLAT)
                - `Additional_Info: <text>` (overrides OpenOLAT Zusatzinformationen)
                - `Language: <iso-code>` (e.g. `en`, `de`, `fr`)
                - `Type: <type-name>` (optional explicit question type override)
                - `Identifier: <custom_id>` (optional, default: auto-generated)

                > **Note on Hints and Solutions:** Always use `### Hint` and `### Feedback` for multi-paragraph explanations and worked solutions. Single-line `Hint:` or `Feedback:` metadata only covers a single line and warns if subsequent paragraphs could leak into the student prompt.

                ```markdown
                ## Order the biological taxonomy ranks
                Points: 2
                Topic: Taxonomy
                Keywords: biology, classification
                1. [ ] Domain
                1. [ ] Kingdom
                1. [ ] Phylum
                1. [ ] Class

                ### Hint
                Think of the mnemonic starting with "Dear King Philip".

                ### Feedback: Taxonomy Mnemonic
                Remember "Dear King Philip Came Over For Good Soup".

                This mnemonic represents: Domain, Kingdom, Phylum, Class, Order, Family, Genus, Species.
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
