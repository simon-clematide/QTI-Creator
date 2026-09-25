"""IMS Content Packaging generator for imsmanifest.xml (QTI 2.1).

Generates manifest with OpenOLAT-specific metadata (ns4:ooMetadata) and
IMS QTI metadata (imsqti:qtiMetadata) to guarantee native editable recognition
in OpenOLAT.
"""

import html

from src.model import (
    EssayQuestion,
    FillBlankQuestion,
    HottextQuestion,
    InlineChoiceQuestion,
    KprimQuestion,
    MultipleChoiceQuestion,
    NumericalQuestion,
    OrderQuestion,
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
    elif isinstance(q, InlineChoiceQuestion):
        return "inlineChoiceInteraction"
    elif isinstance(q, HottextQuestion):
        return "hottextInteraction"
    elif isinstance(q, (FillBlankQuestion, NumericalQuestion)):
        return "textEntryInteraction"
    elif isinstance(q, EssayQuestion):
        return "extendedTextInteraction"
    elif isinstance(q, OrderQuestion):
        return "orderInteraction"
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
    elif isinstance(q, InlineChoiceQuestion):
        return "inlinechoice"
    elif isinstance(q, HottextQuestion):
        return "hottext"
    elif isinstance(q, NumericalQuestion):
        return "numerical"
    elif isinstance(q, EssayQuestion):
        return "essay"
    elif isinstance(q, OrderQuestion):
        return "order"
    return "sc"



from typing import Dict, List, Optional


def generate_manifest_xml(quiz: Quiz, question_asset_map: Optional[Dict[str, List[str]]] = None) -> str:
    """Generate the root-level imsmanifest.xml required by OpenOLAT.
    
    If question_asset_map is provided (mapping question_id -> list of package relative filenames),
    each media file is declared under its referencing item <resource>.
    """
    test_res_id = f"RES_{quiz.identifier}"
    escaped_version = html.escape(quiz.version)
    escaped_lang = html.escape(quiz.language)

    item_dependencies = []
    item_resources = []

    for q in quiz.questions:
        item_res_id = f"RES_{q.identifier}"
        item_filename = f"{q.identifier}.xml"
        interaction_type = _get_qti_interaction_type(q)
        oo_question_type = _get_openolat_question_type(q)
        q_lang = html.escape(q.language or quiz.language)

        # Build imsmd:general if keywords or language/context are present
        general_parts = []
        for kw in q.keywords:
            general_parts.append(
                f"""          <imsmd:keyword>
            <imsmd:langstring xml:lang="{q_lang}">{html.escape(kw)}</imsmd:langstring>
          </imsmd:keyword>"""
            )
        general_parts.append(
            f"""          <imsmd:coverage>
            <imsmd:langstring xml:lang="{q_lang}"></imsmd:langstring>
          </imsmd:coverage>"""
        )
        general_parts.append(
            f"""          <imsmd:context xsi:type="imsmd:stringType" xml:lang="{q_lang}">{q_lang}</imsmd:context>"""
        )
        general_block = f"""        <imsmd:general>
{chr(10).join(general_parts)}
        </imsmd:general>"""

        # Build ns4:ooMetadata
        oo_parts = [f"          <ns4:questionType>{oo_question_type}</ns4:questionType>"]
        if q.topic:
            oo_parts.append(f"          <ns4:topic>{html.escape(q.topic)}</ns4:topic>")
        if q.additional_info:
            oo_parts.append(f"          <ns4:additionalInformations>{html.escape(q.additional_info)}</ns4:additionalInformations>")

        oo_block = f"""        <ns4:ooMetadata>
{chr(10).join(oo_parts)}
        </ns4:ooMetadata>"""

        file_entries = [f'      <file href="{item_filename}"/>']
        if question_asset_map and q.identifier in question_asset_map:
            for asset_path in question_asset_map[q.identifier]:
                file_entries.append(f'      <file href="{html.escape(asset_path)}"/>')

        item_dependencies.append(f'      <dependency identifierref="{item_res_id}"/>')
        item_resources.append(f"""    <resource identifier="{item_res_id}" type="imsqti_item_xmlv2p1" href="{item_filename}">
      <metadata>
        <imsmd:lom>
{general_block}
          <imsmd:technical>
            <imsmd:format>text/x-imsqti-item-xml</imsmd:format>
          </imsmd:technical>
          <imsmd:educational/>
        </imsmd:lom>
        <imsqti:qtiMetadata>
          <imsqti:interactionType>{interaction_type}</imsqti:interactionType>
        </imsqti:qtiMetadata>
{oo_block}
      </metadata>
{chr(10).join(file_entries)}
    </resource>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
          xmlns:imsmd="http://www.imsglobal.org/xsd/imsmd_v1p2"
          xmlns:imsqti="http://www.imsglobal.org/xsd/imsqti_metadata_v2p1"
          xmlns:ns4="http://www.openolat.org/xsd/oomd_v1p1"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          identifier="MANIFEST_{quiz.identifier}"
          version="{escaped_version}"
          xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 http://www.imsglobal.org/xsd/imscp_v1p1.xsd http://www.imsglobal.org/xsd/imsmd_v1p2 http://www.imsglobal.org/xsd/imsmd_v1p2p4.xsd http://www.imsglobal.org/xsd/imsqti_metadata_v2p1 http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_metadata_v2p1.xsd">
  <metadata>
    <schema>QTIv2.1</schema>
    <schemaversion>2.1</schemaversion>
    <imsmd:lom>
      <imsmd:lifecycle>
        <imsmd:version>
          <imsmd:langstring xml:lang="{escaped_lang}">{escaped_version}</imsmd:langstring>
        </imsmd:version>
      </imsmd:lifecycle>
    </imsmd:lom>
  </metadata>
  <organizations/>
  <resources>
    <resource identifier="{test_res_id}" type="imsqti_test_xmlv2p1" href="Test.xml">
      <metadata>
        <imsmd:lom>
          <imsmd:lifecycle>
            <imsmd:version>
              <imsmd:langstring xml:lang="{escaped_lang}">{escaped_version}</imsmd:langstring>
            </imsmd:version>
          </imsmd:lifecycle>
        </imsmd:lom>
      </metadata>
      <file href="Test.xml"/>
{chr(10).join(item_dependencies)}
    </resource>
{chr(10).join(item_resources)}
  </resources>
</manifest>"""

