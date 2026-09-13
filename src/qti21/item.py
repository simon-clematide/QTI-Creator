import html
from typing import Dict, Optional
from src.markdown import markdown_to_qti_xhtml


def wrap_assessment_item(
    identifier: str,
    title: str,
    response_declarations: str,
    item_body_content: str,
    response_processing: str,
    feedback: Optional[str] = None,
    hint: Optional[str] = None,
    max_score: float = 1.0,
    min_score: Optional[float] = None,
    extra_outcome_declarations: Optional[str] = None,
    asset_map: Optional[Dict[str, str]] = None,
) -> str:
    """Wrap components into a fully compliant QTI 2.1 <assessmentItem> XML document."""
    escaped_title = html.escape(title)

    hint_xml = ""
    if hint:
        hint_body = markdown_to_qti_xhtml(hint, asset_map=asset_map)
        hint_xml = f"""
    <rubricBlock view="candidate">
      {hint_body}
    </rubricBlock>"""

    feedback_xml = ""
    if feedback:
        feedback_body = markdown_to_qti_xhtml(feedback, asset_map=asset_map)
        feedback_xml = f"""
  <modalFeedback outcomeIdentifier="FEEDBACK" identifier="feedback_modal" showHide="show">
    {feedback_body}
  </modalFeedback>"""

    minscore_xml = ""
    if min_score is not None:
        minscore_xml = f"""
  <outcomeDeclaration identifier="MINSCORE" cardinality="single" baseType="float" view="testConstructor">
    <defaultValue>
      <value>{min_score}</value>
    </defaultValue>
  </outcomeDeclaration>"""

    extra_outcomes_xml = f"\n{extra_outcome_declarations}" if extra_outcome_declarations else ""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<assessmentItem xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"
                identifier="{identifier}"
                title="{escaped_title}"
                adaptive="false"
                timeDependent="false"
                toolName="OpenOLAT"
                toolVersion="8.4.0"
                xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/imsqti_v2p1.xsd">
{response_declarations}
  <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float">
    <defaultValue>
      <value>0.0</value>
    </defaultValue>
  </outcomeDeclaration>{minscore_xml}
  <outcomeDeclaration identifier="MAXSCORE" cardinality="single" baseType="float">
    <defaultValue>
      <value>{max_score}</value>
    </defaultValue>
  </outcomeDeclaration>{extra_outcomes_xml}
  <outcomeDeclaration identifier="FEEDBACK" cardinality="single" baseType="identifier"/>
  <itemBody>
{item_body_content}{hint_xml}
  </itemBody>
{response_processing}{feedback_xml}
</assessmentItem>"""
