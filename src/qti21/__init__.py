"""QTI 2.1 generation package for OpenOLAT."""

from typing import Dict
from src.model import (
    EssayQuestion,
    FillBlankQuestion,
    KprimQuestion,
    MultipleChoiceQuestion,
    NumericalQuestion,
    Question,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)


def generate_item_xml(question: Question) -> str:
    """Dispatch question to its specific QTI 2.1 generator."""
    from src.qti21.choice import generate_single_choice_xml, generate_multiple_choice_xml, generate_true_false_xml
    from src.qti21.essay import generate_essay_xml
    from src.qti21.text_entry import generate_fill_blank_xml
    from src.qti21.numerical import generate_numerical_xml
    from src.qti21.kprim import generate_kprim_xml

    if isinstance(question, SingleChoiceQuestion):
        return generate_single_choice_xml(question)
    elif isinstance(question, MultipleChoiceQuestion):
        return generate_multiple_choice_xml(question)
    elif isinstance(question, TrueFalseQuestion):
        return generate_true_false_xml(question)
    elif isinstance(question, EssayQuestion):
        return generate_essay_xml(question)
    elif isinstance(question, FillBlankQuestion):
        return generate_fill_blank_xml(question)
    elif isinstance(question, NumericalQuestion):
        return generate_numerical_xml(question)
    elif isinstance(question, KprimQuestion):
        return generate_kprim_xml(question)
    else:
        raise NotImplementedError(f"No QTI 2.1 generator for {type(question).__name__}")
