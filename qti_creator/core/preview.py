"""HTML preview generator for QuizMD."""

import base64
import html
import json
import re
from qti_creator.core.ui_icons import icon as ui_icon
from typing import Any, Dict, List, Optional, Tuple
from qti_creator.core.media import ResolvedHotspotImage, _detect_image_mime, _extract_image_dimensions
from qti_creator.core.model import (
    AssociationQuestion,
    Choice,
    EssayQuestion,
    FillBlankQuestion,
    HotspotQuestion,
    HottextItem,
    HottextQuestion,
    InlineChoiceQuestion,
    InvalidQuestion,
    KprimQuestion,
    MultipleChoiceQuestion,
    NumericalQuestion,
    OrderQuestion,
    Question,
    Quiz,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)
from qti_creator.core.markdown import contains_markdown, extract_hottexts, markdown_to_qti_xhtml, RE_GAP, RE_DROPDOWN_GAP



def render_expand_all_control() -> str:
    """Render the shared disclosure control for embedded and standalone previews."""
    return """      <button type="button" class="quiz-expand-btn" title="Expand or collapse all question cards" onclick="
        var items = document.querySelectorAll('.quiz-question-card, .quiz-section-desc-details');
        var anyClosed = Array.from(items).some(c => !c.open);
        items.forEach(c => c.open = anyClosed);
        this.innerHTML = anyClosed ? '▼ Collapse All' : '▶ Expand All';
        this.title = anyClosed ? 'Collapse all question cards' : 'Expand all question cards';
        if (window.onQuizExpandAllToggle) window.onQuizExpandAllToggle(anyClosed);
      ">▶ Expand All</button>"""

