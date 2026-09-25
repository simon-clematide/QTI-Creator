"""Tests for the preview generator."""

import unittest
from src.parser import parse_quizmd
from src.preview import render_quiz_preview_html


class TestPreview(unittest.TestCase):

    def test_preview_renders_collapsible_details(self):
        text = """# Sample Quiz
## Capital of France?
- [ ] Berlin
- [X] Paris

## Prime numbers?
- [x] 2
- [x] 3
- [ ] 4
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        html_out = render_quiz_preview_html(quiz)

        # Ensure details cards are generated (collapsed by default)
        self.assertIn('<details class="quiz-question-card"', html_out)
        self.assertIn("Expand All", html_out)
        self.assertIn("1. Capital of France?", html_out)
        self.assertIn("Single Choice", html_out)
        self.assertIn("2. Prime numbers?", html_out)
        self.assertIn("Multiple Choice", html_out)
        self.assertIn("1.0 pt", html_out)
        # Ensure Markdown source button and block are present for questions
        self.assertIn('<details class="quiz-question-source-details"', html_out)
        self.assertIn("Markdown</span>", html_out)
        self.assertIn("- [X] Paris", html_out)

    def test_preview_with_asset_map(self):
        text = """## Tree Anatomy
![Oak Tree](images/tree.png)
- [X] Root
- [ ] Leaf
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        asset_map = {"images/tree.png": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="}
        html_out = render_quiz_preview_html(quiz, asset_map=asset_map)
        self.assertIn('src="data:image/png;base64,', html_out)
        self.assertIn('alt="Oak Tree"', html_out)

    def test_preview_section_markdown_title_warning(self):
        text = """# **Section 1**: *Calculus*
## Simple Question
- [X] A
- [ ] B
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("contains Markdown syntax" in d.message for d in diags))
        html_out = render_quiz_preview_html(quiz)
        self.assertIn("⚠️ Markdown/Math in title", html_out)
        self.assertIn("**Section 1**: *Calculus*", html_out)
        # Ensure it does not render formatted HTML like <strong> or <em> in section title
        self.assertNotIn("<strong>Section 1</strong>", html_out)

    def test_preview_multi_section_markdown_title_warning(self):
        text = """---
title: Test Exam
---

# `Part A`: **Math**
Instructions for Part A

## Q1
- [X] 1
- [ ] 2

# Part B
## Q2
- [X] Yes
- [ ] No
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any("contains Markdown syntax" in d.message for d in diags))
        html_out = render_quiz_preview_html(quiz)
        self.assertIn("⚠️ Markdown/Math in title", html_out)
        self.assertIn("`Part A`: **Math**", html_out)
        self.assertNotIn("<code>Part A</code>", html_out)

    def test_preview_prompt_not_repeated_when_same_as_title(self):
        text = """## Capital of France?
- [ ] Berlin
- [X] Paris

## Question with distinct prompt
This is a detailed prompt describing what needs to be answered.
- [X] Option 1
- [ ] Option 2
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        html_out = render_quiz_preview_html(quiz)

        # First question: title is "Capital of France?", prompt is identical -> prompt should not be repeated in expanded block
        # Check that "<div style='color: #334155; margin-bottom: 12px; line-height: 1.5;'>" only appears for the second question
        self.assertEqual(html_out.count("margin-bottom: 12px; line-height: 1.5;"), 1)
        self.assertIn("This is a detailed prompt describing what needs to be answered.", html_out)

    def test_preview_status_badges(self):
        text = """## Q1 Hint only
Hint: Here is a helpful hint.
- [X] A
- [ ] B

## Q2 Feedback only
Feedback: Good job if you got this right!
- [X] A
- [ ] B

## Q3 Both hint and feedback
Hint: A hint
Feedback: Some feedback
- [X] A
- [ ] B

