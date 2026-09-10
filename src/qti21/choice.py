"""QTI 2.1 generator for Single Choice, Multiple Choice, and True/False questions."""

import html
from src.markdown import markdown_to_qti_xhtml
from src.model import MultipleChoiceQuestion, SingleChoiceQuestion, TrueFalseQuestion
from src.qti21.item import wrap_assessment_item


def generate_single_choice_xml(q: SingleChoiceQuestion) -> str:
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
        choice_xhtml = markdown_to_qti_xhtml(c.text)
        choices_xml.append(
            f'      <simpleChoice identifier="{c.identifier}">{choice_xhtml}</simpleChoice>'
        )

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt)
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
        max_score=q.points,
    )


def generate_multiple_choice_xml(q: MultipleChoiceQuestion) -> str:
    """Generate QTI 2.1 XML for a Multiple Choice question."""
    correct_choices = [c for c in q.choices if c.is_correct]
    pts_per_correct = q.points / len(correct_choices) if correct_choices else q.points

    correct_values_xml = "\n".join(
        f"      <value>{c.identifier}</value>" for c in correct_choices
    )

    mapping_entries_xml = []
    for c in q.choices:
        val = pts_per_correct if c.is_correct else 0.0
        mapping_entries_xml.append(
            f'      <mapEntry mapKey="{c.identifier}" mappedValue="{val}"/>'
        )

    response_decl = f"""  <responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="identifier">
    <correctResponse>
{correct_values_xml}
    </correctResponse>
    <mapping defaultValue="0.0" lowerBound="0.0">
{chr(10).join(mapping_entries_xml)}
    </mapping>
  </responseDeclaration>"""

    choices_xml = []
    for c in q.choices:
        choice_xhtml = markdown_to_qti_xhtml(c.text)
        choices_xml.append(
            f'      <simpleChoice identifier="{c.identifier}">{choice_xhtml}</simpleChoice>'
        )

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt)
    item_body = f"""    {prompt_xhtml}
    <choiceInteraction responseIdentifier="RESPONSE" shuffle="false" maxChoices="0">
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
        max_score=q.points,
    )


def generate_true_false_xml(q: TrueFalseQuestion) -> str:
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
        choice_xhtml = markdown_to_qti_xhtml(c.text)
        choices_xml.append(
            f'      <simpleChoice identifier="{c.identifier}">{choice_xhtml}</simpleChoice>'
        )

    prompt_xhtml = markdown_to_qti_xhtml(q.prompt)
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
        max_score=q.points,
    )