def render_quiz_preview_html(
    quiz: Quiz,
    asset_map: Optional[Dict[str, str]] = None,
    render_math: bool = True,
    hotspot_images: Optional[Dict[str, ResolvedHotspotImage]] = None,
    source_hash: Optional[str] = None,
    show_expand_all: bool = True,
) -> str:
    """Generate clean collapsible HTML cards to visually preview parsed questions.

    If asset_map is provided (mapping relative image source -> data URI or resolved path),
    images in prompts, choices, hints, and feedback are rewritten to display them in preview.
    If render_math is True (default), math delimiters ($...$ and $$...$$) are preserved in the
    output so that MathJax — loaded globally by the host application — can render them after
    the HTML is injected into the DOM. If render_math is False, formulas are shown as raw code.
    """
    if not quiz.questions:
        return "<p style='color: #666; font-style: italic;'>No questions detected yet. Start typing or choose an example on the left.</p>"

    has_multiple_sections = len(quiz.sections) > 1

    sections_html = []
    global_idx = 1

    for s_idx, sec in enumerate(quiz.sections, start=1):
        sec_cards = []
        for q in sec.questions:
            type_name = _get_type_label(q)

            is_invalid = isinstance(q, InvalidQuestion) or bool(getattr(q, "errors", None))
            has_distinct_prompt = bool(q.prompt and q.prompt.strip() and q.prompt.strip() != q.title.strip())

            # For invalid questions, display an alert box listing all validation errors at the top of the body
            validation_alert_html = ""
            if is_invalid:
                q_errors = getattr(q, "errors", [])
                error_items = "".join(
                    f"<li style='margin-bottom: 4px;'>{html.escape(d.message)}</li>"
                    for d in q_errors
                ) or "<li>Validation error detected in question structure.</li>"
                validation_alert_html = f"""
<div style="background: #fef2f2; border: 1px solid #f87171; border-left: 4px solid #ef4444; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; color: #991b1b; font-size: 0.9em;">
  <div style="font-weight: 700; display: flex; align-items: center; gap: 6px; margin-bottom: 6px; color: #b91c1c;">
    <span>⚠️ Validation Errors:</span>
  </div>
  <ul style="margin: 0; padding-left: 18px; line-height: 1.4;">{error_items}</ul>
</div>
"""

            # Question title: OpenOLAT does not render Markdown or math in question titles.
            # Expanded summary headings wrap to show the full raw title; the body only adds a formatting warning.
            has_title_md = contains_markdown(q.title)
            q_title_warning = ""
            if has_title_md:
                q_title_warning = (
                    f" <span title=\"Question titles do not support Markdown or math formatting and will display as raw syntax in OpenOLAT (e.g. '{html.escape(q.title)}')\" "
                    f"style=\"display: inline-flex; align-items: center; gap: 4px; background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 4px; padding: 1px 6px; font-size: 0.72em; font-weight: 600; cursor: help;\">"
                    f"⚠️ Markdown/Math in title</span>"
                )
            question_title_html = q_title_warning

            if isinstance(q, InlineChoiceQuestion):
                # Render dropdown prompt with styled select dropdowns
                base_html = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map, render_math=render_math)
                gap_counter = 0
                def _replace_preview_dropdown(match):
                    nonlocal gap_counter
                    gap_idx = gap_counter
                    gap_counter += 1
                    opts_html = ["<option value=''>-- Select --</option>"]
                    if gap_idx < len(q.gaps):
                        for c in q.gaps[gap_idx].choices:
                            tag = " ✓" if c.is_correct else ""
                            opts_html.append(f"<option>{html.escape(c.text)}{tag}</option>")
                    return (
                        f"<select disabled style='display: inline-block; vertical-align: middle; margin: 0 4px; padding: 2px 8px; "
                        f"border-radius: 4px; border: 1px solid #0d9488; background: #f0fdfa; color: #0f766e; font-weight: 500; font-size: 0.9em;'>"
                        f"{''.join(opts_html)}</select>"
                    )
                rendered_prompt = RE_DROPDOWN_GAP.sub(_replace_preview_dropdown, base_html)
                prompt_html = (
                    f"<div style='color: #334155; margin-bottom: 12px; line-height: 1.8;'>{rendered_prompt}</div>"
                    if (has_distinct_prompt or is_invalid)
                    else ""
                )

            elif isinstance(q, HottextQuestion):
                # Render hottext prompt with highlighted selectable spans:
                # Convert markdown prompt to XHTML first, then substitute raw hottext tokens with styled preview spans
                base_html = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map, render_math=render_math)
                raw_hottexts = extract_hottexts(q.prompt)
                item_map = {}
                for idx, ht in enumerate(raw_hottexts):
                    raw_token = ht[2]
                    content = ht[3]
                    is_correct = ht[4]
                    inner_html = markdown_to_qti_xhtml(content, asset_map=asset_map, render_math=render_math)
                    if inner_html.startswith("<p>") and inner_html.endswith("</p>"):
                        inner_html = inner_html[3:-4]
                    if is_correct:
                        span_html = (
                            f"<span style='display: inline-block; margin: 1px 3px; padding: 2px 8px; border-radius: 5px; "
                            f"border: 1.5px solid #16a34a; background: #dcfce7; color: #166534; font-weight: 600; font-size: 0.95em;' "
                            f"title='Selectable hottext (Correct)'>{inner_html} <span style='font-size: 0.85em; color: #15803d;'>✓</span></span>"
                        )
                    else:
                        span_html = (
                            f"<span style='display: inline-block; margin: 1px 3px; padding: 2px 8px; border-radius: 5px; "
                            f"border: 1.5px dashed #cbd5e1; background: #f8fafc; color: #475569; font-size: 0.95em;' "
                            f"title='Selectable hottext (Incorrect)'>{inner_html}</span>"
                        )
                    item_map[raw_token] = span_html

                def _replace_preview_hottext(match):
                    raw = match.group(0)
                    return item_map.get(raw, raw)

                re_ht_token = re.compile(r"\{(?:\*\*|\+|\-)?\s+[\s\S]*?\}")
                rendered_prompt = re_ht_token.sub(_replace_preview_hottext, base_html)

                prompt_html = (
                    f"<div style='color: #334155; margin-bottom: 12px; line-height: 1.9;'>{rendered_prompt}</div>"
                    if (has_distinct_prompt or is_invalid)
                    else ""
                )

            elif isinstance(q, FillBlankQuestion):
                # Render fill-in-the-blank prompt with styled input fields representing gaps
                base_html = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map, render_math=render_math)
                gap_counter = 0

                def _replace_preview_gap(match):
                    nonlocal gap_counter
                    gap_idx = gap_counter
                    gap_counter += 1
                    val = ""
                    alts_title = ""
                    if gap_idx < len(q.gaps):
                        g = q.gaps[gap_idx]
                        val = g.expected_value
                        if g.alternatives:
                            alts_desc = ", ".join(g.alternatives)
                            alts_title = f" title='Alternatives: {html.escape(alts_desc, quote=True)}'"
                    width_ch = max(8, min(30, len(val) + 4))
                    return (
                        f"<input type='text' disabled value='{html.escape(val, quote=True)}'{alts_title} "
                        f"style='display: inline-block; vertical-align: middle; margin: 0 4px; padding: 2px 8px; "
                        f"width: {width_ch}ch; border-radius: 4px; border: 1.5px solid #10b981; background: #f0fdf4; "
                        f"color: #166534; font-weight: 600; font-size: 0.9em; text-align: center;' />"
                    )

                rendered_prompt = RE_GAP.sub(_replace_preview_gap, base_html)
                prompt_html = (
                    f"<div style='color: #334155; margin-bottom: 12px; line-height: 1.8;'>{rendered_prompt}</div>"
                    if (has_distinct_prompt or is_invalid)
                    else ""
                )

            else:
                base_html = markdown_to_qti_xhtml(q.prompt, asset_map=asset_map, render_math=render_math)
                if is_invalid and RE_GAP.search(base_html):
                    def _replace_invalid_gap(match):
                        inner = match.group(1).split("|")[0].strip()
                        return (
                            f"<input type='text' disabled value='{html.escape(inner, quote=True)}' "
                            f"style='display: inline-block; vertical-align: middle; margin: 0 4px; padding: 2px 8px; "
                            f"border-radius: 4px; border: 1.5px solid #ef4444; background: #fef2f2; "
                            f"color: #991b1b; font-weight: 600; font-size: 0.9em; text-align: center;' />"
                        )
                    base_html = RE_GAP.sub(_replace_invalid_gap, base_html)
                prompt_html = (
                    f"<div style='color: #334155; margin-bottom: 12px; line-height: 1.5;'>{base_html}</div>"
                    if (has_distinct_prompt or is_invalid)
                    else ""
                )

            body_html = _render_question_body(
                q,
                asset_map=asset_map,
                render_math=render_math,
                hotspot_images=hotspot_images,
                question_idx=global_idx,
                source_hash=source_hash,
            )
            hint_header = ui_icon("hint") + (f" Hint: {html.escape(q.hint_title)}" if getattr(q, "hint_title", None) else " Hint")
            hint_html = (
                f"<details class='question-hint' style='margin-top: 12px; padding: 8px 0; font-size: 0.95em; color: #475569;'>"
                f"<summary style='font-weight: 600; outline: none;'>{hint_header}</summary>"
                f"<div style='margin-top: 6px; color: #334155;'>{markdown_to_qti_xhtml(q.hint, asset_map=asset_map, render_math=render_math)}</div></details>"
                if q.hint
                else ""
            )

            feedback_header = f"Feedback: {html.escape(q.feedback_title)}" if getattr(q, "feedback_title", None) else "Feedback:"
            feedback_html = (
                f"<div class='question-feedback' style='margin-top: 12px; padding: 10px 0; border-top: 1px solid #e2e8f0; font-size: 0.95em; color: #475569;'>"
                f"<strong>{feedback_header}</strong> {markdown_to_qti_xhtml(q.feedback, asset_map=asset_map, render_math=render_math)}</div>"
                if q.feedback
                else ""
            )

            # Warning alert for leaked metadata lines or format issues
            leak_warning = getattr(q, "warning_message", None)
            warning_alert_html = ""
            if leak_warning:
                warning_alert_html = f"""
<div style="background: #fffbeb; border: 1px solid #fcd34d; border-left: 4px solid #f59e0b; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; color: #92400e; font-size: 0.9em;">
  <div style="font-weight: 700; display: flex; align-items: center; gap: 6px; margin-bottom: 4px; color: #b45309;">
    <span>⚠️ Potential Content Leak:</span>
  </div>
  <div style="line-height: 1.4;">{html.escape(leak_warning)}</div>
</div>
"""

            status_badges = []
            if is_invalid:
                status_badges.append('<span title="Validation error" style="cursor: help; font-size: 0.95em;">⚠️</span>')
            elif leak_warning:
                status_badges.append(f'<span title="{html.escape(leak_warning, quote=True)}" style="cursor: help; font-size: 0.95em;">⚠️</span>')
            elif has_title_md:
                status_badges.append(f'<span title="Question title contains Markdown or math syntax" style="cursor: help; font-size: 0.95em;">⚠️</span>')
            if q.hint and q.hint.strip():
                status_badges.append('<span title="Hint available" aria-label="Hint available">' + ui_icon("hint") + "</span>")
            if q.feedback and q.feedback.strip():
                status_badges.append('<span title="Feedback available" aria-label="Feedback available">' + ui_icon("feedback") + "</span>")
            status_badges_html = (
                f"<span style='display: inline-flex; align-items: center; gap: 4px; margin-right: 6px;'>{' '.join(status_badges)}</span>"
                if status_badges
                else ""
            )

            markdown_source_html = ""
            raw_src = getattr(q, "raw_markdown", None) or getattr(q, "raw_text", None) or ""
            if raw_src.strip():
                line_no = getattr(q, "line_number", 1) or 1
                escaped_title_attr = html.escape(q.title or "", quote=True)
                markdown_source_html = f"""
<div class="quiz-question-source-container" style="margin-top: 12px; font-size: 0.88em; border-top: 1px dashed #e2e8f0; padding-top: 8px;">
  <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
    <details class="quiz-question-source-details" style="flex: 1 1 auto;">
      <summary title="Toggle raw QuizMD source for question {global_idx}">
        <span>Markdown</span>
      </summary>
      <pre style="margin-top: 8px; margin-bottom: 0; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 12px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.88em; overflow-x: auto; white-space: pre-wrap; word-break: break-word; color: #1e293b;"><code>{html.escape(raw_src.strip())}</code></pre>
    </details>
    <button type="button" class="quiz-edit-jump-btn" title="Jump to question {global_idx} in QuizMD editor" data-line="{line_no}" data-title="{escaped_title_attr}" onclick="var l = parseInt(this.getAttribute('data-line'), 10); var t = this.getAttribute('data-title'); var fn = window.quizJumpToLine || (window.parent && window.parent.quizJumpToLine); if (typeof fn === 'function') {{ fn(l, t); }} else if (window.parent &amp;&amp; window.parent.postMessage) {{ window.parent.postMessage({{action: 'quiz-jump', line: l, title: t}}, '*'); }}">
      {ui_icon("edit")} Edit
    </button>
  </div>
</div>
"""

            card_id = f"qcard_{global_idx}"
            card_border_style = "border-left: 3px solid #dc2626;" if is_invalid else ""
            card = f"""
<details class="quiz-question-card" data-card-id="{card_id}" data-question-idx="{global_idx}" style="{card_border_style} border-bottom: 1px solid #e2e8f0; margin: 0;">
  <summary style="display: flex; justify-content: space-between; align-items: center; padding: 12px 8px; cursor: pointer; user-select: none; list-style: none;">
    <div style="display: flex; align-items: center; gap: 8px; flex-1; min-width: 0;">
      <span class="quiz-chevron" style="display: inline-block; font-size: 0.8em; color: #64748b; transition: transform 0.2s;">▶</span>
      <span class="question-title" style="font-weight: 600; font-size: 1em; color: #1e293b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{global_idx}. {html.escape(q.title)}</span>
    </div>
    <div style="display: flex; align-items: center; flex-shrink: 0; margin-left: 12px;">
      <span class="question-type" title="Question type: {type_name}">{type_name}</span>
      {status_badges_html}
      <span class="question-points" title="Score weight: {q.points} pt">{q.points} pt</span>
    </div>
  </summary>
  <div class="question-content" style="padding: 8px 24px 16px;">
    {validation_alert_html}
    {warning_alert_html}
    {question_title_html}
    {prompt_html}
    {body_html}
    {hint_html}
    {feedback_html}
    {markdown_source_html}
  </div>
</details>
"""
            sec_cards.append(card)
            global_idx += 1

        sec_header = ""
        if has_multiple_sections or sec.title != quiz.title or sec.description:
            sec_points = sum(q.points for q in sec.questions)
            sec_hints = sum(1 for q in sec.questions if q.hint and q.hint.strip())
            sec_feedbacks = sum(1 for q in sec.questions if q.feedback and q.feedback.strip())

            sec_summary_parts = [f"{len(sec.questions)} question{'s' if len(sec.questions) != 1 else ''}"]
            if sec_hints > 0:
                sec_summary_parts.append(f"{sec_hints} hint{'s' if sec_hints != 1 else ''}")
            if sec_feedbacks > 0:
                sec_summary_parts.append(f"{sec_feedbacks} feedback")
            sec_summary_parts.append(f"{sec_points} pt")
            sec_summary_text = " &bull; ".join(sec_summary_parts)

            desc_html = (
                f"<details class=\"quiz-section-desc-details\" open style=\"margin-bottom: 12px;\">"
                f"<summary style=\"display: inline-flex; align-items: center; gap: 6px; font-size: 0.85em; font-weight: 600; color: #475569; cursor: pointer; user-select: none; margin-bottom: 6px; list-style: none; outline: none;\">"
                f"<span class=\"quiz-desc-chevron\" style=\"display: inline-block; font-size: 0.75em; color: #94a3b8; transition: transform 0.2s;\">▼</span>"
                f"<span>Section Description / Instructions</span>"
                f"</summary>"
                f"<div style='color: #475569; font-size: 0.92em; line-height: 1.5; padding: 4px 0; margin-top: 2px;'>{markdown_to_qti_xhtml(sec.description, asset_map=asset_map, render_math=render_math)}</div>"
                f"</details>"
                if sec.description
                else ""
            )

            # Check if section title contains unrendered Markdown or math syntax
            md_warning_badge = ""
            if contains_markdown(sec.title):
                md_warning_badge = (
                    f"<span title=\"Section titles do not support Markdown or math formatting and will display as raw syntax in OpenOLAT (e.g. '{html.escape(sec.title)}')\" "
                    f"style=\"display: inline-flex; align-items: center; gap: 4px; background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 4px; padding: 1px 6px; font-size: 0.72em; font-weight: 600; cursor: help;\">"
                    f"⚠️ Markdown/Math in title</span>"
                )

            section_title_row = f"""
  <div class="section-heading">
    <h4>{html.escape(sec.title)} {md_warning_badge}</h4>
    <span>{sec_summary_text}</span>
  </div>
""" if len(quiz.sections) > 1 or sec.title != quiz.title else ""
            sec_header = f"""
<div class="quiz-section-container">
  {section_title_row}
  {desc_html}
  {''.join(sec_cards)}
</div>
"""
            sections_html.append(sec_header)
        else:
            sections_html.extend(sec_cards)

    total_questions = len(quiz.questions)
    total_hints = sum(1 for q in quiz.questions if q.hint and q.hint.strip())
    total_feedbacks = sum(1 for q in quiz.questions if q.feedback and q.feedback.strip())

    summary_meta = [f"{total_questions} question{'s' if total_questions != 1 else ''} parsed"]
    if len(quiz.sections) > 1:
        summary_meta[0] += f" across {len(quiz.sections)} section{'s' if len(quiz.sections) != 1 else ''}"
    if total_hints > 0:
        summary_meta.append(f"{total_hints} hint{'s' if total_hints != 1 else ''}")
    if total_feedbacks > 0:
        summary_meta.append(f"{total_feedbacks} feedback{'s' if total_feedbacks != 1 else ''}")
    summary_meta.append(f"{sum(q.points for q in quiz.questions):g} pt total")
    summary_meta_text = " &bull; ".join(summary_meta)

    return f"""
<style>
  pre {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 14px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.88em; overflow-x: auto; margin: 8px 0; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-size: 0.88em; color: #0f172a; }}
  pre code {{ background: transparent; padding: 0; border-radius: 0; color: inherit; }}
  blockquote {{ border-left: 3px solid #cbd5e1; margin: 8px 0; padding-left: 12px; color: #475569; }}
  .order-answer {{ padding-left: 1.8rem; margin: 0; }}
  .order-answer li {{ padding-left: 0.25rem; margin: 0.25rem 0; color: #1e293b; }}
  .order-answer li::marker {{ color: #16a34a; font-weight: 700; }}
  img {{ max-width: 100%; height: auto; border-radius: 4px; margin: 8px 0; }}
  .quiz-question-card summary::-webkit-details-marker {{ display: none; }}
  .quiz-question-card[open] {{ border-color: #cbd5e1; box-shadow: 0 2px 5px rgba(0,0,0,0.06); }}
  .quiz-question-card[open] > summary .quiz-chevron {{ transform: rotate(90deg); }}
  .quiz-section-desc-details summary::-webkit-details-marker {{ display: none; }}
  .quiz-section-desc-details:not([open]) > summary .quiz-desc-chevron {{ transform: rotate(-90deg); }}
  .quiz-section-desc-details > summary:hover {{ color: #1e293b; }}
  .quiz-question-source-details summary::-webkit-details-marker {{ display: none; }}
  .quiz-question-source-details summary {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-family: var(--font, 'Source Sans 3', 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    line-height: 1 !important;
    height: 24px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    color: #334155 !important;
    cursor: pointer;
    user-select: none;
    list-style: none;
    outline: none;
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 4px !important;
    padding: 2px 8px !important;
    box-sizing: border-box !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }}
  .quiz-question-source-details summary:hover {{ background: #f1f5f9 !important; color: #0f172a !important; border-color: #94a3b8 !important; }}
  .quiz-edit-jump-btn {{
    font-family: var(--font, 'Source Sans 3', 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    line-height: 1 !important;
    height: 24px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    padding: 2px 8px !important;
    border-radius: 4px !important;
    border: 1px solid #cbd5e1 !important;
    color: #334155 !important;
    background: #ffffff !important;
    cursor: pointer !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 4px !important;
    box-sizing: border-box !important;
    white-space: nowrap !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    transition: background 0.15s, color 0.15s, border-color 0.15s !important;
    user-select: none !important;
    outline: none !important;
  }}
  .quiz-edit-jump-btn:hover {{
    background: #f1f5f9 !important;
    color: #0f172a !important;
    border-color: #94a3b8 !important;
  }}
  .quiz-expand-btn {{
    font-family: var(--font, 'Source Sans 3', 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    line-height: 1 !important;
    height: 24px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    padding: 2px 8px !important;
    border-radius: 4px !important;
    border: 1px solid #cbd5e1 !important;
    color: #334155 !important;
    background: #ffffff !important;
    cursor: pointer !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 4px !important;
    box-sizing: border-box !important;
    white-space: nowrap !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    transition: background 0.15s, color 0.15s, border-color 0.15s !important;
    user-select: none !important;
    outline: none !important;
  }}
  .quiz-expand-btn:hover {{
    background: #f1f5f9 !important;
    color: #0f172a !important;
    border-color: #94a3b8 !important;
  }}
  /* Hotspot Milestone 2 SVG Preview & Author/Learner Toggle */
  .hotspot-preview-widget {{
    margin-top: 4px;
  }}
  .hotspot-toolbar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
    padding: 6px 10px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    font-size: 0.85em;
  }}
  .hotspot-mode-toggle {{
    display: inline-flex;
    background: #e2e8f0;
    border-radius: 6px;
    padding: 2px;
    gap: 2px;
  }}
  .hotspot-mode-btn {{
    font-family: var(--font, 'Source Sans 3', 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    line-height: 1 !important;
    height: 24px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    padding: 2px 8px !important;
    border-radius: 4px !important;
    border: 1px solid transparent !important;
    background: transparent !important;
    color: #475569 !important;
    cursor: pointer !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-sizing: border-box !important;
    white-space: nowrap !important;
    transition: background 0.15s, color 0.15s, box-shadow 0.15s !important;
  }}
  .hotspot-preview-widget[data-view-mode="author"] .hotspot-mode-btn[data-mode="author"],
  .hotspot-preview-widget[data-view-mode="learner"] .hotspot-mode-btn[data-mode="learner"] {{
    background: #ffffff !important;
    color: #0f172a !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08) !important;
  }}
  .hotspot-preview-widget[data-view-mode="editor"] .hotspot-mode-btn[data-mode="editor"] {{
    background: #ffffff !important;
    color: #1d4ed8 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08) !important;
  }}
  .hotspot-canvas-stage {{
    position: relative;
    display: inline-block;
    max-width: 100%;
    line-height: 0;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #cbd5e1;
    background: #f8fafc;
  }}
  .hotspot-canvas-stage img.hotspot-bg-image {{
    display: block;
    max-width: 100%;
    height: auto;
    margin: 0 !important;
    border-radius: 0 !important;
    user-select: none;
  }}
  .hotspot-overlay-svg {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: auto;
  }}
  .hotspot-provisional-svg {{
    position: static;
    display: block;
    width: 100%;
    max-width: 680px;
    height: auto;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: #f8fafc;
  }}
  .hotspot-region-group {{
    cursor: pointer;
  }}
  /* Author and Editor View shape colors */
  .hotspot-preview-widget[data-view-mode="author"] .hotspot-region-group[data-correct="1"] .hotspot-shape,
  .hotspot-preview-widget[data-view-mode="editor"] .hotspot-region-group[data-correct="1"] .hotspot-shape {{
    fill: rgba(34, 197, 94, 0.24);
    stroke: #16a34a;
  }}
  .hotspot-preview-widget[data-view-mode="author"] .hotspot-region-group[data-correct="0"] .hotspot-shape,
  .hotspot-preview-widget[data-view-mode="editor"] .hotspot-region-group[data-correct="0"] .hotspot-shape {{
    fill: rgba(239, 68, 68, 0.18);
    stroke: #dc2626;
    stroke-dasharray: 6, 4;
  }}
  .hotspot-preview-widget[data-view-mode="author"] .hotspot-region-group[data-highlighted="1"] .hotspot-shape,
  .hotspot-preview-widget[data-view-mode="editor"] .hotspot-region-group[data-highlighted="1"] .hotspot-shape {{
    fill: rgba(14, 165, 233, 0.36);
    stroke: #0284c7;
    stroke-dasharray: none;
    filter: drop-shadow(0 0 4px rgba(2, 132, 199, 0.6));
  }}
  /* Learner View shape colors (neutral, no answer-key leakage) */
  .hotspot-preview-widget[data-view-mode="learner"] .hotspot-region-group .hotspot-shape {{
    fill: rgba(59, 130, 246, 0.14);
    stroke: #3b82f6;
    stroke-dasharray: none;
  }}
  .hotspot-preview-widget[data-view-mode="learner"] .hotspot-region-group:hover .hotspot-shape {{
    fill: rgba(59, 130, 246, 0.28);
    stroke: #2563eb;
  }}
  .hotspot-preview-widget[data-view-mode="learner"] .hotspot-region-group[data-learner-selected="1"] .hotspot-shape {{
    fill: rgba(37, 99, 235, 0.42);
    stroke: #1d4ed8;
  }}
  .hotspot-preview-widget[data-view-mode="learner"] .hotspot-author-badge,
  .hotspot-preview-widget[data-view-mode="learner"] .hotspot-author-legend {{
    display: none !important;
  }}
  .hotspot-preview-widget[data-view-mode="author"] .hotspot-learner-bar,
  .hotspot-preview-widget[data-view-mode="author"] .hotspot-editor-controls,
  .hotspot-preview-widget[data-view-mode="learner"] .hotspot-editor-controls {{
    display: none !important;
  }}
  .hotspot-preview-widget[data-view-mode="editor"] .hotspot-learner-bar {{
    display: none !important;
  }}
  .hotspot-preview-widget[data-view-mode="editor"] .hotspot-region-group[data-selected="1"] .hotspot-shape {{
    stroke: #2563eb !important;
    stroke-width: 3.5 !important;
    stroke-dasharray: none !important;
    filter: drop-shadow(0 0 5px rgba(37, 99, 235, 0.7));
  }}
  .hotspot-editor-btn {{
    font-family: var(--font, 'Source Sans 3', 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif) !important;
    border: 1px solid #cbd5e1 !important;
    background: #ffffff !important;
    color: #334155 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 2px 8px !important;
    border-radius: 4px !important;
    cursor: pointer !important;
    line-height: 1 !important;
    height: 24px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 4px !important;
    box-sizing: border-box !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    transition: background 0.15s, border-color 0.15s !important;
    white-space: nowrap !important;
  }}
  .hotspot-editor-btn:hover {{
    background: #f1f5f9 !important;
    color: #0f172a !important;
    border-color: #94a3b8 !important;
  }}
  .hotspot-editor-btn-danger {{
    color: #b91c1c !important;
    border-color: #fca5a5 !important;
  }}
  .hotspot-editor-btn-danger:hover {{
    background: #fef2f2 !important;
    border-color: #f87171 !important;
  }}
  .hotspot-region-pill {{
    font-family: var(--font, 'Source Sans 3', 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 4px !important;
    border: 1px solid #cbd5e1 !important;
    background: #ffffff !important;
    color: #334155 !important;
    font-size: 12.5px !important;
    font-weight: 600 !important;
    padding: 2px 8px !important;
    border-radius: 12px !important;
    cursor: pointer !important;
    line-height: 1 !important;
    height: 24px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    box-sizing: border-box !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    transition: all 0.15s ease !important;
    white-space: nowrap !important;
  }}
  .hotspot-region-pill:hover {{
    background: #f1f5f9 !important;
    border-color: #94a3b8 !important;
  }}
  .hotspot-region-pill[data-selected="1"] {{
    background: #eff6ff !important;
    border-color: #2563eb !important;
    color: #1d4ed8 !important;
    font-weight: 700 !important;
    box-shadow: 0 0 0 1.5px #2563eb !important;
  }}
  .hotspot-handle {{
    fill: #ffffff;
    stroke: #2563eb;
    stroke-width: 1.5;
    cursor: pointer;
  }}
  .hotspot-legend-item {{
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid transparent;
    transition: background 0.12s, border-color 0.12s;
  }}
  .hotspot-legend-item:hover {{
    background: #f8fafc;
  }}
  .hotspot-legend-item[data-selected="1"] {{
    background: #eff6ff !important;
    border-color: #93c5fd !important;
  }}
  .hotspot-legend-item[data-highlighted="1"] {{
    background: #e0f2fe !important;
    border-color: #7dd3fc !important;
  }}

  .ui-icon {{ width: 1rem; height: 1rem; display: inline-block; flex: 0 0 1rem; vertical-align: -0.15em; }}
  .question-type {{ color: #475569; background: #f1f5f9; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; margin-right: 8px; }}
  .question-points {{ color: #64748b; font-size: 0.8em; white-space: nowrap; }}
  .quiz-section-container {{ margin: 12px 0 20px; padding: 0; }}
  .section-heading {{ display: flex; gap: 12px; align-items: baseline; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #cbd5e1; }}
  .section-heading h4 {{ margin: 0; font-size: 1em; }}
  .section-heading > span {{ color: #64748b; font-size: 0.85em; }}
  .quiz-question-card[open] {{ background: #fafbfc; box-shadow: none !important; }}
  .quiz-question-card[open] > summary .question-title {{ white-space: normal !important; overflow: visible !important; }}
  .quiz-question-card > summary:hover {{ background: #f8fafc; }}
  .quiz-question-card > summary:focus-visible {{ outline: 2px solid #334155; outline-offset: -2px; }}
  .quiz-question-card > summary > div:first-child {{ flex: 1 1 auto; }}
  .quiz-question-card > summary > div:last-child {{ color: #64748b; gap: 4px; }}
  .quiz-expand-btn, .quiz-edit-jump-btn, .quiz-question-source-details summary, .hotspot-mode-btn, .hotspot-editor-btn {{ box-shadow: none !important; }}
  @media(max-width: 640px) {{
    .quiz-question-card > summary {{ flex-wrap: wrap; gap: 6px; }}
    .quiz-question-card > summary > div:last-child {{ margin-left: 20px !important; }}
  }}
</style>
<div class="quiz-preview-root" data-source-hash="{html.escape(source_hash or '', quote=True)}" style="font-family: var(--font, 'Source Sans 3', 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);">
  <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid #f1f5f9;">
    <div>
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <h3 style="margin: 0; color: #0f172a; font-size: 1.25em;">{html.escape(quiz.title)}</h3>
        {f'<span title="Test and section titles do not support Markdown or math formatting and will display as raw syntax in OpenOLAT" style="display: inline-flex; align-items: center; gap: 4px; background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 4px; padding: 1px 6px; font-size: 0.72em; font-weight: 600; cursor: help;">⚠️ Markdown/Math in title</span>' if contains_markdown(quiz.title) and not has_multiple_sections else ''}
      </div>
      <span style="color: #64748b; font-size: 0.9em;">{summary_meta_text}</span>
    </div>
    <div>

      {render_expand_all_control() if show_expand_all else ""}
    </div>
  </div>
  {''.join(sections_html)}
</div>
"""


