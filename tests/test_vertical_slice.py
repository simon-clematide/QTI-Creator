"""End-to-end vertical slice test based on Section 18 Definition of Success."""

import io
import unittest
import xml.etree.ElementTree as ET
import zipfile

from src.model import (
    EssayQuestion,
    FillBlankQuestion,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)
from src.packager import create_qti_package_bytes
from src.parser import parse_quizmd


class TestVerticalSlice(unittest.TestCase):

    def test_section_18_definition_of_success(self):
        text = """# Week 1 Quiz

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
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0, [str(d) for d in diags])
        self.assertEqual(quiz.title, "Week 1 Quiz")
        self.assertEqual(len(quiz.questions), 4)

        # Q1: Single Choice
        q1 = quiz.questions[0]
        self.assertIsInstance(q1, SingleChoiceQuestion)
        self.assertEqual(q1.points, 1.0)
        self.assertEqual(len(q1.choices), 4)
        self.assertEqual([c.text for c in q1.choices if c.is_correct], ["Germanic"])

        # Q2: True/False
        q2 = quiz.questions[1]
        self.assertIsInstance(q2, TrueFalseQuestion)
        self.assertEqual(q2.points, 1.0)
        self.assertEqual(len(q2.choices), 2)
        false_choice = [c for c in q2.choices if c.text == "False"][0]
        self.assertTrue(false_choice.is_correct)

        # Q3: Fill in the blank
        q3 = quiz.questions[2]
        self.assertIsInstance(q3, FillBlankQuestion)
        self.assertEqual(q3.points, 1.0)
        self.assertEqual(len(q3.gaps), 1)
        self.assertEqual(q3.gaps[0].expected_value, "phoneme")

        # Q4: Essay
        q4 = quiz.questions[3]
        self.assertIsInstance(q4, EssayQuestion)
        self.assertEqual(q4.points, 1.0)
        self.assertIn("minimal pair", q4.prompt)

        # Generate QTI 2.1 ZIP package
        zip_bytes = create_qti_package_bytes(quiz)
        self.assertGreater(len(zip_bytes), 500)

        # Verify ZIP contents and XML well-formedness
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            namelist = zf.namelist()
            self.assertIn("imsmanifest.xml", namelist)
            self.assertIn("Test.xml", namelist)

            # Check that every XML file in the ZIP parses cleanly
            for filename in namelist:
                content = zf.read(filename)
                tree = ET.fromstring(content)
                self.assertIsNotNone(tree)


if __name__ == "__main__":
    unittest.main()
