# QTI-Creator: Markdown to OpenOLAT QTI 2.1
## Revised Design and Implementation Plan

---

### 1. Goal

**QTI-Creator** is a lightweight web application for writing quizzes in a natural Markdown-style format and converting them into QTI 2.1 packages for **OpenOLAT**.

The central design principle is:

> **Write ordinary Markdown whenever possible. Add quiz-specific syntax only where Markdown cannot express the required meaning. Use sensible defaults instead of requiring configuration.**

A simple quiz should therefore look like a normal Markdown document rather than a configuration file.

The conversion pipeline is:

```
QuizMD / GIFT
      ↓
    Parser
      ↓
Typed Quiz Model
      ↓
QTI 2.1 Generator
      ↓
Manifest + Resources
      ↓
  ZIP Package
      ↓
   OpenOLAT
```

**QuizMD** is the primary authoring format. **GIFT** is an optional import format for existing question banks.

---

### 2. Design Principles

#### 2.1 Markdown is Markdown
Standard Markdown constructs retain their normal meaning:
* `#` and `##` for headings
* paragraphs for prose
* `-` for lists
* `- [ ]` and `- [x]` for choices
* `**bold**` and `*italic*`
* block quotes
* fenced code blocks
* links
* images
* inline and display mathematics where supported

QuizMD should not replace existing Markdown syntax unnecessarily.

#### 2.2 Infer the Obvious
The parser determines the question type from its structure whenever the intention is unambiguous.

For example:
```markdown
## What is the capital of France?
- [ ] Berlin
- [x] Paris
- [ ] Rome
```
One checked answer means **single choice**.

```markdown
## Which are Germanic languages?
- [x] English
- [x] German
- [ ] French
- [ ] Finnish
```
Several checked answers mean **multiple choice**.

The author does not need to write `Type:`.

#### 2.3 Defaults First
The minimal question should contain only information that actually matters to the author.

Defaults include, initially:
* **Points:** `1`
* **Type:** `inferred`
* **Identifier:** generated automatically
* **Feedback:** `none`
* **Title:** generated from question text
* **Scoring:** standard for question type

Defaults should be centralized rather than scattered through the parser and QTI generator.

#### 2.4 Explicit Metadata Overrides Defaults
Metadata remains available when authors need control:

```markdown
## Which languages are Germanic?
Points: 3
Type: multiple-choice
- [x] English
- [x] German
- [ ] French
```

Explicit declarations override inferred/default values. They are not required for ordinary questions.

#### 2.5 Prefer Readability Over Compactness
QuizMD should remain understandable when viewed as plain text.

Special syntax should therefore be:
* visually meaningful;
* easy to remember;
* difficult to mistype;
* compatible with normal Markdown;
* minimal.

---

### 3. Basic QuizMD Structure

A quiz is an ordinary Markdown document:

```markdown
# Introduction to Linguistics
Some optional introductory text.

## What is a morpheme?
- [ ] A speech sound
- [x] The smallest unit carrying meaning or grammatical function
- [ ] A writing system
- [ ] A sentence

## Which are Germanic languages?
- [x] English
- [x] German
- [ ] French
- [ ] Finnish
```

* The first level-1 heading (`#`) is the quiz title by default.
* Level-2 headings (`##`) introduce questions.
* Everything between the question heading and its answer specification belongs to that question.

---

### 4. Question Types

#### 4.1 Single Choice
Use ordinary Markdown task lists or radio button markers (`[o]` / `[x]` / `(o)`):

```markdown
## What is the capital of France?
- [ ] Berlin
- [o] Paris
- [ ] Rome
- [ ] Madrid
```
* **Inference:** Exactly one checked alternative (`[o]`, `[x]`, `(o)`) $\rightarrow$ **Single Choice**.
* **Default points:** 1.

#### 4.2 Multiple Choice
The syntax is identical:

```markdown
## Which are prime numbers?
- [x] 2
- [x] 3
- [ ] 4
- [x] 5
- [ ] 6
```
* **Inference:** More than one checked alternative $\rightarrow$ **Multiple Choice**.
* The author does not need separate SC and MC syntax.

#### 4.3 True / False
True/false uses the same choice mechanism:

