"""Tests for the QuizMD parser."""

import unittest
from src.parser import parse_quizmd
from src.model import (
    SingleChoiceQuestion,
    MultipleChoiceQuestion,
    TrueFalseQuestion,
    EssayQuestion,
    FillBlankQuestion,
    InlineChoiceQuestion,
    NumericalQuestion,
    KprimQuestion,
    OrderQuestion,
)



class TestQuizMDParser(unittest.TestCase):

    def test_single_choice_inference(self):
        text = """# Capitals Quiz
## What is the capital of France?
- [ ] Berlin
- [X] Paris
- [ ] Rome
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(quiz.title, "Capitals Quiz")
        self.assertEqual(len(quiz.questions), 1)
        q = quiz.questions[0]
        self.assertIsInstance(q, SingleChoiceQuestion)
        self.assertEqual(q.points, 1.0)
        self.assertEqual(len(q.choices), 3)
        self.assertEqual([c.text for c in q.choices if c.is_correct], ["Paris"])

    def test_single_choice_multiple_uppercase_X_error(self):
        text = """## Multiple Single Choice answers:
- [X] Option 1
- [X] Option 2
- [ ] Option 3
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Single-choice question has 2 [X] answers; exactly 1 is required." in d.message for d in diags))

    def test_mixed_markers_error(self):
        text = """## Mixed markers question:
- [X] Option 1
- [x] Option 2
- [ ] Option 3
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Mixed markers: cannot combine single-choice [X] and multiple-choice [x]" in d.message for d in diags))

    def test_choice_and_kprim_conflict_error(self):
        text = """## Conflicting choice and kprim:
- [X] Option 1
- [+] Option 2
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Cannot combine choice markers [X]/[x] with Kprim markers [+]/[-]" in d.message for d in diags))

    def test_multiple_choice_single_lowercase_x(self):
        text = """## Question with single lowercase x:
- [ ] Option 1
- [x] Option 2
- [ ] Option 3
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        self.assertIsInstance(q, MultipleChoiceQuestion)
        self.assertEqual([c.text for c in q.choices if c.is_correct], ["Option 2"])


    def test_multiple_choice_inference(self):
        text = """## Select prime numbers:
- [x] 2
- [x] 3
- [ ] 4
- [x] 5
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertIsInstance(q, MultipleChoiceQuestion)
        self.assertEqual(len([c for c in q.choices if c.is_correct]), 3)
        self.assertEqual(q.scoring, "partial")

    def test_multiple_choice_scoring_metadata(self):
        text = """# Quiz with Scoring Settings
scoring: all-correct

## Question with Inherited Scoring
- [x] Choice A
- [x] Choice B
- [ ] Choice C

## Question with Explicit Override
scoring: partial
- [x] Choice 1
- [x] Choice 2
- [ ] Choice 3
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        self.assertEqual(quiz.mc_scoring, "all-correct")
        self.assertEqual(quiz.questions[0].scoring, "all-correct")
        self.assertEqual(quiz.questions[1].scoring, "partial")

    def test_multiple_choice_invalid_scoring_diagnostic(self):
        text = """## Bad Scoring
scoring: invalid_method
- [x] A
- [x] B
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Invalid scoring method 'invalid_method'" in d.message for d in diags))

    def test_question_hint_parsing(self):
        text = """## Capital of Italy
Hint: It is known as the Eternal City.
Feedback: Rome is the capital of Italy.
- [ ] Milan
- [X] Rome
- [ ] Naples
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertEqual(q.hint, "It is known as the Eternal City.")
        self.assertEqual(q.feedback, "Rome is the capital of Italy.")

    def test_true_false_inference(self):
        text = """## Earth is flat.
- [ ] True
- [X] False
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertIsInstance(q, TrueFalseQuestion)
        self.assertEqual(len(q.choices), 2)
        false_choice = [c for c in q.choices if c.text.lower() == "false"][0]
        self.assertTrue(false_choice.is_correct)

    def test_essay_inference(self):
        text = """## Discuss the causes of the Industrial Revolution.
Provide at least two key economic factors.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertIsInstance(q, EssayQuestion)
        self.assertIn("economic factors", q.prompt)

    def test_fill_blank_inference(self):
        text = """## Irregular verbs:
The past tense of *go* is {{went}} and the past participle is {{gone}}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertIsInstance(q, FillBlankQuestion)
        self.assertEqual(len(q.gaps), 2)
        self.assertEqual(q.gaps[0].expected_value, "went")
        self.assertEqual(q.gaps[1].expected_value, "gone")

    def test_fill_blank_escaping(self):
        text = r"""## Code and Math Gaps
The function is {{answer containing \}\} braces | alternative}}.
The symbol is {{a \| b}} and the path is {{C:\\data}}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertIsInstance(q, FillBlankQuestion)
        self.assertEqual(len(q.gaps), 3)
        self.assertEqual(q.gaps[0].expected_value, "answer containing }} braces")
        self.assertEqual(q.gaps[0].alternatives, ["alternative"])
        self.assertEqual(q.gaps[1].expected_value, "a | b")
        self.assertEqual(q.gaps[1].alternatives, [])
        self.assertEqual(q.gaps[2].expected_value, r"C:\data")

    def test_numerical_inference(self):
        text = """## Gravitational acceleration:
= 9.81 ± 0.05
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertIsInstance(q, NumericalQuestion)
        self.assertAlmostEqual(q.answer, 9.81)
        self.assertAlmostEqual(q.tolerance, 0.05)

    def test_kprim_inference(self):
        text = """## Mammal characteristics:
Points: 2
- [+] Have hair
- [+] Produce milk
- [-] All lay eggs
- [-] Cold-blooded
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        self.assertIsInstance(q, KprimQuestion)
        self.assertEqual(q.points, 2.0)
        self.assertEqual(len(q.statements), 4)
        self.assertTrue(q.statements[0].is_correct)
        self.assertFalse(q.statements[2].is_correct)

    def test_kprim_with_optional_header(self):
        text = """## Mammal characteristics with header:
Kprim:
- [+] Have hair
- [+] Produce milk
- [-] All lay eggs
- [-] Cold-blooded
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        self.assertIsInstance(q, KprimQuestion)
        self.assertEqual(len(q.statements), 4)


    def test_metadata_override(self):
        text = """## Single option but explicit MC:
Points: 5
Type: multiple-choice
Feedback: Important question.
- [x] Only choice correct
- [ ] Another choice
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertIsInstance(q, MultipleChoiceQuestion)
        self.assertEqual(q.points, 5.0)
        self.assertEqual(q.feedback, "Important question.")

    def test_feedback_placement_after_choices(self):
        text = """## Capital of France
- [ ] Berlin
- [X] Paris
Feedback: Paris has been the capital since 508 AD.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        self.assertEqual(q.feedback, "Paris has been the capital since 508 AD.")

    def test_missing_correct_answer_diagnostic(self):
        text = """## Broken question:
- [ ] Option 1
- [ ] Option 2
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("No correct answer is marked with [X] or [x]." in d.message for d in diags))

    def test_fenced_code_block_in_question(self):
        text = '''## What does this function return?
Consider the following `Python` implementation:
```python
def calc(x):
    # This line has an equals sign:
    val = x * 2
    # This line looks like a task item: - [ ]
    return val + 1
```
What is the result of `calc(5)`?
- [X] `11`
- [ ] `10`
- [ ] `5`
'''
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        self.assertIsInstance(q, SingleChoiceQuestion)
        self.assertEqual(len(q.choices), 3)
        self.assertIn("```python", q.prompt)
        self.assertIn("return val + 1", q.prompt)
        self.assertEqual([c.text for c in q.choices if c.is_correct], ["`11`"])

    def test_kprim_wrong_statement_count_diagnostic(self):
        text = """## Bad Kprim:
- [+] One
- [-] Two
- [+] Three
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Kprim requires exactly 4 statements" in d.message for d in diags))


    def test_code_block_with_newlines(self):
        from src.markdown import markdown_to_qti_xhtml
        prompt = """```python

def greet():
    return "hi"

```

- [ ] A
- [X] B"""
        xhtml = markdown_to_qti_xhtml(prompt)
        self.assertIn("<pre><code>def greet():\n    return &quot;hi&quot;</code></pre>", xhtml)


    def test_latex_math_preservation_and_protection(self):
        from src.markdown import markdown_to_qti_xhtml
        
        # Display math block ($$ and \[)
        disp_text = "$$\\frac{a}{b}$$"
        self.assertEqual(markdown_to_qti_xhtml(disp_text), '<p style="text-align:center"><span class="math" title="%5Cfrac%7Ba%7D%7Bb%7D">\\frac{a}{b}</span></p>')
        self.assertEqual(markdown_to_qti_xhtml(disp_text, render_math=False), "<pre class='math-raw'>$$\\frac{a}{b}$$</pre>")

        bracket_disp_text = "\\[\\frac{c}{d}\\]"
        self.assertEqual(markdown_to_qti_xhtml(bracket_disp_text), '<p style="text-align:center"><span class="math" title="%5Cfrac%7Bc%7D%7Bd%7D">\\frac{c}{d}</span></p>')

        # Inline math wrapped in <span class="math" title="...">latex</span> (no dollar signs)
        inl_text = "The solution is $x=\\frac{a}{b}$."
        self.assertEqual(
            markdown_to_qti_xhtml(inl_text, render_math=True),
            '<p>The solution is <span class="math" title="x%3D%5Cfrac%7Ba%7D%7Bb%7D">x=\\frac{a}{b}</span>.</p>',
        )
        self.assertEqual(
            markdown_to_qti_xhtml(inl_text, render_math=False),
            "<p>The solution is <code>$x=\\frac{a}{b}$</code>.</p>",
        )

        # Inline math with \( ... \) delimiters
        paren_text = "What is \\(AB\\)?"
        self.assertEqual(
            markdown_to_qti_xhtml(paren_text, render_math=True),
            '<p>What is <span class="math" title="AB">AB</span>?</p>',
        )

        # Math symbols (* and _) protected from markdown italics/bold
        formula_text = "Check $x_1 * y_2 * z_3$ and **bold text**."
        xhtml = markdown_to_qti_xhtml(formula_text)
        self.assertIn('<span class="math" title="x_1%20%2A%20y_2%20%2A%20z_3">x_1 * y_2 * z_3</span>', xhtml)
        self.assertIn("<strong>bold text</strong>", xhtml)
        self.assertNotIn("<em>", xhtml)

        # XML-sensitive characters inside math properly escaped for QTI XML
        xml_math = "Condition: $a < b & c > d$."
        self.assertIn('<span class="math" title="a%20%3C%20b%20%26%20c%20%3E%20d">a &lt; b &amp; c &gt; d</span>', markdown_to_qti_xhtml(xml_math))

    def test_quiz_version_from_header_metadata(self):
        text = """# Physics Quiz
Version: 1.2.3
Language: de

## What is the speed of light?
- [X] ~300,000 km/s
- [ ] ~150,000 km/s
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(quiz.version, "1.2.3")
        self.assertEqual(quiz.language, "de")
        self.assertEqual(quiz.title, "Physics Quiz")

    def test_quiz_version_from_yaml_frontmatter(self):
        text = """---
title: Biology Quiz
version: 2.0.1
language: fr
---

## What is DNA?
- [X] Genetic material
- [ ] A protein
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(quiz.version, "2.0.1")
        self.assertEqual(quiz.title, "Biology Quiz")
        self.assertEqual(quiz.language, "fr")

    def test_quiz_version_consistent_frontmatter_and_header(self):
        text = """---
title: History Quiz
version: 1.0.0
---
# History Quiz
Version: 1.0.0

## What year did WW2 end?
- [X] 1945
- [ ] 1939
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(quiz.version, "1.0.0")

    def test_quiz_version_inconsistent_warning(self):
        text = """---
title: Math Quiz
version: 1.0.0
---
# Math Quiz
Version: 2.0.0

