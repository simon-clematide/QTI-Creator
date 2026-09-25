# HOW TO CREATE A QTI-CREATOR MARKDOWN QUIZ

This guide defines the Markdown syntax for generating quizzes for **QTI-Creator**, which converts Markdown quizzes into OpenOLAT QTI 2.1 packages.

**Important:** Use only the syntax described below. Do not invent generic quiz conventions such as `> Answer: A`, `Correct: B`, or similar annotations. QTI-Creator infers question types from the answer syntax.

**Prefer minimal syntax.** QTI-Creator infers question types and applies sensible defaults. Add metadata only when it is needed to override those defaults.

---

## 1. Basic Structure

Use `#` headings for quiz sections and `##` headings for questions.

A minimal quiz looks like this:

```markdown
# Introduction

## Which process divides text into smaller units?

- [X] Tokenization
- [ ] Parsing
- [ ] Classification
```

Section headings are optional. Questions must use `##`.

Headings must contain **plain text only**. Do not put Markdown formatting, inline code, or math notation inside `#` or `##` headings. Put formatted content in the question body instead.

---

## 2. Question Types

QTI-Creator infers the question type from the syntax below. Do not add question-type labels unless explicitly requested.

### Single Choice

Use uppercase `[X]` for the single correct answer and `[ ]` for incorrect answers.

There must be **exactly one** `[X]`.

```markdown
## What is the capital of France?

- [X] Paris
- [ ] Berlin
- [ ] Rome
```

**Important:** `[X]` is uppercase.

---

### Multiple Choice

Use lowercase `[x]` for every correct answer and `[ ]` for incorrect answers.

There must be **at least one** `[x]`. Multiple Choice may also have only one correct answer.

```markdown
## Which are official languages of Switzerland?

- [x] German
- [x] French
- [x] Italian
- [ ] English
```

**Important:** `[x]` is lowercase.

Never mix uppercase `[X]` and lowercase `[x]` within one question.

---

### True / False

Use Single Choice syntax with exactly the alternatives `True` and `False`.

```markdown
## The Earth orbits the Sun.

- [X] True
- [ ] False
```

or:

```markdown
## The Sun orbits the Earth.

- [ ] True
- [X] False
```

---

### Kprim

A Kprim question consists of **exactly four statements**.

Use `[+]` for a true/correct statement and `[-]` for a false/incorrect statement.

```markdown
## Evaluate these statements about mammals.

- [+] They possess hair or fur.
- [+] Females produce milk.
- [-] All mammals give birth to live young.
- [-] They are ectothermic.
```

Do not mix `[+]` or `[-]` with Single Choice or Multiple Choice markers.

---

### Fill-in-the-Blank

Put the expected answer inside double braces:

```markdown
## Complete the sentence.

The process of splitting text into units is called {{tokenization}}.
```

A question may contain multiple gaps.

Use `|` to specify alternative accepted answers:

```markdown
## Complete the sentence.

The spelling may be {{gray | grey}}.
```

All listed alternatives are accepted as correct answers.

---

### Dropdown / Inline Choice

Use `{[...]}` to place a dropdown inside the text. Separate alternatives with `|`.

For AI-generated quizzes, **always mark the correct alternative with Markdown bold**:

```markdown
## European Geography

Switzerland has its federal city in {[**Bern**|Zurich|Geneva]}, while the capital of Germany is {[Munich|**Berlin**|Hamburg]}.
```

Use exactly one bold alternative in each dropdown.

QTI-Creator also accepts a dropdown without a bold alternative, in which case the first alternative is interpreted as correct:

```markdown
{[Bern|Zurich|Geneva]}
```

However, **do not use this shorthand when generating quizzes automatically**. Explicitly mark the correct answer instead.

QTI-Creator shuffles the displayed dropdown alternatives.

Do not mix open text gaps `{{...}}` and dropdown gaps `{[...]}` in the same question, because OpenOLAT does not support that combination.

---

### Hottext (Selectable Spans in Running Text)

Hottext questions present running text where the learner can click words or phrases to select or deselect them.

Mark selectable hottext spans directly within the sentence:
- `{ text }` — Selectable distractor (incorrect). **Whitespace after `{` is strictly required.**
- `{** text **}` — Selectable correct answer. The outer `**` acts as an author-facing solution marker stripped from learner text.
- `{- text }` — Explicitly incorrect selectable distractor.
- `{+ text }` — Explicitly correct selectable answer (preserves any internal markdown, code, or math).

```markdown
## Identify the Parts of Speech

Select all nouns in the following sentence:

The {** cat **} { sat } on the {** mat **} near the {** fireplace **}.
```

Example with code and explicit markup:
```markdown
## Python Keywords

Select all valid Python statements that declare or import modules:

In Python, we write {+ `import math` } or {- `using math;` } to load libraries.
```

Rules:
- Whitespace after the opening brace (`{ `, `{** `, `{+ `, `{- `) is strictly required to avoid collisions with code, LaTeX math, or template curly braces.
- Hottext questions support partial credit scoring by default (proportional correct minus incorrect, clamped between 0 and maximum points), or `Scoring: all-correct`.
- Cannot be mixed with open gaps `{{...}}`, dropdown gaps `{[...]}`, or task-list choices (`- [ ]`) in the same question.

---

### Numerical

Start the answer line with `=` followed by the correct numerical value.

An optional tolerance can be specified with `±`.

```markdown
## Acceleration due to gravity

What is the approximate acceleration due to gravity on Earth?

= 9.81 ± 0.05
```

Without a tolerance, the specified value is treated as the target value.