```markdown
## English is a Germanic language.
- [x] True
- [ ] False
```
* **Inference:** If the two alternatives are `True` and `False` (case-insensitive), the parser recognizes the question as **True / False**.
* This preserves normal Markdown and avoids another special marker.

#### 4.4 Essay / Free Text
A question without an answer specification is an essay question:

```markdown
## Explain the difference between a phoneme and an allophone.
```

Additional Markdown may form part of the prompt:

```markdown
## Explain the difference between a phoneme and an allophone.
Give one example and briefly explain why the distinction matters in
phonological analysis.
```
* **Inference:** question + no answer specification $\rightarrow$ **Essay**.

#### 4.5 Fill-in-the-Blank
Use a small QuizMD extension:

```markdown
## Complete the sentence.
The past tense of *go* is {{went}}.
```

The braces mark the expected answer while preserving the readability of the sentence. Multiple gaps are supported:

```markdown
## Complete the sentence.
The comparative of *good* is {{better}} and the superlative is {{best}}.
```
Alternative accepted forms can be added later without changing the basic syntax.

#### 4.6 Numerical Answer
Use an answer line:

```markdown
## How many vowels are traditionally recognized in Spanish?
= 5
```

A numerical tolerance uses a lightweight extension:

```markdown
## What is the approximate gravitational acceleration on Earth in m/s²?
= 9.81 ± 0.05
```
(Also supports `+-` syntax e.g. `= 9.81 +- 0.05`). The simple case remains simple.

#### 4.7 Kprim
The presence of `[+]` or `[-]` markers infers Kprim automatically:

```markdown
## Which statements about mammals are correct?
- [+] They have hair or fur.
- [+] Females produce milk for their young.
- [-] All mammals give birth to live young.
- [-] Mammals are ectothermic.
```

* `[+]` indicates a true statement; `[-]` indicates a false statement.
* Validation requires **exactly four statements**.
* `Type: kprim` and optional `Kprim:` header remain supported as explicit overrides.
* The QTI representation and scoring behavior are based on known-good packages exported by the target OpenOLAT version: 4/4 correct = full points, 3/4 correct = half points, $\le$ 2/4 correct = 0 points.

---

### 5. Optional Metadata

Metadata is optional and should be needed only when changing defaults:

```markdown
## Which languages are Germanic?
Points: 3
- [x] English
- [x] German
- [ ] French
```

Initially supported metadata:
* `Points:`
* `Type:`
* `Feedback:`
* `Identifier:`

Most authors should rarely need `Type:`. For example: `Type: multiple-choice` can override automatic inference when necessary.
Metadata uses forgiving, case-insensitive names and normalized values.

---

### 6. Inference Rules

The parser uses a deterministic sequence rather than a collection of unrelated heuristics:

```
Explicit Type?
    ↓ yes
Use explicit type
    ↓ no
Statements with [+] or [-]?
    → Kprim
Fill-in markers {{...}}?
    → Fill-in-the-blank
Numerical answer "= number"?
    → Numerical
Task-list alternatives?
    ↓
    True + False only?
        → True/False
    One correct?
        → Single Choice
    Multiple correct?
        → Multiple Choice
No answer specification?
    → Essay
Otherwise
    → Validation error
```

Inference must be predictable and documented.

---

### 7. Typed Internal Model

Parsing and QTI generation remain completely independent. **Do not generate QTI directly while parsing Markdown.**

The parser produces a typed intermediate model:

```
Quiz
├── title
├── metadata
└── questions
    ├── SingleChoiceQuestion
    ├── MultipleChoiceQuestion
    ├── TrueFalseQuestion
    ├── FillBlankQuestion
    ├── NumericalQuestion
    ├── EssayQuestion
    └── KprimQuestion
```

Each question class enforces its own invariants:
* `SingleChoiceQuestion` $\rightarrow$ exactly one correct choice
* `MultipleChoiceQuestion` $\rightarrow$ at least one correct choice
* `TrueFalseQuestion` $\rightarrow$ exactly True and False
* `KprimQuestion` $\rightarrow$ exactly four statements
* `NumericalQuestion` $\rightarrow$ valid numeric answer, optional valid tolerance

Once an object reaches the QTI generator, its semantic validity is already established.

---

### 8. Defaults

Defaults live in one explicit configuration object:

```python
DEFAULTS = {
    "points": 1,
    "language": "en",
    "feedback": None,
}
```