## Q4 Neither
- [X] A
- [ ] B
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        html_out = render_quiz_preview_html(quiz)

        # In summary header:
        # Q1 has 💡 but not 💬
        self.assertIn('<span style=\'display: inline-flex; align-items: center; gap: 4px; margin-right: 6px;\'><span title="Hint available" style="cursor: help; font-size: 0.95em;">💡</span></span>', html_out)
        # Q2 has 💬 but not 💡
        self.assertIn('<span style=\'display: inline-flex; align-items: center; gap: 4px; margin-right: 6px;\'><span title="Feedback available" style="cursor: help; font-size: 0.95em;">💬</span></span>', html_out)
        # Q3 has both in order 💡 💬
        self.assertIn('<span style=\'display: inline-flex; align-items: center; gap: 4px; margin-right: 6px;\'><span title="Hint available" style="cursor: help; font-size: 0.95em;">💡</span> <span title="Feedback available" style="cursor: help; font-size: 0.95em;">💬</span></span>', html_out)
        # Verify sequence: Single Choice (type), then status badges, then points
        self.assertIn('Single Choice</span>\n      <span style=\'display: inline-flex; align-items: center; gap: 4px; margin-right: 6px;\'><span title="Hint available" style="cursor: help; font-size: 0.95em;">💡</span></span>\n      <span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 12px; font-size: 0.78em; font-weight: 600;">1.0 pt</span>', html_out)
        # Q4 has neither badge
        self.assertIn('Single Choice</span>\n      \n      <span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 12px; font-size: 0.78em; font-weight: 600;">1.0 pt</span>', html_out)

    def test_preview_section_summary_counts(self):
        text = """---
title: Test Exam
---

# Section 1
Instructions for section 1.

## Q1
Hint: Look closely
- [X] A
- [ ] B

## Q2
Feedback: Great work!
- [X] C
- [ ] D

# Section 2
## Q3
- [X] E
- [ ] F
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        html_out = render_quiz_preview_html(quiz)

        # Section 1 has 2 Qs, 1 Hint, 1 Feedback, 2.0 pt in sequence Qs &bull; 💡 &bull; 💬 &bull; pt
        self.assertIn("2 Qs &bull; 💡 1 &bull; 💬 1 &bull; 2.0 pt", html_out)

    def test_preview_section_description_collapsible(self):
        text = """# Test Exam

# Section 1
Instructions for section 1.

## Q1
- [X] A
- [ ] B
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        html_out = render_quiz_preview_html(quiz)

        # Check that description is wrapped in collapsible details
        self.assertIn('<details class="quiz-section-desc-details" open', html_out)
        self.assertIn("Section Description / Instructions", html_out)
        self.assertIn("Instructions for section 1.", html_out)
        # Verify Expand All button toggles both cards and section descriptions
        self.assertIn(".quiz-question-card, .quiz-section-desc-details", html_out)

    def test_preview_invalid_question_display_and_validation_errors(self):
        text = """# Quiz With Error
## Broken Question
Points: 2
- [ ] Option 1
- [ ] Option 2
"""
        quiz, diags = parse_quizmd(text)
        self.assertTrue(any(d.severity.name == "ERROR" for d in diags))
        self.assertEqual(len(quiz.questions), 1)
        self.assertEqual(quiz.questions[0].title, "Broken Question")

        html_out = render_quiz_preview_html(quiz)
        # Should contain Invalid badge and validation error alert box
        self.assertIn("Invalid", html_out)
        self.assertIn("⚠️ Validation Errors:", html_out)
        self.assertIn("No correct answer is marked with [X] or [x].", html_out)
        self.assertIn("quiz-question-source-details", html_out)
        self.assertIn("<span>Markdown</span>", html_out)

    def test_preview_mathjax_toggle(self):
        text = """## Math Question
Calculate $x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$
- [X] Correct
- [ ] Incorrect
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)

        # render_math=True -> OpenOLAT-compatible <span class="math" title="...">formula</span> (no dollar signs inside)
        # MathJax scripts are NOT embedded in the preview HTML string — they live in gr.Blocks(head=...)
        html_math_on = render_quiz_preview_html(quiz, render_math=True)
        self.assertNotIn("MathJax =", html_math_on)      # script no longer in preview HTML
        self.assertNotIn("tex-chtml.js", html_math_on)   # CDN loader not in preview HTML
        self.assertIn('<span class="math"', html_math_on)
        self.assertIn('title="x%20%3D%20%5Cfrac%7B-b%20%5Cpm%20%5Csqrt%7Bb%5E2%20-%204ac%7D%7D%7B2a%7D"', html_math_on)
        self.assertIn(">x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}</span>", html_math_on)

        # render_math=False -> formula wrapped in <code>$...$</code>, never as bare delimiters
        html_math_off = render_quiz_preview_html(quiz, render_math=False)
        self.assertNotIn("MathJax =", html_math_off)
        self.assertNotIn("tex-chtml.js", html_math_off)
        self.assertIn("<code>$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$</code>", html_math_off)

    def test_invalid_question_blocks_packaging(self):
        import io
        from src.packager import create_qti_package
        from src.validation import QuizValidationError

        text = """# Quiz With Error
