"""Assessment item XML envelope builder for QTI 2.1."""

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
    feedback_title: Optional[str] = None,
    hint: Optional[str] = None,
    hint_title: Optional[str] = None,
    max_score: float = 1.0,
    min_score: Optional[float] = None,
    extra_outcome_declarations: Optional[str] = None,
    asset_map: Optional[Dict[str, str]] = None,
) -> str:
    """Wrap components into a fully compliant QTI 2.1 <assessmentItem> XML document."""
    escaped_title = html.escape(title)

    hint_interaction = ""
    hint_modal = ""
    hint_resp_decl = ""
    hint_outcome_decl = ""
    hint_cond = ""

    if hint:
        hint_body = markdown_to_qti_xhtml(hint, asset_map=asset_map)
        hint_title_attr = html.escape(hint_title, quote=True) if hint_title else ""
        hint_resp_decl = '\n  <responseDeclaration identifier="HINTREQUEST" cardinality="single" baseType="boolean"/>'
        hint_outcome_decl = '\n  <outcomeDeclaration identifier="HINTFEEDBACKMODAL" cardinality="single" baseType="identifier"/>'
        hint_interaction = f'\n    <p><endAttemptInteraction responseIdentifier="HINTREQUEST" title="{hint_title_attr}"/></p>'
        hint_modal = f"""
  <modalFeedback showHide="show" outcomeIdentifier="HINTFEEDBACKMODAL" identifier="HINT" title="{hint_title_attr}">
    {hint_body}
  </modalFeedback>"""
        hint_cond = """    <responseCondition>
      <responseIf>
        <variable identifier="HINTREQUEST"/>
        <setOutcomeValue identifier="HINTFEEDBACKMODAL">
          <baseValue baseType="identifier">HINT</baseValue>
        </setOutcomeValue>
      </responseIf>
    </responseCondition>"""

    feedback_xml = ""
    if feedback:
        feedback_body = markdown_to_qti_xhtml(feedback, asset_map=asset_map)
        feedback_title_attr = html.escape(feedback_title, quote=True) if feedback_title else ""
        feedback_xml = f"""
  <modalFeedback outcomeIdentifier="FEEDBACK" identifier="feedback_modal" showHide="show" title="{feedback_title_attr}">
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

    # Response processing handling with hints:
    # If a hint is present, responseProcessing must be an expanded element enclosing the hint condition.
    final_response_proc = response_processing
    if hint:
        rp_stripped = response_processing.strip()
        if 'template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response"' in rp_stripped and rp_stripped.endswith("/>"):
            # Expand map_response inline
            inner = f"""{hint_cond}
    <responseCondition>
      <responseIf>
        <not>
          <isNull>
            <variable identifier="RESPONSE"/>
          </isNull>
        </not>
        <setOutcomeValue identifier="SCORE">
          <mapResponse identifier="RESPONSE"/>
        </setOutcomeValue>
      </responseIf>
    </responseCondition>"""
            final_response_proc = f"  <responseProcessing>\n{inner}\n  </responseProcessing>"
        elif 'template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"' in rp_stripped and rp_stripped.endswith("/>"):
            # Expand match_correct inline
            inner = f"""{hint_cond}
    <responseCondition>
      <responseIf>
        <match>
          <variable identifier="RESPONSE"/>
          <correct identifier="RESPONSE"/>
        </match>
        <setOutcomeValue identifier="SCORE">
          <variable identifier="MAXSCORE"/>
        </setOutcomeValue>
      </responseIf>
      <responseElse>
        <setOutcomeValue identifier="SCORE">
          <baseValue baseType="float">0.0</baseValue>
        </setOutcomeValue>
      </responseElse>
    </responseCondition>"""
            final_response_proc = f"  <responseProcessing>\n{inner}\n  </responseProcessing>"
        elif rp_stripped in ("<responseProcessing/>", "<!-- Manual evaluation in OpenOLAT -->\n  <responseProcessing/>"):
            final_response_proc = f"  <responseProcessing>\n{hint_cond}\n  </responseProcessing>"
        elif "<responseProcessing" in rp_stripped and "</responseProcessing>" in rp_stripped:
            # Prepend hint condition inside existing <responseProcessing ...>
            import re
            def _inject_hint(match):
                cleaned_tag = re.sub(r'\s+template="[^"]*"', '', match.group(1))
                return f"{cleaned_tag}\n{hint_cond}"
            final_response_proc = re.sub(
                r"(<responseProcessing[^>]*>)",
                _inject_hint,
                response_processing,
                count=1,
            )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<assessmentItem xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"
                identifier="{identifier}"
                title="{escaped_title}"
                adaptive="false"
                timeDependent="false"
                toolName="OpenOLAT"
                toolVersion="8.4.1"
                xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/imsqti_v2p1.xsd">
{response_declarations}{hint_resp_decl}
  <outcomeDeclaration identifier="FEEDBACKBASIC" cardinality="single" baseType="identifier" view="testConstructor">
    <defaultValue>
      <value>none</value>
    </defaultValue>
  </outcomeDeclaration>
  <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float">
    <defaultValue>
      <value>0.0</value>
    </defaultValue>
  </outcomeDeclaration>{minscore_xml}
  <outcomeDeclaration identifier="MAXSCORE" cardinality="single" baseType="float">
    <defaultValue>
      <value>{max_score}</value>
    </defaultValue>
  </outcomeDeclaration>{extra_outcomes_xml}{hint_outcome_decl}
  <outcomeDeclaration identifier="FEEDBACK" cardinality="single" baseType="identifier"/>
  <itemBody>
{item_body_content}{hint_interaction}
  </itemBody>
{final_response_proc}{feedback_xml}{hint_modal}
</assessmentItem>"""
