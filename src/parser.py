"""Staged QuizMD parser with line-aware diagnostics and deterministic inference.

Rule: Avoid building the entire language as one large regular expression.
Use a staged parser:
  Markdown source
        ↓
  Document/question segmentation
        ↓
  Metadata extraction
        ↓
  Answer-structure recognition
        ↓
  Type inference
        ↓
  Semantic validation
        ↓
  Typed Quiz model
"""

import re
from typing import List, Optional, Tuple, Dict, Any

from src.defaults import DEFAULTS
from src.model import (
    Choice,
    EssayQuestion,
    FillBlankQuestion,
    Gap,
    KprimQuestion,
    KprimStatement,
    MultipleChoiceQuestion,
    NumericalQuestion,
    Question,
    Quiz,
    SingleChoiceQuestion,
    TrueFalseQuestion,
    generate_id,
)
from src.validation import Diagnostic, QuizValidationError, Severity


# Regex patterns
RE_H1 = re.compile(r"^#\s+(.+)$")
RE_H2 = re.compile(r"^##\s+(.+)$")
RE_META = re.compile(r"^(points|type|feedback|identifier):\s*(.+)$", re.IGNORECASE)
RE_TASK_LIST = re.compile(r"^-\s*\[([ xX])\]\s*(.*)$")
RE_KPRIM_HEADER = re.compile(r"^kprim:\s*$", re.IGNORECASE)
RE_KPRIM_ITEM = re.compile(r"^-\s*\[([+-])\]\s*(.*)$")
RE_NUMERICAL = re.compile(
    r"^=\s*([+-]?\d+(?:\.\d+)?)\s*(?:(?:±|\+-|\+/-)\s*(\d+(?:\.\d+)?))?$"
)
RE_GAP = re.compile(r"\{\{([^}]+)\}\}")


class RawQuestionBlock:
    """Intermediate container for segmented question lines before typing."""

    def __init__(self, title: str, start_line: int):
        self.title = title
        self.start_line = start_line
        self.raw_lines: List[Tuple[int, str]] = []
        self.metadata: Dict[str, Any] = {}
        self.prompt_lines: List[str] = []
        self.choices: List[Tuple[bool, str, str, int]] = []  # (is_correct, mark, text, line_no)
        self.kprim_items: List[Tuple[bool, str, int]] = []  # (is_true, text, line_no)
        self.numerical: Optional[Tuple[float, float, int]] = None  # (val, tol, line_no)
        self.is_kprim_mode = False


RE_TOP_META = re.compile(r"^(version|language|title|description):\s*(.+)$", re.IGNORECASE)