## What is 1 + 1?
- [X] 2
- [ ] 3
"""
        quiz, diags = parse_quizmd(text)
        warnings = [d for d in diags if "Inconsistent version" in d.message]
        self.assertEqual(len(warnings), 1)
        self.assertIn("frontmatter specifies '1.0.0'", warnings[0].message)
        self.assertIn("header metadata specifies '2.0.0'", warnings[0].message)
        self.assertEqual(quiz.version, "2.0.0")

    def test_quiz_title_inconsistent_warning(self):
        text = """---
title: Front Title
version: 1.0.0
---
# Header Title

## Question
- [X] A
- [ ] B
"""
        quiz, diags = parse_quizmd(text)
        warnings = [d for d in diags if "Inconsistent title" in d.message]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(quiz.title, "Header Title")

    def test_quiz_and_question_metadata_inheritance_and_override(self):
        text = """---
topic: General Science
keywords: [science, intro]
---
# Science Quiz
Version: 1.2.3
Language: de

## Question 1 (Inherits quiz metadata)
- [X] Correct
- [ ] Wrong

## Question 2 (Overrides topic, keywords, language, version)
Topic: Quantum Physics
Keywords: physics, quantum, subatomic
Language: en
Version: 2.0.0
- [X] Quantum
- [ ] Classical
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(quiz.topic, "General Science")
        self.assertEqual(quiz.keywords, ["science", "intro"])
        self.assertEqual(quiz.version, "1.2.3")
        self.assertEqual(quiz.language, "de")

        # Q1 inherited
        q1 = quiz.questions[0]
        self.assertEqual(q1.topic, "General Science")
        self.assertEqual(q1.keywords, ["science", "intro"])
        self.assertEqual(q1.language, "de")
        self.assertEqual(q1.additional_info, "Version: 1.2.3")

        # Q2 overridden
        q2 = quiz.questions[1]
        self.assertEqual(q2.topic, "Quantum Physics")
        self.assertEqual(q2.keywords, ["physics", "quantum", "subatomic"])
        self.assertEqual(q2.language, "en")
        self.assertEqual(q2.additional_info, "Version: 2.0.0")

    def test_shuffle_parsing_and_inheritance(self):
        text = """# Default Shuffled Quiz

## Question 1 (Inherits QuizMD default: True)
- [X] A
- [ ] B

## Question 2 (Explicit override to False)
Shuffle: no
- [x] C
- [ ] D
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        self.assertTrue(quiz.shuffle)
        self.assertTrue(quiz.questions[0].shuffle)
        self.assertFalse(quiz.questions[1].shuffle)

    def test_gap_alternatives_parsing(self):
        text = """## Spelling Test
The color can be written {{gray | grey |  greyish }}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        self.assertEqual(len(quiz.questions), 1)
        q = quiz.questions[0]
        self.assertIsInstance(q, FillBlankQuestion)
        self.assertEqual(len(q.gaps), 1)
        gap = q.gaps[0]
        self.assertEqual(gap.expected_value, "gray")
        self.assertEqual(gap.alternatives, ["grey", "greyish"])

    def test_order_question_inference_generous_numbering(self):
        text = """## Order the stages of an NLP pipeline
1. [ ] Tokenization
1. [ ] Feature extraction
99. [ ] Model inference
2. [ ] Evaluation
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(len(quiz.questions), 1)
        q = quiz.questions[0]
        self.assertIsInstance(q, OrderQuestion)
        self.assertEqual(len(q.items), 4)
        # Verify source order is strictly preserved
        self.assertEqual(
            [it.text for it in q.items],
            ["Tokenization", "Feature extraction", "Model inference", "Evaluation"]
        )

    def test_order_question_min_items_validation(self):
        text = """## Only One Item
1. [ ] Solo item
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("requires at least 2 items" in d.message for d in diags))

    def test_order_question_invalid_mark_rejected(self):
        text = """## Invalid Numbered Task List
1. [x] First
2. [ ] Second
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Numbered task-list items cannot contain [x]" in d.message for d in diags))

    def test_ordinary_numbered_list_not_converted_to_order(self):
        text = """## Essay with Numbered Points
