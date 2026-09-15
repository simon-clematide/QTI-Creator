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
        self.assertIn("⚠️ Markdown syntax in title", html_out)
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
        self.assertIn("⚠️ Markdown syntax in title", html_out)
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


if __name__ == "__main__":
    unittest.main()


