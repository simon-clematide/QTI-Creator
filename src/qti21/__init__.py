"""QTI 2.1 generation package for OpenOLAT."""

from typing import Dict, Optional

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
    SingleChoiceQuestion,
    TrueFalseQuestion,
)
from src.qti21.choice import generate_single_choice_xml, generate_multiple_choice_xml, generate_true_false_xml
from src.qti21.essay import generate_essay_xml
from src.qti21.hottext import generate_hottext_xml
from src.qti21.inline_choice import generate_inline_choice_xml
from src.qti21.text_entry import generate_fill_blank_xml
from src.qti21.numerical import generate_numerical_xml
from src.qti21.kprim import generate_kprim_xml
from src.qti21.order import generate_order_xml


def generate_item_xml(question: Question, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Dispatch question to its specific QTI 2.1 generator."""
    if isinstance(question, SingleChoiceQuestion):
        return generate_single_choice_xml(question, asset_map=asset_map)
    elif isinstance(question, MultipleChoiceQuestion):
        return generate_multiple_choice_xml(question, asset_map=asset_map)
    elif isinstance(question, TrueFalseQuestion):
        return generate_true_false_xml(question, asset_map=asset_map)
    elif isinstance(question, EssayQuestion):
        return generate_essay_xml(question, asset_map=asset_map)
    elif isinstance(question, FillBlankQuestion):
        return generate_fill_blank_xml(question, asset_map=asset_map)
    elif isinstance(question, InlineChoiceQuestion):
        return generate_inline_choice_xml(question, asset_map=asset_map)
    elif isinstance(question, HottextQuestion):
        return generate_hottext_xml(question, asset_map=asset_map)
    elif isinstance(question, NumericalQuestion):
        return generate_numerical_xml(question, asset_map=asset_map)
    elif isinstance(question, KprimQuestion):
        return generate_kprim_xml(question, asset_map=asset_map)
    elif isinstance(question, OrderQuestion):
        return generate_order_xml(question, asset_map=asset_map)
    else:
        raise NotImplementedError(f"No QTI 2.1 generator for {type(question).__name__}")