Explain why the following three principles matter:
1. Transparency
2. Accountability
3. Fairness
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        self.assertEqual(len(quiz.questions), 1)
        q = quiz.questions[0]
        self.assertIsInstance(q, EssayQuestion)
        self.assertIn("1. Transparency", q.prompt)

    def test_all_registered_examples_parse_and_package(self):
        from src.examples import EXAMPLES
        from src.packager import create_qti_package_bytes
        from src.validation import Severity

        for name, text in EXAMPLES.items():
            with self.subTest(example=name):
                quiz, diags = parse_quizmd(text)
                errors = [d for d in diags if d.severity == Severity.ERROR]
                self.assertEqual(len(errors), 0, f"Errors in {name}: {[str(e) for e in errors]}")
                self.assertGreater(len(quiz.questions), 0, f"No questions in {name}")
                pkg = create_qti_package_bytes(quiz)
                self.assertGreater(len(pkg), 1000, f"Package too small for {name}")


    def test_multi_section_parsing_and_descriptions(self):
        text = """---
title: Comprehensive Final Exam
version: 1.0.0
---

# Section 1: Mathematics & Logic
Instructions: Calculators are permitted for this section.

## Simple Arithmetic
- [X] 4
- [ ] 5

## Prime Numbers
- [x] 2
- [x] 3
- [ ] 4

# Section 2: Biology & Chemistry
Instructions: Answer all questions in this section carefully.

## Water Formula
What is water?
- [X] H2O
- [ ] CO2
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(quiz.title, "Comprehensive Final Exam")
        self.assertEqual(len(quiz.sections), 2)
        self.assertEqual(len(quiz.questions), 3)

        s1 = quiz.sections[0]
        self.assertEqual(s1.title, "Section 1: Mathematics & Logic")
        self.assertIn("Calculators are permitted", s1.description)
        self.assertEqual(len(s1.questions), 2)

        s2 = quiz.sections[1]
        self.assertEqual(s2.title, "Section 2: Biology & Chemistry")
        self.assertIn("Answer all questions in this section", s2.description)
        self.assertEqual(len(s2.questions), 1)

    def test_section_title_used_as_test_title_when_no_yaml_title(self):
        text = """# First Section As Test Title
## Question in Section
- [X] Yes
- [ ] No

# Second Section
## Another Question
- [X] True
- [ ] False
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(quiz.title, "First Section As Test Title")
        self.assertEqual(len(quiz.sections), 2)
        self.assertEqual(quiz.sections[0].title, "First Section As Test Title")
        self.assertEqual(quiz.sections[1].title, "Second Section")

    def test_implicit_section_when_no_h1_present(self):
        text = """## Question 1 Without Section
- [X] A
- [ ] B

## Question 2 Without Section
- [X] C
- [ ] D
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(len(quiz.sections), 1)
        self.assertEqual(len(quiz.questions), 2)
        self.assertEqual(quiz.sections[0].questions[0].title, "Question 1 Without Section")


    def test_markdown_table_rendering(self):
        from src.markdown import markdown_to_qti_xhtml
        md = """Consider the following table:

| Function | Complexity | Description |
| :--- | :---: | ---: |
| `sort()` | $\\mathcal{O}(n \\log n)$ | Quick sort |
| `find()` | $\\mathcal{O}(n)$ | **Linear** scan |

What is the fastest?
"""
        html_out = markdown_to_qti_xhtml(md)
        self.assertIn('<table class="b_default" style="border-collapse:collapse;width:100%;">', html_out)
        self.assertIn('<thead>', html_out)
        self.assertIn('<tbody>', html_out)
        self.assertIn('<th style="text-align: left;">Function</th>', html_out)
        self.assertIn('<th style="text-align: center;">Complexity</th>', html_out)
        self.assertIn('<th style="text-align: right;">Description</th>', html_out)
        self.assertIn('<code>sort()</code>', html_out)
        self.assertIn('<strong>Linear</strong>', html_out)
        self.assertIn('<span class="math"', html_out)


    def test_inline_choice_inference_with_bold(self):
        text = """## European Geography
