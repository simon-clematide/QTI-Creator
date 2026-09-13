"""HTML preview generator for QuizMD."""

import html
import re
from src.model import (
    Choice,
    EssayQuestion,
    FillBlankQuestion,
    KprimQuestion,
    MultipleChoiceQuestion,
    NumericalQuestion,
    OrderQuestion,
    Question,
    Quiz,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)


from src.markdown import markdown_to_qti_xhtml


def render_quiz_preview_html(quiz: Quiz) -> str:
    """Generate clean collapsible HTML cards to visually preview parsed questions."""
    if not quiz.questions:
        return "<p style='color: #666; font-style: italic;'>No questions detected yet. Start typing or choose an example on the left.</p>"

    cards = []
    for idx, q in enumerate(quiz.questions, start=1):
        type_name = _get_type_label(q)
        badge_color = _get_badge_color(q)

        prompt_html = markdown_to_qti_xhtml(q.prompt)
        body_html = _render_question_body(q)
        hint_html = (
            f"<details style='margin-top: 10px; padding: 8px 12px; background: #fffbeb; border-left: 3px solid #f59e0b; font-size: 0.9em; border-radius: 4px; color: #92400e; cursor: pointer;'>"
            f"<summary style='font-weight: 600; outline: none;'>💡 Hint</summary>"
            f"<div style='margin-top: 6px; color: #78350f;'>{markdown_to_qti_xhtml(q.hint)}</div></details>"
            if q.hint
            else ""
        )
        feedback_html = (
            f"<div style='margin-top: 10px; padding: 8px 12px; background: #f0fdf4; border-left: 3px solid #22c55e; font-size: 0.9em; border-radius: 4px;'>"
            f"<strong>Feedback:</strong> {html.escape(q.feedback)}</div>"
            if q.feedback
            else ""
        )

        card = f"""
<details class="quiz-question-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); transition: border-color 0.2s;">
  <summary style="display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; cursor: pointer; user-select: none; list-style: none;">
    <div style="display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0;">
      <span class="quiz-chevron" style="display: inline-block; font-size: 0.8em; color: #64748b; transition: transform 0.2s;">▶</span>
      <span style="font-weight: 600; font-size: 1.05em; color: #1e293b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{idx}. {html.escape(q.title)}</span>
    </div>
    <div style="flex-shrink: 0; margin-left: 12px;">
      <span style="background: {badge_color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.78em; font-weight: 500; margin-right: 6px;">{type_name}</span>
      <span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 12px; font-size: 0.78em; font-weight: 600;">{q.points} pt</span>
    </div>
  </summary>
  <div style="padding: 12px 16px 16px 16px; border-top: 1px solid #f1f5f9;">
    <div style="color: #334155; margin-bottom: 12px; line-height: 1.5;">{prompt_html}</div>
    {body_html}
    {hint_html}
    {feedback_html}
  </div>
</details>
"""
        cards.append(card)

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
  .quiz-expand-btn {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    color: #475569;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.82em;
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
      <h3 style="margin: 0; color: #0f172a; font-size: 1.25em;">{html.escape(quiz.title)}</h3>
      <span style="color: #64748b; font-size: 0.9em;">{len(quiz.questions)} Question(s) parsed</span>
    </div>
    <div>
      <button type="button" class="quiz-expand-btn" onclick="
        var cards = document.querySelectorAll('.quiz-question-card');
        var anyClosed = Array.from(cards).some(c => !c.open);
        cards.forEach(c => c.open = anyClosed);
        this.innerHTML = anyClosed ? '▼ Collapse All' : '▶ Expand All';
      ">▶ Expand All</button>
    </div>
  </div>
  {''.join(cards)}
</div>
"""


def _get_type_label(q: Question) -> str:
    if isinstance(q, SingleChoiceQuestion):
        return "Single Choice"
    elif isinstance(q, MultipleChoiceQuestion):
        return "Multiple Choice"
    elif isinstance(q, TrueFalseQuestion):
        return "True / False"
    elif isinstance(q, EssayQuestion):
        return "Essay / Free Text"
    elif isinstance(q, FillBlankQuestion):
        return "Fill-in-the-Blank"
    elif isinstance(q, NumericalQuestion):
        return "Numerical"
    elif isinstance(q, KprimQuestion):
        return "Kprim (Matrix)"
    elif isinstance(q, OrderQuestion):
        return "Order / Sequencing"
    return "Question"


def _get_badge_color(q: Question) -> str:
    if isinstance(q, SingleChoiceQuestion):
        return "#3b82f6"  # Blue
    elif isinstance(q, MultipleChoiceQuestion):
        return "#8b5cf6"  # Purple
    elif isinstance(q, TrueFalseQuestion):
        return "#06b6d4"  # Cyan
    elif isinstance(q, EssayQuestion):
        return "#f59e0b"  # Amber
    elif isinstance(q, FillBlankQuestion):
        return "#10b981"  # Emerald
    elif isinstance(q, NumericalQuestion):
        return "#ec4899"  # Pink
    elif isinstance(q, KprimQuestion):
        return "#6366f1"  # Indigo
    elif isinstance(q, OrderQuestion):
        return "#0ea5e9"  # Sky
    return "#64748b"


def _render_question_body(q: Question) -> str:
    if isinstance(q, (SingleChoiceQuestion, MultipleChoiceQuestion, TrueFalseQuestion)):
        is_single = isinstance(q, (SingleChoiceQuestion, TrueFalseQuestion))
        bullet = "○" if is_single else "□"
        checked_bullet = "●" if is_single else "■"
        items = []
        for c in q.choices:
            icon = checked_bullet if c.is_correct else bullet
            style = "color: #16a34a; font-weight: 600;" if c.is_correct else "color: #475569;"
            tag = " (Correct)" if c.is_correct else ""
            choice_text_esc = html.escape(c.text)
            choice_text_formatted = re.sub(
                r"`([^`]+)`",
                r'<code style="background: #f1f5f9; padding: 2px 4px; border-radius: 3px;">\1</code>',
                choice_text_esc,
            )
            items.append(f"<li style='margin-bottom: 6px; list-style: none; {style}'>{icon} {choice_text_formatted}{tag}</li>")
        return f"<ul style='padding-left: 4px; margin: 0;'>{''.join(items)}</ul>"

    elif isinstance(q, FillBlankQuestion):
        items = []
        for i, g in enumerate(q.gaps):
            alts_str = f" <span style='color: #64748b; font-size: 0.9em;'>(alternatives: {', '.join(html.escape(a) for a in g.alternatives)})</span>" if g.alternatives else ""
            items.append(f"<li style='margin-bottom: 4px;'><strong>Gap {i+1}:</strong> <code style='background: #dcfce7; color: #166534; font-weight: 600; padding: 2px 6px; border-radius: 4px; border: 1px solid #bbf7d0;'>{html.escape(g.expected_value)}</code>{alts_str}</li>")
        return f"<ul style='padding-left: 20px; margin: 0; color: #475569;'>{''.join(items)}</ul>"

    elif isinstance(q, NumericalQuestion):
        tol_str = f" ± {q.tolerance}" if q.tolerance > 0 else ""
        return f"<div style='color: #475569;'><strong>Expected Answer:</strong> <code style='background: #dcfce7; color: #166534; font-weight: 600; padding: 2px 6px; border-radius: 4px; border: 1px solid #bbf7d0;'>{q.answer}{tol_str}</code></div>"

    elif isinstance(q, EssayQuestion):
        return "<div style='color: #64748b; font-style: italic; background: #f8fafc; padding: 8px 12px; border-radius: 4px;'>[Open text response area for learner]</div>"

    elif isinstance(q, KprimQuestion):
        rows = []
        for stmt in q.statements:
            symbol = "<span style='color: #16a34a; font-weight: bold;'>[+] True</span>" if stmt.is_correct else "<span style='color: #dc2626; font-weight: bold;'>[-] False</span>"
            rows.append(f"<tr><td style='padding: 6px 12px; border: 1px solid #e2e8f0;'>{html.escape(stmt.text)}</td><td style='padding: 6px 12px; border: 1px solid #e2e8f0; text-align: center;'>{symbol}</td></tr>")
        return f"<table style='width: 100%; border-collapse: collapse; font-size: 0.9em;'><tr style='background: #f8fafc;'><th style='padding: 6px 12px; border: 1px solid #e2e8f0; text-align: left;'>Statement</th><th style='padding: 6px 12px; border: 1px solid #e2e8f0; width: 100px;'>Key</th></tr>{''.join(rows)}</table>"

    elif isinstance(q, OrderQuestion):
        items = [f"<li>{html.escape(it.text)}</li>" for it in q.items]
        return f"<ol class='order-answer'>{''.join(items)}</ol>"

    return ""