def _get_type_label(q: Question) -> str:
    if isinstance(q, InvalidQuestion) or bool(getattr(q, "errors", None)):
        return "Invalid"
    elif isinstance(q, SingleChoiceQuestion):
        return "Single Choice"
    elif isinstance(q, MultipleChoiceQuestion):
        return "Multiple Choice"
    elif isinstance(q, TrueFalseQuestion):
        return "True / False"
    elif isinstance(q, EssayQuestion):
        return "Essay / Free Text"
    elif isinstance(q, FillBlankQuestion):
        return "Fill in the Blank (Text)"
    elif isinstance(q, InlineChoiceQuestion):
        return "Fill in the Blank (Dropdown)"
    elif isinstance(q, HottextQuestion):
        return "Hottext"
    elif isinstance(q, NumericalQuestion):
        return "Numerical"
    elif isinstance(q, KprimQuestion):
        return "Kprim (Matrix)"
    elif isinstance(q, OrderQuestion):
        return "Order / Sequencing"
    elif isinstance(q, AssociationQuestion):
        return "Drag & Drop" if q.interaction == "drag" else "Match"
    elif isinstance(q, HotspotQuestion):
        return "Hotspot (MC)" if q.multiple else "Hotspot (SC)"
    return "Question"


def _render_question_body(
    q: Question,
    asset_map: Optional[Dict[str, str]] = None,
    render_math: bool = True,
    hotspot_images: Optional[Dict[str, ResolvedHotspotImage]] = None,
    question_idx: int = 1,
    source_hash: Optional[str] = None,
) -> str:
    if isinstance(q, InvalidQuestion):
        return ""

    elif isinstance(q, (SingleChoiceQuestion, MultipleChoiceQuestion, TrueFalseQuestion)):
        is_single = isinstance(q, (SingleChoiceQuestion, TrueFalseQuestion))
        bullet = "○" if is_single else "□"
        checked_bullet = "●" if is_single else "■"
        items = []
        for c in q.choices:
            icon = checked_bullet if c.is_correct else bullet
            style = "color: #16a34a; font-weight: 600;" if c.is_correct else "color: #475569;"
            tag = " (Correct)" if c.is_correct else ""
            choice_html = markdown_to_qti_xhtml(c.text, asset_map=asset_map, render_math=render_math)
            # Remove enclosing <p>...</p> tags if present to keep inline list layout
            if choice_html.startswith("<p>") and choice_html.endswith("</p>"):
                choice_html = choice_html[3:-4]
            items.append(f"<li style='margin-bottom: 6px; list-style: none; {style}'>{icon} {choice_html}{tag}</li>")
        return f"<ul style='padding-left: 4px; margin: 0;'>{''.join(items)}</ul>"

    elif isinstance(q, FillBlankQuestion):
        items = []
        for i, g in enumerate(q.gaps):
            canonical_badge = f"<code style='background: #dcfce7; color: #166534; font-weight: 600; padding: 2px 6px; border-radius: 4px; border: 1px solid #bbf7d0;'>{html.escape(g.expected_value)}</code>"
            alts_badges = "".join(
                f" <code style='background: #dcfce7; color: #166534; font-weight: 600; padding: 2px 6px; border-radius: 4px; border: 1px solid #bbf7d0;'>{html.escape(a)}</code>"
                for a in g.alternatives
            )
            items.append(f"<li style='margin-bottom: 4px;'><strong>Gap {i+1}:</strong> {canonical_badge}{alts_badges}</li>")
        return f"<ul style='padding-left: 20px; margin: 0; color: #475569;'>{''.join(items)}</ul>"

    elif isinstance(q, InlineChoiceQuestion):
        items = []
        for i, g in enumerate(q.gaps):
            opts_desc = []
            for c in g.choices:
                if c.is_correct:
                    opts_desc.append(f"<strong style='color: #166534; background: #dcfce7; padding: 1px 5px; border-radius: 3px; border: 1px solid #bbf7d0;'>{html.escape(c.text)} (Correct)</strong>")
                else:
                    opts_desc.append(f"<span style='color: #64748b;'>{html.escape(c.text)}</span>")
            shuffle_note = " <em>[shuffled]</em>" if g.shuffle else ""
            items.append(f"<li style='margin-bottom: 6px;'><strong>Dropdown {i+1}{shuffle_note}:</strong> {' | '.join(opts_desc)}</li>")
        return f"<ul style='padding-left: 20px; margin: 0; font-size: 0.95em;'>{''.join(items)}</ul>"

    elif isinstance(q, HottextQuestion):
        items = []
        for item in q.items:
            it_html = markdown_to_qti_xhtml(item.text, asset_map=asset_map, render_math=render_math)
            if it_html.startswith("<p>") and it_html.endswith("</p>"):
                it_html = it_html[3:-4]
            if item.is_correct:
                items.append(f"<li style='margin-bottom: 4px;'><strong style='color: #166534; background: #dcfce7; padding: 1px 6px; border-radius: 3px; border: 1px solid #bbf7d0;'>{it_html} (Correct)</strong></li>")
            else:
                items.append(f"<li style='margin-bottom: 4px; color: #64748b;'>{it_html} <span style='font-size: 0.85em;'>(Incorrect)</span></li>")
        scoring_desc = f" <span style='color: #64748b; font-size: 0.9em;'>(Scoring: {html.escape(q.scoring)})</span>" if q.scoring else ""
        return f"<div style='font-size: 0.9em; margin-bottom: 4px; font-weight: 600; color: #475569;'>Selectable Hottext Spans{scoring_desc}:</div><ul style='padding-left: 20px; margin: 0; font-size: 0.95em;'>{''.join(items)}</ul>"

    elif isinstance(q, NumericalQuestion):
        tol_str = f" ± {q.tolerance}" if q.tolerance > 0 else ""
        return f"<div style='color: #475569;'><strong>Expected Answer:</strong> <code style='background: #dcfce7; color: #166534; font-weight: 600; padding: 2px 6px; border-radius: 4px; border: 1px solid #bbf7d0;'>{q.answer}{tol_str}</code></div>"

    elif isinstance(q, EssayQuestion):
        return "<div style='color: #64748b; font-style: italic; background: #f8fafc; padding: 8px 12px; border-radius: 4px;'>[Open text response area for learner]</div>"

    elif isinstance(q, KprimQuestion):
        rows = []
        for stmt in q.statements:
            symbol = "<span style='color: #16a34a; font-weight: bold;'>[+] True</span>" if stmt.is_correct else "<span style='color: #dc2626; font-weight: bold;'>[-] False</span>"
            stmt_html = markdown_to_qti_xhtml(stmt.text, asset_map=asset_map, render_math=render_math)
            if stmt_html.startswith("<p>") and stmt_html.endswith("</p>"):
                stmt_html = stmt_html[3:-4]
            rows.append(f"<tr><td style='padding: 6px 12px; border: 1px solid #e2e8f0;'>{stmt_html}</td><td style='padding: 6px 12px; border: 1px solid #e2e8f0; text-align: center;'>{symbol}</td></tr>")
        return f"<table style='width: 100%; border-collapse: collapse; font-size: 0.9em;'><tr style='background: #f8fafc;'><th style='padding: 6px 12px; border: 1px solid #e2e8f0; text-align: left;'>Statement</th><th style='padding: 6px 12px; border: 1px solid #e2e8f0; width: 100px;'>Key</th></tr>{''.join(rows)}</table>"

    elif isinstance(q, OrderQuestion):
        items = []
        for it in q.items:
            it_html = markdown_to_qti_xhtml(it.text, asset_map=asset_map, render_math=render_math)
            if it_html.startswith("<p>") and it_html.endswith("</p>"):
                it_html = it_html[3:-4]
            items.append(f"<li>{it_html}</li>")
        return f"<ol class='order-answer'>{''.join(items)}</ol>"

    elif isinstance(q, AssociationQuestion):
        target_map = {t.identifier: t for t in q.targets}
        if q.interaction == "match":
            # Render a 2D matrix table with items as rows and targets as columns
            th_cells = ["<th style='padding: 6px 12px; border: 1px solid #cbd5e1; background: #f8fafc; text-align: left;'>Item</th>"]
            for t in q.targets:
                t_html = markdown_to_qti_xhtml(t.text, asset_map=asset_map, render_math=render_math)
                if t_html.startswith("<p>") and t_html.endswith("</p>"):
                    t_html = t_html[3:-4]
                th_cells.append(f"<th style='padding: 6px 12px; border: 1px solid #cbd5e1; background: #f8fafc; text-align: center;'>{t_html}</th>")
            thead = f"<tr>{''.join(th_cells)}</tr>"

            tr_rows = []
            symbol_on = "■" if q.multiple else "●"
            symbol_off = "□" if q.multiple else "○"

            for item in q.items:
                td_cells = []
                it_html = markdown_to_qti_xhtml(item.text, asset_map=asset_map, render_math=render_math)
                if it_html.startswith("<p>") and it_html.endswith("</p>"):
                    it_html = it_html[3:-4]
                td_cells.append(f"<td style='padding: 6px 12px; border: 1px solid #e2e8f0; font-weight: 500;'>{it_html}</td>")
                for t in q.targets:
                    is_assoc = t.identifier in item.target_ids
                    icon = f"<span style='color: #16a34a; font-weight: bold;'>{symbol_on}</span>" if is_assoc else f"<span style='color: #94a3b8;'>{symbol_off}</span>"
                    td_cells.append(f"<td style='padding: 6px 12px; border: 1px solid #e2e8f0; text-align: center;'>{icon}</td>")
                tr_rows.append(f"<tr>{''.join(td_cells)}</tr>")

            tbody = "\n".join(tr_rows)
            type_mode = "Multiple Choice" if q.multiple else "Single Choice"
            scoring_str = f", Scoring: {q.scoring}" if q.scoring else ""
            table_info = f"<div style='font-size: 0.85em; color: #64748b; margin-bottom: 6px;'>Matrix ({type_mode}{scoring_str})</div>"
            return f"{table_info}<table style='width: 100%; border-collapse: collapse; font-size: 0.9em;'>{thead}\n{tbody}</table>"

        else:
            # Drag & Drop preview: show target categories as containers with associated draggable items
            cards = []
            # Group items by target
            target_to_items: Dict[str, List[str]] = {t.identifier: [] for t in q.targets}
            for item in q.items:
                it_html = markdown_to_qti_xhtml(item.text, asset_map=asset_map, render_math=render_math)
                if it_html.startswith("<p>") and it_html.endswith("</p>"):
                    it_html = it_html[3:-4]
                for tid in item.target_ids:
                    if tid in target_to_items:
                        target_to_items[tid].append(it_html)

            for t in q.targets:
                t_html = markdown_to_qti_xhtml(t.text, asset_map=asset_map, render_math=render_math)
                if t_html.startswith("<p>") and t_html.endswith("</p>"):
                    t_html = t_html[3:-4]
                assigned_items = target_to_items.get(t.identifier, [])
                items_pills = "".join(
                    f"<span style='display: inline-block; background: #e0e7ff; color: #3730a3; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; font-weight: 500; margin: 2px 4px 2px 0; border: 1px solid #c7d2fe;'>{it}</span>"
                    for it in assigned_items
                ) or "<span style='color: #94a3b8; font-style: italic; font-size: 0.85em;'>No items</span>"
                cards.append(
                    f"<div style='background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 8px 12px; margin-bottom: 8px;'>"
                    f"<div style='font-weight: 600; color: #1e293b; margin-bottom: 4px; font-size: 0.9em;'>{t_html}:</div>"
                    f"<div>{items_pills}</div>"
                    f"</div>"
                )

            type_mode = "Multiple Choice" if q.multiple else "Single Choice"
            scoring_str = f", Scoring: {q.scoring}" if q.scoring else ""
            desc = f"<div style='font-size: 0.85em; color: #64748b; margin-bottom: 6px;'>Drag & Drop Categories ({type_mode}{scoring_str}):</div>"
            return f"{desc}{''.join(cards)}"

    elif isinstance(q, HotspotQuestion):
        return _render_hotspot_preview(
            q,
            asset_map=asset_map,
            hotspot_images=hotspot_images,
            question_idx=question_idx,
            source_hash=source_hash,
        )

    return ""


