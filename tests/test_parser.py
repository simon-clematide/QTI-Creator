"""Tests for the QuizMD parser."""

import unittest
from src.parser import parse_quizmd
from src.model import (
    SingleChoiceQuestion,
    MultipleChoiceQuestion,
    TrueFalseQuestion,
    EssayQuestion,
    FillBlankQuestion,
    NumericalQuestion,
    KprimQuestion,
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
        
        # Display math block
        disp_text = "$$\\frac{a}{b}$$"
        self.assertEqual(markdown_to_qti_xhtml(disp_text), "<p>$$\\frac{a}{b}$$</p>")

        # Inline math wrapped in <span class="math" title="...">latex</span> for OpenOLAT
        inl_text = "The solution is $x=\\frac{a}{b}$."
        self.assertEqual(
            markdown_to_qti_xhtml(inl_text),
            '<p>The solution is <span class="math" title="x%3D%5Cfrac%7Ba%7D%7Bb%7D">x=\\frac{a}{b}</span>.</p>',
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


if __name__ == "__main__":
    unittest.main()


