"""Regression test for the Syntax Cheat Sheet table documentation rendering."""

import re
from qti_creator.ui.syntax import SYNTAX_MARKDOWN


def test_syntax_cheat_sheet_table_structure():
    """Verify that SYNTAX_MARKDOWN has a valid, unbroken HTML table with no blank lines inside <tbody>."""
    assert "### QuizMD Cheat Sheet" in SYNTAX_MARKDOWN
    assert "<table" in SYNTAX_MARKDOWN
    assert "</table>" in SYNTAX_MARKDOWN

    # Extract table content
    table_match = re.search(r"<table[^>]*>(.*?)</table>", SYNTAX_MARKDOWN, re.DOTALL)
    assert table_match is not None, "Complete <table>...</table> not found"
    table_content = table_match.group(1)

    # In Markdown processors (like python-markdown/commonmark), a blank line inside an HTML block
    # ends the HTML block and causes subsequent lines to be parsed as raw markdown paragraphs.
    tbody_match = re.search(r"<tbody>(.*?)</tbody>", table_content, re.DOTALL)
    assert tbody_match is not None, "Complete <tbody>...</tbody> not found"
    tbody_content = tbody_match.group(1)

    # Check there are no blank lines between rows inside tbody
    raw_lines = [l for l in tbody_content.splitlines() if l.strip()]
    assert len(raw_lines) > 0
    # Also verify that the raw string has no double-newlines (which signify blank lines)
    assert "\n\n" not in tbody_content, "Found empty line inside <tbody> which breaks HTML table parsing"

    # Verify all 12 question types are present inside the table
    expected_types = [
        "Single Choice",
        "True / False",
        "Multiple Choice",
        "Kprim (Matrix)",
        "Fill in the Blank (Text)",
        "Fill in the Blank (Dropdown)",
        "Hottext",
        "Numerical",
        "Order / Sequencing",
        "Match",
        "Drag & Drop",
        "Essay / Free Text",
    ]
    for q_type in expected_types:
        assert (q_type in tbody_content or q_type.replace("&", "&amp;") in tbody_content), (
            f"Question type '{q_type}' missing from table rows"
        )

    # Verify post-table note is present
    assert "*All questions are worth 1 point by default. Use `Points: <number>` to change a question's weight.*" in SYNTAX_MARKDOWN
