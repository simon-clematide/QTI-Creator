"""QTI 2.1 generator for Single Choice, Multiple Choice, and True/False questions."""

import html
from typing import Dict, Optional

from src.defaults import DEFAULTS
from src.markdown import markdown_to_qti_xhtml
from src.model import MultipleChoiceQuestion, SingleChoiceQuestion, TrueFalseQuestion
from src.qti21.item import wrap_assessment_item


def generate_single_choice_xml(q: SingleChoiceQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:

    """Generate QTI 2.1 XML for a Single Choice question."""
    correct_choice = next(c for c in q.choices if c.is_correct)

    response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="identifier">
    <correctResponse>
      <value>{correct_choice.identifier}</value>
    </correctResponse>
    <mapping defaultValue="0.0">
      <mapEntry mapKey="{correct_choice.identifier}" mappedValue="{q.points}"/>
    </mapping>
  </responseDeclaration>"""

    choices_xml = []
    for c in q.choices:
        choice_xhtml = markdown_to_qti_xhtml(c.text, asset_map=asset_map)
        choices_xml.append(
            f'      <simpleChoice identifier="{c.identifier}">{choice_xhtml}</simpleChoice>'
        )

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)
    shuffle_bool = q.shuffle if q.shuffle is not None else DEFAULTS["shuffle"]
    shuffle_str = "true" if shuffle_bool else "false"
    item_body = f"""    {prompt_xhtml}
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="{shuffle_str}" maxChoices="1">

{chr(10).join(choices_xml)}
    </choiceInteraction>"""

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
        asset_map=asset_map,
    )


def generate_multiple_choice_xml(q: MultipleChoiceQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate QTI 2.1 XML for a Multiple Choice question with partial or all-correct scoring."""
    correct_choices = [c for c in q.choices if c.is_correct]
    incorrect_choices = [c for c in q.choices if not c.is_correct]
    n_correct = len(correct_choices)
    n_incorrect = len(incorrect_choices)

    correct_values_xml = "\n".join(
        f"      <value>{c.identifier}</value>" for c in correct_choices
    )

    choices_xml = []
    for c in q.choices:
        choice_xhtml = markdown_to_qti_xhtml(c.text, asset_map=asset_map)
        choices_xml.append(
            f'      <simpleChoice identifier="{c.identifier}">{choice_xhtml}</simpleChoice>'
        )

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)
    shuffle_bool = q.shuffle if q.shuffle is not None else DEFAULTS["shuffle"]
    shuffle_str = "true" if shuffle_bool else "false"
    item_body = f"""    {prompt_xhtml}
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="{shuffle_str}" maxChoices="0">
{chr(10).join(choices_xml)}
    </choiceInteraction>"""


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
            feedback_title=q.feedback_title,
            hint_title=q.hint_title,
            max_score=q.points,
            min_score=0.0,
            asset_map=asset_map,
        )

    elif scoring_mode in ("points-per-answer", "per-answer", "points_per_answer", "per_answer"):
        # Explicit mapping per choice
        pos_val = round(q.points / n_correct, 4) if n_correct > 0 else 0.0
        neg_val = round(-(q.points / n_incorrect), 4) if n_incorrect > 0 else 0.0

        mapping_entries_xml = []
        for c in q.choices:
            val = pos_val if c.is_correct else neg_val
            mapping_entries_xml.append(
                f'      <mapEntry mapKey="{c.identifier}" mappedValue="{val}"/>'
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
            feedback_title=q.feedback_title,
            hint_title=q.hint_title,
            max_score=q.points,
            min_score=0.0,
            asset_map=asset_map,
        )

    else:
        # OpenOLAT native "Teilpunkte" (Partial scoring):
        # OpenOLAT uses NPS_NUMCORRECT and NPS_NUMINCORRECT accumulators in responseProcessing
        # without a <mapping> element, calculating:
        # SCORE = (NPS_NUMCORRECT * MAXSCORE / n_correct) - (NPS_NUMINCORRECT * MAXSCORE / n_incorrect)
        # clamped between MINSCORE (0.0) and MAXSCORE.
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
        for c in q.choices:
            target_var = "NPS_NUMCORRECT" if c.is_correct else "NPS_NUMINCORRECT"
            condition_blocks.append(f"""    <responseCondition>
      <responseIf>
        <member>
          <baseValue baseType="identifier">{c.identifier}</baseValue>
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

        # Build subtract expression for correct vs incorrect
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


def generate_true_false_xml(q: TrueFalseQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate QTI 2.1 XML for a True/False question (represented as Single Choice in QTI 2.1)."""
    correct_choice = next(c for c in q.choices if c.is_correct)

    response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="identifier">
    <correctResponse>
      <value>{correct_choice.identifier}</value>
    </correctResponse>
    <mapping defaultValue="0.0">
      <mapEntry mapKey="{correct_choice.identifier}" mappedValue="{q.points}"/>
    </mapping>
  </responseDeclaration>"""

    choices_xml = []
    for c in q.choices:
        choice_xhtml = markdown_to_qti_xhtml(c.text, asset_map=asset_map)
        choices_xml.append(
            f'      <simpleChoice identifier="{c.identifier}">{choice_xhtml}</simpleChoice>'
        )

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)
    item_body = f"""    {prompt_xhtml}
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="false" maxChoices="1">
{chr(10).join(choices_xml)}
    </choiceInteraction>"""

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
        asset_map=asset_map,
    )
