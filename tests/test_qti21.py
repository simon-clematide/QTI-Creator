"""Tests for QTI 2.1 generator, XML validity, and ZIP packaging."""

import io
import unittest
import xml.etree.ElementTree as ET
import zipfile

from src.model import (
    Choice,
    EssayQuestion,
    FillBlankQuestion,
    Gap,
    KprimQuestion,
    KprimStatement,
    MultipleChoiceQuestion,
    NumericalQuestion,
    Quiz,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)
from src.packager import create_qti_package, create_qti_package_bytes
from src.parser import parse_quizmd
from src.qti21 import generate_item_xml
from src.qti21.manifest import generate_manifest_xml
from src.qti21.test import generate_test_xml


class TestQTI21Generator(unittest.TestCase):

    def test_single_choice_xml_validity(self):
        q = SingleChoiceQuestion(
            prompt="What is the capital of Switzerland?",
            choices=[
                Choice("Zurich", False),
                Choice("Bern", True),
                Choice("Geneva", False),
            ],
            points=2.0,
            feedback="Bern is the federal city.",
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("assessmentItem", root.tag)
        self.assertIn("Bern", xml_str)
        self.assertIn("Bern is the federal city.", xml_str)

    def test_code_snippets_in_qti_xml(self):
        text = '''## Function Output
What does this function return?
```python
def square(n):
    return n * n
```
- [o] `16`
- [ ] `8`
'''
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        q = quiz.questions[0]
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIsNotNone(root)
        self.assertIn("<pre><code>def square(n):", xml_str)
        self.assertIn("<code>16</code>", xml_str)


    def test_multiple_choice_xml_validity(self):
        q = MultipleChoiceQuestion(
            prompt="Select official languages of Switzerland:",
            choices=[
                Choice("German", True),
                Choice("French", True),
                Choice("Italian", True),
                Choice("English", False),
            ],
            points=3.0,
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("assessmentItem", root.tag)
        self.assertIn("maxChoices=\"0\"", xml_str)

    def test_true_false_xml_validity(self):
        q = TrueFalseQuestion(
            prompt="Zurich is the capital of Switzerland.",
            choices=[
                Choice("True", False),
                Choice("False", True),
            ],
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("assessmentItem", root.tag)

    def test_essay_xml_validity(self):
        q = EssayQuestion(
            prompt="Explain the Swiss political system of direct democracy.",
            points=5.0,
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("extendedTextInteraction", xml_str)

    def test_fill_blank_xml_validity(self):
        q = FillBlankQuestion(
            prompt="The largest city in *Switzerland* is {{Zurich}}.",
            gaps=[Gap("Zurich")],
        )
        xml_str = generate_item_xml(q)
        self.assertNotIn("&lt;textEntryInteraction", xml_str)
        self.assertIn("<textEntryInteraction", xml_str)
        root = ET.fromstring(xml_str)
        self.assertIn("Zurich", xml_str)
        # Verify textEntryInteraction is a true XML element in the namespace
        elem = root.find(".//{http://www.imsglobal.org/xsd/imsqti_v2p1}textEntryInteraction")
        self.assertIsNotNone(elem, "textEntryInteraction must exist as an XML element, not escaped text")
        self.assertEqual(elem.attrib.get("responseIdentifier"), "RESPONSE_0")


    def test_numerical_xml_validity(self):
        q = NumericalQuestion(
            prompt="How many cantons are there in Switzerland?",
            answer=26.0,
            tolerance=0.0,
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("26", xml_str)

    def test_kprim_xml_validity(self):
        q = KprimQuestion(
            prompt="Facts about Swiss geography:",
            statements=[
                KprimStatement("Matterhorn is located in Valais", True),
                KprimStatement("Rhine falls are the largest plain waterfall in Europe", True),
                KprimStatement("Switzerland borders the Atlantic Ocean", False),
                KprimStatement("Lake Geneva is completely in France", False),
            ],
            points=2.0,
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("matchInteraction", xml_str)
        self.assertIn("simpleAssociableChoice", xml_str)

    def test_manifest_and_test_xml(self):
        quiz = Quiz(title="Swiss Test")
        q = SingleChoiceQuestion(
            prompt="Capital?",
            choices=[Choice("Bern", True), Choice("Zurich", False)],
        )
        quiz.questions.append(q)

        manifest_xml = generate_manifest_xml(quiz)
        m_root = ET.fromstring(manifest_xml)
        self.assertIn("manifest", m_root.tag)

        test_xml = generate_test_xml(quiz)
        t_root = ET.fromstring(test_xml)
        self.assertIn("assessmentTest", t_root.tag)

    def test_zip_packaging_structure(self):
        """Verify ZIP archive has imsmanifest.xml at the root level."""
        text = """# Comprehensive Test
## What is 2 + 2?
- [ ] 3
- [x] 4
- [ ] 5

## Is Earth round?
- [x] True
- [ ] False
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)

        zip_bytes = create_qti_package_bytes(quiz)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            namelist = zf.namelist()
            # CRITICAL CHECK FOR OPENOLAT:
            self.assertIn("imsmanifest.xml", namelist)
            self.assertIn("Test.xml", namelist)
            self.assertIn("QTI21PackageConfig.xml", namelist)
            self.assertTrue(any(name.endswith(".xml") and name not in ("imsmanifest.xml", "Test.xml", "QTI21PackageConfig.xml") for name in namelist))
            # Verify no nested root folder prefix
            for name in namelist:
                self.assertFalse(name.startswith("/") or name.startswith("quiz/"))


if __name__ == "__main__":
    unittest.main()
