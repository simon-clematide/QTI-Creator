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

A lightweight, author-friendly tool for writing quizzes in natural **Markdown** and converting them instantly into standardized **IMS QTI 2.1 Content Packages (`.zip`)** that are directly importable, executable, and **editable in OpenOLAT**.

---

## 🎯 Motivation

### The Problem
Creating high-quality quizzes and exams in modern Learning Management Systems (LMS) like **OpenOLAT** is often a frustrating experience:
- **Click-Heavy Web Forms**: Creating questions one-by-one inside web forms requires dozens of clicks, modal popups, and tab navigations for every single question.
- **XML Complexity**: Under the hood, OpenOLAT assessments rely on the **IMS QTI 2.1** standard. While QTI 2.1 is powerful and robust, writing or editing multi-file XML manifests and assessment items manually is virtually impossible for educators.
- **Existing Text Formats Fall Short**:
  - **Aiken Format**: Wonderfully simple, but strictly limited to Single Choice questions. It cannot express Multiple Choice, Fill-in-the-Blank, Numerical, Essay, or Kprim.
  - **GIFT Format**: Powerful, but its cryptic bracket syntax (`{~=}`) is difficult to read and error-prone when writing math formulas or formatted prose.
  - **Text2QTI**: Designed specifically for Canvas LMS using legacy QTI 1.2, which modern OpenOLAT (v15+) no longer supports.

### The Solution: "QuizMD"
Educators, instructional designers, and LLMs write in **Markdown** every day. **QTI-Creator** bridges the gap:
1. **Write ordinary Markdown** — Use natural headings, paragraphs, bullet lists, and checkboxes (`- [ ]`, `- [X]`, `- [x]`).
2. **Infer the obvious** — The parser detects question types deterministically: uppercase `- [X]` infers Single Choice (exactly one answer allowed); lowercase `- [x]` infers Multiple Choice; `[+]`/`[-]` markers infer Kprim; `{{gap}}` infers Fill-in-the-Blank.
3. **Download OpenOLAT-native QTI 2.1** — The generated package includes root-level manifests, delivery configurations, and metadata so OpenOLAT recognizes the questions as **native items** that open directly in OpenOLAT's visual question editor.

---

## 💡 Core Design Principles

1. **Markdown is Markdown**:
   Standard Markdown syntax retains its normal meaning. Use `#` for the quiz title, `##` for questions, `- [ ]` / `- [X]` / `- [x]` for options, `**bold**`, `*italic*`, code blocks, blockquotes, and LaTeX math notation (`$...$`).
2. **Infer the Obvious**:
   Authors do not need to write `Type: SingleChoice`. One checked box with `[X]` infers Single Choice; one or more checked boxes with `[x]` infer Multiple Choice; `[+]`/`[-]` markers infer Kprim; `{{gap}}` infers Fill-in-the-Blank; `= number` infers Numerical; a question with no answer specification infers an Essay question.
3. **Sensible Defaults**:
   Questions default to 1 point, automatic QTI identifiers, and standard scoring. Metadata is optional and only required when overriding defaults (e.g. `Points: 3`).
4. **OpenOLAT Native Compatibility**:
   - Manifest `imsmanifest.xml` is placed strictly at the root level of the ZIP archive.
   - Includes OpenOLAT's native `QTI21PackageConfig.xml` package delivery configuration.
   - Adds `toolName="OpenOLAT"` and `toolVersion="8.4.0"` metadata to each assessment item, allowing seamless editing in OpenOLAT's question editor without foreign-format warnings.

---

## 📋 Syntax Reference by Question Type

### 1. Single Choice (SC)
Use uppercase `[X]` to mark the correct single-choice answer. Exactly one `[X]` is required:

```markdown
## What is the capital of France?
- [ ] Berlin
- [X] Paris
- [ ] Rome
- [ ] Madrid
```

### 2. Multiple Choice (MC)
Use lowercase `[x]` to mark correct multiple-choice answers. One or more `[x]` answers are valid:

```markdown
## Which of the following are prime numbers?
Points: 2
- [x] 2
- [x] 3
- [ ] 4
- [x] 5
- [ ] 6
```

### 3. True / False (TF)
Two choices matching "True" and "False" are recognized as a True/False question:

```markdown
## The Earth completes one orbit around the Sun in approximately 365.25 days.
- [X] True
- [ ] False
```

