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

A lightweight tool for writing quizzes in natural **Markdown** and converting them into standardized **IMS QTI 2.1 Content Packages (`.zip`)** ready for direct import into **OpenOLAT**.

---

## ⚡ Quick Start: Zero Configuration

Writing a quiz requires almost no syntax overhead. Question types are inferred automatically:

```markdown
# My First Quiz

## What is the capital of France?
- [X] Paris
- [ ] Berlin
- [ ] Rome

## Which are official languages of Switzerland?
- [x] German
- [x] French
- [x] Italian
- [ ] English

## Zurich is the capital of Switzerland.
- [ ] True
- [X] False

## Irregular Verbs
The past tense of *go* is {{went}}.

## Order these processing stages.
1. [ ] Tokenization
1. [ ] Parsing
1. [ ] Evaluation

## Gravitational Acceleration
What is the acceleration due to gravity on Earth's surface in m/s²?
= 9.81 ± 0.05

## Cellular Respiration
Explain the difference between aerobic and anaerobic respiration in 2-3 sentences.

## Characteristics of Mammals
- [+] They possess hair or fur.
- [+] Females produce milk to nourish their young.
- [-] All mammals give birth to live young without exception.
- [-] Mammals are ectothermic organisms.
```

### Core Syntax at a Glance

| Question Type | How to Write It | Inference Rule |
| :--- | :--- | :--- |
| **Single Choice** | `- [X] Correct Option`<br>`- [ ] Wrong Option` | Exactly 1 marked with uppercase `[X]` |
| **Multiple Choice** | `- [x] Correct Option 1`<br>`- [x] Correct Option 2`<br>`- [ ] Distractor` | One or more marked with lowercase `[x]` |
| **True / False** | `- [X] True`<br>`- [ ] False` | Exactly 2 choices with "True" and "False" |
| **Fill in the Blank** | `The capital is {{Paris}}.` | Wrap target word in `{{gap}}` |
| **Order / Sequencing** | `1. [ ] First`<br>`1. [ ] Second`<br>`1. [ ] Third` | Numbered task list with empty `[ ]` (min 2 items) |
| **Numerical** | `= 9.81 ± 0.05` | Line starting with `= number (± tolerance)` |
| **Essay / Free Text** | Prompt without answer markers | Open text area for student response |
| **Kprim (Matrix)** | `- [+] True statement`<br>`- [-] False statement` | Exactly 4 statements marked `[+]` or `[-]` |

---

## 📥 How to Import into OpenOLAT (3 Steps)

1. **Export from QTI-Creator**: Write your quiz in the editor and click **"Generate OpenOLAT QTI Package"** to download the `.zip` archive.
2. **Upload to Question Bank**: In OpenOLAT, open **Question Bank** $\rightarrow$ click **Import** $\rightarrow$ choose **"ZIP-file from local computer"** and upload the file. All questions will appear in your pool.
3. **Use in a Course**: Add a **Test** element to your OpenOLAT course, choose **"Select or create test"**, and pick your imported questions.

---

## 📖 In-Depth Syntax Reference & Advanced Features

### 1. Choice Questions: Strict Case-Sensitive Markers
QTI-Creator enforces clear marker families:
- **Single Choice**: Exactly one `[X]` (uppercase). If more than 1 `[X]` is used, the parser returns a diagnostic error.
- **Multiple Choice**: Lowercase `[x]`. Any question with `[x]` is Multiple Choice (even if only 1 option is checked).
- **Prohibited**: Mixing `[X]` and `[x]` in the same question is forbidden to prevent ambiguity. Legacy `[o]`, `(o)`, or `(*)` are not supported.

### 2. Multiple Choice Scoring (Automatic Kprim Proportion)
In OpenOLAT, multiple-choice questions are automatically evaluated with **Kprim-style proportion scoring**:
- Selecting a correct option awards `+1.0`.
- Selecting an incorrect option deducts `-1.0` (eliminating the "select-all" guessing cheat).
- **100% (full points)**: All choices evaluated correctly (all correct items selected, no distractors selected).
- **50% (half points)**: Exactly 1 mistake made (either 1 missed correct answer OR 1 distractor selected).
- **0%**: 2 or more mistakes made (with score floored at `0.0`).

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

### 4. Order / Sequencing Questions (`N. [ ]`)
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

### 5. Shuffling / Randomization
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

### 6. Preamble Metadata & Frontmatter Space
Quiz-level metadata acts as defaults that inherit down to every individual question in OpenOLAT:

```markdown
---
title: Cellular Biology Quiz
version: 1.2.0
language: en
shuffle: yes
topic: Cell Biology
keywords: [cell, organelle, biology]
---
```
*(Or via top-level headers `Version: 1.2.0`, `Language: en`, `Topic: Cell Biology`, `Keywords: cell, organelle, biology`).*

- **`Version:`** Encoded into `<manifest version="...">` and inherited to question `<ns4:additionalInformations>Version: ...</ns4:additionalInformations>`.
- **`Topic:`** Mapped to OpenOLAT's native `<ns4:topic>`.
- **`Keywords:`** / **`Tags:`** Mapped to `<imsmd:keyword><imsmd:langstring ...>`.
- **`Language:`** Sets the ISO language code for LOM and QTI items.

### 7. Question-Level Metadata & Post-Submission Feedback
Metadata lines can appear **before or after** choices:
- `Points: <number>` (default: 1)
- `Feedback: <text>`: Post-submission feedback displayed to learners in OpenOLAT. Supports Markdown and LaTeX math (`$...$`).
- `Shuffle: <bool>`: Overrides quiz shuffling.
- `Topic: <text>`: Overrides question topic in OpenOLAT.
- `Keywords: <kw1, kw2>`: Overrides question keywords.
- `Additional_Info: <text>`: Overrides OpenOLAT *Zusatzinformationen*.

```markdown
## What is the capital of France?
Topic: European Capitals
Keywords: france, geography
- [ ] Berlin
- [X] Paris
- [ ] Rome
Feedback: Paris has been the capital since 508 AD.
```

### 8. Full Configuration & Metadata Example
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

### 9. Mathematical Formulas & Code Blocks
- **Inline LaTeX**: Wrap in `$ ... $`, e.g. `$E = mc^2$`. OpenOLAT renders this natively with MathJax.
- **Display Math**: Wrap in `$$ ... $$` on its own line.
- **Inline Code**: Use backticks: `` `x = 42` ``.
- **Fenced Code Blocks**: Standard triple backticks ```` ```python ... ``` ````. Lines inside code blocks are protected from being misinterpreted as quiz markers.

---

## 🧪 Testing & Validation

Run the automated test suite covering all parser rules, model invariants, and QTI XML generators:

```bash
python3 -m unittest discover tests/
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
