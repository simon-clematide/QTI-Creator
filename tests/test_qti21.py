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
    HottextItem,
    HottextQuestion,
    InlineChoice,
    InlineChoiceGap,
    InlineChoiceQuestion,
    KprimQuestion,
    KprimStatement,

    MultipleChoiceQuestion,
    NumericalQuestion,
    OrderItem,
    OrderQuestion,
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
            hint="Think of the Swiss canton with a bear on its flag.",
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("assessmentItem", root.tag)
        self.assertIn("Bern", xml_str)
        self.assertIn("Bern is the federal city.", xml_str)
        self.assertNotIn("<rubricBlock", xml_str)
        self.assertIn('responseIdentifier="HINTREQUEST" title=""', xml_str)
        self.assertIn('outcomeIdentifier="HINTFEEDBACKMODAL" identifier="HINT" title=""', xml_str)
        self.assertIn('endAttemptInteraction', xml_str)
        self.assertIn('identifier="FEEDBACKBASIC"', xml_str)
        self.assertIn('toolVersion="8.4.1"', xml_str)
        self.assertIn("Think of the Swiss canton with a bear on its flag.", xml_str)

    def test_code_snippets_in_qti_xml(self):
        text = '''## Function Output
What does this function return?
```python
def square(n):
    return n * n
```
- [X] `16`
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
            scoring="partial",
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("assessmentItem", root.tag)
        self.assertIn('maxChoices="0"', xml_str)
        # Verify OpenOLAT native Teilpunkte scoring with NPS variables
        self.assertIn("NPS_NUMCORRECT", xml_str)
        self.assertIn("NPS_NUMINCORRECT", xml_str)
        self.assertIn("MINSCORE", xml_str)
        self.assertIn("<baseValue baseType=\"integer\">3</baseValue>", xml_str)
        self.assertIn("<baseValue baseType=\"integer\">1</baseValue>", xml_str)
        self.assertNotIn("template=", xml_str)
        self.assertNotIn("mapResponse", xml_str)

    def test_multiple_choice_partial_with_hint_preserves_nps_and_no_map_response(self):
        q = MultipleChoiceQuestion(
            prompt="Which problems does the long tail of word frequencies create?",
            choices=[
                Choice("Rare words have sparse statistics.", True),
                Choice("Large vocabulary.", True),
                Choice("All words same frequency.", False),
            ],
            points=2.0,
            scoring="partial",
            hint="Think about Zipf's law.",
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("HINTREQUEST", xml_str)
        self.assertIn("HINTFEEDBACKMODAL", xml_str)
        self.assertIn("NPS_NUMCORRECT", xml_str)
        self.assertIn("NPS_NUMINCORRECT", xml_str)
        # Crucial: Must NEVER contain mapResponse because responseDeclaration has no mapping
        self.assertNotIn("mapResponse", xml_str)
        self.assertNotIn("template=", xml_str)

    def test_multiple_choice_all_correct_xml_validity(self):
        q = MultipleChoiceQuestion(
            prompt="Select primes:",
            choices=[
                Choice("2", True),
                Choice("3", True),
                Choice("4", False),
            ],
            points=2.0,
            scoring="all-correct",
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("assessmentItem", root.tag)
        self.assertIn('rptemplates/match_correct', xml_str)
        self.assertNotIn('NPS_NUMCORRECT', xml_str)

    def test_multiple_choice_per_answer_xml_validity(self):
        q = MultipleChoiceQuestion(
            prompt="Select primes:",
            choices=[
                Choice("2", True),
                Choice("3", True),
                Choice("4", False),
            ],
            points=2.0,
            scoring="per-answer",
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("assessmentItem", root.tag)
        self.assertIn('<mapping defaultValue="0.0"', xml_str)
        self.assertIn('mappedValue="1.0"', xml_str)
        self.assertIn('mappedValue="-2.0"', xml_str)

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
        self.assertIn('<mapResponse identifier="RESPONSE_0"/>', xml_str)
        self.assertNotIn("template=", xml_str)

    def test_fill_blank_escapes_xml_validity(self):
        q = FillBlankQuestion(
            prompt=r"The template is {{answer containing \}\} braces | alternative}}.",
            gaps=[Gap("answer containing }} braces", ["alternative"])],
        )
        xml_str = generate_item_xml(q)
        self.assertNotIn("&lt;textEntryInteraction", xml_str)
        self.assertIn("<textEntryInteraction", xml_str)
        root = ET.fromstring(xml_str)
        self.assertIn("answer containing }} braces", xml_str)
        self.assertIn("alternative", xml_str)


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
            shuffle=True,
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("matchInteraction", xml_str)
        self.assertIn('class="match_krpim"', xml_str)
        self.assertIn('responseIdentifier="KPRIM_RESPONSE_1"', xml_str)
        self.assertIn('shuffle="true"', xml_str)
        self.assertIn('matchMax="1" matchMin="1"', xml_str)
        self.assertIn('identifier="correct" fixed="true"', xml_str)
        self.assertIn('identifier="wrong" fixed="true"', xml_str)
        self.assertIn("simpleAssociableChoice", xml_str)

    def test_kprim_xml_with_hint_and_math(self):
        q = KprimQuestion(
            prompt="Facts about Swiss geography:",
            statements=[
                KprimStatement("Matterhorn is located in Valais", True),
                KprimStatement("Rhine falls are the largest plain waterfall in Europe", True),
                KprimStatement("Switzerland borders the Atlantic Ocean", False),
                KprimStatement("Lake Geneva is completely in France", False),
            ],
            points=2.0,
            hint="Think of $a+b$ and the mountains.",
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn('responseIdentifier="HINTREQUEST"', xml_str)
        self.assertIn('outcomeIdentifier="HINTFEEDBACKMODAL"', xml_str)
        self.assertIn('<span class="math"', xml_str)
        self.assertIn('>a+b</span>', xml_str)
        self.assertIn('<variable identifier="HINTREQUEST"/>', xml_str)
        self.assertIn('<setOutcomeValue identifier="HINTFEEDBACKMODAL">', xml_str)

    def test_order_xml_validity(self):
        q = OrderQuestion(
            prompt="Order the following steps:",
            items=[
                OrderItem("Step 1"),
                OrderItem("Step 2"),
                OrderItem("Step 3"),
            ],
            points=2.0,
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("orderInteraction", xml_str)
        self.assertIn('shuffle="true"', xml_str)
        self.assertIn("match_correct", xml_str)
        # Check correct response order
        values = [elem.text for elem in root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p1}correctResponse/{http://www.imsglobal.org/xsd/imsqti_v2p1}value")]
        self.assertEqual(values, [it.identifier for it in q.items])

    def test_order_xml_no_shuffle(self):
        q = OrderQuestion(
            prompt="Order the following steps:",
            items=[
                OrderItem("Step 1"),
                OrderItem("Step 2"),
            ],
            shuffle=False,
        )
        xml_str = generate_item_xml(q)
        self.assertIn('shuffle="false"', xml_str)

    def test_multiple_choice_per_answer_alias_xml(self):
        # Test that 'per_answer' alias generates mapping correctly
        q = MultipleChoiceQuestion(
            prompt="Select primes:",
            choices=[
                Choice("2", True),
                Choice("3", True),
                Choice("4", False),
            ],
            points=2.0,
            scoring="per_answer",
        )
        xml_str = generate_item_xml(q)
        self.assertIn('<mapping defaultValue="0.0"', xml_str)
        self.assertIn('mappedValue="1.0"', xml_str)
        self.assertIn('mappedValue="-2.0"', xml_str)


    def test_gap_alternatives_xml(self):
        q = FillBlankQuestion(
            prompt="The color is {{gray | grey}}.",
            gaps=[Gap("gray", alternatives=["grey"])],
            points=2.0,
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        # In QTI 2.1 single-cardinality, correctResponse contains the primary value
        values = [elem.text for elem in root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p1}correctResponse/{http://www.imsglobal.org/xsd/imsqti_v2p1}value")]
        self.assertEqual(values, ["gray"])
        # Verify mapping entries for both with full score
        self.assertIn('mapKey="gray" mappedValue="2.0"', xml_str)
        self.assertIn('mapKey="grey" mappedValue="2.0"', xml_str)

    def test_manifest_and_test_xml(self):
        quiz = Quiz(title="Swiss Test", version="1.3.5", language="fr", topic="Geography")
        q = SingleChoiceQuestion(
            prompt="Capital?",
            choices=[Choice("Bern", True), Choice("Zurich", False)],
            keywords=["geography", "swiss"],
            additional_info="Version: 1.3.5",
            topic="Geography",
        )
        quiz.questions.append(q)

        manifest_xml = generate_manifest_xml(quiz)
        m_root = ET.fromstring(manifest_xml)
        self.assertIn("manifest", m_root.tag)
        self.assertEqual(m_root.attrib.get("version"), "1.3.5")
        self.assertIn("<imsmd:version>", manifest_xml)
        self.assertIn('<imsmd:langstring xml:lang="fr">1.3.5</imsmd:langstring>', manifest_xml)
        self.assertIn("<ns4:topic>Geography</ns4:topic>", manifest_xml)
        self.assertIn("<ns4:additionalInformations>Version: 1.3.5</ns4:additionalInformations>", manifest_xml)
        self.assertIn('<imsmd:langstring xml:lang="fr">geography</imsmd:langstring>', manifest_xml)
        self.assertIn('<imsmd:langstring xml:lang="fr">swiss</imsmd:langstring>', manifest_xml)
        self.assertIn('<imsmd:context xsi:type="imsmd:stringType" xml:lang="fr">fr</imsmd:context>', manifest_xml)

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


    def test_multi_section_test_xml(self):
        text = """---
title: Final Exam
---
# Part A
Section instructions for candidate.

## Q1
- [X] Yes
- [ ] No

# Part B
## Q2
- [X] True
- [ ] False
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        self.assertEqual(len(quiz.sections), 2)

        test_xml = generate_test_xml(quiz)
        root = ET.fromstring(test_xml)
        self.assertIn("assessmentTest", root.tag)

        # Verify multiple assessmentSection elements
        sections = root.findall(".//{http://www.imsglobal.org/xsd/imsqti_v2p1}assessmentSection")
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].attrib.get("title"), "Part A")
        self.assertEqual(sections[1].attrib.get("title"), "Part B")

        # Verify rubricBlock in section 1
        rubric = sections[0].find(".//{http://www.imsglobal.org/xsd/imsqti_v2p1}rubricBlock")
        self.assertIsNotNone(rubric)
        self.assertIn("Section instructions for candidate.", test_xml)

    def test_inline_math_in_qti_xml_and_title_plain_text(self):
        text = """# Math Quiz
## Calculating the output of $f(x) = x^2$
Given the function $f(x) = x^2$, what is $f(3)$?
- [X] $9$
- [ ] $6$
Feedback: Since $3^2 = 9$, the answer is $9$.
Hint: Recall that $x^2 = x \\cdot x$.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 1)
        self.assertIn("contains Markdown or math syntax", diags[0].message)
        q = quiz.questions[0]

        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)

        # 1. Check title attribute contract: plain text, NEVER contains <span or HTML tags
        item_title = root.attrib.get("title", "")
        self.assertEqual(item_title, "Calculating the output of $f(x) = x^2$")
        self.assertNotIn("<span", item_title)
        self.assertNotIn("class=\"math\"", item_title)

        # 2. Check item body content contract: inline math is wrapped in <span class="math" title="...">formula</span> (no dollar signs)
        self.assertIn('<span class="math" title="f%28x%29%20%3D%20x%5E2">f(x) = x^2</span>', xml_str)
        self.assertIn('<span class="math" title="f%283%29">f(3)</span>', xml_str)
        self.assertIn('<span class="math" title="9">9</span>', xml_str)
        self.assertIn('<span class="math" title="3%5E2%20%3D%209">3^2 = 9</span>', xml_str)
        self.assertIn('<span class="math" title="x%5E2%20%3D%20x%20%5Ccdot%20x">x^2 = x \\cdot x</span>', xml_str)

        # 3. Check section title in Test.xml contract: plain text
        test_xml = generate_test_xml(quiz)
        test_root = ET.fromstring(test_xml)
        sec = test_root.find(".//{http://www.imsglobal.org/xsd/imsqti_v2p1}assessmentSection")
        self.assertIsNotNone(sec)
        self.assertNotIn("<span", sec.attrib.get("title", ""))


    def test_inline_choice_xml_validity(self):
        q = InlineChoiceQuestion(
            prompt="Switzerland has its capital in {[Bern|Zurich|Geneva]}.",
            gaps=[
                InlineChoiceGap(
                    choices=[
                        InlineChoice("Bern", is_correct=True),
                        InlineChoice("Zurich", is_correct=False),
                        InlineChoice("Geneva", is_correct=False),
                    ],
                    shuffle=True,
                )
            ],
            points=2.0,
            feedback="Bern is the federal city.",
            hint="Bear on flag.",
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("assessmentItem", root.tag)
        self.assertIn("<inlineChoiceInteraction", xml_str)
        self.assertIn('shuffle="true"', xml_str)
        self.assertIn("<inlineChoice", xml_str)
        self.assertIn("Bern", xml_str)
        self.assertIn("Zurich", xml_str)
        self.assertIn("Geneva", xml_str)
        self.assertIn("<setOutcomeValue identifier=\"SCORE\">", xml_str)
        self.assertIn("<mapResponse", xml_str)

        # Verify manifest metadata
        quiz = Quiz(title="Inline Choice Quiz", questions=[q])
        manifest_xml = generate_manifest_xml(quiz)
        self.assertIn('qtiMetadata', manifest_xml)
        self.assertIn('inlineChoiceInteraction', manifest_xml)
        self.assertIn('questionType>inlinechoice</', manifest_xml)


    def test_inline_choice_package_generation(self):
        text = """# Capitals Quiz
## Switzerland and Germany
Switzerland: {[Bern|Zurich]}, Germany: {[Munich|**Berlin**]}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        zip_bytes = create_qti_package_bytes(quiz)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            names = zf.namelist()
            self.assertIn("imsmanifest.xml", names)
            item_files = [n for n in names if n.endswith(".xml") and "item" in n]
            self.assertEqual(len(item_files), 1)
            item_xml = zf.read(item_files[0]).decode("utf-8")
            self.assertIn("inlineChoiceInteraction", item_xml)

    def test_hottext_xml_validity(self):
        q = HottextQuestion(
            prompt="The {** cat **} { sat } on the {** mat **}.",
            items=[
                HottextItem("cat", is_correct=True),
                HottextItem("sat", is_correct=False),
                HottextItem("mat", is_correct=True),
            ],
            points=2.0,
            feedback="Cat and mat are nouns.",
            hint="Look for nouns.",
        )
        xml_str = generate_item_xml(q)
        root = ET.fromstring(xml_str)
        self.assertIn("assessmentItem", root.tag)
        self.assertIn("<hottextInteraction", xml_str)
        self.assertIn("<hottext", xml_str)
        self.assertIn("cat", xml_str)
        self.assertIn("sat", xml_str)
        self.assertIn("mat", xml_str)
        self.assertIn('identifier="NPS_NUMCORRECT"', xml_str)
        self.assertIn('identifier="NPS_NUMINCORRECT"', xml_str)

        # Verify manifest metadata
        quiz = Quiz(title="Hottext Quiz", questions=[q])
        manifest_xml = generate_manifest_xml(quiz)
        self.assertIn('qtiMetadata', manifest_xml)
        self.assertIn('hottextInteraction', manifest_xml)
        self.assertIn('questionType>hottext</', manifest_xml)

    def test_hottext_package_generation(self):
        text = """# Grammar Quiz
## Parts of Speech
The {** cat **} { sat } on the {** mat **}.
"""
        quiz, diags = parse_quizmd(text)
        self.assertEqual(len(diags), 0)
        zip_bytes = create_qti_package_bytes(quiz)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            names = zf.namelist()
            self.assertIn("imsmanifest.xml", names)
            item_files = [n for n in names if n.endswith(".xml") and "item" in n]
            self.assertEqual(len(item_files), 1)
            item_xml = zf.read(item_files[0]).decode("utf-8")
            self.assertIn("hottextInteraction", item_xml)


if __name__ == "__main__":
    unittest.main()