### 4. Fill-in-the-Blank (Text Entry Gap)
Wrap the expected word or phrase in double curly braces `{{...}}`. Multiple gaps are supported:

```markdown
## Irregular English Verbs
The past tense of *go* is {{went}} and the past participle is {{gone}}.
```

### 5. Numerical with Optional Tolerance
Use an answer line starting with `=`. Tolerances can be specified with `±`, `+-`, or `+/-`:

```markdown
## Gravitational Acceleration
What is the acceleration due to gravity on Earth's surface in m/s²?
= 9.81 ± 0.05
```

### 6. Essay / Free Text
A question prompt without answer markers is automatically treated as an open-ended essay question:

```markdown
## Explain the process of cellular respiration.
Briefly distinguish between aerobic and anaerobic respiration and state the primary ATP yield for each.
Points: 5
```

### 7. Kprim (Swiss 4-Statement True/False Matrix)
Kprim is a signature format in Swiss and German universities and a native feature of OpenOLAT. Use `[+]` for true statements and `[-]` for false statements. Exactly four statements are required:

```markdown
## Characteristics of Mammals
Points: 2
- [+] They possess hair or fur.
- [+] Females produce milk to nourish their young.
- [-] All mammals give birth to live young without exception.
- [-] Mammals are ectothermic organisms.
```
*Scoring in OpenOLAT:* 4/4 correct = full points (2 pt); 3/4 correct = half points (1 pt); $\le$ 2/4 correct = 0 points.

### 8. Quiz Metadata, Versioning & OpenOLAT Attributes
You can specify the quiz version, language, topic, keywords, or title using either **Top-Level Header Metadata** (Way A) or **YAML Frontmatter** (Way B).

Quiz-level metadata automatically inherits down to every question as defaults unless locally overridden.

#### Protected Keywords at the Beginning of a Quiz
In the preamble section before the first `## Question`, the following keywords are reserved:
- **`Version:`** — Sets the quiz version (e.g. `Version: 1.2.0`). Default: `1.0.0`. Automatically mapped to OpenOLAT *Zusatzinformationen* (Additional Information) on questions if not overridden.
- **`Language:`** — Sets the ISO language code (e.g. `Language: en`, `Language: de`). Default: `en`.
- **`Topic:`** — Sets the default topic/theme (e.g. `Topic: Molecular Biology`). Mapped to OpenOLAT `<ns4:topic>`.
- **`Keywords:`** or **`Tags:`** — Comma-separated or YAML list of keywords (e.g. `Keywords: cell, genetics, biology`). Mapped to OpenOLAT `<imsmd:keyword>` tags.
- **`Additional_Info:`** — Explicit text for OpenOLAT *Zusatzinformationen* (`<ns4:additionalInformations>`).
- **`Title:`** — Alternative way to declare the quiz title (standard is `# Title`).
- **`Description:`** — Explicit single-line description (regular preamble paragraphs are also collected as description).
- **`# Title`** — Standard Markdown Level 1 heading for the quiz title.

**Way A: Top-Level Header Metadata**
```markdown
# Cellular Biology Quiz
Version: 1.2.0
Language: en
Topic: Cell Biology
Keywords: cell, organelle, biology

This is an introductory test covering cell structures.
```

**Way B: YAML Frontmatter**
```markdown
---
title: Cellular Biology Quiz
version: 1.2.0
language: en
topic: Cell Biology
keywords: [cell, organelle, biology]
---

This is an introductory test covering cell structures.
```
*(If both frontmatter and header metadata are specified, they must be consistent; contradictory values will produce a warning diagnostic).*

### 9. Question-Level Metadata, Local Overrides & Post-Submission Feedback
Question metadata lines are optional and case-insensitive. They can be placed **before or after** the choices:
- `Points: <number>` — Sets the question point value (default: `1`).
- `Feedback: <text>` — Adds post-submission modal feedback shown to learners in OpenOLAT after the test is completed. Full Markdown and LaTeX math (`$...$`) are supported in feedback text.
- `Topic: <topic>` — Overrides the quiz default topic for this question in OpenOLAT.
- `Keywords: <kw1, kw2>` — Overrides quiz keywords for this question in OpenOLAT.
- `Additional_Info: <text>` — Custom text for OpenOLAT *Zusatzinformationen*.
- `Language: <lang>` — Overrides language code for this question.
- `Type: <type>` — Explicit override if you wish to bypass inference (e.g. `Type: multiple-choice`).
- `Identifier: <id>` — Custom QTI item identifier (default: auto-generated `item_xxxxxxxx`).

