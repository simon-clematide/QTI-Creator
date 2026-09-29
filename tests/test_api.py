"""Unit tests for the programmatic QTI-Creator API endpoints."""

import os
import unittest
import zipfile

import gradio as gr

from qti_creator.api import check_quiz_api, export_qti_api, validate_jqti_api


class TestQtiCreatorApi(unittest.TestCase):

    def test_check_quiz_empty_input(self):
        res = check_quiz_api("")
        self.assertFalse(res["valid"])
        self.assertEqual(res["total_questions"], 0)
        self.assertEqual(res["diagnostics"][0]["message"], "Quiz content is empty.")

    def test_check_quiz_valid(self):
        md = """# My Quiz
## Capital of France
- [ ] Berlin
- [X] Paris
- [ ] Rome
"""
        res = check_quiz_api(md)
        self.assertTrue(res["valid"])
        self.assertEqual(res["quiz_title"], "My Quiz")
        self.assertEqual(res["total_questions"], 1)
        self.assertEqual(res["total_points"], 1.0)
        self.assertNotIn("diagnostics", res, "Success response should omit diagnostics")
        self.assertNotIn("questions", res, "Success response should omit questions")

    def test_check_quiz_gap_in_math_error(self):
        md = """## Math Question
What is $\\bar x={{24}}$?
"""
        res = check_quiz_api(md)
        self.assertFalse(res["valid"])
        self.assertTrue(any("located inside LaTeX math delimiters" in d["message"] for d in res["diagnostics"]))

    def test_validate_jqti_invalid_markdown(self):
        md = """## Broken Single Choice
- [ ] Only one choice
"""
        res = validate_jqti_api(md)
        self.assertFalse(res["valid"])
        self.assertFalse(res["package_built"])
        self.assertGreater(len(res["errors"]), 0)

    def test_validate_jqti_valid_quiz(self):
        md = """## Simple Question
What is 1+1?
- [X] 2
- [ ] 3
"""
        res = validate_jqti_api(md)
        self.assertTrue(res["valid"])
        self.assertTrue(res["package_built"])
        if res["jqti_available"]:
            self.assertTrue(res["jqti_valid"])
            self.assertEqual(res["errors"], [])

    def test_export_qti_valid(self):
        md = """## Export Test
What color is the sky?
- [X] Blue
- [ ] Green
"""
        zip_path = export_qti_api(md)
        self.assertIsNotNone(zip_path)
        self.assertTrue(os.path.exists(zip_path))
        self.assertTrue(zipfile.is_zipfile(zip_path))

        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("imsmanifest.xml", namelist)
            self.assertIn("Test.xml", namelist)
            self.assertIn("QTI21PackageConfig.xml", namelist)

        if os.path.exists(zip_path):
            os.remove(zip_path)

    def test_export_qti_invalid_raises_error(self):
        md = """## Broken Question
- [ ] No correct answer marked
- [ ] Still no correct answer
"""
        with self.assertRaises(gr.Error):
            export_qti_api(md)


if __name__ == "__main__":
    unittest.main()
