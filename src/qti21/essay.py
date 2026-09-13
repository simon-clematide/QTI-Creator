from typing import Dict, Optional
from src.markdown import markdown_to_qti_xhtml
from src.model import EssayQuestion
from src.qti21.item import wrap_assessment_item


def generate_essay_xml(q: EssayQuestion, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Generate QTI 2.1 XML for an Essay / Free Text question."""
    response_decl = """  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="string"/>"""

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map)
    item_body = f"""    {prompt_xhtml}
    <extendedTextInteraction responseIdentifier="RESPONSE" expectedLength="500"/>"""

    response_proc = """  <!-- Manual evaluation in OpenOLAT -->
  <responseProcessing/>"""

    return wrap_assessment_item(
        identifier=q.identifier,
        title=q.title,
        response_declarations=response_decl,
        item_body_content=item_body,
        response_processing=response_proc,
        feedback=q.feedback,
        max_score=q.points,
        asset_map=asset_map,
    )