---

### Order / Sequencing

Use an ordered Markdown task list with empty brackets.

Write the items in the **correct order**:

```markdown
## Order these processing stages.

1. [ ] Tokenization
1. [ ] Parsing
1. [ ] Evaluation
```

The order in the Markdown source defines the correct solution.

The numeric labels themselves are ignored, so repeated `1.` numbering is recommended.

Do not use `[X]` or `[x]` in an ordering question.

---

### Essay / Free Text

Write a question without any answer specification:

```markdown
## Cellular Respiration

Explain the difference between aerobic and anaerobic respiration.
```

Essay questions are intended for manual grading.

---

## 3. Optional Quiz Metadata

Quiz-level metadata can be specified using YAML frontmatter.

**YAML frontmatter is optional.** Do not generate it unless quiz-level metadata or overrides are useful or explicitly requested.

Example:

```yaml
---
title: "Introduction to Linguistics"
version: "1.0.0"
language: "en"
topic: "Linguistics"
keywords: ["tokenization", "morphology"]
shuffle: yes
---
```

Do not invent unnecessary metadata merely to fill these fields.

In particular, do not specify settings that simply reproduce QTI-Creator's defaults.

---

## 4. Optional Question Metadata

Question-specific metadata can be added when needed.

Questions are worth **1 point by default**. Use `Points:` only when a different weight is required.

Example:

```markdown
## Which data structure provides constant-time average lookup?

Points: 2
Topic: Data Structures
Keywords: hash table, complexity
Shuffle: no
Hint: Think about the average-case lookup operation.
Feedback: A hash table provides average-case constant-time lookup.

- [X] Hash table
- [ ] Linked list
- [ ] Binary search tree
- [ ] Array searched sequentially
```

Supported metadata includes fields such as:

```text
Points: 2
Topic: Sub-topic
Keywords: keyword1, keyword2
Shuffle: no
Hint: A useful hint for the student.
Feedback: An explanation shown after submission.
```

Metadata should be used only when it adds useful information or overrides a default.

`Points:` always specifies the maximum score for the **whole question**, not an individual answer.

---

## 5. Markdown Content

Normal Markdown can be used in question bodies, answers, hints, and feedback.

This includes ordinary formatting, lists, code, mathematical notation, links, and images where appropriate.

### Images

Use normal Markdown image syntax:

```markdown
![Diagram of the architecture](architecture.png)
```

A custom display width can be specified when needed:

```markdown
![Diagram of the architecture](architecture.png =300x)
```

Use meaningful alt text.

Do not use ordinary links as substitutes for images.

---

## 6. Rules for Generating Good Questions

When generating questions automatically, follow these rules.

1. **Stay grounded in the supplied material.** When source material such as slides, notes, or readings is provided, questions and answer keys must be supported by that material. Do not introduce facts merely because they seem plausible or are known from elsewhere.

2. **Omit unsupported questions.** If the supplied material does not support a reliable question and answer, omit that question rather than inventing information.

3. **Verify every answer key.** Before returning the quiz, check every correct answer against the supplied material.

4. **Prefer meaningful understanding over trivial recall.** For university-level teaching, prefer questions that test concepts, relationships, interpretation, application, or common misunderstandings when the material supports them. Use factual recall when it is itself a relevant learning objective.

5. **Write unambiguous questions.** A Single Choice question must have exactly one defensible correct answer. For Multiple Choice, identify every correct alternative.

6. **Write plausible distractors.** Incorrect alternatives should be relevant to the topic and plausible enough to test understanding. Avoid obviously absurd alternatives or wording that reveals the correct answer.

7. **Do not give away the answer.** Avoid repeating the correct answer or an obvious paraphrase of it in the question wording.

8. **Use hints selectively.** For self-tests, use `Hint:` when a useful hint can guide the student's reasoning without revealing the answer. Do not add generic or redundant hints merely because the field is available.

9. **Use feedback for explanations.** Put post-submission explanations in `Feedback:`. Do not invent syntax such as `> Explanation:`.

10. **Keep headings simple.** Do not put Markdown formatting, code, or mathematical notation inside `#` or `##` headings. Put such content in the question body.

---

## 7. Syntax Validation Checklist

Before returning a generated quiz, check all of the following:

- Every question begins with a `##` heading.
- Single Choice uses exactly one uppercase `[X]`.
- Multiple Choice uses one or more lowercase `[x]`.
- `[X]` and `[x]` are never mixed within one question.
- Kprim uses exactly four statements marked only with `[+]` or `[-]`.
- Fill-in answers use `{{...}}`.
- Dropdown answers use `{[...]}` and explicitly mark exactly one correct alternative with `**...**`.
- Open text gaps and dropdown gaps are not mixed in the same question.
- Numerical answers use `= value` or `= value ± tolerance`.
- Ordering uses an ordered list with `[ ]`, written in the correct source order.
- Essay questions contain no answer specification.
- Every answer key is factually correct.
- Metadata is omitted when it is not needed.

---

## 8. Output Requirements

When asked to generate a QTI-Creator quiz:

- Return **only the finished QTI-Creator Markdown**.
- Do **not** wrap the output in a Markdown code fence.
- Do not add commentary before or after the quiz.
- Do not invent syntax that is not described in this specification.
- Prefer minimal syntax and omit unnecessary metadata.
- Use only question types appropriate to the supplied material and learning objectives.
- If the requested number of reliable questions cannot be supported by the source material, generate fewer rather than inventing unsupported content.
- Check that every question conforms to exactly one recognized question type.
- Verify all correct answers before returning the quiz.
