"""QTI 2.1 generator for Association questions (Match and Drag & Drop)."""

import html
from typing import Dict, Optional

from src.defaults import DEFAULTS
from src.markdown import markdown_to_qti_xhtml
from src.model import AssociationQuestion
from src.qti21.item import wrap_assessment_item


def generate_association_xml(q: AssociationQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate QTI 2.1 XML for an Association question (Match or Drag & Drop).

    Supports:
    - Single choice (each item has 1 target) vs Multiple choice (any item has >=2 targets).
    - Shuffling (items shuffled by default, targets fixed).
    - Partial scoring (OpenOLAT NPS accumulator rules) vs all-correct scoring.
    - Match matrix (class="match_matrix") vs Drag & drop (class="match_dnd").
    """
    scoring_mode = (q.scoring or DEFAULTS["mc_scoring"]).strip().lower()

    # Collect correct pairs
    correct_pairs = []
    for item in q.items:
        for tid in item.target_ids:
            correct_pairs.append((item.identifier, tid))

    n_correct = len(correct_pairs)
    n_sources = len(q.items)
    n_targets = len(q.targets)

    # In OpenOLAT MatchAssessmentItemBuilder:
    # If single choice (not multiple choice):
    #   total incorrect capacity = number of source items
    # If multiple choice:
    #   total incorrect capacity = (n_sources * n_targets) - n_correct
    if q.multiple:
        n_incorrect = (n_sources * n_targets) - n_correct
    else:
        n_incorrect = n_sources

    correct_values_xml = "\n".join(
        f"      <value>{src_id} {tgt_id}</value>" for src_id, tgt_id in correct_pairs
    )

    # Build simpleMatchSet 1: Source items
    source_choices_xml = []
    source_match_max = 0 if q.multiple else 1
    for item in q.items:
        item_xhtml = markdown_to_qti_xhtml(item.text, asset_map=asset_map)
        source_choices_xml.append(
            f'        <simpleAssociableChoice identifier="{item.identifier}" matchMax="{source_match_max}" matchMin="0">{item_xhtml}</simpleAssociableChoice>'
        )

    # Build simpleMatchSet 2: Target categories
    target_choices_xml = []
    for target in q.targets:
        target_xhtml = markdown_to_qti_xhtml(target.text, asset_map=asset_map)
        target_choices_xml.append(
            f'        <simpleAssociableChoice identifier="{target.identifier}" fixed="true" matchMax="0" matchMin="0">{target_xhtml}</simpleAssociableChoice>'
        )

    # Interaction tag attributes
    interaction_class = "match_dnd" if q.interaction == "drag" else "match_matrix"
    shuffle_bool = q.shuffle if q.shuffle is not None else DEFAULTS["shuffle"]
    shuffle_str = "true" if shuffle_bool else "false"
    max_associations = 0 if q.multiple else n_sources

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)
    item_body = f"""    {prompt_xhtml}
    <matchInteraction class="{interaction_class}" responseIdentifier="RESPONSE" shuffle="{shuffle_str}" maxAssociations="{max_associations}">
      <simpleMatchSet>
{chr(10).join(source_choices_xml)}
      </simpleMatchSet>
      <simpleMatchSet>
{chr(10).join(target_choices_xml)}
      </simpleMatchSet>
    </matchInteraction>"""

    if scoring_mode in ("all-correct", "all_correct", "allcorrect"):
        # All-or-nothing scoring
        response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="directedPair">
    <correctResponse>
{correct_values_xml}
    </correctResponse>
  </responseDeclaration>"""

        response_proc = f"""  <responseProcessing>
    <responseCondition>
      <responseIf>
        <match>
          <variable identifier="RESPONSE"/>
          <correct identifier="RESPONSE"/>
        </match>
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
            min_score=0.0,
            asset_map=asset_map,
        )

    else:
        # Partial scoring (OpenOLAT native NPS negative point system):
        # Accumulate NPS_NUMCORRECT and NPS_NUMINCORRECT across Cartesian product of sources and targets.
        response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="directedPair">
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

        correct_pair_set = set(correct_pairs)
        condition_blocks = []

        for item in q.items:
            for target in q.targets:
                pair = (item.identifier, target.identifier)
                target_var = "NPS_NUMCORRECT" if pair in correct_pair_set else "NPS_NUMINCORRECT"
                condition_blocks.append(f"""    <responseCondition>
      <responseIf>
        <member>
          <baseValue baseType="directedPair">{pair[0]} {pair[1]}</baseValue>
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

        # Clamped formula:
        # SCORE = (NPS_NUMCORRECT * MAXSCORE / n_correct) - (NPS_NUMINCORRECT * MAXSCORE / n_incorrect)
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