Switzerland has its federal city in {[Bern|Zurich|Geneva]}, while the capital of Germany is {[Munich|**Berlin**|Hamburg]}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(len(quiz.questions), 1)
        q = quiz.questions[0]
        self.assertIsInstance(q, InlineChoiceQuestion)
        self.assertEqual(len(q.gaps), 2)
        # Gap 1: No bold -> first item Bern is correct, shuffle must be enforced
        self.assertTrue(q.gaps[0].shuffle)
        self.assertEqual([c.text for c in q.gaps[0].choices if c.is_correct], ["Bern"])
        self.assertEqual([c.text for c in q.gaps[0].choices], ["Bern", "Zurich", "Geneva"])
        # Gap 2: Berlin is bold -> Berlin is correct, shuffle inherits from quiz default (True)
        self.assertTrue(q.gaps[1].shuffle)
        self.assertEqual([c.text for c in q.gaps[1].choices if c.is_correct], ["Berlin"])
        self.assertEqual([c.text for c in q.gaps[1].choices], ["Munich", "Berlin", "Hamburg"])

    def test_inline_choice_first_item_correct_enforces_shuffle(self):
        text = """---
shuffle: false
---
## Dropdown with quiz shuffle false
Choose the right word: The sky is {[blue|green|red]}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        self.assertIsInstance(q, InlineChoiceQuestion)
        # Because no bold was used, the first option is correct and shuffle is strictly enforced (True)
        self.assertTrue(q.gaps[0].shuffle)
        self.assertEqual([c.text for c in q.gaps[0].choices if c.is_correct], ["blue"])

    def test_inline_choice_bold_respects_shuffle_false(self):
        text = """---
shuffle: false
---
## Dropdown with quiz shuffle false
Choose the right word: The sky is {[green|**blue**|red]}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        self.assertIsInstance(q, InlineChoiceQuestion)
        # Because bold was used, gap.shuffle inherits quiz shuffle: false
        self.assertFalse(q.gaps[0].shuffle)
        self.assertEqual([c.text for c in q.gaps[0].choices if c.is_correct], ["blue"])

    def test_mixed_text_and_dropdown_gaps_error(self):
        text = """## Mixed Cloze Question
Fill in the text {{word}} and choose from dropdown {[option 1|option 2]}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Cannot mix open text gaps {{...}} and dropdown gaps {[...]}" in d.message for d in diags))

    def test_dropdown_gap_with_choices_conflict_error(self):
        text = """## Conflicting dropdown and task list
Choose: {[A|B]}
- [X] Choice A
- [ ] Choice B
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Cannot combine dropdown gaps {[...]} with choices" in d.message for d in diags))

    def test_hottext_canonical_parsing(self):
        text = """## Parts of Speech
The {** cat **} { sat } on the {** mat **}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        from src.model import HottextQuestion
        self.assertIsInstance(q, HottextQuestion)
        self.assertEqual(len(q.items), 3)
        self.assertEqual(q.items[0].text, "cat")
        self.assertTrue(q.items[0].is_correct)
        self.assertEqual(q.items[1].text, "sat")
        self.assertFalse(q.items[1].is_correct)
        self.assertEqual(q.items[2].text, "mat")
        self.assertTrue(q.items[2].is_correct)

    def test_hottext_explicit_authoring_and_formatting(self):
        text = """## Python Statements
In Python, we use {+ `import math` } or {- `using math;` } to load libraries.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        from src.model import HottextQuestion
        self.assertIsInstance(q, HottextQuestion)
        self.assertEqual(len(q.items), 2)
        self.assertEqual(q.items[0].text, "`import math`")
        self.assertTrue(q.items[0].is_correct)
        self.assertEqual(q.items[1].text, "`using math;`")
        self.assertFalse(q.items[1].is_correct)

    def test_hottext_whitespace_requirement_avoids_templates(self):
        # {template} without whitespace after { is not a hottext token
        text = """## Code Template
Here is `{variable}` in Python.
"""
        quiz, diags = parse_quizmd(text)
        q = quiz.questions[0]
        from src.model import EssayQuestion
        self.assertIsInstance(q, EssayQuestion)

    def test_hottext_conflict_with_gaps_error(self):
        text = """## Conflict Hottext and Gap
The {** cat **} is {{black}}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Cannot mix hottext tokens and open text gaps" in d.message for d in diags))

    def test_hottext_conflict_with_choices_error(self):
        text = """## Conflict Hottext and Choices