def parse_quizmd(text: str) -> Tuple[Quiz, List[Diagnostic]]:
    """Parse a QuizMD Markdown string into a typed Quiz and diagnostic messages."""
    diagnostics: List[Diagnostic] = []
    lines = text.splitlines()

    # Step 0: Extract YAML Frontmatter if present at start of document
    frontmatter: Dict[str, str] = {}
    content_start_idx = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "---":
            # Search for closing ---
            for close_idx in range(idx + 1, len(lines)):
                if lines[close_idx].strip() == "---":
                    content_start_idx = close_idx + 1
                    raw_fm = "\n".join(lines[idx + 1 : close_idx])
                    try:
                        import yaml
                        data = yaml.safe_load(raw_fm)
                        if isinstance(data, dict):
                            frontmatter = {str(k).lower(): str(v) for k, v in data.items() if v is not None}
                    except Exception:
                        for fm_line in lines[idx + 1 : close_idx]:
                            m = re.match(r"^([a-zA-Z0-9_-]+):\s*(.+)$", fm_line.strip())
                            if m:
                                frontmatter[m.group(1).lower()] = m.group(2).strip().strip("'\"")
                    break
        break

    h1_title: Optional[str] = None
    h1_line: Optional[int] = None
    top_meta: Dict[str, str] = {}
    top_meta_lines: Dict[str, int] = {}
    description_lines: List[str] = []
    question_blocks: List[RawQuestionBlock] = []
    current_block: Optional[RawQuestionBlock] = None

    # Step 1: Document & question segmentation
    for line_idx, line in enumerate(lines[content_start_idx:], start=content_start_idx + 1):
        stripped = line.strip()

        # Check Level 2 heading (Question start)
        h2_match = RE_H2.match(stripped)
        if h2_match:
            if current_block is not None:
                question_blocks.append(current_block)
            current_block = RawQuestionBlock(
                title=h2_match.group(1).strip(),
                start_line=line_idx,
            )
            continue

        if current_block is not None:
            current_block.raw_lines.append((line_idx, line))
        else:
            # Preamble section (before any question)
            h1_match = RE_H1.match(stripped)
            if h1_match and h1_title is None:
                h1_title = h1_match.group(1).strip()
                h1_line = line_idx
                continue

            top_meta_match = RE_TOP_META.match(stripped)
            if top_meta_match:
                key = top_meta_match.group(1).lower()
                val = top_meta_match.group(2).strip()
                top_meta[key] = val
                top_meta_lines[key] = line_idx
                continue

            description_lines.append(line)

    if current_block is not None:
        question_blocks.append(current_block)

    # Resolve Quiz-level metadata with consistency checking between Way A & Way B
    # 1. Version
    fm_ver = frontmatter.get("version")
    meta_ver = top_meta.get("version")
    if fm_ver is not None and meta_ver is not None:
        if fm_ver.strip() != meta_ver.strip():
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent version: frontmatter specifies '{fm_ver.strip()}' but header metadata specifies '{meta_ver.strip()}'. Using header metadata '{meta_ver.strip()}'.",
                    Severity.WARNING,
                    top_meta_lines.get("version"),
                )
            )
            quiz_version = meta_ver.strip()
        else:
            quiz_version = meta_ver.strip()
    elif meta_ver is not None:
        quiz_version = meta_ver.strip()
    elif fm_ver is not None:
        quiz_version = fm_ver.strip()
    else:
        quiz_version = DEFAULTS["quiz_version"]

    # 2. Title
    fm_title = frontmatter.get("title")
    header_title = h1_title or top_meta.get("title")
    if fm_title is not None and header_title is not None:
        if fm_title.strip() != header_title.strip():
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent title: frontmatter specifies '{fm_title.strip()}' but header specifies '{header_title.strip()}'. Using header title '{header_title.strip()}'.",
                    Severity.WARNING,
                    h1_line or top_meta_lines.get("title"),
                )
            )
            quiz_title = header_title.strip()
        else:
            quiz_title = header_title.strip()
    elif header_title is not None:
        quiz_title = header_title.strip()
    elif fm_title is not None:
        quiz_title = fm_title.strip()
    else:
        quiz_title = DEFAULTS["quiz_title"]

    # 3. Language
    fm_lang = frontmatter.get("language")
    meta_lang = top_meta.get("language")
    if fm_lang is not None and meta_lang is not None:
        if fm_lang.strip() != meta_lang.strip():
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent language: frontmatter specifies '{fm_lang.strip()}' but header metadata specifies '{meta_lang.strip()}'. Using header metadata '{meta_lang.strip()}'.",
                    Severity.WARNING,
                    top_meta_lines.get("language"),
                )
            )
            quiz_language = meta_lang.strip()
        else:
            quiz_language = meta_lang.strip()
    elif meta_lang is not None:
        quiz_language = meta_lang.strip()
    elif fm_lang is not None:
        quiz_language = fm_lang.strip()
    else:
        quiz_language = DEFAULTS["language"]

    # 4. Description
    quiz_description = (
        "\n".join(description_lines).strip()
        or top_meta.get("description")
        or frontmatter.get("description")
        or None
    )

    # Step 2: Line classification for each block
    for block in question_blocks:
        _classify_block_lines(block)

    # Step 3: Type inference and model creation
    questions: List[Question] = []
    for q_idx, block in enumerate(question_blocks):
        try:
            q = _build_question_from_block(block, q_idx)
            if q is not None:
                questions.append(q)
        except QuizValidationError as e:
            for d in e.diagnostics:
                d.question_index = q_idx
                diagnostics.append(d)

    quiz = Quiz(
        title=quiz_title,
        description=quiz_description,
        questions=questions,
        language=quiz_language,
        version=quiz_version,
    )

    # Add any global quiz diagnostics
    quiz_diags = quiz.validate()
    diagnostics.extend(quiz_diags)

    return quiz, diagnostics


