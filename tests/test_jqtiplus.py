"""Unit tests running against OpenOLAT's native Java QTI 2.1 engine (JQTI+)."""

import io
import unittest
from pathlib import Path

from src.jqti_validator import (
    is_java_available,
    is_javac_available,
    validate_qti_xml_string,
    validate_with_jqti,
)
from src.model import Choice, MultipleChoiceQuestion, SingleChoiceQuestion
from src.packager import create_qti_package
from src.parser import parse_quizmd
from src.qti21 import generate_item_xml

JAVA_PRESENT = is_java_available() and is_javac_available()


@unittest.skipUnless(JAVA_PRESENT, "Java and javac are required for JQTI+ runtime tests")
class TestJqtiPlusRuntimeValidation(unittest.TestCase):

    def test_single_choice_validates_in_jqti(self):
        q = SingleChoiceQuestion(
            prompt="What is the capital of Switzerland?",
            choices=[Choice("Bern", True), Choice("Zurich", False)],
            hint="Federal city.",
        )
        xml_str = generate_item_xml(q)
        is_valid, errors = validate_qti_xml_string(xml_str, "item_single_choice.xml")
        self.assertTrue(is_valid, f"Single choice failed JQTI+ validation: {errors}")
        self.assertEqual(len(errors), 0)

    def test_multiple_choice_partial_scoring_with_hint_validates_in_jqti(self):
        """Regression test for the OpenOLAT runtime crash."""
        q = MultipleChoiceQuestion(
            prompt="Select official languages:",
            choices=[
                Choice("German", True),
                Choice("French", True),
                Choice("English", False),
            ],
            scoring="partial",
            hint="National languages.",
        )
        xml_str = generate_item_xml(q)
        is_valid, errors = validate_qti_xml_string(xml_str, "item_mc_partial.xml")
        self.assertTrue(is_valid, f"Multiple choice partial scoring failed JQTI+ validation: {errors}")
        self.assertEqual(len(errors), 0)

    def test_crashed_item_is_caught_by_jqti_validation(self):
        """Verify that JQTI+ flags mapResponse on an unmapped declaration as an error."""
        broken_xml = """<?xml version="1.0" encoding="UTF-8"?>
<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"
                identifier="item_broken" title="Broken"
                adaptive="false" timeDependent="false">
  <responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="identifier">
    <correctResponse>
      <value>choice_1</value>
    </correctResponse>
    <!-- Notice: NO <mapping> defined here! -->
  </responseDeclaration>
  <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float"/>
  <itemBody>
    <p>Broken question</p>
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="false" maxChoices="0">
      <simpleChoice identifier="choice_1"><p>Option 1</p></simpleChoice>
    </choiceInteraction>
  </itemBody>
  <responseProcessing>
    <responseCondition>
      <responseIf>
        <not><isNull><variable identifier="RESPONSE"/></isNull></not>
        <setOutcomeValue identifier="SCORE">
          <mapResponse identifier="RESPONSE"/>
        </setOutcomeValue>
      </responseIf>
    </responseCondition>
  </responseProcessing>
</assessmentItem>"""
        is_valid, errors = validate_qti_xml_string(broken_xml, "item_broken.xml")
        self.assertFalse(is_valid)
        self.assertTrue(
            any("Cannot find mapping for response declaration" in e for e in errors),
            f"Expected 'Cannot find mapping' error, got: {errors}",
        )

    def test_all_sample_quizzes_pass_jqti_validation(self):
        """Validate all generated sample zip packages against OpenOLAT JQTI+."""
        sample_dir = Path(__file__).resolve().parent.parent / "sample_quizzes"
        zips = sorted(sample_dir.glob("*_qti21.zip"))
        if not zips:
            self.skipTest("No sample quiz packages found in sample_quizzes/")

        is_valid, errors = validate_with_jqti(zips)
        self.assertTrue(is_valid, f"Sample quizzes failed JQTI+ validation: {errors}")
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