The {** cat **} sat.
- [X] Choice A
- [ ] Choice B
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Cannot combine hottext tokens with choices" in d.message for d in diags))


    def test_match_single_choice_inference(self):
        text = """## Match each word with its category.
| Item | Match |
|---|---|
| dog | noun |
| cat | noun |
| run | verb |
| quickly | adverb |
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(len(quiz.questions), 1)
        from src.model import AssociationQuestion
        q = quiz.questions[0]
        self.assertIsInstance(q, AssociationQuestion)
        self.assertEqual(q.interaction, "match")
        self.assertFalse(q.multiple)
        self.assertEqual(len(q.items), 4)
        self.assertEqual([it.text for it in q.items], ["dog", "cat", "run", "quickly"])
        self.assertEqual([t.text for t in q.targets], ["noun", "verb", "adverb"])
        # dog and cat share same target ID
        self.assertEqual(q.items[0].target_ids, [q.targets[0].identifier])
        self.assertEqual(q.items[1].target_ids, [q.targets[0].identifier])
        self.assertEqual(q.items[2].target_ids, [q.targets[1].identifier])
        self.assertEqual(q.items[3].target_ids, [q.targets[2].identifier])

    def test_match_multiple_choice_ditto_inference(self):
        text = """## Match countries with official languages.
| Item | Match |
|---|---|
| Switzerland | German |
|             | French |
|             | Italian |
| Belgium     | French |
|             | Dutch |
| Canada      | English |
|             | French |
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        from src.model import AssociationQuestion
        self.assertIsInstance(q, AssociationQuestion)
        self.assertEqual(q.interaction, "match")
        self.assertTrue(q.multiple)
        self.assertEqual(len(q.items), 3)
        self.assertEqual([it.text for it in q.items], ["Switzerland", "Belgium", "Canada"])
        self.assertEqual([t.text for t in q.targets], ["German", "French", "Italian", "Dutch", "English"])
        self.assertEqual(len(q.items[0].target_ids), 3)  # German, French, Italian
        self.assertEqual(len(q.items[1].target_ids), 2)  # French, Dutch
        self.assertEqual(len(q.items[2].target_ids), 2)  # English, French

    def test_drag_and_drop_inference(self):
        text = """## Drag items to categories.
| Item | Drag |
|---|---|
| dog | noun |
| cat | noun |
| run | verb |
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        from src.model import AssociationQuestion
        self.assertIsInstance(q, AssociationQuestion)
        self.assertEqual(q.interaction, "drag")
        self.assertFalse(q.multiple)

    def test_drag_and_drop_header_variants(self):
        text = """## Drag items.
| Item | Drag & Drop |
|---|---|
| dog | noun |
| run | verb |
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        q = quiz.questions[0]
        from src.model import AssociationQuestion
        self.assertIsInstance(q, AssociationQuestion)
        self.assertEqual(q.interaction, "drag")

    def test_association_ditto_error_on_first_row(self):
        text = """## Broken table.
| Item | Match |
|---|---|
|      | noun |
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Empty Item cell has no preceding value to repeat." in d.message for d in diags))

    def test_association_duplicate_error(self):
        text = """## Duplicate associations.
| Item | Match |
|---|---|
| dog | noun |
| dog | noun |
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Duplicate association: 'dog' → 'noun'." in d.message for d in diags))

    def test_association_conflict_with_choices_error(self):
        text = """## Conflict.
| Item | Match |
|---|---|
| dog | noun |
- [X] Some choice
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("Cannot combine association table with choice markers" in d.message for d in diags))

    def test_normal_table_not_association(self):
        text = """## Normal Table Question
Here is reference info:
| Property | Value |
|---|---|
| Color | Blue |
| Size | Large |

Explain what this property table describes.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        from src.model import EssayQuestion
        self.assertIsInstance(quiz.questions[0], EssayQuestion)


if __name__ == "__main__":
    unittest.main()



