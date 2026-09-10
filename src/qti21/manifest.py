"""IMS Content Packaging generator for imsmanifest.xml (QTI 2.1).

Generates manifest with OpenOLAT-specific metadata (ns4:ooMetadata) and
IMS QTI metadata (imsqti:qtiMetadata) to guarantee native editable recognition
in OpenOLAT.
"""

from src.model import (
    EssayQuestion,
    FillBlankQuestion,
    KprimQuestion,
    MultipleChoiceQuestion,
    NumericalQuestion,
    Question,
    Quiz,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)


def _get_qti_interaction_type(q: Question) -> str:
    """Return the standard IMS QTI interaction type."""
    if isinstance(q, (SingleChoiceQuestion, MultipleChoiceQuestion, TrueFalseQuestion)):
        return "choiceInteraction"
    elif isinstance(q, KprimQuestion):
        return "matchInteraction"
    elif isinstance(q, (FillBlankQuestion, NumericalQuestion)):
        return "textEntryInteraction"
    elif isinstance(q, EssayQuestion):
        return "extendedTextInteraction"
    return "choiceInteraction"


def _get_openolat_question_type(q: Question) -> str:
    """Return OpenOLAT's native question type identifier."""
    if isinstance(q, SingleChoiceQuestion):
        return "sc"
    elif isinstance(q, MultipleChoiceQuestion):
        return "mc"
    elif isinstance(q, TrueFalseQuestion):
        return "sc"
    elif isinstance(q, KprimQuestion):
        return "kprim"
    elif isinstance(q, FillBlankQuestion):
        return "fib"
    elif isinstance(q, NumericalQuestion):
        return "numerical"
    elif isinstance(q, EssayQuestion):
        return "essay"
    return "sc"


def generate_manifest_xml(quiz: Quiz) -> str:
    """Generate the root-level imsmanifest.xml required by OpenOLAT."""
    test_res_id = f"RES_{quiz.identifier}"

    item_dependencies = []
    item_resources = []

    for q in quiz.questions:
        item_res_id = f"RES_{q.identifier}"
        item_filename = f"{q.identifier}.xml"
        interaction_type = _get_qti_interaction_type(q)
        oo_question_type = _get_openolat_question_type(q)

        item_dependencies.append(f'      <dependency identifierref="{item_res_id}"/>')
        item_resources.append(f"""    <resource identifier="{item_res_id}" type="imsqti_item_xmlv2p1" href="{item_filename}">
      <metadata>
        <imsmd:lom>
          <imsmd:technical>
            <imsmd:format>text/x-imsqti-item-xml</imsmd:format>
          </imsmd:technical>
          <imsmd:educational/>
        </imsmd:lom>
        <imsqti:qtiMetadata>
          <imsqti:interactionType>{interaction_type}</imsqti:interactionType>
        </imsqti:qtiMetadata>
        <ns4:ooMetadata>
          <ns4:questionType>{oo_question_type}</ns4:questionType>
        </ns4:ooMetadata>
      </metadata>
      <file href="{item_filename}"/>
    </resource>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
          xmlns:imsmd="http://www.imsglobal.org/xsd/imsmd_v1p2"
          xmlns:imsqti="http://www.imsglobal.org/xsd/imsqti_metadata_v2p1"
          xmlns:ns4="http://www.openolat.org/xsd/oomd_v1p1"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          identifier="MANIFEST_{quiz.identifier}"
          xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 http://www.imsglobal.org/xsd/imscp_v1p1.xsd http://www.imsglobal.org/xsd/imsmd_v1p2 http://www.imsglobal.org/xsd/imsmd_v1p2p4.xsd http://www.imsglobal.org/xsd/imsqti_metadata_v2p1 http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_metadata_v2p1.xsd">
  <metadata>
    <schema>QTIv2.1</schema>
    <schemaversion>2.1</schemaversion>
  </metadata>
  <organizations/>
  <resources>
    <resource identifier="{test_res_id}" type="imsqti_test_xmlv2p1" href="Test.xml">
      <file href="Test.xml"/>
{chr(10).join(item_dependencies)}
    </resource>
{chr(10).join(item_resources)}
  </resources>
</manifest>"""

