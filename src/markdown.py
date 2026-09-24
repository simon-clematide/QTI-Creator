"""Conservative Markdown to QTI-compliant XHTML converter.

Rule: Distinguish quiz semantics from Markdown presentation.
Initial support:
- paragraphs (<p>)
- emphasis (<em>, <strong>)
- lists (<ul>, <ol>, <li>)
- inline code (<code>) and fenced code (<pre><code>)
- block quotes (<blockquote>)
- math notation ($...$ and $$...$$, MathJax-compatible TeX)
"""

import html
import re
import urllib.parse
from typing import Dict, List, Optional

# Shared pattern for fill-in-the-blank gaps: {{answer}} or {{answer|alt1|alt2}}
RE_GAP = re.compile(r"\{\{((?:\\.|[^\}\\]|\}(?!\})*?)*?)\}\}")


def markdown_to_qti_xhtml(
    text: str,
    asset_map: Optional[Dict[str, str]] = None,
    render_math: bool = True,
) -> str:
    """Convert a Markdown text string into well-formed XHTML suitable for <itemBody>.
    
    If asset_map is provided (mapping original source -> packaged relative path),
    image src attributes are rewritten accordingly.
    When render_math is True (default), MathJax-compatible TeX formulas are preserved
    with delimiters ($...$ and $$...$$).
    When render_math is False, formulas are displayed literally as code.
    """
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

        # Display math block: $$ ... $$ or \[ ... \]
        if stripped.startswith("$$") or stripped.startswith(r"\["):
            is_bracket = stripped.startswith(r"\[")
            close_delim = r"\]" if is_bracket else "$$"
            math_lines = []
            if stripped in ("$$", r"\["):
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(close_delim):
                    math_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1  # Skip closing delimiter
                math_text = "\n".join(math_lines).strip()
            else:
                regex_pattern = r"^\\\[(.*?)\\\]$" if is_bracket else r"^\$\$(.*?)\$\$$"
                m = re.match(regex_pattern, stripped)
                if m:
                    math_text = m.group(1).strip()
                    i += 1
                else:
                    prefix_len = 2
                    math_lines.append(stripped[prefix_len:])
                    i += 1
                    while i < len(lines) and not lines[i].strip().endswith(close_delim):
                        math_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        end_line = lines[i].strip()
                        math_lines.append(end_line[:-len(close_delim)])
                        i += 1
                    math_text = "\n".join(math_lines).strip()

            if render_math:
                title_val = urllib.parse.quote(math_text)
                escaped_latex = html.escape(math_text, quote=False)
                output_blocks.append(f'<p style="text-align:center"><span class="math" title="{title_val}">{escaped_latex}</span></p>')
            else:
                output_blocks.append(f"<pre class='math-raw'>$${html.escape(math_text)}$$</pre>")
            continue

        # Blockquote: > text
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            quote_body = markdown_to_qti_xhtml(
                "\n".join(quote_lines),
                asset_map=asset_map,
                render_math=render_math,
            )
            output_blocks.append(f"<blockquote>{quote_body}</blockquote>")
            continue

        # Unordered list: - or * (excluding task lists and kprim items)
        choice_prefix = r"^[-*]\s+(?!\[[ xX+-]\])"
        if re.match(choice_prefix, stripped):
            items = []
            while i < len(lines) and re.match(choice_prefix, lines[i].strip()):
                item_text = re.sub(r"^[-*]\s+", "", lines[i].strip())
                items.append(f"<li>{_format_inlines(item_text, asset_map=asset_map, render_math=render_math)}</li>")
                i += 1
            output_blocks.append(f"<ul>{''.join(items)}</ul>")
            continue

        # Ordered list: 1. 2.
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                items.append(f"<li>{_format_inlines(item_text, asset_map=asset_map, render_math=render_math)}</li>")
                i += 1
            output_blocks.append(f"<ol>{''.join(items)}</ol>")
            continue

        # Markdown Table (GFM pipe syntax)
        if "|" in stripped and i + 1 < len(lines) and _is_table_separator_row(lines[i + 1]):
            table_lines = [stripped]
            i += 1
            # Add separator line
            table_lines.append(lines[i].strip())
            i += 1
            # Accumulate data rows
            while i < len(lines):
                row_line = lines[i].strip()
                if not row_line or not ("|" in row_line):
                    break
                table_lines.append(row_line)
                i += 1
            table_html = _render_table(table_lines, asset_map=asset_map, render_math=render_math)
            output_blocks.append(table_html)
            continue

        # Normal paragraph (accumulate consecutive lines)
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if (
                not next_line
                or next_line.startswith("```")
                or next_line.startswith("$$")
                or next_line.startswith(r"\[")
                or next_line.startswith(">")
                or re.match(r"^[-*]\s+", next_line)
                or re.match(r"^\d+\.\s+", next_line)
                or ("|" in next_line and i + 1 < len(lines) and _is_table_separator_row(lines[i + 1]))
            ):
                break
            para_lines.append(next_line)
            i += 1

        para_text = " ".join(para_lines)
        output_blocks.append(f"<p>{_format_inlines(para_text, asset_map=asset_map, render_math=render_math)}</p>")

    return "\n".join(output_blocks)


