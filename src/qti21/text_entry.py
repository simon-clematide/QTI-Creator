from typing import Dict, Optional
import re
import html
from src.markdown import markdown_to_qti_xhtml
from src.model import FillBlankQuestion
from src.qti21.item import wrap_assessment_item


def generate_fill_blank_xml(q: FillBlankQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate QTI 2.1 XML for a Fill-in-the-Blank question."""
    pts_per_gap = q.points / len(q.gaps) if q.gaps else q.points

    response_decls = []
    map_responses = []

    for idx, gap in enumerate(q.gaps):
        resp_id = f"RESPONSE_{idx}"
        escaped_val = html.escape(gap.expected_value)
        
        alt_values = "\n".join(
            f"      <value>{html.escape(alt)}</value>" for alt in gap.alternatives
        )
        alt_mappings = "\n".join(
            f'      <mapEntry mapKey="{html.escape(alt)}" mappedValue="{pts_per_gap}"/>'
            for alt in gap.alternatives
        )

        decl = f"""  <responseDeclaration identifier="{resp_id}" cardinality="single" baseType="string">
    <correctResponse>
      <value>{escaped_val}</value>
{alt_values}
    </correctResponse>
    <mapping defaultValue="0.0">
      <mapEntry mapKey="{escaped_val}" mappedValue="{pts_per_gap}"/>
{alt_mappings}
    </mapping>
  </responseDeclaration>"""
        response_decls.append(decl)
        map_responses.append(f'<mapResponse identifier="{resp_id}"/>')

    # 1. Convert prompt markdown to XHTML first
    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)

    # 2. Replace {{gap}} tokens in XHTML with unescaped XML <textEntryInteraction>
    gap_counter = 0

    def replace_gap(match):
        nonlocal gap_counter
        resp_id = f"RESPONSE_{gap_counter}"
        gap_counter += 1
        return f'<textEntryInteraction responseIdentifier="{resp_id}" expectedLength="15"/>'

    item_body = re.sub(r"\{\{([^}]+)\}\}", replace_gap, prompt_xhtml)

    if len(q.gaps) == 1:
        response_proc = """  <responseProcessing template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response"/>"""
    else:
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
        max_score=q.points,
        asset_map=asset_map,
    )