def _resolve_preview_hotspot_dimensions(
    q: HotspotQuestion,
    target_src: str,
    hotspot_images: Optional[Dict[str, ResolvedHotspotImage]] = None,
) -> Tuple[int, int, bool]:
    """Return (width, height, is_resolved_image) for a HotspotQuestion preview."""
    if hotspot_images and q.identifier in hotspot_images:
        resolved = hotspot_images[q.identifier]
        if resolved.width > 0 and resolved.height > 0:
            return resolved.width, resolved.height, True

    if target_src.startswith("data:image/") and ";base64," in target_src:
        try:
            _, b64_payload = target_src.split(";base64,", 1)
            raw_bytes = base64.b64decode(b64_payload)
            mime_info = _detect_image_mime(raw_bytes)
            if mime_info:
                dims = _extract_image_dimensions(raw_bytes, mime_info[0])
                if dims and dims[0] > 0 and dims[1] > 0:
                    return dims[0], dims[1], True
        except Exception:
            pass

    # Provisional coordinate-grid dimensions when image bytes are not yet loaded
    if q.declared_width and q.declared_height and q.declared_width > 0 and q.declared_height > 0:
        return q.declared_width, q.declared_height, False

    max_px_x = 0.0
    max_px_y = 0.0
    for r in q.regions:
        if r.unit == "px":
            if r.shape == "rect" and len(r.coordinates) == 4:
                max_px_x = max(max_px_x, r.coordinates[2])
                max_px_y = max(max_px_y, r.coordinates[3])
            elif r.shape == "circle" and len(r.coordinates) == 3:
                max_px_x = max(max_px_x, r.coordinates[0] + r.coordinates[2])
                max_px_y = max(max_px_y, r.coordinates[1] + r.coordinates[2])
    if max_px_x > 0 or max_px_y > 0:
        return max(800, int(max_px_x * 1.15)), max(600, int(max_px_y * 1.15)), False

    return 800, 600, False


