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
    Question,
    Quiz,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)


from src.markdown import markdown_to_qti_xhtml


def render_quiz_preview_html(quiz: Quiz) -> str:
    """Generate clean HTML cards to visually preview parsed questions."""
    if not quiz.questions:
        return "<p style='color: #666; font-style: italic;'>No questions detected yet. Start typing or choose an example on the left.</p>"

    cards = []
    for idx, q in enumerate(quiz.questions, start=1):
        type_name = _get_type_label(q)
        badge_color = _get_badge_color(q)

        prompt_html = markdown_to_qti_xhtml(q.prompt)
        body_html = _render_question_body(q)
        feedback_html = (
            f"<div style='margin-top: 10px; padding: 8px 12px; background: #f0fdf4; border-left: 3px solid #22c55e; font-size: 0.9em; border-radius: 4px;'>"
            f"<strong>Feedback:</strong> {html.escape(q.feedback)}</div>"
            if q.feedback
            else ""
        )

        card = f"""
<div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
    <span style="font-weight: 600; font-size: 1.1em; color: #1e293b;">{idx}. {html.escape(q.title)}</span>
    <div>
      <span style="background: {badge_color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.78em; font-weight: 500; margin-right: 6px;">{type_name}</span>
      <span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 12px; font-size: 0.78em; font-weight: 600;">{q.points} pt</span>
    </div>
  </div>
  <div style="color: #334155; margin-bottom: 12px; line-height: 1.5;">{prompt_html}</div>
  {body_html}
  {feedback_html}
</div>
"""
        cards.append(card)

    return f"""
<style>
  pre {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 14px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.88em; overflow-x: auto; margin: 8px 0; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-size: 0.88em; color: #0f172a; }}
  pre code {{ background: transparent; padding: 0; border-radius: 0; color: inherit; }}
  blockquote {{ border-left: 3px solid #cbd5e1; margin: 8px 0; padding-left: 12px; color: #475569; }}
</style>
<div style="font-family: system-ui, -apple-system, sans-serif;">
  <div style="margin-bottom: 16px;">
    <h3 style="margin: 0; color: #0f172a;">{html.escape(quiz.title)}</h3>
    <span style="color: #64748b; font-size: 0.9em;">{len(quiz.questions)} Question(s) parsed</span>
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
        items = [f"<li><strong>Gap {i+1}:</strong> <code>{html.escape(g.expected_value)}</code></li>" for i, g in enumerate(q.gaps)]
        return f"<ul style='padding-left: 20px; margin: 0; color: #475569;'>{''.join(items)}</ul>"

    elif isinstance(q, NumericalQuestion):
        tol_str = f" ± {q.tolerance}" if q.tolerance > 0 else ""
        return f"<div style='color: #475569;'><strong>Expected Answer:</strong> <code>{q.answer}{tol_str}</code></div>"

    elif isinstance(q, EssayQuestion):
        return "<div style='color: #64748b; font-style: italic; background: #f8fafc; padding: 8px 12px; border-radius: 4px;'>[Open text response area for learner]</div>"

    elif isinstance(q, KprimQuestion):
        rows = []
        for stmt in q.statements:
            symbol = "<span style='color: #16a34a; font-weight: bold;'>[+] True</span>" if stmt.is_correct else "<span style='color: #dc2626; font-weight: bold;'>[-] False</span>"
            rows.append(f"<tr><td style='padding: 6px 12px; border: 1px solid #e2e8f0;'>{html.escape(stmt.text)}</td><td style='padding: 6px 12px; border: 1px solid #e2e8f0; text-align: center;'>{symbol}</td></tr>")
        return f"<table style='width: 100%; border-collapse: collapse; font-size: 0.9em;'><tr style='background: #f8fafc;'><th style='padding: 6px 12px; border: 1px solid #e2e8f0; text-align: left;'>Statement</th><th style='padding: 6px 12px; border: 1px solid #e2e8f0; width: 100px;'>Key</th></tr>{''.join(rows)}</table>"

    return ""
