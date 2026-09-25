# HOW TO CREATE A QTI-CREATOR MARKDOWN QUIZ

A concise syntax and formatting guide for AI agents generating quizzes for the **QTI-Creator** engine. This engine parses Markdown into OpenOLAT QTI 2.1 packages.

**CRITICAL RULE:** Do NOT invent generic markdown quiz formats (e.g. `> Answer: A`). You MUST strictly use the native syntax indicators below for the engine to recognize the question types.

---

## 1. Global Structure & Metadata

Every quiz should start with a YAML frontmatter block for global configuration, followed by sections (`#`) and questions (`##`).

```yaml
---
title: "Quiz Title"
version: "1.0.0"
language: "en"
topic: "General Topic"
keywords: ["keyword1", "keyword2"]
shuffle: yes
scoring: partial
---

# Section 1: Introduction (Optional)
Optional instructions for this section.

## Question 1 text here
...
```

*Note: Headings (`#` and `##`) must contain **plain text only**. No markdown formatting (`**`, `\``) or LaTeX math (`$ $`) inside the headings.*

---

## 2. Question Types & Syntax

The engine automatically infers the question type based strictly on the marker syntax.

### Single Choice (Strict Uppercase `[X]`)
Exactly ONE correct answer marked with an uppercase `X`.
```markdown
## What is the capital of France?
- [X] Paris
- [ ] Berlin
- [ ] Rome
```

### Multiple Choice (Strict Lowercase `[x]`)
One or more correct answers marked with a lowercase `x`.
```markdown
## Which are official languages of Switzerland?
- [x] German
- [x] French
- [x] Italian
- [ ] English
```

### Kprim / Matrix (True/False Statements)
Exactly 4 statements. Use `[+]` for true and `[-]` for false.
```markdown
## Evaluate these statements about Mammals:
- [+] They possess hair or fur.
- [+] Females produce milk.
- [-] All mammals give birth to live young.
- [-] They are ectothermic.
```

### Fill-in-the-Blank (Text Entry)
Embed the answer inside the text using double braces. Use `|` for accepted alternatives.
```markdown
## Color Spelling
The American spelling of the colour is {{gray | grey | gray colour}}.
```

### Fill-in-the-Blank with Dropdown (Inline Choice)
Embed multiple choices inside text using `{[option 1|option 2|option 3]}`.
Mark the correct answer using Markdown bold `**...**` (or `__...__`).
If no bold option is specified, the first option is the correct answer and shuffling is automatically enforced for the dropdown options.
*(Note: OpenOLAT does not allow mixing open text entry gaps and dropdown gaps in the same question).*
```markdown
## European Geography
Switzerland has its federal city in {[Bern|Zurich|Geneva]}, while the capital of Germany is {[Munich|**Berlin**|Hamburg]}.
```


### Numerical
Start the answer line with `=` followed by the value and an optional `±` tolerance.
```markdown
## Gravity
What is the acceleration due to gravity on Earth?
= 9.81 ± 0.05
```

### Order / Sequencing
Use a numbered list with empty brackets. The order written in the Markdown is the correct solution.
```markdown
## Order the processing stages:
1. [ ] Tokenization
1. [ ] Parsing
1. [ ] Evaluation
```

### Essay / Free Text
Just write the question prompt with no answer options.
```markdown
## Cellular Respiration
Explain the difference between aerobic and anaerobic respiration.
```

---

## 3. Question Metadata & Overrides

You can add metadata to individual questions by putting these keys right after the `##` heading or after the options.

```markdown
## Complex Question Example
Points: 2
Topic: Sub-topic
Keywords: kw3, kw4
Shuffle: no
Hint: Think about the time complexity.
Feedback: This is the explanation shown to the student after submission. You can use math here like $O(n)$.
- [X] Correct
- [ ] Incorrect
```

---

## 4. Content Quality Rules for AI Agents

1. **Strictly adhere to the syntax.** Mixing `[X]` and `[x]` in the same question is a fatal parse error.
2. **University-Level Difficulty:** Questions must be adequate for a university level. Avoid trivial recall; focus on application, analysis, and deeper conceptual understanding.
3. **Use Hints for Self-Tests:** Since these are often used as self-tests, actively provide a `Hint: ...` for questions to guide students toward the goal or solution without giving away the answer directly.
4. **Explanations go in `Feedback:`:** Do not use `> Explanation:`. Use the native `Feedback:` keyword to provide the post-submission rationale.
5. **No formatting in Headers:** Move any code (`\``) or math (`$ $`) from the `##` title down into the body of the question.
6. **Images:** Use the custom size syntax if needed: `![Alt text](image.png =300x)`.