def _classify_block_lines(block: RawQuestionBlock) -> None:
    """Classify lines inside a question block into metadata, choices, or prompt."""
    in_code_block = False
    for line_no, line in block.raw_lines:
        stripped = line.strip()

        # Handle fenced code block toggle: ```lang ... ```
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            block.prompt_lines.append(line)
            continue

        # Lines inside a fenced code block belong exclusively to the prompt
        if in_code_block:
            block.prompt_lines.append(line)
            continue

        if not stripped:
            if not block.is_kprim_mode and block.prompt_lines:
                block.prompt_lines.append("")
            continue

        # Check metadata lines: Points, Type, Feedback, Identifier
        meta_match = RE_META.match(stripped)
        if meta_match and not block.choices and not block.kprim_items:
            key = meta_match.group(1).lower()
            val = meta_match.group(2).strip()
            block.metadata[key] = val
            continue

        # Check optional Kprim header (for backwards compatibility)
        if RE_KPRIM_HEADER.match(stripped):
            block.is_kprim_mode = True
            continue

        # Check Kprim item: - [+] or - [-] (automatically infers Kprim)
        k_match = RE_KPRIM_ITEM.match(stripped)
        if k_match:
            is_true = k_match.group(1) == "+"
            stmt_text = k_match.group(2).strip()
            block.kprim_items.append((is_true, stmt_text, line_no))
            continue

        # Check Task list item: - [ ], - [x], - [X]
        task_match = RE_TASK_LIST.match(stripped)
        if task_match:
            mark = task_match.group(1)
            is_correct = mark in ("x", "X")
            choice_text = task_match.group(2).strip()
            block.choices.append((is_correct, mark, choice_text, line_no))
            continue

        # Check Numerical answer line: = 42 +- 0.5
        num_match = RE_NUMERICAL.match(stripped)
        if num_match:
            val = float(num_match.group(1))
            tol = float(num_match.group(2)) if num_match.group(2) is not None else 0.0
            block.numerical = (val, tol, line_no)
            continue

        # Otherwise, line is part of question prompt / description
        block.prompt_lines.append(line)