## Broken Question
- [ ] Option 1
- [ ] Option 2
"""
        quiz, _ = parse_quizmd(text)
        out = io.BytesIO()
        with self.assertRaises(QuizValidationError):
            create_qti_package(quiz, out)

    def test_preview_full_raw_question_title_in_card_body(self):
        text = """## Very long question title about **thermodynamics** & *fluid mechanics* that exceeds typical widths?
- [X] Yes
- [ ] No
"""
        quiz, diags = parse_quizmd(text)
        html_out = render_quiz_preview_html(quiz)

        # Title should appear in full as escaped raw text in the card body, NOT parsed as markdown (no <strong> or <em>)
        expected_raw_title = "Very long question title about **thermodynamics** &amp; *fluid mechanics* that exceeds typical widths?"
        self.assertIn(expected_raw_title, html_out)
        self.assertNotIn("<strong>thermodynamics</strong>", html_out)
        self.assertNotIn("<em>fluid mechanics</em>", html_out)

        # Check that Markdown/Math warning badge is displayed for the question title
        self.assertIn("⚠️ Markdown/Math in title", html_out)

        # Verify the question title wrapper in the body
        self.assertIn("<div style='font-size: 1.05em; font-weight: 600; color: #0f172a; margin-bottom: 8px; line-height: 1.4;'>", html_out)

    def test_preview_question_math_in_title_warning(self):
        text = """## Solve for $x$: $2x + 5 = 15$
What is $x$?
- [X] 5
- [ ] 10
"""
        quiz, diags = parse_quizmd(text)
        # Should have a warning diagnostic for question title
        self.assertTrue(any("contains Markdown or math syntax" in d.message for d in diags))
        html_out = render_quiz_preview_html(quiz)

        # Title should appear in full as escaped raw text in the card body
        self.assertIn("Solve for $x$: $2x + 5 = 15$", html_out)
        # Warning badge should be present in card body
        self.assertIn("⚠️ Markdown/Math in title", html_out)
        # Warning icon badge should also be in summary status badges
        self.assertIn('title="Question title contains Markdown or math syntax"', html_out)


    def test_preview_inline_choice_dropdown(self):
        text = """## Geography Dropdown
Switzerland has its federal city in {[Bern|Zurich]}, and Germany in {[Munich|**Berlin**]}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        html_out = render_quiz_preview_html(quiz)

        self.assertIn("Inline Choice", html_out)
        self.assertIn("<select disabled", html_out)
        self.assertIn("-- Select --", html_out)
        self.assertIn("Bern ✓", html_out)
        self.assertIn("Berlin ✓", html_out)
        self.assertIn("Dropdown 1 <em>[shuffled]</em>:", html_out)
        self.assertIn("Bern (Correct)", html_out)

    def test_preview_hottext(self):
        text = """## Parts of Speech
The {** cat **} { sat } on the {** mat **}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        html_out = render_quiz_preview_html(quiz)

        self.assertIn("Hottext", html_out)
        self.assertIn("Selectable hottext (Correct)", html_out)
        self.assertIn("Selectable hottext (Incorrect)", html_out)
        self.assertIn("Selectable Hottext Spans", html_out)
        self.assertIn("cat (Correct)", html_out)
        self.assertIn("sat", html_out)
        # Ensure HTML tags are not double-escaped as literal &lt;span
        self.assertNotIn("&lt;span", html_out)


    def test_preview_match(self):
        text = """## Parts of Speech Matrix
| Item | Match |
|---|---|
| dog | noun |
| run | verb |
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        html_out = render_quiz_preview_html(quiz)
        self.assertIn("Match", html_out)
        self.assertIn("Matrix (Single Choice)", html_out)
        self.assertIn("dog", html_out)
        self.assertIn("noun", html_out)
        self.assertIn("verb", html_out)

    def test_preview_drag_and_drop(self):
        text = """## Drag to Groups
| Item | Drag |
|---|---|
| dog | noun |
| cat | noun |
| run | verb |
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        html_out = render_quiz_preview_html(quiz)
        self.assertIn("Drag & Drop", html_out)
        self.assertIn("Drag & Drop Categories (Single Choice)", html_out)
        self.assertIn("📂 noun:", html_out)
        self.assertIn("📂 verb:", html_out)
        self.assertIn("dog", html_out)
        self.assertIn("cat", html_out)
        self.assertIn("run", html_out)


if __name__ == "__main__":
    unittest.main()



