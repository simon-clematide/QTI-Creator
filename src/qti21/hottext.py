"""QTI 2.1 generator for Hottext questions (hottextInteraction)."""

import html
import re
from typing import Dict, Optional

from src.markdown import extract_hottexts, markdown_to_qti_xhtml
from src.model import HottextQuestion
from src.qti21.item import wrap_assessment_item


def generate_hottext_xml(q: HottextQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate QTI 2.1 XML for a Hottext question."""
    correct_items = [it for it in q.items if it.is_correct]
    incorrect_items = [it for it in q.items if not it.is_correct]
    n_correct = len(correct_items)
    n_incorrect = len(incorrect_items)

    correct_values_xml = "\n".join(
        f"      <value>{it.identifier}</value>" for it in correct_items
    )

    # 1. Convert prompt markdown to XHTML first
    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)

    # 2. Extract hottexts in the prompt and replace tokens with <hottext identifier="...">content</hottext>
    # Note: we need content to be formatted inlines (bold, italic, code, etc.) without surrounding <p>
    hottext_tokens = extract_hottexts(q.prompt)
    item_map = {}
    for idx, ht in enumerate(hottext_tokens):
        if idx < len(q.items):
            item_map[ht[2]] = q.items[idx]

    # Function to replace each raw token with <hottext>...</hottext>
    def replace_hottext(match):
        raw = match.group(0)
        item = item_map.get(raw)
        if not item:
            # Fallback search if exact match doesn't hit
            for it in q.items:
                if it.text == raw:
                    item = it
                    break
        if not item:
            return raw
        # Convert inner text to QTI XHTML (preserving bold/italic/code/math, but strip wrapping <p>)
        inner_xhtml = markdown_to_qti_xhtml(item.text, asset_map=asset_map)
        if inner_xhtml.startswith("<p>") and inner_xhtml.endswith("</p>"):
            inner_xhtml = inner_xhtml[3:-4]
        return f'<hottext identifier="{item.identifier}">{inner_xhtml}</hottext>'

    # Regex matching { ... } with required whitespace
    re_ht_token = re.compile(r"\{(?:\*\*|\+|\-)?\s+[\s\S]*?\}")
    body_with_hottext = re_ht_token.sub(replace_hottext, prompt_xhtml)

    # Hottext interaction wraps the prompt body inside <hottextInteraction>
    # Note: in QTI 2.1, hottextInteraction is a block interaction. OpenOLAT wraps the content in <p> inside <hottextInteraction>
    item_body = f"""    <hottextInteraction responseIdentifier="RESPONSE" maxChoices="0">
      {body_with_hottext}
    </hottextInteraction>"""

    scoring_mode = q.scoring.lower() if q.scoring else "partial"

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
            max_score=q.points,
            min_score=0.0,
            asset_map=asset_map,
        )

    elif scoring_mode in ("points-per-answer", "per-answer", "points_per_answer", "per_answer"):
        pos_val = round(q.points / n_correct, 4) if n_correct > 0 else 0.0
        neg_val = round(-(q.points / n_incorrect), 4) if n_incorrect > 0 else 0.0

        mapping_entries_xml = []
        for it in q.items:
            val = pos_val if it.is_correct else neg_val
            mapping_entries_xml.append(
                f'      <mapEntry mapKey="{it.identifier}" mappedValue="{val}"/>'
            )

        response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="identifier">
    <correctResponse>
{correct_values_xml}
    </correctResponse>
    <mapping defaultValue="0.0" lowerBound="0.0" upperBound="{q.points}">
{chr(10).join(mapping_entries_xml)}
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
            max_score=q.points,
            min_score=0.0,
            asset_map=asset_map,
        )

    else:
        # Default: Partial credit (OpenOLAT native NPS calculation)
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
        for it in q.items:
            target_var = "NPS_NUMCORRECT" if it.is_correct else "NPS_NUMINCORRECT"
            condition_blocks.append(f"""    <responseCondition>
      <responseIf>
        <member>
          <baseValue baseType="identifier">{it.identifier}</baseValue>
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
            max_score=q.points,
            min_score=0.0,
            extra_outcome_declarations=extra_outcomes,
            asset_map=asset_map,
        )