def _build_question_from_block(block: RawQuestionBlock, q_idx: int) -> Question:
    """Infer the question type and build the strongly typed Question object."""
    # Metadata extraction
    points = DEFAULTS["points"]
    if "points" in block.metadata:
        try:
            points = float(block.metadata["points"])
        except ValueError:
            raise QuizValidationError(
                f"Invalid Points value: '{block.metadata['points']}'",
                [Diagnostic(f"Invalid Points value: '{block.metadata['points']}'", Severity.ERROR, block.start_line, q_idx)],
            )

    identifier = block.metadata.get("identifier") or generate_id("item")
    feedback = block.metadata.get("feedback") or DEFAULTS["feedback"]
    explicit_type = block.metadata.get("type", "").lower().replace("-", "").replace("_", "")

    # Combine prompt text
    prompt = "\n".join(block.prompt_lines).strip()
    if not prompt:
        # Fallback to heading title if no body text
        prompt = block.title

    common_kwargs = {
        "title": block.title,
        "prompt": prompt,
        "points": points,
        "feedback": feedback,
        "identifier": identifier,
        "line_number": block.start_line,
    }

    # Prevent conflicting choice markers and Kprim markers
    if block.choices and (block.kprim_items or block.is_kprim_mode):
        raise QuizValidationError(
            "Cannot combine choice markers [X]/[x] with Kprim markers [+]/[-] in the same question.",
            [Diagnostic(
                "Cannot combine choice markers [X]/[x] with Kprim markers [+]/[-] in the same question.",
                Severity.ERROR,
                block.start_line,
                q_idx,
            )],
        )

    # Deterministic Inference Sequence

    # 1. Explicit Type Override
    if explicit_type:
        if explicit_type in ("singlechoice", "sc"):
            choices = [Choice(text=text, is_correct=is_corr) for is_corr, _, text, _ in block.choices]
            return SingleChoiceQuestion(**common_kwargs, choices=choices)
        elif explicit_type in ("multiplechoice", "mc"):
            choices = [Choice(text=text, is_correct=is_corr) for is_corr, _, text, _ in block.choices]
            return MultipleChoiceQuestion(**common_kwargs, choices=choices)
        elif explicit_type in ("truefalse", "tf"):
            choices = [Choice(text=text, is_correct=is_corr) for is_corr, _, text, _ in block.choices]
            return TrueFalseQuestion(**common_kwargs, choices=choices)
        elif explicit_type in ("essay", "freetext", "open"):
            return EssayQuestion(**common_kwargs)
        elif explicit_type in ("fillinblank", "fillblank", "fib"):
            gaps = [Gap(expected_value=g) for g in RE_GAP.findall(prompt)]
            return FillBlankQuestion(**common_kwargs, gaps=gaps)
        elif explicit_type in ("numerical", "num"):
            val, tol = (block.numerical[0], block.numerical[1]) if block.numerical else (0.0, 0.0)
            return NumericalQuestion(**common_kwargs, answer=val, tolerance=tol)
        elif explicit_type == "kprim":
            stmts = [KprimStatement(text=it[1], is_correct=it[0]) for it in block.kprim_items]
            return KprimQuestion(**common_kwargs, statements=stmts)

    # 2. Inferred: Kprim
    if block.is_kprim_mode or block.kprim_items:
        stmts = [KprimStatement(text=it[1], is_correct=it[0]) for it in block.kprim_items]
        return KprimQuestion(**common_kwargs, statements=stmts)

    # 3. Inferred: Fill-in-the-Blank
    gaps_found = RE_GAP.findall(prompt)
    if gaps_found:
        gaps = [Gap(expected_value=g) for g in gaps_found]
        return FillBlankQuestion(**common_kwargs, gaps=gaps)

    # 4. Inferred: Numerical
    if block.numerical is not None:
        val, tol = block.numerical[0], block.numerical[1]
        return NumericalQuestion(**common_kwargs, answer=val, tolerance=tol)

    # 5. Inferred: Task-list choices (Single Choice [X], Multiple Choice [x], True/False)
    if block.choices:
        count_X = sum(1 for _, mark, _, _ in block.choices if mark == "X")
        count_x = sum(1 for _, mark, _, _ in block.choices if mark == "x")

        if count_X > 0 and count_x > 0:
            raise QuizValidationError(
                "Mixed markers: cannot combine single-choice [X] and multiple-choice [x] in the same question.",
                [Diagnostic(
                    "Mixed markers: cannot combine single-choice [X] and multiple-choice [x] in the same question.",
                    Severity.ERROR,
                    block.start_line,
                    q_idx,
                )],
            )

        if count_X > 1:
            raise QuizValidationError(
                f"Single-choice question has {count_X} [X] answers; exactly 1 is required.",
                [Diagnostic(
                    f"Single-choice question has {count_X} [X] answers; exactly 1 is required.",
                    Severity.ERROR,
                    block.start_line,
                    q_idx,
                )],
            )

        if count_X == 0 and count_x == 0:
            raise QuizValidationError(
                "No correct answer is marked with [X] or [x].",
                [Diagnostic(
                    "No correct answer is marked with [X] or [x].",
                    Severity.ERROR,
                    block.start_line,
                    q_idx,
                )],
            )

        choices = [Choice(text=text, is_correct=is_corr) for is_corr, _, text, _ in block.choices]

        # Check if True/False: exactly 2 items with text 'True' and 'False'
        if len(choices) == 2:
            texts = {c.text.strip().lower() for c in choices}
            if texts == {"true", "false"}:
                return TrueFalseQuestion(**common_kwargs, choices=choices)

        if count_X == 1:
            return SingleChoiceQuestion(**common_kwargs, choices=choices)
        elif count_x >= 1:
            return MultipleChoiceQuestion(**common_kwargs, choices=choices)

    # 6. Inferred: Essay / Free Text (question prompt with no answer tokens)
    return EssayQuestion(**common_kwargs)
