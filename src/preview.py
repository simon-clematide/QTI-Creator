"""HTML preview generator for QuizMD."""

import html
import json
import re
from src.model import (
    AssociationQuestion,
    Choice,
    EssayQuestion,
    FillBlankQuestion,
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


from typing import Dict, Optional
from src.markdown import contains_markdown, extract_hottexts, markdown_to_qti_xhtml, RE_DROPDOWN_GAP



def render_quiz_preview_html(
    quiz: Quiz,
    asset_map: Optional[Dict[str, str]] = None,
    render_math: bool = True,
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

    has_multiple_sections = len(quiz.sections) > 1 or (
        len(quiz.sections) == 1 and bool(quiz.sections[0].description)
    )

    sections_html = []
    global_idx = 1

    for s_idx, sec in enumerate(quiz.sections, start=1):
        sec_cards = []
        for q in sec.questions:
            type_name = _get_type_label(q)
            badge_color = _get_badge_color(q)

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
            # Render the raw title in full at the top of the body so users can read the entire title even when truncated in the summary.
            has_title_md = contains_markdown(q.title)
            q_title_warning = ""
            if has_title_md:
                q_title_warning = (
                    f" <span title=\"Question titles do not support Markdown or math formatting and will display as raw syntax in OpenOLAT (e.g. '{html.escape(q.title)}')\" "
                    f"style=\"display: inline-flex; align-items: center; gap: 4px; background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 4px; padding: 1px 6px; font-size: 0.72em; font-weight: 600; cursor: help;\">"
                    f"⚠️ Markdown/Math in title</span>"
                )
            question_title_html = f"<div style='font-size: 1.05em; font-weight: 600; color: #0f172a; margin-bottom: 8px; line-height: 1.4;'>{html.escape(q.title)}{q_title_warning}</div>"

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

            else:
                prompt_html = (
                    f"<div style='color: #334155; margin-bottom: 12px; line-height: 1.5;'>{markdown_to_qti_xhtml(q.prompt, asset_map=asset_map, render_math=render_math)}</div>"
                    if (has_distinct_prompt or is_invalid)
                    else ""
                )

            body_html = _render_question_body(q, asset_map=asset_map, render_math=render_math)
            hint_html = (
                f"<details style='margin-top: 10px; padding: 8px 12px; background: #fffbeb; border-left: 3px solid #f59e0b; font-size: 0.9em; border-radius: 4px; color: #92400e; cursor: pointer;'>"
                f"<summary style='font-weight: 600; outline: none;'>💡 Hint</summary>"
                f"<div style='margin-top: 6px; color: #78350f;'>{markdown_to_qti_xhtml(q.hint, asset_map=asset_map, render_math=render_math)}</div></details>"
                if q.hint
                else ""
            )
            feedback_html = (
                f"<div style='margin-top: 10px; padding: 8px 12px; background: #f0fdf4; border-left: 3px solid #22c55e; font-size: 0.9em; border-radius: 4px;'>"
                f"<strong>Feedback:</strong> {markdown_to_qti_xhtml(q.feedback, asset_map=asset_map, render_math=render_math)}</div>"
                if q.feedback
                else ""
            )

            status_badges = []
            if is_invalid:
                status_badges.append('<span title="Validation error" style="cursor: help; font-size: 0.95em;">⚠️</span>')
            elif has_title_md:
                status_badges.append(f'<span title="Question title contains Markdown or math syntax" style="cursor: help; font-size: 0.95em;">⚠️</span>')
            if q.hint and q.hint.strip():
                status_badges.append('<span title="Hint available" style="cursor: help; font-size: 0.95em;">💡</span>')
            if q.feedback and q.feedback.strip():
                status_badges.append('<span title="Feedback available" style="cursor: help; font-size: 0.95em;">💬</span>')
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
      <summary>
        <span>Markdown</span>
      </summary>
      <pre style="margin-top: 8px; margin-bottom: 0; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 12px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.88em; overflow-x: auto; white-space: pre-wrap; word-break: break-word; color: #1e293b;"><code>{html.escape(raw_src.strip())}</code></pre>
    </details>
    <button type="button" class="quiz-edit-jump-btn" title="Jump to this question in QuizMD editor" data-line="{line_no}" data-title="{escaped_title_attr}" onclick="var l = parseInt(this.getAttribute('data-line'), 10); var t = this.getAttribute('data-title'); var fn = window.quizJumpToLine || (window.parent && window.parent.quizJumpToLine); if (typeof fn === 'function') {{ fn(l, t); }} else if (window.parent &amp;&amp; window.parent.postMessage) {{ window.parent.postMessage({{action: 'quiz-jump', line: l, title: t}}, '*'); }}">
      ✏️ Edit
    </button>
  </div>
</div>
"""

            card_border_style = "border: 1px solid #f87171;" if is_invalid else "border: 1px solid #e2e8f0;"
            card = f"""
<details class="quiz-question-card" style="background: white; {card_border_style} border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); transition: border-color 0.2s;">
  <summary style="display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; cursor: pointer; user-select: none; list-style: none;">
    <div style="display: flex; align-items: center; gap: 8px; flex-1; min-width: 0;">
      <span class="quiz-chevron" style="display: inline-block; font-size: 0.8em; color: #64748b; transition: transform 0.2s;">▶</span>
      <span style="font-weight: 600; font-size: 1.05em; color: #1e293b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{global_idx}. {html.escape(q.title)}</span>
    </div>
    <div style="display: flex; align-items: center; flex-shrink: 0; margin-left: 12px;">
      <span style="background: {badge_color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.78em; font-weight: 500; margin-right: 6px;">{type_name}</span>
      {status_badges_html}
      <span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 12px; font-size: 0.78em; font-weight: 600;">{q.points} pt</span>
    </div>
  </summary>
  <div style="padding: 12px 16px 16px 16px; border-top: 1px solid #f1f5f9;">
    {validation_alert_html}
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
        if has_multiple_sections:
            sec_points = sum(q.points for q in sec.questions)
            sec_hints = sum(1 for q in sec.questions if q.hint and q.hint.strip())
            sec_feedbacks = sum(1 for q in sec.questions if q.feedback and q.feedback.strip())

            sec_summary_parts = [f"{len(sec.questions)} Qs"]
            if sec_hints > 0:
                sec_summary_parts.append(f"💡 {sec_hints}")
            if sec_feedbacks > 0:
                sec_summary_parts.append(f"💬 {sec_feedbacks}")
            sec_summary_parts.append(f"{sec_points} pt")
            sec_summary_text = " &bull; ".join(sec_summary_parts)

            desc_html = (
                f"<details class=\"quiz-section-desc-details\" open style=\"margin-bottom: 12px;\">"
                f"<summary style=\"display: inline-flex; align-items: center; gap: 6px; font-size: 0.85em; font-weight: 600; color: #475569; cursor: pointer; user-select: none; margin-bottom: 6px; list-style: none; outline: none;\">"
                f"<span class=\"quiz-desc-chevron\" style=\"display: inline-block; font-size: 0.75em; color: #94a3b8; transition: transform 0.2s;\">▼</span>"
                f"<span>Section Description / Instructions</span>"
                f"</summary>"
                f"<div style='color: #475569; font-size: 0.92em; line-height: 1.5; padding: 6px 10px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; margin-top: 2px;'>{markdown_to_qti_xhtml(sec.description, asset_map=asset_map, render_math=render_math)}</div>"
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

            sec_header = f"""
<div class="quiz-section-container" style="margin-top: {('20px' if s_idx > 1 else '6px')}; margin-bottom: 16px; padding: 14px 16px 8px 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;">
  <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px;">
    <h4 style="margin: 0; color: #1e293b; font-size: 1.1em; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
      <span>📁</span> <span>{html.escape(sec.title)}</span> {md_warning_badge}
    </h4>
    <span style="color: #64748b; font-size: 0.85em; font-weight: 500; white-space: nowrap; margin-left: 12px;">{sec_summary_text}</span>
  </div>
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

    summary_meta = [f"{total_questions} Question(s) parsed"]
    if len(quiz.sections) > 1:
        summary_meta[0] += f" across {len(quiz.sections)} section(s)"
    if total_hints > 0:
        summary_meta.append(f"💡 {total_hints} hint{'s' if total_hints != 1 else ''}")
    if total_feedbacks > 0:
        summary_meta.append(f"💬 {total_feedbacks} feedback{'s' if total_feedbacks != 1 else ''}")
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
    color: #475569;
    font-weight: 500;
    cursor: pointer;
    user-select: none;
    list-style: none;
    outline: none;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.82em;
    line-height: 1.4;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }}
  .quiz-question-source-details summary:hover {{ background: #f1f5f9; color: #0f172a; border-color: #94a3b8; }}
  .quiz-edit-jump-btn {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    color: #475569;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.82em;
    line-height: 1.4;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    user-select: none;
    outline: none;
    white-space: nowrap;
  }}
  .quiz-edit-jump-btn:hover {{
    background: #e0f2fe;
    color: #0369a1;
    border-color: #7dd3fc;
  }}
  .quiz-expand-btn {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    color: #475569;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.82em;
    line-height: 1.4;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }}
  .quiz-expand-btn:hover {{
    background: #f1f5f9;
    color: #1e293b;
    border-color: #94a3b8;
  }}
</style>
<div style="font-family: system-ui, -apple-system, sans-serif;">
  <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid #f1f5f9;">
    <div>
      <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <h3 style="margin: 0; color: #0f172a; font-size: 1.25em;">{html.escape(quiz.title)}</h3>
        {f'<span title="Test and section titles do not support Markdown or math formatting and will display as raw syntax in OpenOLAT" style="display: inline-flex; align-items: center; gap: 4px; background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 4px; padding: 1px 6px; font-size: 0.72em; font-weight: 600; cursor: help;">⚠️ Markdown/Math in title</span>' if contains_markdown(quiz.title) and not has_multiple_sections else ''}
      </div>
      <span style="color: #64748b; font-size: 0.9em;">{summary_meta_text}</span>
    </div>
    <div>

      <button type="button" class="quiz-expand-btn" onclick="
        var items = document.querySelectorAll('.quiz-question-card, .quiz-section-desc-details');
        var anyClosed = Array.from(items).some(c => !c.open);
        items.forEach(c => c.open = anyClosed);
        this.innerHTML = anyClosed ? '▼ Collapse All' : '▶ Expand All';
      ">▶ Expand All</button>
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
        return "Fill-in-the-Blank"
    elif isinstance(q, InlineChoiceQuestion):
        return "Inline Choice"
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
    return "Question"


def _get_badge_color(q: Question) -> str:
    if isinstance(q, InvalidQuestion) or bool(getattr(q, "errors", None)):
        return "#ef4444"  # Red
    elif isinstance(q, SingleChoiceQuestion):
        return "#3b82f6"  # Blue
    elif isinstance(q, MultipleChoiceQuestion):
        return "#8b5cf6"  # Purple
    elif isinstance(q, TrueFalseQuestion):
        return "#06b6d4"  # Cyan
    elif isinstance(q, EssayQuestion):
        return "#f59e0b"  # Amber
    elif isinstance(q, FillBlankQuestion):
        return "#10b981"  # Emerald
    elif isinstance(q, InlineChoiceQuestion):
        return "#0d9488"  # Teal
    elif isinstance(q, HottextQuestion):
        return "#d97706"  # Amber/Ochre
    elif isinstance(q, NumericalQuestion):
        return "#ec4899"  # Pink
    elif isinstance(q, KprimQuestion):
        return "#6366f1"  # Indigo
    elif isinstance(q, OrderQuestion):
        return "#0ea5e9"  # Sky
    elif isinstance(q, AssociationQuestion):
        return "#8b5cf6" if q.interaction == "drag" else "#2563eb"
    return "#64748b"


def _render_question_body(
    q: Question,
    asset_map: Optional[Dict[str, str]] = None,
    render_math: bool = True,
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
                    f"<div style='font-weight: 600; color: #1e293b; margin-bottom: 4px; font-size: 0.9em;'>📂 {t_html}:</div>"
                    f"<div>{items_pills}</div>"
                    f"</div>"
                )

            type_mode = "Multiple Choice" if q.multiple else "Single Choice"
            scoring_str = f", Scoring: {q.scoring}" if q.scoring else ""
            desc = f"<div style='font-size: 0.85em; color: #64748b; margin-bottom: 6px;'>Drag & Drop Categories ({type_mode}{scoring_str}):</div>"
            return f"{desc}{''.join(cards)}"

    return ""
