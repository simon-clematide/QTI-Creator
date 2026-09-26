"""QTI 2.1 generator for Numerical questions."""

from typing import Dict, Optional

from src.markdown import markdown_to_qti_xhtml
from src.model import NumericalQuestion
from src.qti21.item import wrap_assessment_item



def generate_numerical_xml(q: NumericalQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate QTI 2.1 XML for a Numerical question."""
    lower_bound = q.answer - q.tolerance
    upper_bound = q.answer + q.tolerance

    response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="float">
    <correctResponse>
      <value>{q.answer}</value>
    </correctResponse>
    <mapping defaultValue="0.0">
      <mapEntry mapKey="{q.answer}" mappedValue="{q.points}"/>
    </mapping>
  </responseDeclaration>"""

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)
    item_body = f"""    {prompt_xhtml}
    <p>
      <textEntryInteraction responseIdentifier="RESPONSE" expectedLength="10"/>
    </p>"""

    if q.tolerance == 0.0:
        response_proc = """  <responseProcessing template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response"/>"""
    else:
        response_proc = f"""  <responseProcessing>
    <responseCondition>
      <responseIf>
        <and>
          <gte>
            <variable identifier="RESPONSE"/>
            <baseValue baseType="float">{lower_bound}</baseValue>
          </gte>
          <lte>
            <variable identifier="RESPONSE"/>
            <baseValue baseType="float">{upper_bound}</baseValue>
          </lte>
        </and>
        <setOutcomeValue identifier="SCORE">
          <baseValue baseType="float">{q.points}</baseValue>
        </setOutcomeValue>
      </responseIf>
      <responseElse>
        <setOutcomeValue identifier="SCORE">
          <baseValue baseType="float">0.0</baseValue>
        </setOutcomeValue>
      </responseElse>
    </responseCondition>
  </responseProcessing>"""

    return wrap_assessment_item(
        identifier=q.identifier,
        title=q.title,
        response_declarations=response_decl,
        item_body_content=item_body,
        response_processing=response_proc,
        feedback=q.feedback,
        hint=q.hint,
        feedback_title=q.feedback_title,
        hint_title=q.hint_title,
        max_score=q.points,
        asset_map=asset_map,
    )