#### Example: Feedback after choices (recommended)
```markdown
## What is the capital of France?
Topic: Geography
Keywords: europe, france, capitals
- [ ] Berlin
- [X] Paris
- [ ] Rome
Feedback: Paris has been the capital since 508 AD.
```

#### Example: Metadata before choices with LaTeX math
```markdown
## Calculus: Integration by Parts
Points: 2
Topic: Calculus
Keywords: math, calculus, integration
Feedback: Use $\int u \, dv = uv - \int v \, du$ with $u = x$ and $dv = e^x dx$.
- [ ] $(x + 1)e^x + C$
- [X] $(x - 1)e^x + C$
```

### 10. Code Snippets (Inline & Multiline Fenced Blocks)
Both inline code and multiline fenced code blocks are supported in prompts and choices:
- **Inline code**: Wrap code in single backticks: `` `print("hello")` `` or `` `int main()` ``.
- **Multiline code blocks**: Use standard triple backticks ```` ```python ... ``` ````. Lines inside code blocks (including assignment operators `=`, task items `- [ ]`, or comments) are protected and will never be misclassified as quiz markers.

```markdown
## Python Function Output
What does this function return when called with `mystery(3)`?
```python
def mystery(n):
    total = 0
    for i in range(n):
        total += i
    return total
```
- [X] `3`
- [ ] `6`
- [ ] `0`
```

---

## 🚀 Complete Quiz Examples

### Example 1: General Knowledge & Science Quiz (Header Metadata)
```markdown
# General Knowledge & Science Quiz
Version: 1.0.0
Language: en

A comprehensive demonstration covering all question types.

## What is the capital of France?
- [ ] Berlin
- [X] Paris
- [ ] Rome
- [ ] Madrid
Feedback: Paris has been the capital since 508 AD.

## Which of the following numbers are prime?
Points: 2
- [x] 2
- [x] 3
- [ ] 4
- [x] 5
- [ ] 6

## The Earth completes one full orbit around the Sun in approximately 365.25 days.
- [X] True
- [ ] False

## Irregular Verb Forms
The past tense of *go* is {{went}} and the past participle is {{gone}}.

## Gravitational Acceleration
What is the acceleration due to gravity on Earth's surface in m/s²?
= 9.81 ± 0.05

## Cellular Respiration
Explain the difference between aerobic and anaerobic respiration in 2-3 sentences.
Points: 3

## Characteristics of Mammals
Points: 2
- [+] They possess hair or fur.
- [+] Females produce milk to nourish their young.
- [-] All mammals give birth to live young without exception.
- [-] Mammals are ectothermic organisms.
```

### Example 2: Linguistics & Language Quiz (YAML Frontmatter)
```markdown
---
title: Introduction to Linguistics Quiz
version: 1.1.0
language: en
---

## Which language family does English belong to?
- [ ] Romance
- [X] Germanic
- [ ] Slavic
- [ ] Uralic

## English has grammatical gender comparable to German.
- [ ] True
- [X] False

## Contrastive Sound Units
The smallest contrastive sound unit in a language that can distinguish meaning is a {{phoneme}}.

## Phonological Minimal Pairs
Briefly explain what a minimal pair is and provide at least one clear example in English.
Points: 2

## Indo-European Branches
Select all language families that belong to the Indo-European family:
Points: 2
- [x] Celtic
- [x] Indo-Iranian
- [ ] Sino-Tibetan
- [x] Hellenic (Greek)
- [ ] Afroasiatic
```

