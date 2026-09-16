"""QTI 2.1 generator for Kprim questions."""

import html
from typing import Dict, Optional

from src.defaults import DEFAULTS
from src.markdown import markdown_to_qti_xhtml
from src.model import KprimQuestion
from src.qti21.item import wrap_assessment_item


def generate_kprim_xml(q: KprimQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate QTI 2.1 XML for a Kprim question with 4/4, 3/4, <=2/4 scoring."""
    num_stmts = DEFAULTS["kprim_num_statements"]
    half_points_ratio = DEFAULTS["kprim_half_points"]
    full_threshold = float(num_stmts)
    half_threshold = float(num_stmts - 1)

    correct_values = []
    map_entries = []
    associable_choices = []

    for idx, stmt in enumerate(q.statements):
        stmt_id = f"kprim_{idx}"
        target_id = "correct" if stmt.is_correct else "wrong"
        pair_key = f"{stmt_id} {target_id}"

        correct_values.append(f"      <value>{pair_key}</value>")
        map_entries.append(f'      <mapEntry mapKey="{pair_key}" mappedValue="1.0"/>')

        stmt_xhtml = markdown_to_qti_xhtml(stmt.text, asset_map=asset_map)
        associable_choices.append(
            f'        <simpleAssociableChoice identifier="{stmt_id}" matchMax="1">{stmt_xhtml}</simpleAssociableChoice>'
        )

    response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="directedPair">
    <correctResponse>
{chr(10).join(correct_values)}
    </correctResponse>
    <mapping defaultValue="0.0">
{chr(10).join(map_entries)}
    </mapping>
  </responseDeclaration>"""

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)
    shuffle_bool = q.shuffle if q.shuffle is not None else DEFAULTS["shuffle"]
    shuffle_str = "true" if shuffle_bool else "false"
    item_body = f"""    {prompt_xhtml}
    <matchInteraction responseIdentifier="RESPONSE" shuffle="{shuffle_str}" maxAssociations="{num_stmts}">

      <simpleMatchSet>
{chr(10).join(associable_choices)}
      </simpleMatchSet>
      <simpleMatchSet>
        <simpleAssociableChoice identifier="correct" matchMax="{num_stmts}">+</simpleAssociableChoice>
        <simpleAssociableChoice identifier="wrong" matchMax="{num_stmts}">-</simpleAssociableChoice>
      </simpleMatchSet>
    </matchInteraction>"""

    half_pts = q.points * half_points_ratio
    response_proc = f"""  <responseProcessing>
    <responseCondition>
      <responseIf>
        <gte>
          <mapResponse identifier="RESPONSE"/>
          <baseValue baseType="float">{full_threshold}</baseValue>
        </gte>
        <setOutcomeValue identifier="SCORE">
          <baseValue baseType="float">{q.points}</baseValue>
        </setOutcomeValue>
      </responseIf>
      <responseElseIf>
        <gte>
          <mapResponse identifier="RESPONSE"/>
          <baseValue baseType="float">{half_threshold}</baseValue>
        </gte>
        <setOutcomeValue identifier="SCORE">
          <baseValue baseType="float">{half_pts}</baseValue>
        </setOutcomeValue>
      </responseElseIf>
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
        max_score=q.points,
        asset_map=asset_map,
    )
