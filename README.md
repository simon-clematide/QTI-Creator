---
title: OpenOLAT QTI Quiz Creator
emoji: 📝
colorFrom: indigo
colorTo: blue
sdk: gradio
app_file: app.py
pinned: false
license: mit
---

# 📝 QTI-Creator: Markdown to OpenOLAT QTI 2.1

Write quizzes in natural Markdown. No XML or complex syntax required. Export standardized 1EdTech Question & Test Interoperability (QTI) 2.1 ZIP packages ready for direct import into OpenOLAT.

Learn more: [QTI 2.1 specification](https://www.imsglobal.org/question/qtiv2p1/index.html) · [OpenOLAT eTesting](https://www.openolat.com/etesting)

---

## ⚡ Quick Start: Zero Configuration

Writing a quiz requires almost no syntax overhead. Question types are inferred automatically:

```markdown
# My First Quiz

## What is the capital of France?
- [X] Paris
- [ ] Berlin
- [ ] Rome

## Zurich is the capital of Switzerland.
- [ ] True
- [X] False

## Which are official languages of Switzerland?
- [x] German
- [x] French
- [x] Italian
- [ ] English

## Characteristics of Mammals
- [+] They possess hair or fur.
- [+] Females produce milk to nourish their young.
- [-] All mammals give birth to live young without exception.
- [-] Mammals are ectothermic organisms.

## Irregular Verbs
The past tense of *go* is {{went}}.

## Gravitational Acceleration
What is the acceleration due to gravity on Earth's surface in m/s²?
= 9.81 ± 0.05

## Order these processing stages.
1. [ ] Tokenization
1. [ ] Parsing
1. [ ] Evaluation

## Cellular Respiration
Explain the difference between aerobic and anaerobic respiration in 2-3 sentences.
```

### Core Syntax at a Glance

| Question Type | Syntax Pattern | Inference Rule | Default Scoring (1 point per question) |
| :--- | :--- | :--- | :--- |
| **Single Choice** | `- [ ] Option`<br>`- [X] Correct Option` | Exactly one option marked `[X]` | All or nothing |
| **True / False** | `- [X] True`<br>`- [ ] False` | Single Choice with exactly True and False | All or nothing |
| **Multiple Choice** | `- [x] Option 1`<br>`- [x] Option 2` | One or more options marked `[x]` | Partial credit for correct and incorrect selections |
| **Kprim (Matrix)** | `- [+] True statement`<br>`- [-] False statement` | Exactly 4 statements marked `[+]` or `[-]` | 4/4 = full, 3/4 = half, ≤2/4 = zero |
| **Fill in the Blank (Text)** | `The word is {{gray \| grey}}.` | Answer embedded as `{{answer \| alternative}}` | Points divided equally across blanks |
| **Fill in the Blank (Dropdown)** | `The capital is {[Munich\|**Berlin**\|Hamburg]}.` | Options embedded as `{[opt 1\|**opt 2**\|opt 3]}` (`**` marks correct option) | Points divided equally across dropdowns |
| **Hottext** | `The {** cat **} { sat } on the {** mat **}.` | Selectable spans: `{ text }` (distractor), `{** text **}` / `{+ text }` (correct), `{- text }` | Partial credit for correct and incorrect selections |
| **Numerical** | `= 9.81 ± 0.05` | Answer line starts with `= number (optional ± tolerance)` | All or nothing within tolerance |
| **Order / Sequencing** | `1. [ ] First`<br>`1. [ ] Second`<br>`1. [ ] Third` | Ordered list with empty `[ ]` (minimum 2 items) | All or nothing |
| **Match** | `\| Item \| Match \|`<br>`\|---\|---\|`<br>`\| dog \| noun \|`<br>`\| cat \| noun \|` | 2-column table with `Item` and `Match` headers (ditto supported via empty cells) | Partial credit (OpenOLAT negative point system) |
| **Drag & Drop** | `\| Item \| Drag \|`<br>`\|---\|---\|`<br>`\| dog \| noun \|`<br>`\| run \| verb \|` | 2-column table with `Item` and `Drag` headers. Native OpenOLAT drag-and-drop | Partial credit (OpenOLAT negative point system) |
| **Essay / Free Text** | Question prompt with no answers | No answer syntax | Manual grading |

*All questions are worth 1 point by default. Use `Points: <number>` to change a question's weight.*

---

## 📥 How to Import into OpenOLAT (3 Steps)

1. **Export from QTI-Creator**: Write your quiz in the editor and click **"Generate OpenOLAT QTI Package"** to download the `.zip` archive.
2. **Upload to Question Bank**: In OpenOLAT, open **Question Bank** $\rightarrow$ click **Import** $\rightarrow$ choose **"ZIP-file from local computer"** and upload the file. All questions will appear in your pool.
3. **Use in a Course**: Add a **Test** element to your OpenOLAT course, choose **"Select or create test"**, and pick your imported questions.

---

## 📖 In-Depth Syntax Reference & Advanced Features

### 1. Choice Questions: Strict Case-Sensitive Markers
QTI-Creator enforces clear, case-sensitive marker families:
- **Single Choice**: Exactly one `[X]` (uppercase). If more than 1 `[X]` is used, the parser returns a diagnostic error.
- **Multiple Choice**: Lowercase `[x]`. Any question with `[x]` is Multiple Choice (even if only 1 option is checked).
- **Prohibited**: Mixing `[X]` and `[x]` in the same question is forbidden to prevent ambiguity. Legacy `[o]`, `(o)`, or `(*)` are not supported.
- **Do not post-process with Pandoc or Markdown linters**: Tools like Pandoc or automated formatters normalize Markdown by converting uppercase `[X]` to lowercase `[x]`, escaping Kprim brackets (`\[+\]`), and reflowing metadata lines. Always preserve QuizMD files as pure, unformatted literal Markdown.

### 2. Native OpenOLAT Partial Scoring for Multiple Choice
Multiple Choice questions (`- [x]`) use OpenOLAT's native **Partial score** by default:
- Each question defaults to 1.0 point (or any custom value set via `Points: <n>`).
- Partial scoring follows OpenOLAT's proportional model:
  - Correct selections contribute proportionally according to the number of correct alternatives ($+\text{points} / N_{\text{correct}}$).
  - Incorrect selections subtract proportionally according to the number of incorrect alternatives ($-\text{points} / N_{\text{incorrect}}$).
  - When all alternatives are correct (e.g. 4/4 correct options), selecting all awards 100%, 3/4 awards 75%, 2/4 awards 50%, and 1/4 awards 25%.
  - The result is strictly bounded by $[0.0, \text{Points}]$ (`lowerBound="0.0"` and `upperBound="points"`), ensuring a score can never become negative.
- **Scoring Method Overrides**:
  - `Scoring: partial` (default): Proportional partial scoring with penalty deductions bounded at 0.0.
  - `Scoring: all-correct`: All-or-nothing evaluation requiring all correct choices and zero distractors for full credit, otherwise 0.0.
  - **Kprim Evaluation**: If an item consists of 4 statements to be judged as true or false, write it as a Kprim question with `+` and `-` markers (`- [+]` and `- [-]`). This generates OpenOLAT's native Kprim matrix with 4/4 = full, 3/4 = half, ≤2/4 = 0 scoring.

### 3. Fill-in-the-Blank with Gap Alternatives
Accept multiple valid spellings or synonyms using the pipe `|` separator:

```markdown
## Color Spelling
The American spelling of the colour between black and white is {{gray | grey}}.
```
- The first value (`gray`) is the canonical primary answer.
- All subsequent values (`grey`) are accepted alternatives.
- In OpenOLAT, every alternative receives the same full credit for that blank.
- Whitespace around `|` is automatically trimmed.
- **Escaping syntax characters**: Within `{{...}}`, use a backslash to escape syntax characters: `\|` (literal `|`), `\}` (literal `}`), and `\\` (literal `\`). For example: `{{answer containing \}\} braces | alternative}}`.

### 4. Dropdown / Inline Choice (`{[...]}`)
Embed dropdown selections directly within sentences using `{[...]}` with pipe `|` separators:

```markdown
## European Capitals
Switzerland has its federal city in {[**Bern**|Zurich|Geneva]}, while the capital of Germany is {[Munich|**Berlin**|Hamburg]}.
```
- Mark the correct option with Markdown bold: `**...**`.
- If no bold option is specified, the first option is interpreted as correct and options are automatically shuffled.
- *Note:* Do not mix text entry gaps `{{...}}` and dropdown gaps `{[...]}` in the same question (OpenOLAT limitation).

### 5. Hottext (Selectable Spans in Running Text)
Hottext questions present running text where learners click words or phrases to select or deselect them:

```markdown
## Identify Parts of Speech
Select all nouns in the following sentence:
The {** cat **} { sat } on the {** mat **} near the {** fireplace **}.
```
- `{ text }` — Selectable distractor (incorrect). **Whitespace after `{` is strictly required** to distinguish from template or LaTeX braces.
- `{** text **}` — Selectable correct answer. The outer `**` is an author-facing solution marker.
- `{- text }` — Explicitly incorrect selectable distractor.
- `{+ text }` — Explicitly correct selectable answer (preserves internal markdown, code, or math, e.g. `{+ `import sys` }`).
- Hottext questions support proportional partial scoring bounded at 0.0 by default, or `Scoring: all-correct`.
- Cannot be mixed with open gaps `{{...}}`, dropdown gaps `{[...]}`, or choice checkboxes (`- [ ]`).

### 6. Order / Sequencing Questions (`N. [ ]`)
Order questions require students to drag and drop items into the correct target sequence.

```markdown
## Stages of a Machine Learning Pipeline
Points: 2
1. [ ] Data collection
1. [ ] Feature engineering
1. [ ] Model training
1. [ ] Model evaluation
```

**Rules:**
- **Inference**: An ordered Markdown list consisting of empty task-list items (`N. [ ] ...`) is recognized as an Order question.
- **Ordinary Numbered Lists Are Preserved**: Regular lists (`1. Foo\n2. Bar`) without task boxes `[ ]` remain standard Markdown text and are NOT converted into Order questions.
- **Source Order is the Solution**: The order written in Markdown is the target correct answer.
- **Generous Numbering**: The actual numbers carry no assessment semantics—repeated numbers (`1. [ ] ... 1. [ ] ...`) or arbitrary numbers (`7. [ ] ... 2. [ ] ...`) are fully valid.
- **Empty Checkboxes Required**: If a numbered task item contains `[X]` or `[x]`, it is rejected with a diagnostic error.
- **Automatic Shuffling**: In the generated QTI package, the question interaction is set to `shuffle="true"` so students are presented with scrambled tiles.

### 7. Match & Drag-and-Drop (Association Tables)
Association questions are specified as clean two-column Markdown tables:

**Match (Matrix Interaction):**
```markdown
## Match each word with its category
| Item | Match |
|---|---|
| dog | noun |
| cat | noun |
| run | verb |
| quickly | adverb |
```
- Headers: `| Item | Match |`.
- Single Choice matrix if every item has 1 target; Multiple Choice matrix if any item has 2+ targets.
- Multiple associations for one item use empty cells as ditto (repeats the nearest item above).

**Drag & Drop (`class="match_dnd"`):**
```markdown
## Drag words into categories
| Item | Drag |
|---|---|
| dog | noun |
| run | verb |
```
- Headers: `| Item | Drag |` or `| Item | Drag & Drop |`.
- Generates OpenOLAT's native visual drag-and-drop interaction.
- Partial credit uses OpenOLAT's negative point system (bounded at 0.0), or `Scoring: all-correct`.

### 8. Shuffling / Randomization
QuizMD defaults to **shuffling answer options** wherever the interaction supports and benefits from it (`Shuffle: yes` by default), reducing authoring boilerplate and preventing accidental answer leakage.

- **Choice & Kprim Questions**: Answer choices are shuffled by default in OpenOLAT. Use `Shuffle: no` (or `false`, `0`, `off`) when choice ordering matters pedagogically (e.g. "All of the above" or progressive numeric options).
- **Order Questions**: Learner-facing item order is **always presented in shuffled order** (`shuffle="true"`), because the source order represents the correct solution. A quiz-level `Shuffle: no` will not disable the necessary presentation scrambling of an Order question.

**Disabling Shuffling for a Specific Question:**
```markdown
## Which of the following is true?
Shuffle: no
- [ ] Option A
- [ ] Option B
- [X] All of the above
```

**Disabling Shuffling Across the Entire Quiz:**
```markdown
# History Quiz
Shuffle: no
```

### 9. Quiz Metadata & Shuffling
You can specify quiz-level settings using either **Top-Level Header Metadata** (Way A) or **YAML Frontmatter** (Way B):

**Way A: Top-Level Header Metadata**
```markdown
# Biology Exam
Version: 1.2.0
Language: en
Shuffle: yes
Topic: Molecular Biology
Keywords: cells, genetics, dna
Scoring: partial
Additional_Info: Final Exam - Section A
Description: Comprehensive exam covering cell structure and genetics.
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
scoring: partial
additional_info: Final Exam - Section A
description: |
  Comprehensive exam covering cell structure and genetics.
---
```

Quiz-level metadata acts as defaults that automatically inherit down to every individual question in OpenOLAT:
- **`Title:`** Sets the assessment title (or use `# Heading 1`).
- **`Version:`** Encoded into `<manifest version="...">` and inherited to questions as `<ns4:additionalInformations>Version: ...</ns4:additionalInformations>`.
- **`Language:`** Sets the ISO language code for LOM metadata and QTI items (default: `en`).
- **`Topic:`** Mapped to OpenOLAT's native `<ns4:topic>`.
- **`Keywords:`** / **`Tags:`** Comma-separated or YAML list, mapped to `<imsmd:keyword><imsmd:langstring ...>`.
- **`Shuffle:`** `yes` / `no` (or `true` / `false`, `1` / `0`). Controls answer option randomization (default: `yes`).
- **`Scoring:`** `partial` or `all-correct`. Default scoring model for Multiple Choice questions across the quiz (default: `partial`).
- **`Additional_Info:`** Mapped to OpenOLAT *Zusatzinformationen* (`<ns4:additionalInformations>`).
- **`Description:`** Quiz description or introductory text.

---

### 10. Test Structure & Sections (`#` and `##`)
QuizMD uses deterministic heading semantics to model OpenOLAT's native test hierarchy:
- **YAML `title:`** defines the overall test title.
- **`#` always starts an Assessment Section** (rendered as `<assessmentSection>` in OpenOLAT).
- **`##` always starts an Assessment Question** (rendered as `<assessmentItemRef>`).
- **Plain Text Headings Only**: The text of `#` and `##` headings must be plain text only. Do not use LaTeX math (`$...$`), Markdown formatting (`**bold**`, `*italic*`, `` `code` ``), or links inside headings. OpenOLAT does not format Markdown or math in title attributes and displays them as raw syntax. Place all formulas, formatted text, and symbols in the question body or section instructions below the heading.
- **Section Instructions (`<rubricBlock>`)**: Any text written between a `# Section` heading and its first `## Question` becomes candidate instructions, shown by OpenOLAT at the beginning of that section. In the test preview, section descriptions are collapsible.
- **Title Fallback**: If no test title is specified in YAML frontmatter, the first `#` section title is also used as the overall test title. The section itself remains intact.
- **Sensible Defaults**: If questions appear without any `#` heading, an implicit section is created automatically with default naming.
- *Headings are strictly deterministic: `#` is always a section, `##` is always a question.*

```markdown
---
title: Comprehensive Final Exam
version: 1.0.0
---

# Section 1: Mathematics & Logic
Calculators are permitted for this section. Answer all questions.

## Simple Arithmetic
- [X] 4
- [ ] 5

# Section 2: Biology & Chemistry
Formula sheets are provided in the appendix.

## Water Formula
- [X] H2O
- [ ] CO2
```

---

### 11. Question Metadata & Local Overrides
Question metadata can be placed **before or after** choices/statements (case-insensitive):
- `Points: <number>` (default: 1) — Point weight for the question.
- `Hint: <text>` — Pre-submission interactive hint displayed during test-taking in OpenOLAT (supports Markdown and math). *Note on OpenOLAT layout:* If personal notes are enabled in the test options, OpenOLAT positions the personal notes field directly beneath the question choices, placing it in-between the interactive Hint button and the revealed hint text/modal.
- `Feedback: <text>` — Post-submission explanation displayed after test completion in OpenOLAT (supports Markdown and math).
- `Scoring: partial` or `all-correct` — Scoring model for Multiple Choice questions (default: `partial`).
- `Shuffle: yes / no` — Controls answer scrambling for this question (default: `yes`).
- `Topic: <text>` — Overrides quiz-level Topic in OpenOLAT.
- `Keywords: <kw1, kw2>` — Overrides quiz-level Keywords/Tags in OpenOLAT.
- `Additional_Info: <text>` — Overrides OpenOLAT *Zusatzinformationen*.
- `Language: <iso-code>` — Overrides question language (e.g. `en`, `de`, `fr`).
- `Type: <type-name>` — Optional explicit question type override (e.g. `single_choice`, `multiple_choice`, `kprim`, `gap_fill`, `numerical`, `order`, `essay`).
- `Identifier: <custom_id>` — Custom QTI item identifier (optional, default: auto-generated `item_...`).

```markdown
## Order the biological taxonomy ranks
Points: 2
Topic: Taxonomy
Keywords: biology, classification
Additional_Info: Source: General Biology Curriculum
1. [ ] Domain
1. [ ] Kingdom
1. [ ] Phylum
1. [ ] Class
Feedback: Remember "Dear King Philip Came Over For Good Soup".
```

### 12. Full Configuration & Metadata Example
Here is a comprehensive example demonstrating every available global and question-level configuration option in QuizMD:

```markdown
---
title: Advanced Configuration & Metadata Showcase
version: 2.1.0
language: de
topic: Computer Science
keywords: [algorithms, data-structures, python]
shuffle: yes
additional_info: Final Exam - Section A
description: |
  Demonstrating all global and question-level configuration options in QuizMD:
  YAML frontmatter, metadata inheritance, local overrides, custom point weights,
  post-submission feedback, custom QTI identifiers, and shuffling toggles.
---

## Linear Search Time Complexity
Points: 2
Shuffle: no
Topic: Search Algorithms
Keywords: search, linear, complexity
Additional_Info: Source: Knuth TAOCP Vol 3
Feedback: Linear search scans sequentially through $n$ elements, resulting in $O(n)$ worst-case time complexity.
- [ ] $O(1)$
- [X] $O(n)$
- [ ] $O(n \log n)$
- [ ] $O(n^2)$

## Which data structures are non-linear?
Points: 3
- [x] Tree
- [x] Graph
- [ ] Array
- [ ] Linked list
Feedback: Trees and graphs are non-linear hierarchical or networked structures.

## An empty Python list evaluates to True in a boolean context.
Points: 0.5
Feedback: In Python, empty collections (lists, tuples, dicts, sets) evaluate to False.
- [ ] True
- [X] False

## Complexity Hierarchy
Points: 2.5
Feedback: Arrange from slowest growing (fastest execution) to fastest growing.
1. [ ] Constant: $O(1)$
1. [ ] Logarithmic: $O(\log n)$
1. [ ] Linear: $O(n)$
1. [ ] Quadratic: $O(n^2)$

## String Formatting Syntax
Points: 2
Feedback: Both 'upper' and 'str.upper' or 'uppercase' are accepted synonyms.
In Python, to convert a string to uppercase one calls the {{upper | uppercase | str.upper}} method, while {{lower | lowercase}} converts to lowercase.

## Floating Point Tolerance
Points: 2
Feedback: Exact answer is 0.125 with an allowable tolerance band of ±0.001.
What is the decimal value of $2^{-3}$?
= 0.125 +- 0.001

## Binary Search Trees
Points: 4
Topic: Tree Data Structures
Keywords: bst, trees, invariant
Evaluate each statement regarding Binary Search Trees:
- [+] The left subtree contains only nodes with keys less than the node's key.
- [+] The right subtree contains only nodes with keys greater than the node's key.
- [-] An in-order traversal of a BST yields elements in descending order.
- [-] Lookup in any binary search tree is guaranteed to be $O(\log n)$ in the worst case.
Feedback: In-order traversal yields ascending order. Unbalanced trees degrade to $O(n)$.

## Explain Amortized Complexity
Points: 5
Topic: Complexity Theory
Keywords: amortized, analysis, array
Identifier: amortized_analysis_q08
Provide a detailed explanation of amortized time complexity.
Discuss how dynamic array resizing achieves $O(1)$ amortized insertion despite $O(n)$ worst-case copy steps.
```

### 13. Mathematical Formulas & Code Blocks
- **Inline LaTeX**: Wrap in `$ ... $` or `\( ... \)`. In generated QTI packages, inline math is wrapped in OpenOLAT-compatible `<span class="math" title="URL_ENCODED">latex</span>` elements (without delimiters inside the span).
- **Display Math**: Wrap in `$$ ... $$` or `\[ ... \]`. In generated QTI packages, display math is formatted as a centered paragraph `<p style="text-align:center"><span class="math" title="URL_ENCODED">latex</span></p>` matching OpenOLAT's native editor.
- **Headings Prohibition**: Do not put mathematical formulas (`$...$`) or code inside `#` or `##` headings. Always put them in the body, choices, hint, or feedback.
- **Inline Code**: Use backticks: `` `x = 42` ``.
- **Fenced Code Blocks**: Standard triple backticks ```` ```python ... ``` ````. Lines inside code blocks are protected from being misinterpreted as quiz markers.

### 14. Markdown Tables (GFM Pipe Syntax)
Standard GitHub Flavored Markdown (GFM) tables are supported in question prompts, section descriptions, hints, and feedback (everywhere apart from headings/titles):

```markdown
| Function | Time Complexity | Space Complexity |
| :--- | :---: | ---: |
| `Binary Search` | $\mathcal{O}(\log n)$ | $\mathcal{O}(1)$ |
| `Merge Sort` | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n)$ |
```

- **Column Alignments**: Supports left (`:---`), center (`:---:`), and right (`---:`) alignment.
- **Rich Inlines in Cells**: Cells support math (`$...$`), code spans, bold, italic, and links.
- **Native OpenOLAT Styling**: Exported with `<table class="b_default" style="border-collapse:collapse;width:100%;">` for native rendering in OpenOLAT and the live preview.

### 15. Media & Image Support (Remote & Relative Packaging)
Embed images anywhere in questions, choices, or feedback using standard Markdown:
```markdown
## Plant Biology
![Leaf Anatomy](https://example.org/leaf.png =300x)
What tissue facilitates photosynthesis?
- [X] Mesophyll
- [ ] Epidermis
```

- **Image Sizing (HackMD Syntax)**:
  - Fixed width: `![Diagram](diagram.png =300x)`
  - Proportional width: `![Chart](chart.png =30%x)`
  - Explicit width & height: `![Photo](photo.png =400x250)`
  - *(Requires a space before `=`; maintains image proportions when specifying width-only).*

**Packaging Modes:**
- **Default (Include media OFF)**: Media references remain external URLs or relative links in the generated QTI. Passive preflight inventories references and checks URL schemes with zero network requests or ZIP unpacking.
- **Enabled (Include media ON)**: Remote images are fetched and verified (PNG, JPEG, GIF, WebP, max 10MB, timeout 10s, SSRF protection). Relative images (e.g. `![Tree](images/tree.png)`) are extracted from the uploaded **Media ZIP** from the ZIP root. Assets are deduplicated by source and content hash (SHA-256) and packaged into `media/` within the self-contained QTI package.

---

## 📦 Installation & Setup

### Runtime Dependencies (Application only)
To run the Gradio web application or use QTI-Creator as a Python library:

```bash
pip install -r requirements.txt
python3 app.py
```

### Development & Testing Dependencies
To install the testing and development dependencies:

```bash
pip install -r requirements-dev.txt
```

---

## 🧪 Testing & Validation

Run the automated test suite with either `pytest` or `unittest`:

```bash
pytest
# or: python3 -m unittest discover tests/
```

### OpenOLAT JQTI+ Runtime Validation

If Java is installed, the test suite automatically runs regression and semantic validation against OpenOLAT's native Java QTI 2.1 engine (**JQTI+ / qtiworks**). You can also validate any standalone QTI XML file or `.zip` package from the command line:

```bash
python3 scripts/validate_qti.py my_quiz_qti21.zip
```

---

## 🔌 Programmatic API Access (Gradio API)

Integrate QTI-Creator directly into automated workflows:

```python
from gradio_client import Client

client = Client("simon-clmtd/qti-creator")
zip_path, status = client.predict(
    quiz_text="# Quick Quiz\n## What is 2 + 2?\n- [X] 4\n- [ ] 5",
    api_name="/convert"
)
print("Saved QTI package to:", zip_path)
```

---

## 📄 License
MIT License. Open source and free for academic and commercial use.