def _render_hotspot_preview(
    q: HotspotQuestion,
    asset_map: Optional[Dict[str, str]] = None,
    hotspot_images: Optional[Dict[str, ResolvedHotspotImage]] = None,
    question_idx: int = 1,
    source_hash: Optional[str] = None,
) -> str:
    """Render Milestone 2 responsive SVG overlay preview with Author/Learner View toggle and Milestone 3 Visual Editor."""
    target_src = asset_map.get(q.image_src, q.image_src) if asset_map else q.image_src
    img_w, img_h, is_resolved = _resolve_preview_hotspot_dimensions(
        q, target_src=target_src, hotspot_images=hotspot_images
    )

    short_dim = max(100, min(img_w, img_h))
    stroke_w = max(2.0, round(short_dim * 0.0055, 1))
    badge_r = max(11.0, round(short_dim * 0.028, 1))
    font_sz = max(10.5, round(short_dim * 0.025, 1))

    # Inline JS snippets for hover linking, mode switching, learner click simulation, and editor dispatch
    hover_in_js = (
        "var w=this.closest('.hotspot-preview-widget');"
        "var idx=this.getAttribute('data-region-idx');"
        "if(w&&idx){w.querySelectorAll('[data-region-idx=\"'+idx+'\"]').forEach(function(el){el.setAttribute('data-highlighted','1');});}"
    )
    hover_out_js = (
        "var w=this.closest('.hotspot-preview-widget');"
        "var idx=this.getAttribute('data-region-idx');"
        "if(w&&idx){w.querySelectorAll('[data-region-idx=\"'+idx+'\"]').forEach(function(el){el.removeAttribute('data-highlighted');});}"
    )
    region_click_js = (
        "var w=this.closest('.hotspot-preview-widget');"
        "if(!w)return;"
        "var mode=w.getAttribute('data-view-mode');"
        "if(mode==='learner'){"
        "var mult=w.getAttribute('data-multiple')==='1';"
        "var cur=this.getAttribute('data-learner-selected')==='1';"
        "if(!mult){w.querySelectorAll('.hotspot-region-group').forEach(function(g){g.setAttribute('data-learner-selected','0');});}"
        "this.setAttribute('data-learner-selected',cur&&mult?'0':'1');"
        "var sel=Array.from(w.querySelectorAll('.hotspot-region-group[data-learner-selected=\"1\"]')).map(function(g){return '#'+g.getAttribute('data-region-idx');});"
        "var statusEl=w.querySelector('.hotspot-learner-status');"
        "if(statusEl){statusEl.textContent=sel.length?'Selected region(s): '+sel.join(', '):'Click a region on the image to simulate learner selection.';}"
        "}else if(mode==='editor'){"
        "var rIdx=this.getAttribute('data-region-idx');"
        "if(window.selectHotspotRegion){window.selectHotspotRegion(w,parseInt(rIdx,10));}"
        "}"
    )
    mode_btn_js = (
        "var w=this.closest('.hotspot-preview-widget');"
        "var mode=this.getAttribute('data-mode');"
        "if(w&&mode){"
        "w.setAttribute('data-view-mode',mode);"
        "if(mode==='author'){"
        "w.querySelectorAll('.hotspot-region-group').forEach(function(g){g.setAttribute('data-learner-selected','0');});"
        "var statusEl=w.querySelector('.hotspot-learner-status');"
        "if(statusEl){statusEl.textContent='Click a region on the image to simulate learner selection.';}"
        "}else if(mode==='editor'){"
        "if(window.initHotspotEditor){window.initHotspotEditor(w);}"
        "}"
        "}"
    )

    svg_elements: List[str] = []

    if not is_resolved:
        # Draw provisional coordinate grid background & guide lines
        grid_font = max(11.0, round(short_dim * 0.022, 1))
        svg_elements.append(
            f"<rect x='0' y='0' width='{img_w}' height='{img_h}' fill='#f8fafc' />"
        )
        for pct in (25, 50, 75):
            gx = round(img_w * (pct / 100.0), 1)
            gy = round(img_h * (pct / 100.0), 1)
            dash = "6,4" if pct != 50 else "none"
            color = "#cbd5e1" if pct == 50 else "#e2e8f0"
            svg_elements.append(
                f"<line x1='{gx}' y1='0' x2='{gx}' y2='{img_h}' stroke='{color}' stroke-width='1.5' stroke-dasharray='{dash}' />"
                f"<line x1='0' y1='{gy}' x2='{img_w}' y2='{gy}' stroke='{color}' stroke-width='1.5' stroke-dasharray='{dash}' />"
                f"<text x='{gx + 4}' y='{grid_font + 4}' fill='#94a3b8' font-size='{grid_font}' font-family='ui-monospace, monospace'>{pct}%</text>"
                f"<text x='6' y='{gy - 4}' fill='#94a3b8' font-size='{grid_font}' font-family='ui-monospace, monospace'>{pct}%</text>"
            )

    bullet = "□" if q.multiple else "○"
    checked_bullet = "■" if q.multiple else "●"
    reg_items: List[str] = []

    for idx, r in enumerate(q.regions, start=1):
        px_coords = r.resolve_pixel_coords(img_w, img_h)
        correct_flag = "1" if r.correct else "0"
        badge_fill = "#16a34a" if r.correct else "#dc2626"

        shape_svg = ""
        bx, by = 0.0, 0.0
        if r.shape == "rect" and len(px_coords) == 4:
            x1, y1, x2, y2 = px_coords
            rw = max(1, x2 - x1)
            rh = max(1, y2 - y1)
            shape_svg = (
                f"<rect class='hotspot-shape' x='{x1}' y='{y1}' width='{rw}' height='{rh}' "
                f"stroke-width='{stroke_w}' rx='2' />"
            )
            bx = min(float(img_w) - badge_r - 2, max(badge_r + 2, float(x1) + badge_r + 4))
            by = min(float(img_h) - badge_r - 2, max(badge_r + 2, float(y1) + badge_r + 4))
        elif r.shape == "circle" and len(px_coords) == 3:
            cx, cy, rad = px_coords
            shape_svg = (
                f"<circle class='hotspot-shape' cx='{cx}' cy='{cy}' r='{max(1, rad)}' "
                f"stroke-width='{stroke_w}' />"
            )
            bx = min(float(img_w) - badge_r - 2, max(badge_r + 2, float(cx)))
            by = min(float(img_h) - badge_r - 2, max(badge_r + 2, float(cy)))

        badge_svg = (
            f"<g class='hotspot-author-badge' style='pointer-events: none;'>"
            f"<circle cx='{bx:.1f}' cy='{by:.1f}' r='{badge_r}' fill='{badge_fill}' stroke='#ffffff' stroke-width='1.5' />"
            f"<text x='{bx:.1f}' y='{by:.1f}' fill='#ffffff' font-size='{font_sz}' font-weight='700' "
            f"font-family='system-ui, -apple-system, sans-serif' text-anchor='middle' dominant-baseline='central'>#{idx}</text>"
            f"</g>"
        )

        px_raw_str = ",".join(str(c) for c in px_coords)
        svg_title = f"<title>Hotspot #{idx} ({r.shape.capitalize()}, {'Correct' if r.correct else 'Distractor'}) — Click to edit</title>"
        svg_elements.append(
            f"<g class='hotspot-region-group' data-region-idx='{idx}' "
            f"data-region-id='{html.escape(r.identifier, quote=True)}' "
            f"data-shape='{r.shape}' data-unit='{r.unit}' "
            f"data-px-coords='{px_raw_str}' "
            f"data-correct='{correct_flag}' data-learner-selected='0' data-selected='0' "
            f"onmouseenter=\"{hover_in_js}\" onmouseleave=\"{hover_out_js}\" onclick=\"{region_click_js}\">"
            f"{svg_title}{shape_svg}{badge_svg}</g>"
        )

        # Build Author View legend row
        icon = checked_bullet if r.correct else bullet
        style = "color: #16a34a; font-weight: 600;" if r.correct else "color: #475569;"
        unit_suffix = "%" if r.unit == "pct" else ""
        coords_fmt = ", ".join(f"{int(c) if c == int(c) else c}{unit_suffix}" for c in r.coordinates)
        px_fmt = ", ".join(str(c) for c in px_coords)
        px_part = f" <span style='color: #64748b; font-weight: 400; font-size: 0.9em;'>&rarr; ({px_fmt}) px</span>"
        label_part = f" — {html.escape(r.author_label)}" if r.author_label else ""
        tag = " (Correct)" if r.correct else ""
        legend_click_js = (
            "var w=this.closest('.hotspot-preview-widget');"
            f"if(w){{w.setAttribute('data-view-mode','editor');"
            f"if(window.selectHotspotRegion){{window.selectHotspotRegion(w,{idx});}}}}"
        )
        reg_items.append(
            f"<li class='hotspot-legend-item' data-region-idx='{idx}' "
            f"style='margin-bottom: 4px; list-style: none; cursor: pointer; {style}' "
            f"title='Click to select and edit hotspot #{idx} ({r.shape}, {'Correct' if r.correct else 'Distractor'})' "
            f"onclick=\"{legend_click_js}\" "
            f"onmouseenter=\"{hover_in_js}\" onmouseleave=\"{hover_out_js}\">"
            f"{icon} <code>#{idx} ({html.escape(r.identifier)})</code>: "
            f"<code>{html.escape(r.shape)}({coords_fmt})</code>{px_part}{label_part}{tag}</li>"
        )

    region_pills = []
    for p_idx, pr in enumerate(q.regions, start=1):
        p_sym = "✓" if pr.correct else "○"
        p_col = "#16a34a" if pr.correct else "#dc2626"
        p_type = "Correct" if pr.correct else "Distractor"
        p_title = f"Select #{p_idx} ({pr.identifier}): {pr.shape.capitalize()} [{p_type}] - Click to edit on canvas"
        region_pills.append(
            f"<button type='button' class='hotspot-region-pill' data-region-idx='{p_idx}' "
            f"title='{html.escape(p_title, quote=True)}' "
            f"onclick=\"var w=this.closest('.hotspot-preview-widget'); if(w&&window.selectHotspotRegion){{window.selectHotspotRegion(w, {p_idx});}}\">"
            f"<span>#{p_idx}</span> "
            f"<span style='color: {p_col}; font-weight: 700;'>{p_sym}</span>"
            f"</button>"
        )
    region_pills_html = "".join(region_pills)

    provisional_banner = ""
    if not is_resolved:
        provisional_banner = (
            f"<div class='hotspot-provisional-banner' style='background: #fffbeb; border: 1px solid #fcd34d; "
            f"border-left: 4px solid #f59e0b; border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; "
            f"font-size: 0.86em; color: #92400e; line-height: 1.45;'>"
            f"<strong>⚠️ Provisional Coordinate-Grid Preview:</strong> Background image "
            f"<code>{html.escape(q.image_src)}</code> is not loaded in the Media workspace. "
            f"Regions are shown on a provisional {img_w}&times;{img_h} reference grid; "
            f"QTI package export requires packaging the real image."
            f"</div>"
        )

    mode_desc = f"Multiple Choice (Scoring: {html.escape(q.scoring)})" if q.multiple else "Single Choice"
    dim_badge = (
        f"{img_w} &times; {img_h} px"
        if is_resolved
        else f"Provisional Grid ({img_w} &times; {img_h})"
    )

    toolbar_html = (
        f"<div class='hotspot-toolbar'>"
        f"<div style='color: #475569; font-weight: 500;'>"
        f"<span title='Hotspot reference dimensions'>{dim_badge}</span> &bull; <span title='Hotspot interaction and scoring mode'>{mode_desc}</span>"
        f"</div>"
        f"<div class='hotspot-mode-toggle' role='group' aria-label='Hotspot preview mode'>"
        f"<button type='button' class='hotspot-mode-btn' data-mode='author' title='Author View: Inspect correct hotspots, distractors, and coordinate labels' onclick=\"{mode_btn_js}\">{ui_icon('eye')} Author View</button>"
        f"<button type='button' class='hotspot-mode-btn' data-mode='learner' title='Learner View: Simulate learner click selection and response validation' onclick=\"{mode_btn_js}\">{ui_icon('learner')} Learner View</button>"
        f"<button type='button' class='hotspot-mode-btn' data-mode='editor' title='Visual Hotspot Editor: Drag to move, resize with corner handles, or add/delete shapes' onclick=\"{mode_btn_js}\">{ui_icon('edit')} Edit Hotspots</button>"
        f"</div>"
        f"</div>"
    )

    editor_controls_html = (
        f"<div class='hotspot-editor-controls' style='background: #f8fafc; border: 1px solid #cbd5e1; "
        f"border-radius: 6px; padding: 6px 10px; margin-bottom: 8px; font-size: 0.85em; display: flex; "
        f"flex-direction: column; gap: 6px;'>"
        f"<div style='display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px;'>"
        f"<div style='display: flex; align-items: center; gap: 6px;'>"
        f"<span style='font-weight: 600; color: #334155; font-size: 0.9em;'>Visual editor:</span> "
        f"<button type='button' class='hotspot-editor-btn' title='Add a new rectangular hotspot region to the canvas' onclick=\"if(window.addHotspotShape){{window.addHotspotShape(this.closest('.hotspot-preview-widget'), 'rect');}}\">{ui_icon('plus')} Add rectangle</button>"
        f"<button type='button' class='hotspot-editor-btn' title='Add a new circular hotspot region to the canvas' onclick=\"if(window.addHotspotShape){{window.addHotspotShape(this.closest('.hotspot-preview-widget'), 'circle');}}\">{ui_icon('plus')} Add circle</button>"
        f"</div>"
        f"<div class='hotspot-editor-region-bar' style='display: flex; align-items: center; gap: 6px;'>"
        f"<span class='hotspot-editor-sel-info' style='color: #64748b; font-style: italic; font-size: 0.9em;' title='Click any shape, toolbar pill, or legend item to select'>Click a shape, pill, or legend item to edit</span>"
        f"<button type='button' class='hotspot-editor-btn hotspot-editor-btn-correct' style='display:none;' title='Toggle whether this region is a correct answer or distractor' onclick=\"if(window.toggleSelectedCorrectness){{window.toggleSelectedCorrectness(this.closest('.hotspot-preview-widget'));}}\">✓ Toggle Correct</button>"
        f"<button type='button' class='hotspot-editor-btn hotspot-editor-btn-danger' style='display:none;' title='Delete the selected hotspot region' onclick=\"if(window.deleteSelectedRegion){{window.deleteSelectedRegion(this.closest('.hotspot-preview-widget'));}}\">{ui_icon('trash')} Delete</button>"
        f"</div>"
        f"</div>"
        f"<div style='display: flex; align-items: center; gap: 6px; flex-wrap: wrap; padding-top: 5px; border-top: 1px dashed #bbf7d0;'>"
        f"<span style='font-weight: 600; color: #334155; font-size: 0.84em;'>Hotspots:</span>"
        f"{region_pills_html}"
        f"</div>"
        f"</div>"
    )

    if is_resolved:
        stage_html = (
            f"<div class='hotspot-canvas-stage' style='margin-bottom: 10px;'>"
            f"<img class='hotspot-bg-image' src='{html.escape(target_src, quote=True)}' "
            f"alt='{html.escape(q.image_alt, quote=True)}' width='{img_w}' height='{img_h}' />"
            f"<svg class='hotspot-overlay-svg' viewBox='0 0 {img_w} {img_h}' preserveAspectRatio='xMidYMid meet'>"
            f"{''.join(svg_elements)}"
            f"</svg>"
            f"</div>"
        )
    else:
        stage_html = (
            f"<div style='margin-bottom: 10px;'>"
            f"<svg class='hotspot-overlay-svg hotspot-provisional-svg' viewBox='0 0 {img_w} {img_h}' preserveAspectRatio='xMidYMid meet'>"
            f"{''.join(svg_elements)}"
            f"</svg>"
            f"</div>"
        )

    learner_bar_html = (
        f"<div class='hotspot-learner-bar' style='background: #eff6ff; border: 1px solid #bfdbfe; "
        f"border-radius: 6px; padding: 6px 10px; margin-bottom: 8px; font-size: 0.86em; color: #1e40af;'>"
        f"🖱️ <span class='hotspot-learner-status'>Click a region on the image to simulate learner selection.</span>"
        f"</div>"
    )

    legend_html = (
        f"<ul class='hotspot-author-legend' style='padding-left: 4px; margin: 0;'>"
        f"{''.join(reg_items)}"
        f"</ul>"
    )

    safe_hash = html.escape(source_hash or "", quote=True)
    return (
        f"<div class='hotspot-preview-widget' data-view-mode='author' data-multiple='{1 if q.multiple else 0}' "
        f"data-question-idx='{question_idx}' data-img-w='{img_w}' data-img-h='{img_h}' "
        f"data-source-hash='{safe_hash}'>"
        f"{provisional_banner}"
        f"{toolbar_html}"
        f"{editor_controls_html}"
        f"{stage_html}"
        f"{learner_bar_html}"
        f"{legend_html}"
        f"</div>"
    )
