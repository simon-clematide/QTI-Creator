"""Conservative Markdown to QTI-compliant XHTML converter.

Rule: Distinguish quiz semantics from Markdown presentation.
Initial support:
- paragraphs (<p>)
- emphasis (<em>, <strong>)
- lists (<ul>, <ol>, <li>)
- inline code (<code>) and fenced code (<pre><code>)
- block quotes (<blockquote>)
- math notation ($...$ and $$...$$)
"""

import html
import re
import urllib.parse
from typing import List


def markdown_to_qti_xhtml(text: str) -> str:
    """Convert a Markdown text string into well-formed XHTML suitable for <itemBody>."""
    if not text:
        return ""

    lines = text.splitlines()
    output_blocks: List[str] = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Empty line
        if not stripped:
            i += 1
            continue

        # Fenced code block: ```lang ... ```
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(html.escape(lines[i]))
                i += 1
            if i < len(lines):
                i += 1  # Skip closing ```
            # Ignore accidental leading or trailing empty lines (e.g. newline right after ```)
            while code_lines and not code_lines[0].strip():
                code_lines.pop(0)
            while code_lines and not code_lines[-1].strip():
                code_lines.pop()
            code_content = "\n".join(code_lines)
            output_blocks.append(f"<pre><code>{code_content}</code></pre>")
            continue

        # Display math block: $$ ... $$
        if stripped.startswith("$$"):
            math_lines = []
            if stripped == "$$":
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("$$"):
                    math_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1  # Skip closing $$
                math_text = "\n".join(math_lines).strip()
            else:
                m = re.match(r"^\$\$(.*?)\$\$$", stripped)
                if m:
                    math_text = m.group(1).strip()
                    i += 1
                else:
                    math_lines.append(stripped[2:])
                    i += 1
                    while i < len(lines) and not lines[i].strip().endswith("$$"):
                        math_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        end_line = lines[i].strip()
                        math_lines.append(end_line[:-2])
                        i += 1
                    math_text = "\n".join(math_lines).strip()
            output_blocks.append(f"<p>$${html.escape(math_text, quote=False)}$$</p>")
            continue

        # Blockquote: > text
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            quote_body = markdown_to_qti_xhtml("\n".join(quote_lines))
            output_blocks.append(f"<blockquote>{quote_body}</blockquote>")
            continue

        # Unordered list: - or * (excluding task lists, radio markers, and kprim items)
        choice_prefix = r"^[-*]\s+(?!\[[ xX*+-oO]\]|\([ xX*+-oO]\))"
        if re.match(choice_prefix, stripped):
            items = []
            while i < len(lines) and re.match(choice_prefix, lines[i].strip()):
                item_text = re.sub(r"^[-*]\s+", "", lines[i].strip())
                items.append(f"<li>{_format_inlines(item_text)}</li>")
                i += 1
            output_blocks.append(f"<ul>{''.join(items)}</ul>")
            continue

        # Ordered list: 1. 2.
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                items.append(f"<li>{_format_inlines(item_text)}</li>")
                i += 1
            output_blocks.append(f"<ol>{''.join(items)}</ol>")
            continue

        # Normal paragraph (accumulate consecutive lines)
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if not next_line or next_line.startswith("```") or next_line.startswith("$$") or next_line.startswith(">") or re.match(r"^[-*]\s+", next_line) or re.match(r"^\d+\.\s+", next_line):
                break
            para_lines.append(next_line)
            i += 1

        para_text = " ".join(para_lines)
        output_blocks.append(f"<p>{_format_inlines(para_text)}</p>")

    return "\n".join(output_blocks)


def _format_inlines(text: str) -> str:
    """Format inline markdown elements while protecting math spans and code spans.

    OpenOLAT natively renders literal $$...$$ (display math) and $...$ (inline math).
    Math and code spans are protected before markdown styling so that LaTeX symbols
    like underscores, asterisks, and backslashes are preserved verbatim without being
    misinterpreted as Markdown formatting.
    """
    placeholders = {}
    counter = 0

    # 1. Protect display math $$...$$
    def save_display_math(match):
        nonlocal counter
        key = f"XXMATHDISP{counter}XX"
        counter += 1
        raw_math = match.group(1)
        # Escape XML-sensitive characters (&, <, >) while preserving LaTeX syntax
        placeholders[key] = f"$${html.escape(raw_math, quote=False)}$$"
        return key

    text = re.sub(r"\$\$(.+?)\$\$", save_display_math, text, flags=re.DOTALL)

    # 2. Protect inline math $...$ -> <span class="math" title="...">raw_latex</span>
    def save_inline_math(match):
        nonlocal counter
        key = f"XXMATHINL{counter}XX"
        counter += 1
        raw_math = match.group(1)
        # OpenOLAT uses <span class="math" title="encoded">raw_latex</span> without \(...\)
        title_val = urllib.parse.quote(raw_math)
        escaped_latex = html.escape(raw_math, quote=False)
        placeholders[key] = f'<span class="math" title="{title_val}">{escaped_latex}</span>'
        return key

    text = re.sub(r"(?<!\$)\$(?!\$)([^\$\n]+?)(?<!\$)\$(?!\$)", save_inline_math, text)

    # 3. Protect inline code `...`
    def save_code(match):
        nonlocal counter
        key = f"XXCODE{counter}XX"
        counter += 1
        raw_code = match.group(1)
        placeholders[key] = f"<code>{html.escape(raw_code)}</code>"
        return key

    text = re.sub(r"`(.+?)`", save_code, text)

    # 4. Safely HTML-escape remaining text
    s = html.escape(text)

    # 5. Format Markdown inline styles (bold, italic)
    # Bold: **text** or __text__
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"__(.+?)__", r"<strong>\1</strong>", s)

    # Italic: *text* or _text_
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"_(.+?)_", r"<em>\1</em>", s)

    # 6. Restore protected math and code placeholders
    for key, val in placeholders.items():
        s = s.replace(key, val)

    return s
