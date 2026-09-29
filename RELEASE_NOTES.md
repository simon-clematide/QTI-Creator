# Release Notes — QTI-Creator v1.0.0

**Release Date:** September 29, 2026  
**Milestone:** Production General Availability (GA)

---

## 🚀 Overview

QTI-Creator reaches **v1.0.0**, marking its transition from beta to production readiness. QTI-Creator provides a zero-friction Markdown syntax (**QuizMD**) for authoring assessments, instantly compiling them into fully compliant **IMS QTI 2.1** content packages tailored for native import and editing in **OpenOLAT**.

This milestone release introduces a formal **headless programmatic API** on Hugging Face Spaces, integrates OpenOLAT's native **Java JQTI+ validation engine** into cloud deployments, and implements **fail-fast static validation and visual preview protection for LaTeX math/gap conflicts**.

---

## 🌟 Key Highlights in v1.0.0

### 1. Headless Programmatic API & Cloud JQTI+ Validation
QTI-Creator can now be integrated directly into automated grading pipelines, CI/CD workflows, and LLM-driven question generation agents.

* **`/check_quiz` Endpoint**: Fast AST and semantic validator returning structured JSON diagnostics (`line_number`, `severity`, `message`, `question_index`).
* **`/validate_jqti` Endpoint**: Compiles quiz markdown into QTI 2.1 in memory and executes OpenOLAT's native Java engine (`qtiworks-jqtiplus-1.0.37.jar`), validating XML schemas and simulating runtime item evaluation.
* **`/export_qti` Endpoint**: Headless compilation producing a downloadable OpenOLAT-compatible `.zip` package.
* **Cloud Java Runtime**: Added `packages.txt` (`default-jdk`) to automatically provision the Java JDK/JRE environment on Hugging Face Spaces.

**Python Client Example:**
```python
from gradio_client import Client

client = Client("simon-clmtd/qti-creator")

markdown = """# Sample Quiz
## Capital of France
- [ ] Berlin
- [X] Paris
- [ ] Rome
"""

# Instant semantic check
result = client.predict(quiz_markdown=markdown, api_name="/check_quiz")
print("Valid:", result["valid"], "Total Questions:", result["total_questions"])

# OpenOLAT Java engine check
jqti_result = client.predict(quiz_markdown=markdown, api_name="/validate_jqti")
print("JQTI+ Valid:", jqti_result["jqti_valid"])

# Direct ZIP export
zip_file = client.predict(quiz_markdown=markdown, api_name="/export_qti")
```

---

### 2. MathJax & Gap Conflict Prevention
Placing interactive fill-in-the-blank or dropdown widgets inside LaTeX math delimiters (`$...$`, `$$...$$`) causes OpenOLAT's MathJax processor to crash or erase mathematical formulas across the item.

* **Static Parser Guard**: Detects cloze gaps `{{...}}` and dropdown gaps `{[...]}` inside inline math (`$...$`, `\(...\)`) or display math (`$$...$$`, `\[...\]`).
* **Actionable Diagnostics**: Emits clear `Severity.ERROR` diagnostics with exact line numbers and remediation tips (moving the gap into plain text immediately adjacent to the math formula).
* **High-Fidelity Gap Preview**: The preview prompt now renders disabled `<input>` widgets directly in place of gaps.
* **MathJax Safety Guard**: Protects client-side preview typesetting from crashes when invalid widgets are present, applying a clear red `⚠️ [MathJax Gap Conflict]` badge with tooltip explanations.

---

### 3. Full Spectrum of OpenOLAT Question Types
v1.0.0 guarantees comprehensive coverage of OpenOLAT assessment interactions:

| Question Type | QuizMD Syntax | OpenOLAT Interaction |
| :--- | :--- | :--- |
| **Single Choice** | `- [X] Correct`<br>`- [ ] Incorrect` | `<choiceInteraction maxChoices="1">` |
| **Multiple Choice** | `- [x] Option 1`<br>`- [x] Option 2` | `<choiceInteraction maxChoices="0">` |
| **True / False** | `- [X] True`<br>`- [ ] False` | Single choice evaluation |
| **Kprim (Matrix)** | `- [+] True statement`<br>`- [-] False statement` | 4-row matrix with OpenOLAT Kprim scoring |
| **Fill-in-the-Blank** | `The word is {{canonical \| alt1}}` | `<textEntryInteraction>` with mapping |
| **Inline Choice** | `The capital is {[Munich\|**Berlin**]}` | `<inlineChoiceInteraction>` dropdown |
| **Hottext** | `{** selectable correct **}` | `<hottextInteraction>` inline spans |
| **Numerical** | `= 9.81 ± 0.05` | Numerical response with tolerance |
| **Order / Sequencing**| `1. [ ] First step` | `<orderInteraction>` |
| **Match Table** | `\| Item \| Match \|` table | OpenOLAT match interaction (NPS scoring) |
| **Drag & Drop** | `\| Item \| Drag \|` table | OpenOLAT native drag & drop interaction |
| **Essay** | Question prompt without choices | `<extendedTextInteraction>` manual grading |

---

### 4. Native OpenOLAT Package Architecture
All generated packages conform strictly to OpenOLAT’s packaging requirements:
* Root-level `imsmanifest.xml` containing OpenOLAT metadata (`ns4:ooMetadata`).
* Root-level `Test.xml` assessment test container supporting multi-section quizzes.
* Root-level `QTI21PackageConfig.xml` enabling immediate in-place editing inside OpenOLAT's visual Test Editor.
* Correct scoring declarations: OpenOLAT NPS negative point accumulators for partial credit, all-correct templates, and points-per-answer scoring.
* Full multimedia bundling: automatic extraction, path remapping, and packaging of local and remote image assets.

---

## 🛠️ Breaking Changes & Upgrades from Beta

1. **Gaps in Math Delimiters are Strictly Prohibited**:
   * *Before:* Gaps like `$\bar x={{24}}$` were silently absorbed into math spans, generating broken OpenOLAT XML that caused equations to vanish at runtime.
   * *v1.0.0:* The parser flags this as a `Severity.ERROR` diagnostic and blocks package export until corrected.
2. **Version Scheme Graduation**:
   * Transitioned from beta versioning (`v0.8.x`) to official Semantic Versioning (`v1.0.0`).

---

## 🧪 Test Suite & Validation Status

* **176 automated unit and integration tests** passing (`pytest`).
* Regression and runtime compatibility validated against OpenOLAT's official JQTI+ engine test suite (`tests/test_jqtiplus.py`).