def _is_table_separator_row(line: str) -> bool:
    """Check if line is a valid GFM table separator row e.g. |:---|:---:|---:|."""
    stripped = line.strip()
    if not stripped or "|" not in stripped:
        return False
    parts = _split_table_row(stripped)
    if not parts:
        return False
    for p in parts:
        cell = p.strip()
        if not re.match(r"^:?-+:?$", cell):
            return False
    return True


def _split_table_row(line: str) -> List[str]:
    """Split a table row on '|' taking care of optional leading and trailing pipes."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    # Note: escaped \| can be handled if needed, standard markdown splits on |
    # We split on | that is not escaped
    tokens = re.split(r"(?<!\\)\|", s)
    return [t.replace(r"\|", "|").strip() for t in tokens]


def _render_table(
    table_lines: List[str],
    asset_map: Optional[Dict[str, str]] = None,
    render_math: bool = True,
) -> str:
    """Render GFM Markdown table lines into well-formed HTML <table>."""
    if len(table_lines) < 2:
        return ""

    header_cols = _split_table_row(table_lines[0])
    sep_cols = _split_table_row(table_lines[1])
    num_cols = max(len(header_cols), len(sep_cols))

    alignments = []
    for i in range(num_cols):
        align = "left"
        if i < len(sep_cols):
            s = sep_cols[i].strip()
            if s.startswith(":") and s.endswith(":"):
                align = "center"
            elif s.endswith(":"):
                align = "right"
            elif s.startswith(":"):
                align = "left"
        alignments.append(align)

    # Build <thead>
    thead_cells = []
    for i in range(num_cols):
        val = header_cols[i] if i < len(header_cols) else ""
        cell_html = _format_inlines(val, asset_map=asset_map, render_math=render_math)
        align_attr = f' style="text-align: {alignments[i]};"'
        thead_cells.append(f"<th{align_attr}>{cell_html}</th>")
    thead_html = f"  <thead>\n    <tr>{''.join(thead_cells)}</tr>\n  </thead>"

    # Build <tbody>
    tbody_rows = []
    for row_line in table_lines[2:]:
        row_cols = _split_table_row(row_line)
        row_cells = []
        for i in range(num_cols):
            val = row_cols[i] if i < len(row_cols) else ""
            cell_html = _format_inlines(val, asset_map=asset_map, render_math=render_math)
            align_attr = f' style="text-align: {alignments[i]};"'
            row_cells.append(f"<td{align_attr}>{cell_html}</td>")
        tbody_rows.append(f"    <tr>{''.join(row_cells)}</tr>")

    tbody_html = f"  <tbody>\n{chr(10).join(tbody_rows)}\n  </tbody>" if tbody_rows else "  <tbody/>"

    return f'<table class="b_default" style="border-collapse:collapse;width:100%;">\n{thead_html}\n{tbody_html}\n</table>'


def _format_inlines(
    text: str,
    asset_map: Optional[Dict[str, str]] = None,
    render_math: bool = True,
) -> str:
    """Format inline markdown elements while protecting math spans, code spans, and images.

    OpenOLAT renders math via MathJax 3 (OpenOLAT ≥ 16.2). Delimiters $$...$$ and $...$
    are preserved for MathJax to process.
    Math, code spans, and images are protected before markdown styling so that LaTeX symbols
    and URL characters are preserved verbatim without being misinterpreted as Markdown formatting.
    """
    placeholders = {}
    counter = 0

    # 1. Protect display math $$...$$ and \[...\]
    def save_display_math(match):
        nonlocal counter
        key = f"XXMATHDISP{counter}XX"
        counter += 1
        raw_math = match.group(1).strip()
        if render_math:
            title_val = urllib.parse.quote(raw_math)
            escaped_latex = html.escape(raw_math, quote=False)
            placeholders[key] = f'<span class="math" title="{title_val}">{escaped_latex}</span>'
        else:
            placeholders[key] = f"<pre class='math-raw'>$${html.escape(raw_math)}$$</pre>"
        return key

    text = re.sub(r"\$\$(.+?)\$\$", save_display_math, text, flags=re.DOTALL)
    text = re.sub(r"\\\[([\s\S]+?)\\\]", save_display_math, text)

    # 2. Protect inline math $...$ and \(...\) -> <span class="math" title="...">raw_latex</span>
    def save_inline_math(match):
        nonlocal counter
        key = f"XXMATHINL{counter}XX"
        counter += 1
        raw_math = match.group(1).strip()
        if render_math:
            title_val = urllib.parse.quote(raw_math)
            escaped_latex = html.escape(raw_math, quote=False)
            placeholders[key] = f'<span class="math" title="{title_val}">{escaped_latex}</span>'
        else:
            # render_math=False: show raw source literally
            placeholders[key] = f"<code>${html.escape(raw_math)}$</code>"
        return key

    text = re.sub(r"\\\((.+?)\\\)", save_inline_math, text)
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

    # 4. Protect images: ![alt](src =WxH)
    def save_image(match):
        nonlocal counter
        key = f"XXIMG{counter}XX"
        counter += 1
        alt = match.group(1).strip()
        src = match.group(2).strip()
        size_spec = match.group(3)

        # If asset_map is provided and maps this src to a packaged relative path, rewrite it
        target_src = asset_map.get(src, src) if asset_map else src
        escaped_alt = html.escape(alt)
        escaped_src = html.escape(target_src)

        # Parse HackMD size spec: e.g. 300x, 30%x, 500x300, x200, 50%
        extra_attrs = []
        style_parts = []

        if size_spec:
            style_parts.append("max-width: 100%")
            if "x" in size_spec:
                w_str, h_str = size_spec.split("x", 1)
                if w_str:
                    w_val = w_str if (w_str.endswith("%") or w_str.endswith("px")) else f"{w_str}px"
                    extra_attrs.append(f'width="{html.escape(w_val)}"')
                if h_str:
                    h_val = h_str if (h_str.endswith("%") or h_str.endswith("px")) else f"{h_str}px"
                    extra_attrs.append(f'height="{html.escape(h_val)}"')
                else:
                    style_parts.append("height: auto")
            else:
                w_val = size_spec if (size_spec.endswith("%") or size_spec.endswith("px")) else f"{size_spec}px"
                extra_attrs.append(f'width="{html.escape(w_val)}"')
                style_parts.append("height: auto")

        extra_attrs_str = (" " + " ".join(extra_attrs)) if extra_attrs else ""
        style_str = f' style="{"; ".join(style_parts)};"' if style_parts else ""

        placeholders[key] = f'<img src="{escaped_src}" alt="{escaped_alt}"{extra_attrs_str}{style_str} />'
        return key

    text = re.sub(
        r"!\[([^\]]*)\]\(\s*(\S+?)(?:\s+=((?:\d+(?:%|px)?x\d*(?:%|px)?|\d*x\d+(?:%|px)?|\d+(?:%|px)?)))?\s*\)",
        save_image,
        text,
    )

    # 5. Protect standard links: [text](href) -> <a href="...">text</a>
    def save_link(match):
        nonlocal counter
        key = f"XXLINK{counter}XX"
        counter += 1
        link_text = match.group(1)
        href = match.group(2).strip()
        escaped_href = html.escape(href)
        escaped_text = html.escape(link_text)
        placeholders[key] = f'<a href="{escaped_href}">{escaped_text}</a>'
        return key

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", save_link, text)

    # 6. Safely HTML-escape remaining text
    s = html.escape(text)

    # 7. Format Markdown inline styles (bold, italic)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"__(.+?)__", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"_(.+?)_", r"<em>\1</em>", s)

    # 8. Restore protected placeholders
    for key, val in placeholders.items():
        s = s.replace(key, val)

    return s


# Patterns that indicate presence of Markdown formatting or math in a single-line title
RE_MARKDOWN_SYNTAX = re.compile(
    r"(\*\*|__|(?<!\w)\*[^*\n]+?\*(?!\w)|(?<!\w)_[^_\n]+?_(?!\w)|`[^`\n]+`|\$[^$\n]+\$|\$\$[\s\S]+?\$\$|\\\(.*?\\\)|\\\[[\s\S]*?\\\]|!\[.*?\]\(.*?\)|\[.*?\]\(.*?\)|~~.*?~~)"
)


def contains_markdown(text: str) -> bool:
    """Return True if text contains Markdown formatting syntax or math (bold, italic, code, math, links, images)."""
    if not text:
        return False
    return bool(RE_MARKDOWN_SYNTAX.search(text))
