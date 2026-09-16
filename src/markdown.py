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
from typing import Dict, List, Optional

# Shared pattern for fill-in-the-blank gaps: {{answer}} or {{answer|alt1|alt2}}
RE_GAP = re.compile(r"\{\{((?:\\.|[^\}\\]|\}(?!\})*?)*?)\}\}")


def markdown_to_qti_xhtml(text: str, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Convert a Markdown text string into well-formed XHTML suitable for <itemBody>.
    
    If asset_map is provided (mapping original source -> packaged relative path),
    image src attributes are rewritten accordingly.
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
            quote_body = markdown_to_qti_xhtml("\n".join(quote_lines), asset_map=asset_map)
            output_blocks.append(f"<blockquote>{quote_body}</blockquote>")
            continue

        # Unordered list: - or * (excluding task lists and kprim items)
        choice_prefix = r"^[-*]\s+(?!\[[ xX+-]\])"
        if re.match(choice_prefix, stripped):
            items = []
            while i < len(lines) and re.match(choice_prefix, lines[i].strip()):
                item_text = re.sub(r"^[-*]\s+", "", lines[i].strip())
                items.append(f"<li>{_format_inlines(item_text, asset_map=asset_map)}</li>")
                i += 1
            output_blocks.append(f"<ul>{''.join(items)}</ul>")
            continue

        # Ordered list: 1. 2.
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                items.append(f"<li>{_format_inlines(item_text, asset_map=asset_map)}</li>")
                i += 1
            output_blocks.append(f"<ol>{''.join(items)}</ol>")
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
                or next_line.startswith(">")
                or re.match(r"^[-*]\s+", next_line)
                or re.match(r"^\d+\.\s+", next_line)
            ):
                break
            para_lines.append(next_line)
            i += 1


        para_text = " ".join(para_lines)
        output_blocks.append(f"<p>{_format_inlines(para_text, asset_map=asset_map)}</p>")

    return "\n".join(output_blocks)


def _format_inlines(text: str, asset_map: Optional[Dict[str, str]] = None) -> str:
    """Format inline markdown elements while protecting math spans, code spans, and images.

    OpenOLAT natively renders literal $$...$$ (display math) and $...$ (inline math).
    Math, code spans, and images are protected before markdown styling so that LaTeX symbols
    and URL characters are preserved verbatim without being misinterpreted as Markdown formatting.
    """
    placeholders = {}
    counter = 0

    # 1. Protect display math $$...$$
    def save_display_math(match):
        nonlocal counter
        key = f"XXMATHDISP{counter}XX"
        counter += 1
        raw_math = match.group(1)
        placeholders[key] = f"$${html.escape(raw_math, quote=False)}$$"
        return key

    text = re.sub(r"\$\$(.+?)\$\$", save_display_math, text, flags=re.DOTALL)

    # 2. Protect inline math $...$ -> <span class="math" title="...">raw_latex</span>
    def save_inline_math(match):
        nonlocal counter
        key = f"XXMATHINL{counter}XX"
        counter += 1
        raw_math = match.group(1)
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
    r"(\*\*|__|(?<!\w)\*[^*\n]+?\*(?!\w)|(?<!\w)_[^_\n]+?_(?!\w)|`[^`\n]+`|\$[^$\n]+\$|!\[.*?\]\(.*?\)|\[.*?\]\(.*?\)|~~.*?~~)"
)


def contains_markdown(text: str) -> bool:
    """Return True if text contains Markdown formatting syntax (bold, italic, code, math, links, images)."""
    if not text:
        return False
    return bool(RE_MARKDOWN_SYNTAX.search(text))