Question-specific defaults are likewise centralized. This makes later configuration possible without complicating QuizMD.

**Guiding rule**: *Changing a default should not require changing the authoring syntax.*

---

### 9. Markdown Content

Question prompts support ordinary Markdown:

```markdown
## Consider the following sentence:
> The students **have finished** their assignments.
Which word is an auxiliary?
- [ ] students
- [x] have
- [ ] finished
- [ ] assignments
```

The architecture distinguishes **quiz semantics** from **Markdown presentation**.
The Markdown renderer converts supported content to XHTML appropriate for QTI item bodies.

Initial implementation supports a conservative Markdown subset first:
* paragraphs
* emphasis
* strong emphasis
* lists
* inline code
* block quotes

Then adds:
* fenced code
* links
* mathematics
* images

Rich-content support does not block development of the basic converter.

---

### 10. Parsing Strategy

Avoid building the entire language as one large regular expression.
Use a staged parser:

```
Markdown source
      ↓
Document/question segmentation
      ↓
Metadata extraction
      ↓
Answer-structure recognition
      ↓
Type inference
      ↓
Semantic validation
      ↓
Typed Quiz model
```

Parser errors include line numbers where possible:
* *Question 4, line 37: No correct answer is marked.*
* *Question 7, line 62: Kprim requires exactly four statements; found 5.*

Warnings are distinguished from errors.

---

### 11. QTI 2.1 Generation

The QTI layer accepts only validated model objects.

Modular file structure:
```
src/
├── model.py
├── parser.py
├── defaults.py
├── validation.py
├── markdown.py
├── qti21/
│   ├── item.py
│   ├── choice.py
│   ├── text_entry.py
│   ├── numerical.py
│   ├── essay.py
│   ├── kprim.py
│   ├── test.py
│   └── manifest.py
└── packager.py
```
This keeps question-specific QTI logic isolated.

---

### 12. OpenOLAT Compatibility Strategy

The target is: **OpenOLAT-targeted QTI 2.1 output validated against representative OpenOLAT imports.**

Schema validity alone is insufficient. The empirical reference is QTI packages exported from the target OpenOLAT version.

For each supported question type:
```
Create question in OpenOLAT
        ↓
Export QTI package
        ↓
Inspect manifest/XML
        ↓
Create minimal equivalent generator
        ↓
Generate package
        ↓
Import into OpenOLAT
        ↓
Verify rendering + scoring
```

These exported examples become golden fixtures for development and regression testing. Kprim receives particular attention because of its OpenOLAT-specific behavior.

---

### 13. Testing Strategy

Testing operates at three levels:

#### 13.1 Parser and Model Tests
Verify:
* Markdown segmentation
* inference
* defaults
* metadata overrides
* validation
* malformed input
* Unicode
* multiline content

*Example:* `- [x] A` / `- [ ] B` must infer `SingleChoiceQuestion`.

#### 13.2 QTI and Package Tests
Verify:
* generated XML structure
* namespaces (`imscp_v1p1`, `imsqti_v2p1`)
* response declarations
* scoring
* manifest dependencies
* resource paths
* ZIP structure with `imsmanifest.xml` at archive root
* golden-file comparisons

#### 13.3 OpenOLAT Integration Tests
For every supported question type:
1. generate package;
2. import into OpenOLAT;
3. inspect rendering;
4. answer the question;
5. verify scoring;
6. export/reinspect if useful.

A question type is considered supported only after this test succeeds.

---

### 14. User Interface

The Hugging Face Space remains deliberately simple:

```
┌───────────────────────────────────────────────────────────┐
│ QuizMD                                      Preview       │
│                                                           │
│ # Linguistics Quiz                        Linguistics Quiz │
│                                                           │
│ ## What is a morpheme?                    What is ...      │
│                                                           │
│ - [ ] A sound                             ○ A sound        │
│ - [x] A meaningful unit                   ● A meaningful…  │
│                                                           │
│                                                           │
│ Validation: ✓ 5 questions                                 │
│                                                           │
│                   [ Download OpenOLAT QTI ]               │
└───────────────────────────────────────────────────────────┘
```

**Primary workflow:**
$$\text{Write} \longrightarrow \text{Preview} \longrightarrow \text{Download}$$

