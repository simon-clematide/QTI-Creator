"""QTI 2.1 generator for <assessmentTest> XML matching OpenOLAT native structure."""

import html
from typing import Dict, Optional
from src.markdown import markdown_to_qti_xhtml
from src.model import Quiz


def generate_test_xml(quiz: Quiz, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate OpenOLAT-native QTI 2.1 Test.xml (<assessmentTest>) supporting multiple sections."""
    escaped_title = html.escape(quiz.title)
    total_max_score = sum(q.points for q in quiz.questions)

    sections_xml = []
    for s_idx, sec in enumerate(quiz.sections, start=1):
        escaped_sec_title = html.escape(sec.title)
        item_refs = []
        for q in sec.questions:
            item_refs.append(
                f'        <assessmentItemRef identifier="{q.identifier}" href="{q.identifier}.xml"/>'
            )

        rubric_xml = ""
        if sec.description and sec.description.strip():
            desc_html = markdown_to_qti_xhtml(sec.description, asset_map=asset_map)
            rubric_xml = f"""      <rubricBlock view="candidate">
        {desc_html}
      </rubricBlock>
"""

        items_joined = ("\n" + "\n".join(item_refs)) if item_refs else ""
        sec_xml = f"""    <assessmentSection identifier="{sec.identifier}" title="{escaped_sec_title}" visible="true" fixed="true">
      <itemSessionControl/>
{rubric_xml}{items_joined}
    </assessmentSection>"""
        sections_xml.append(sec_xml)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<assessmentTest xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"
                identifier="{quiz.identifier}"
                title="{escaped_title}"
                toolName="OpenOLAT"
                toolVersion="8.4.0">
  <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float"/>
  <outcomeDeclaration identifier="MAXSCORE" cardinality="single" baseType="float">
    <defaultValue>
      <value>{total_max_score}</value>
    </defaultValue>
  </outcomeDeclaration>
  <outcomeDeclaration identifier="MINSCORE" cardinality="single" baseType="float">
    <defaultValue>
      <value>0.0</value>
    </defaultValue>
  </outcomeDeclaration>
  <testPart identifier="testPart_1" navigationMode="nonlinear" submissionMode="individual">
    <itemSessionControl maxAttempts="0" showFeedback="false" allowReview="false" showSolution="false" allowComment="true" allowSkipping="false"/>
{chr(10).join(sections_xml)}
  </testPart>
  <outcomeProcessing>
    <setOutcomeValue identifier="SCORE">
      <sum>
        <testVariables variableIdentifier="SCORE"/>
      </sum>
    </setOutcomeValue>
  </outcomeProcessing>
</assessmentTest>"""

