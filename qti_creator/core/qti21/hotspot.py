"""QTI 2.1 generator for Hotspot Image questions (hotspotInteraction)."""

import html
from typing import Dict, Optional, Sequence

from qti_creator.core.defaults import DEFAULTS
from qti_creator.core.markdown import markdown_to_qti_xhtml
from qti_creator.core.media import ResolvedHotspotImage, ResolvedHotspotRegion
from qti_creator.core.model import HotspotQuestion
from qti_creator.core.qti21.item import wrap_assessment_item


def generate_hotspot_xml(
    q: HotspotQuestion,
    resolved_image: ResolvedHotspotImage,
    resolved_regions: Sequence[ResolvedHotspotRegion],
    asset_map: Optional[Dict[str, str]] = None,
) -> str:
    """Generate OpenOLAT-compatible QTI 2.1 XML for a HotspotQuestion."""
    escaped_data = html.escape(resolved_image.package_path, quote=True)
    escaped_mime = html.escape(resolved_image.mime_type, quote=True)
    width_str = str(resolved_image.width)
    height_str = str(resolved_image.height)

    choices_xml = []
    for reg in resolved_regions:
        coords_str = ",".join(str(c) for c in reg.pixel_coords)
        choices_xml.append(
            f'      <hotspotChoice identifier="{reg.identifier}" shape="{reg.shape}" coords="{coords_str}" fixed="false"/>'
        )

    max_choices = "0" if q.multiple else "1"
    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)
    item_body = f"""    {prompt_xhtml}
    <hotspotInteraction responseIdentifier="RESPONSE" maxChoices="{max_choices}" class="interaction-responsive">
      <object data="{escaped_data}" type="{escaped_mime}" width="{width_str}" height="{height_str}"/>
{chr(10).join(choices_xml)}
    </hotspotInteraction>"""

    scoring_mode = (q.scoring or DEFAULTS["mc_scoring"]).strip().lower()

    if not q.multiple:
        correct_reg = next(r for r in resolved_regions if r.correct)
        if scoring_mode in ("all-correct", "all_correct", "allcorrect"):
            response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="identifier">
    <correctResponse>
      <value>{correct_reg.identifier}</value>
    </correctResponse>
  </responseDeclaration>"""
            response_proc = """  <responseProcessing template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"/>"""
        else:
            response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="identifier">
    <correctResponse>
      <value>{correct_reg.identifier}</value>
    </correctResponse>
    <mapping defaultValue="0.0">
      <mapEntry mapKey="{correct_reg.identifier}" mappedValue="{q.points}"/>
    </mapping>
  </responseDeclaration>"""
            response_proc = """  <responseProcessing template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response"/>"""

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
            min_score=0.0,
            asset_map=asset_map,
        )

    # Multiple-choice hotspot (q.multiple == True)
    correct_regs = [r for r in resolved_regions if r.correct]
    incorrect_regs = [r for r in resolved_regions if not r.correct]
    n_correct = len(correct_regs)
    n_incorrect = len(incorrect_regs)

    correct_values_xml = "\n".join(
        f"      <value>{r.identifier}</value>" for r in correct_regs
    )

    if scoring_mode in ("all-correct", "all_correct", "allcorrect"):
        response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="identifier">
    <correctResponse>
{correct_values_xml}
    </correctResponse>
  </responseDeclaration>"""
        response_proc = """  <responseProcessing template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"/>"""
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
            min_score=0.0,
            asset_map=asset_map,
        )

    # Default 'partial': OpenOLAT native NPS (NPS_NUMCORRECT / NPS_NUMINCORRECT)
    response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="identifier">
    <correctResponse>
{correct_values_xml}
    </correctResponse>
  </responseDeclaration>"""

    extra_outcomes = """  <outcomeDeclaration identifier="NPS_NUMCORRECT" cardinality="single" baseType="integer" view="testConstructor">
    <defaultValue>
      <value>0</value>
    </defaultValue>
  </outcomeDeclaration>
  <outcomeDeclaration identifier="NPS_NUMINCORRECT" cardinality="single" baseType="integer" view="testConstructor">
    <defaultValue>
      <value>0</value>
    </defaultValue>
  </outcomeDeclaration>"""

    condition_blocks = []
    for r in resolved_regions:
        target_var = "NPS_NUMCORRECT" if r.correct else "NPS_NUMINCORRECT"
        condition_blocks.append(f"""    <responseCondition>
      <responseIf>
        <member>
          <baseValue baseType="identifier">{r.identifier}</baseValue>
          <variable identifier="RESPONSE"/>
        </member>
        <setOutcomeValue identifier="{target_var}">
          <sum>
            <variable identifier="{target_var}"/>
            <baseValue baseType="integer">1</baseValue>
          </sum>
        </setOutcomeValue>
      </responseIf>
    </responseCondition>""")

    conditions_xml = "\n".join(condition_blocks)

    correct_term = f"""<divide>
        <product>
          <integerToFloat>
            <variable identifier="NPS_NUMCORRECT"/>
          </integerToFloat>
          <variable identifier="MAXSCORE"/>
        </product>
        <baseValue baseType="integer">{n_correct}</baseValue>
      </divide>"""

    if n_incorrect > 0:
        incorrect_term = f"""<divide>
        <product>
          <integerToFloat>
            <variable identifier="NPS_NUMINCORRECT"/>
          </integerToFloat>
          <variable identifier="MAXSCORE"/>
        </product>
        <baseValue baseType="integer">{n_incorrect}</baseValue>
      </divide>"""
        calc_xml = f"""<subtract>
      {correct_term}
      {incorrect_term}
    </subtract>"""
    else:
        calc_xml = correct_term

    response_proc = f"""  <responseProcessing>
{conditions_xml}
    <setOutcomeValue identifier="SCORE">
      {calc_xml}
    </setOutcomeValue>
    <responseCondition>
      <responseIf>
        <lt>
          <variable identifier="SCORE"/>
          <variable identifier="MINSCORE"/>
        </lt>
        <setOutcomeValue identifier="SCORE">
          <variable identifier="MINSCORE"/>
        </setOutcomeValue>
      </responseIf>
    </responseCondition>
    <responseCondition>
      <responseIf>
        <gt>
          <variable identifier="SCORE"/>
          <variable identifier="MAXSCORE"/>
        </gt>
        <setOutcomeValue identifier="SCORE">
          <variable identifier="MAXSCORE"/>
        </setOutcomeValue>
      </responseIf>
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
        min_score=0.0,
        extra_outcome_declarations=extra_outcomes,
        asset_map=asset_map,
    )