The interface does not expose QTI configuration unless necessary.
Useful secondary functions:
* upload `.md` / `.txt`
* load example
* paste QuizMD
* validation messages
* syntax help
* GIFT import

---

### 15. GIFT Support

GIFT is treated as an input adapter, not part of the core model:

```
QuizMD Parser ──┐
                ├──→ Typed Quiz Model → QTI
GIFT Parser ────┘
```

This keeps the QTI generator independent of input syntax. GIFT support follows successful implementation of the primary QuizMD workflow.

---

### 16. Implementation Roadmap

#### Phase 0 — OpenOLAT Reference Fixtures (Vertical Slice First)
Before building the general QTI generator:
1. create representative questions in OpenOLAT;
2. export QTI 2.1 packages;
3. inspect XML and manifest structure;
4. store sanitized examples as test fixtures.
*Start with single choice.*
**Goal:** minimal generated SC package $\rightarrow$ successful OpenOLAT import. This establishes the empirical foundation.

#### Phase 1 — Core Model
Implement `model.py`, `defaults.py`, `validation.py`.
Create typed question classes and semantic validation. No Markdown or XML concerns belong here.

#### Phase 2 — Minimal QuizMD Parser
Initially support: Single Choice, Multiple Choice, True/False, Essay.
Implement question segmentation, task-list recognition, automatic inference, points, defaults, line-aware errors.

#### Phase 3 — Core QTI Generator
Implement QTI for SC, MC, TF, Essay. Add assessment items, assessment test, manifest, resource dependencies, ZIP packaging. Every type must pass an OpenOLAT import test.

#### Phase 4 — Gap Questions
Add fill-in-the-blank, multiple text gaps, numerical answer, numerical tolerance. Validate each against OpenOLAT.

#### Phase 5 — Kprim
Implement Kprim separately using OpenOLAT-generated reference packages.
Test representation, exactly 4 statements, correct/incorrect state, and scoring (4/4, 3/4, $\le$ 2/4).

#### Phase 6 — Markdown Rendering
Add Markdown-to-QTI XHTML conversion incrementally:
Start with basic text formatting $\rightarrow$ then add code, links, mathematics, images. Test in actual OpenOLAT rendering.

#### Phase 7 — Web Interface
Build the Gradio/Hugging Face interface around the already-tested converter: editor, preview, validation, file upload, example quizzes, QTI download, syntax cheat sheet.

#### Phase 8 — GIFT Import
Implement GIFT parser $\rightarrow$ same typed Quiz model $\rightarrow$ existing QTI generator.

---

### 17. Minimal QuizMD Cheat Sheet

The basic language is explainable almost entirely with examples:

```markdown
# My Quiz

## Single choice
- [ ] Wrong
- [x] Correct
- [ ] Wrong

## Multiple choice
- [x] Correct
- [ ] Wrong
- [x] Correct

## True or false
- [x] True
- [ ] False

## Fill in the blank
The capital of France is {{Paris}}.

## Numerical
What is 2 + 2?
= 4

## Essay
Explain why languages change over time.

## Kprim
- [+] Correct statement
- [-] Incorrect statement
- [+] Correct statement
- [-] Incorrect statement
```

Advanced features are optional:
```markdown
Points: 3
Type: multiple-choice
Feedback: Review chapter 4.
```

---

### 18. Definition of Success

The project succeeds if an instructor can write:

```markdown
# Week 1 Quiz
## Which language family does English belong to?
- [ ] Romance
- [x] Germanic
- [ ] Slavic
- [ ] Uralic

## English has grammatical gender comparable to German.
- [ ] True
- [x] False

## The smallest contrastive sound unit is a {{phoneme}}.

## Briefly explain what a minimal pair is.
```

and click **Download OpenOLAT QTI** to obtain a QTI 2.1 ZIP that imports into OpenOLAT with the intended:
* question types;
* content;
* correct answers;
* points;
* response behavior;
* scoring.

No XML knowledge and almost no QuizMD-specific knowledge is required.

---

### Final Design Principle

> **QuizMD should feel like writing a quiz in Markdown, not programming an assessment.**

The hierarchy is therefore:
1. Standard Markdown
2. Obvious inference
3. Sensible defaults
4. Small QuizMD extensions
5. Explicit metadata only when necessary

When choosing between additional syntax and a reliable default, **prefer the default**.
