"""QTI 2.1 generator for <assessmentTest> XML matching OpenOLAT native structure."""

import html
from src.model import Quiz


def generate_test_xml(quiz: Quiz) -> str:
    """Generate OpenOLAT-native QTI 2.1 Test.xml (<assessmentTest>)."""
    escaped_title = html.escape(quiz.title)
    total_max_score = sum(q.points for q in quiz.questions)

    item_refs = []
    for q in quiz.questions:
        item_refs.append(
            f'        <assessmentItemRef identifier="{q.identifier}" href="{q.identifier}.xml"/>'
        )

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
    <assessmentSection identifier="section_1" title="{escaped_title}" visible="true" fixed="true">
      <itemSessionControl/>
{chr(10).join(item_refs)}
    </assessmentSection>
  </testPart>
  <outcomeProcessing>
    <setOutcomeValue identifier="SCORE">
      <sum>
        <testVariables variableIdentifier="SCORE"/>
      </sum>
    </setOutcomeValue>
  </outcomeProcessing>
</assessmentTest>"""

