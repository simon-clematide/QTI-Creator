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


if __name__ == "__main__":
    unittest.main()


