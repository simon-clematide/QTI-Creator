"""QTI 2.1 generator for Order / Sequencing questions (OpenOLAT native type 'order')."""

import html
from src.markdown import markdown_to_qti_xhtml
from src.model import OrderQuestion
from src.qti21.item import wrap_assessment_item


def generate_order_xml(q: OrderQuestion) -> str:
    """Generate QTI 2.1 XML for an Order question with orderInteraction."""
    # Correct response lists items in the target sequence defined by source order
    correct_values = "\n".join(
        f"      <value>{it.identifier}</value>" for it in q.items
    )

    response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="ordered" baseType="identifier">
    <correctResponse>
{correct_values}
    </correctResponse>
  </responseDeclaration>"""

    choices_xml = []
    for it in q.items:
        choice_xhtml = markdown_to_qti_xhtml(it.text)
        choices_xml.append(
            f'      <simpleChoice identifier="{it.identifier}">{choice_xhtml}</simpleChoice>'
        )

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt)
    # Learner-facing item order should be shuffled by default (shuffle="true") unless shuffle is explicitly False
    shuffle_str = "false" if q.shuffle is False else "true"
    item_body = f"""    {prompt_xhtml}
    <orderInteraction responseIdentifier="RESPONSE" shuffle="{shuffle_str}">
{chr(10).join(choices_xml)}
    </orderInteraction>"""

    response_proc = """  <responseProcessing template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"/>"""

    return wrap_assessment_item(
        identifier=q.identifier,
        title=q.title,
        response_declarations=response_decl,
        item_body_content=item_body,
        response_processing=response_proc,
        feedback=q.feedback,
        max_score=q.points,
    )
