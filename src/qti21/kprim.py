"""QTI 2.1 generator for Kprim questions (OpenOLAT 4-statement matrix)."""

import html
from src.markdown import markdown_to_qti_xhtml
from src.model import KprimQuestion
from src.qti21.item import wrap_assessment_item


def generate_kprim_xml(q: KprimQuestion) -> str:
    """Generate QTI 2.1 XML for a Kprim question with 4/4, 3/4, <=2/4 scoring."""
    correct_values = []
    map_entries = []
    associable_choices = []

    for idx, stmt in enumerate(q.statements):
        stmt_id = f"kprim_{idx}"
        target_id = "correct" if stmt.is_correct else "wrong"
        pair_key = f"{stmt_id} {target_id}"

        correct_values.append(f"      <value>{pair_key}</value>")
        map_entries.append(f'      <mapEntry mapKey="{pair_key}" mappedValue="1.0"/>')

        stmt_xhtml = markdown_to_qti_xhtml(stmt.text)
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

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt)
    shuffle_str = "true" if q.shuffle else "false"
    item_body = f"""    {prompt_xhtml}
    <matchInteraction responseIdentifier="RESPONSE" shuffle="{shuffle_str}" maxAssociations="4">
      <simpleMatchSet>
{chr(10).join(associable_choices)}
      </simpleMatchSet>
      <simpleMatchSet>
        <simpleAssociableChoice identifier="correct" matchMax="4">+</simpleAssociableChoice>
        <simpleAssociableChoice identifier="wrong" matchMax="4">-</simpleAssociableChoice>
      </simpleMatchSet>
    </matchInteraction>"""

    half_pts = q.points * 0.5
    response_proc = f"""  <responseProcessing>
    <responseCondition>
      <responseIf>
        <gte>
          <mapResponse identifier="RESPONSE"/>
          <baseValue baseType="float">4.0</baseValue>
        </gte>
        <setOutcomeValue identifier="SCORE">
          <baseValue baseType="float">{q.points}</baseValue>
        </setOutcomeValue>
      </responseIf>
      <responseElseIf>
        <gte>
          <mapResponse identifier="RESPONSE"/>
          <baseValue baseType="float">3.0</baseValue>
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
        max_score=q.points,
    )