### Example 3: STEM, Physics & Mathematics Quiz
```markdown
# Physics & Mathematics Foundations
Version: 2.0.0
Language: en

## Universal Gravitation
Which physicist formulated the Universal Law of Gravitation?
- [ ] Albert Einstein
- [X] Isaac Newton
- [ ] Niels Bohr
- [ ] Galileo Galilei

## Subatomic Particles
Which particles are located in the nucleus of an atom?
Points: 2
- [x] Protons
- [x] Neutrons
- [ ] Electrons
- [ ] Photons

## Speed of Light
What is the speed of light in vacuum $c$ (in units of $10^8 \text{ m/s}$)?
= 2.998 ± 0.01

## Newton's Third Law
For every action, there is an {{equal}} and {{opposite}} reaction.

## Thermodynamic Entropy
State the Second Law of Thermodynamics and briefly explain how it relates to the concept of entropy in isolated systems.
Points: 4

## Properties of Vectors in $\mathbb{R}^3$
- [+] The dot product of two orthogonal vectors is always zero.
- [+] The cross product $\vec{a} \times \vec{b}$ is perpendicular to both $\vec{a}$ and $\vec{b}$.
- [-] The cross product of two parallel vectors has magnitude equal to the product of their lengths.
- [-] Vector addition is non-commutative.
```

---

## 📥 How to Import into OpenOLAT

1. **Export from QTI-Creator**:
   - Write your quiz in the editor (or paste your Markdown).
   - Click **"Generate OpenOLAT QTI Package"** to download the `.zip` archive.
2. **Import into OpenOLAT Question Bank**:
   - Log into OpenOLAT.
   - Navigate to **Question Bank** in the top navigation.
   - Click **Import** $\rightarrow$ **ZIP-file from local computer**.
   - Select your downloaded `.zip` file and click **Upload**.
   - OpenOLAT will parse the package and immediately import all items into your question pool.
3. **Edit or Use in a Course**:
   - Because QTI-Creator outputs native OpenOLAT metadata, you can click on any question to open it directly in OpenOLAT's visual question editor.
   - Add the imported questions to a **Test** node inside your OpenOLAT course.

---

## 🛠️ Running Locally

```bash
# Clone the repository
git clone https://github.com/simon-clematide/QTI-Creator.git
cd QTI-Creator

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the Gradio app
python3 app.py
```
The web interface will be available at `http://localhost:7860`.

---

## 🧪 Testing

QTI-Creator includes a full test suite verifying model invariants, parser inference rules, QTI 2.1 XML schema compliance, and OpenOLAT packaging integrity:

```bash
python3 -m unittest discover tests/
```

---

## 🔌 Programmatic API Access (Gradio API)

Because QTI-Creator is built with Gradio, it automatically exposes a REST and WebSocket API. You can integrate quiz conversion directly into CI/CD pipelines, LMS automation scripts, or external authoring tools without using the web UI.

An interactive API explorer is always accessible directly at the bottom of the running app via the **"Use via API"** link.

### 1. Python Client (`gradio_client`)

Install the official Gradio client:
```bash
pip install gradio_client
```

Convert Markdown into an OpenOLAT QTI 2.1 `.zip` package:
```python
from gradio_client import Client

# Connect to the Hugging Face Space (or local instance: Client("http://localhost:7860"))
client = Client("simon-clmtd/qti-creator")

markdown_quiz = """# General Knowledge Quiz
Version: 1.0.0

## What is the capital of Switzerland?
- [ ] Zurich
- [X] Bern
- [ ] Geneva
"""

# Call the /convert endpoint
zip_file_path, status_message = client.predict(
    quiz_text=markdown_quiz,
    api_name="/convert"
)

print("Status:", status_message)
print("Downloaded QTI 2.1 package saved at:", zip_file_path)
```

You can also call the `/preview` endpoint to validate Markdown without downloading:
```python
html_preview, diagnostics = client.predict(
    quiz_text=markdown_quiz,
    api_name="/preview"
)
print("Diagnostics:", diagnostics)
```

### 2. JavaScript / TypeScript Client (`@gradio/client`)

Install via npm:
```bash
npm install @gradio/client
```

```javascript
import { Client } from "@gradio/client";

const app = await Client.connect("simon-clmtd/qti-creator");

const result = await app.predict("/convert", [
  `# History Quiz\n## What year did WW2 end?\n- [X] 1945\n- [ ] 1939`
]);

console.log("Result:", result.data);
```

### 3. cURL / REST API

You can also trigger conversions via standard HTTP requests:
```bash
curl -X POST https://simon-clmtd-qti-creator.hf.space/call/convert \
  -H "Content-Type: application/json" \
  -d '{"data": ["# Math Quiz\n## 2 + 2 = ?\n- [X] 4\n- [ ] 5"]}'
```
