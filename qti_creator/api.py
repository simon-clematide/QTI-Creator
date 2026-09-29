"""Programmatic API endpoints for QTI-Creator.

Exposes headless validation, JQTI+ engine checks, and QTI 2.1 package generation
for external CI pipelines, LLM agent workflows, and programmatic callers.
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Any, Dict, List, Optional

import gradio as gr

from src.jqti_validator import is_java_available, is_javac_available, validate_qti_zip_bytes
from src.model import InvalidQuestion
from src.packager import create_qti_package
from src.parser import parse_quizmd
from src.validation import Severity


def check_quiz_api(quiz_markdown: str) -> Dict[str, Any]:
    """Validate QuizMD markdown syntax, structure, and question invariants.

    Args:
        quiz_markdown: Raw QuizMD markdown string.

    Returns:
        Structured dictionary containing:
            - valid (bool): True if there are zero fatal errors and at least one valid question.
            - total_questions (int): Number of parsed questions.
            - total_points (float): Sum of points across all questions.
            - quiz_title (str): Parsed or default quiz title.
            - sections_count (int): Number of sections.
            - diagnostics (list[dict]): List of diagnostic objects with severity, line_number, etc.
            - questions (list[dict]): List of question summaries.
    """
    if not quiz_markdown or not quiz_markdown.strip():
        return {
            "valid": False,
            "total_questions": 0,
            "total_points": 0.0,
            "quiz_title": "",
            "sections_count": 0,
            "diagnostics": [
                {
                    "severity": "error",
                    "message": "Quiz content is empty.",
                    "line_number": 1,
                    "question_index": None,
                }
            ],
            "questions": [],
        }

    quiz, diagnostics = parse_quizmd(quiz_markdown)

    fatal_errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    invalid_questions = [q for q in quiz.questions if isinstance(q, InvalidQuestion)]

    is_valid = len(fatal_errors) == 0 and len(invalid_questions) == 0 and len(quiz.questions) > 0

    diag_list: List[Dict[str, Any]] = [
        {
            "severity": d.severity.value,
            "message": d.message,
            "line_number": d.line_number,
            "question_index": d.question_index,
        }
        for d in diagnostics
    ]

    question_list: List[Dict[str, Any]] = [
        {
            "index": idx + 1,
            "title": q.title,
            "type": q.__class__.__name__,
            "points": getattr(q, "points", 0.0),
            "is_valid": not isinstance(q, InvalidQuestion),
        }
        for idx, q in enumerate(quiz.questions)
    ]

    total_pts = sum(getattr(q, "points", 0.0) for q in quiz.questions)

    return {
        "valid": is_valid,
        "total_questions": len(quiz.questions),
        "total_points": round(total_pts, 2),
        "quiz_title": quiz.title,
        "sections_count": len(quiz.sections),
        "diagnostics": diag_list,
        "questions": question_list,
    }


def validate_jqti_api(quiz_markdown: str) -> Dict[str, Any]:
    """Compile quiz to QTI 2.1 and validate with OpenOLAT's native JQTI+ engine.

    Args:
        quiz_markdown: Raw QuizMD markdown string.

    Returns:
        Structured dictionary containing:
            - valid (bool): Overall validity.
            - package_built (bool): Whether the QTI 2.1 ZIP archive was successfully generated.
            - jqti_available (bool): Whether Java/javac is available to run JQTI+.
            - jqti_valid (bool): JQTI+ engine verdict.
            - errors (list[str]): JQTI+ error messages.
            - diagnostics (list[dict]): Parser/linter diagnostics.
    """
    check_result = check_quiz_api(quiz_markdown)
    if not check_result["valid"]:
        return {
            "valid": False,
            "package_built": False,
            "jqti_available": is_java_available() and is_javac_available(),
            "jqti_valid": False,
            "errors": [d["message"] for d in check_result["diagnostics"] if d["severity"] == "error"],
            "diagnostics": check_result["diagnostics"],
        }

    quiz, _ = parse_quizmd(quiz_markdown)
    buf = io.BytesIO()
    try:
        create_qti_package(quiz, buf)
        zip_bytes = buf.getvalue()
    except Exception as e:
        return {
            "valid": False,
            "package_built": False,
            "jqti_available": is_java_available() and is_javac_available(),
            "jqti_valid": False,
            "errors": [f"Package build failed: {e}"],
            "diagnostics": check_result["diagnostics"],
        }

    java_ready = is_java_available() and is_javac_available()
    if not java_ready:
        return {
            "valid": True,
            "package_built": True,
            "jqti_available": False,
            "jqti_valid": None,
            "message": "QTI package is structurally valid. Java runtime not available on server for JQTI+ simulation.",
            "errors": [],
            "diagnostics": check_result["diagnostics"],
        }

    try:
        is_jqti_valid, jqti_errors = validate_qti_zip_bytes(zip_bytes)
        return {
            "valid": is_jqti_valid,
            "package_built": True,
            "jqti_available": True,
            "jqti_valid": is_jqti_valid,
            "errors": jqti_errors,
            "diagnostics": check_result["diagnostics"],
        }
    except Exception as e:
        return {
            "valid": False,
            "package_built": True,
            "jqti_available": True,
            "jqti_valid": False,
            "errors": [f"JQTI+ execution error: {e}"],
            "diagnostics": check_result["diagnostics"],
        }


def export_qti_api(quiz_markdown: str) -> Optional[str]:
    """Compile QuizMD markdown and generate a downloadable QTI 2.1 ZIP package.

    Args:
        quiz_markdown: Raw QuizMD markdown string.

    Returns:
        Absolute filepath to the generated temporary .zip file, or raises gr.Error on failure.
    """
    if not quiz_markdown or not quiz_markdown.strip():
        raise gr.Error("Cannot export empty quiz markdown.")

    quiz, diagnostics = parse_quizmd(quiz_markdown)
    fatal_errors = [d for d in diagnostics if d.severity == Severity.ERROR]
    if fatal_errors:
        err_msg = "; ".join(d.message for d in fatal_errors[:3])
        if len(fatal_errors) > 3:
            err_msg += f" (+{len(fatal_errors) - 3} more)"
        raise gr.Error(f"Validation failed: {err_msg}")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False, prefix="quiz_qti21_") as tf:
        tmp_path = tf.name

    try:
        create_qti_package(quiz, tmp_path)
        return tmp_path
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise gr.Error(f"Failed to create QTI package: {e}")


def register_api_endpoints(demo: gr.Blocks) -> None:
    """Register headless API endpoints on the Gradio Blocks application."""
    with demo:
        with gr.Column(visible=False):
            # Endpoint 1: check_quiz
            api_inp_check = gr.Textbox(label="Quiz Markdown", visible=False)
            api_out_check = gr.JSON(label="Check Result", visible=False)
            api_btn_check = gr.Button("Check Quiz", visible=False)
            api_btn_check.click(
                fn=check_quiz_api,
                inputs=[api_inp_check],
                outputs=[api_out_check],
                api_name="check_quiz",
            )

            # Endpoint 2: validate_jqti
            api_inp_jqti = gr.Textbox(label="Quiz Markdown", visible=False)
            api_out_jqti = gr.JSON(label="JQTI Result", visible=False)
            api_btn_jqti = gr.Button("Validate JQTI", visible=False)
            api_btn_jqti.click(
                fn=validate_jqti_api,
                inputs=[api_inp_jqti],
                outputs=[api_out_jqti],
                api_name="validate_jqti",
            )

            # Endpoint 3: export_qti
            api_inp_export = gr.Textbox(label="Quiz Markdown", visible=False)
            api_out_export = gr.File(label="QTI Package", visible=False)
            api_btn_export = gr.Button("Export QTI", visible=False)
            api_btn_export.click(
                fn=export_qti_api,
                inputs=[api_inp_export],
                outputs=[api_out_export],
                api_name="export_qti",
            )
