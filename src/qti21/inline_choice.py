"""QTI 2.1 generator for Inline Choice (Dropdown) questions."""

import html
from typing import Dict, Optional

from src.markdown import RE_DROPDOWN_GAP, markdown_to_qti_xhtml
from src.model import InlineChoiceQuestion
from src.qti21.item import wrap_assessment_item


def generate_inline_choice_xml(q: InlineChoiceQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate QTI 2.1 XML for an Inline Choice / Dropdown question."""
    pts_per_gap = q.points / len(q.gaps) if q.gaps else q.points

    response_decls = []
    map_responses = []

    for idx, gap in enumerate(q.gaps):
        resp_id = f"RESPONSE_{idx}"
        correct_choice = next((c for c in gap.choices if c.is_correct), gap.choices[0])

        decl = f"""  <responseDeclaration identifier="{resp_id}" cardinality="single" baseType="identifier">
    <correctResponse>
      <value>{correct_choice.identifier}</value>
    </correctResponse>
    <mapping defaultValue="0.0">
      <mapEntry mapKey="{correct_choice.identifier}" mappedValue="{pts_per_gap}"/>
    </mapping>
  </responseDeclaration>"""
        response_decls.append(decl)
        map_responses.append(f'<mapResponse identifier="{resp_id}"/>')

    # 1. Convert prompt markdown to XHTML first
    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)

    # 2. Replace {[...]} tokens in XHTML with unescaped XML <inlineChoiceInteraction>
    gap_counter = 0

    def replace_dropdown(match):
        nonlocal gap_counter
        if gap_counter >= len(q.gaps):
            return match.group(0)
        gap = q.gaps[gap_counter]
        resp_id = f"RESPONSE_{gap_counter}"
        gap_counter += 1
        shuffle_str = "true" if gap.shuffle else "false"

        choices_xml = "".join(
            f'<inlineChoice identifier="{c.identifier}">{html.escape(c.text)}</inlineChoice>'
            for c in gap.choices
        )
        return f'<inlineChoiceInteraction responseIdentifier="{resp_id}" shuffle="{shuffle_str}">{choices_xml}</inlineChoiceInteraction>'

    item_body = RE_DROPDOWN_GAP.sub(replace_dropdown, prompt_xhtml)

    response_proc = f"""  <responseProcessing>
    <setOutcomeValue identifier="SCORE">
      <sum>
        {' '.join(map_responses)}
      </sum>
    </setOutcomeValue>
  </responseProcessing>"""

    return wrap_assessment_item(
        identifier=q.identifier,
        title=q.title,
        response_declarations="\n".join(response_decls),
        item_body_content=f"    {item_body}",
        response_processing=response_proc,
        feedback=q.feedback,
        hint=q.hint,
        feedback_title=q.feedback_title,
        hint_title=q.hint_title,
        max_score=q.points,
        asset_map=asset_map,
    )
