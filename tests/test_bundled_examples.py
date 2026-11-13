"""Executable documentation and bundled media should work as copied/loaded."""

import io
from pathlib import Path
import re
import zipfile

import pytest

from qti_creator.examples import HOTSPOT_EXAMPLE_NAME, UI_EXAMPLES, load_example
from qti_creator.session import QuizSession
from qti_creator.ui.help_content import SINGLE_SECTION_EXAMPLE, MULTI_SECTION_EXAMPLE
from qti_creator.core.media import preflight_media
from qti_creator.core.model import FillBlankQuestion, HotspotQuestion
from qti_creator.core.packager import create_qti_package
from qti_creator.core.parser import parse_quizmd
from qti_creator.core.validation import Severity


@pytest.mark.parametrize("source,sections,questions", [
    (SINGLE_SECTION_EXAMPLE, 1, 1),
    (MULTI_SECTION_EXAMPLE, 2, 2),
])
def test_documented_complete_examples_export(source, sections, questions):
    quiz, diagnostics = parse_quizmd(source)
    assert not diagnostics
    assert quiz.title == "Biology Practice"
    assert len(quiz.sections) == sections
    assert len(quiz.questions) == questions
    assert all(section.questions for section in quiz.sections)
    output = io.BytesIO()
    create_qti_package(quiz, output)
    with zipfile.ZipFile(output) as package:
        assert "imsmanifest.xml" in package.namelist()


def test_published_escape_examples_match_literal_answers():
    # Exercise the exact inline QuizMD examples in the rendered documentation string.
    from qti_creator.ui.syntax import render_syntax_page
    import gradio as gr
    with gr.Blocks() as documentation:
        render_syntax_page()
    source = "\n".join(
        block.value for block in documentation.blocks.values()
        if isinstance(block, gr.Markdown)
    )
    examples = re.findall(r'`(\{\{[^`]+\}\})`', source)
    literal_examples = [example for example in examples if "\\" in example]
    assert literal_examples
    expected = ["a|b", "answer containing }} braces"]
    for example, answer in zip(literal_examples, expected, strict=True):
        quiz, diagnostics = parse_quizmd("## Complete the text\nAnswer: " + example)
        assert not diagnostics
        question = quiz.questions[0]
        assert isinstance(question, FillBlankQuestion)
        assert question.gaps[0].expected_value == answer


def test_hotspot_example_loads_matching_media_and_exports(tmp_path):
    session = QuizSession(session_id=str(tmp_path / "session"))
    loaded = load_example(HOTSPOT_EXAMPLE_NAME, session)
    assert loaded is session
    assert loaded.media.include_in_package
    assert loaded.media.resolve_in_preview
    assert not loaded.media.missing
    assert len(loaded.media.files) == 1
    assert loaded.media.files[0].relative_path == "quadrants.png"
    quiz, diagnostics = parse_quizmd(loaded.source)
    assert not [d for d in diagnostics if d.severity == Severity.ERROR]
    assert len(quiz.questions) == 2
    assert all(isinstance(q, HotspotQuestion) for q in quiz.questions)
    media = preflight_media(quiz, include_media=True, media_zip_bytes=Path(loaded.media.zip_path).read_bytes())
    assert not media.has_errors
    assert len(media.resolved_hotspot_images) == 2
    output = io.BytesIO()
    create_qti_package(quiz, output, media_preflight=media)
    with zipfile.ZipFile(output) as package:
        assert "imsmanifest.xml" in package.namelist()
        assert any(name.startswith("media/") for name in package.namelist())
    # A text-only example must clear the previous media and generated-package state.
    loaded.package.output_path = "old-package.zip"
    load_example(next(iter(UI_EXAMPLES)), loaded)
    assert not loaded.media.include_in_package
    assert not loaded.media.files
    assert loaded.package.output_path is None
