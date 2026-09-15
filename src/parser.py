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
    OrderItem,
    OrderQuestion,
    Question,
    Quiz,
    Section,
    SingleChoiceQuestion,
    TrueFalseQuestion,
    generate_id,
)
from src.validation import Diagnostic, QuizValidationError, Severity


# Regex patterns
RE_H1 = re.compile(r"^#\s+(.+)$")
RE_H2 = re.compile(r"^##\s+(.+)$")
RE_META = re.compile(r"^(points|type|feedback|hint|identifier|topic|keywords|tags|additional_info|additionalinformations|version|language|shuffle|scoring):\s*(.+)$", re.IGNORECASE)
RE_TASK_LIST = re.compile(r"^-\s*\[([ xX])\]\s*(.*)$")
RE_ORDER_TASK = re.compile(r"^\d+\.\s*\[([ xX])\]\s*(.*)$")
RE_KPRIM_HEADER = re.compile(r"^kprim:\s*$", re.IGNORECASE)
RE_KPRIM_ITEM = re.compile(r"^-\s*\[([+-])\]\s*(.*)$")
RE_NUMERICAL = re.compile(
    r"^=\s*([+-]?\d+(?:\.\d+)?)\s*(?:(?:±|\+-|\+/-)\s*(\d+(?:\.\d+)?))?$"
)
RE_GAP = re.compile(r"\{\{((?:\\.|[^\}\\]|\}(?!\})*?)*?)\}\}")


class RawSectionBlock:
    """Intermediate container for an assessment section and its description/questions."""

    def __init__(self, title: str, start_line: int, is_implicit: bool = False):
        self.title = title
        self.start_line = start_line
        self.is_implicit = is_implicit
        self.description_lines: List[str] = []
        self.question_blocks: List["RawQuestionBlock"] = []


class RawQuestionBlock:
    """Intermediate container for segmented question lines before typing."""

    def __init__(self, title: str, start_line: int):
        self.title = title
        self.start_line = start_line
        self.raw_lines: List[Tuple[int, str]] = []
        self.metadata: Dict[str, Any] = {}
        self.prompt_lines: List[str] = []
        self.choices: List[Tuple[bool, str, str, int]] = []  # (is_correct, mark, text, line_no)
        self.order_items: List[Tuple[str, int]] = []  # (text, line_no)
        self.order_invalid_marks: List[Tuple[str, int]] = []  # (mark, line_no)
        self.kprim_items: List[Tuple[bool, str, int]] = []  # (is_true, text, line_no)
        self.numerical: Optional[Tuple[float, float, int]] = None  # (val, tol, line_no)
        self.is_kprim_mode = False


RE_TOP_META = re.compile(r"^(version|language|title|description|topic|keywords|tags|additional_info|additionalinformations|shuffle|scoring):\s*(.+)$", re.IGNORECASE)


def _parse_bool(val: Any) -> Optional[bool]:
    """Parse common boolean representations."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        cleaned = val.strip().lower()
        if cleaned in ("true", "yes", "1", "on"):
            return True
        if cleaned in ("false", "no", "0", "off"):
            return False
    return None


def _split_gap_inner(inner: str) -> List[str]:
    """Split inner gap on unescaped '|' and unescape \\|, \\}, \\\\."""
    parts = []
    current = []
    i = 0
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner):
            escaped_char = inner[i + 1]
            if escaped_char in ("|", "}", "\\"):
                current.append(escaped_char)
                i += 2
                continue
            else:
                current.append(inner[i])
                current.append(escaped_char)
                i += 2
                continue
        elif inner[i] == "|":
            parts.append("".join(current).strip())
            current = []
            i += 1
            continue
        else:
            current.append(inner[i])
            i += 1
    if current or not parts:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def _parse_gaps(prompt: str) -> List[Gap]:
    """Parse gap tokens {{canonical | alt1 | alt2}} into Gap objects, supporting escapes."""
    raw_gaps = RE_GAP.findall(prompt)
    gaps: List[Gap] = []
    for g in raw_gaps:
        parts = _split_gap_inner(g)
        if not parts:
            continue
        canonical = parts[0]
        alternatives = parts[1:]
        gaps.append(Gap(expected_value=canonical, alternatives=alternatives))
    return gaps


def _split_keywords(val: Any) -> List[str]:
    """Parse keywords into a list of strings from string or list."""
    if isinstance(val, list):
        return [str(k).strip() for k in val if str(k).strip()]
    if isinstance(val, str):
        return [k.strip() for k in val.split(",") if k.strip()]
    return []


def parse_quizmd(text: str) -> Tuple[Quiz, List[Diagnostic]]:
    """Parse a QuizMD Markdown string into a typed Quiz and diagnostic messages."""
    diagnostics: List[Diagnostic] = []
    lines = text.splitlines()

    # Step 0: Extract YAML Frontmatter if present at start of document
    frontmatter: Dict[str, Any] = {}
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
                            frontmatter = {str(k).lower(): v for k, v in data.items() if v is not None}
                    except Exception:
                        for fm_line in lines[idx + 1 : close_idx]:
                            m = re.match(r"^([a-zA-Z0-9_-]+):\s*(.+)$", fm_line.strip())
                            if m:
                                frontmatter[m.group(1).lower()] = m.group(2).strip().strip("'\"")
                    break
        break

    # Step 1: Document, Section & Question segmentation
    raw_sections: List[RawSectionBlock] = []
    current_section: Optional[RawSectionBlock] = None
    current_question: Optional[RawQuestionBlock] = None
    preamble_lines: List[str] = []
    top_meta: Dict[str, str] = {}
    top_meta_lines: Dict[str, int] = {}

    in_code_block = False
    for line_idx, line in enumerate(lines[content_start_idx:], start=content_start_idx + 1):
        stripped = line.strip()

        # Handle fenced code block toggling
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if current_question is not None:
                current_question.raw_lines.append((line_idx, line))
            elif current_section is not None:
                current_section.description_lines.append(line)
            else:
                preamble_lines.append(line)
            continue

        # If inside a code block, never treat # or ## or metadata as headings/markers
        if in_code_block:
            if current_question is not None:
                current_question.raw_lines.append((line_idx, line))
            elif current_section is not None:
                current_section.description_lines.append(line)
            else:
                preamble_lines.append(line)
            continue

        # Check Level 1 heading (# always starts a section)
        h1_match = RE_H1.match(stripped)
        if h1_match:
            # Finalize any ongoing question
            if current_question is not None:
                if current_section is None:
                    current_section = RawSectionBlock(title="", start_line=current_question.start_line, is_implicit=True)
                    raw_sections.append(current_section)
                current_section.question_blocks.append(current_question)
                current_question = None

            section_title = h1_match.group(1).strip()
            current_section = RawSectionBlock(title=section_title, start_line=line_idx, is_implicit=False)
            raw_sections.append(current_section)
            continue

        # Check Level 2 heading (## always starts a question)
        h2_match = RE_H2.match(stripped)
        if h2_match:
            # Finalize previous question
            if current_question is not None:
                if current_section is None:
                    current_section = RawSectionBlock(title="", start_line=current_question.start_line, is_implicit=True)
                    raw_sections.append(current_section)
                current_section.question_blocks.append(current_question)

            # Ensure we have an active section; if none, create implicit section
            if current_section is None:
                current_section = RawSectionBlock(title="", start_line=line_idx, is_implicit=True)
                raw_sections.append(current_section)

            current_question = RawQuestionBlock(
                title=h2_match.group(1).strip(),
                start_line=line_idx,
            )
            continue

        # Accumulate lines depending on context
        if current_question is not None:
            current_question.raw_lines.append((line_idx, line))
        elif current_section is not None:
            # For the first section before any questions, lines like "Version: 1.2.3" or "Scoring: all-correct"
            # act as top_meta if not already defined in preamble
            top_meta_match = RE_TOP_META.match(stripped)
            if top_meta_match and len(raw_sections) == 1 and not current_section.question_blocks:
                key = top_meta_match.group(1).lower()
                val = top_meta_match.group(2).strip()
                if key not in top_meta:
                    top_meta[key] = val
                    top_meta_lines[key] = line_idx
                    continue

            # Content between # Section heading and its first ## Question is section description/instructions
            current_section.description_lines.append(line)
        else:
            # Preamble before any # section or ## question
            top_meta_match = RE_TOP_META.match(stripped)
            if top_meta_match:
                key = top_meta_match.group(1).lower()
                val = top_meta_match.group(2).strip()
                top_meta[key] = val
                top_meta_lines[key] = line_idx
                continue
            preamble_lines.append(line)

    # Finalize trailing question
    if current_question is not None:
        if current_section is None:
            current_section = RawSectionBlock(title="", start_line=current_question.start_line, is_implicit=True)
            raw_sections.append(current_section)
        current_section.question_blocks.append(current_question)

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

    # 2. Title:
    # Rule: YAML title defines the test title.
    # If no test title is given in YAML, the first section title is also used as the test title.
    # If questions occur without any # section, sensible default is used.
    fm_title = frontmatter.get("title")
    meta_title = top_meta.get("title")
    first_explicit_section = None
    for s_blk in raw_sections:
        if not s_blk.is_implicit and s_blk.title:
            first_explicit_section = s_blk
            break

    # If explicit title: was specified in top_meta, compare with frontmatter for warnings
    if fm_title is not None and meta_title is not None:
        if fm_title.strip() != meta_title.strip():
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent title: frontmatter specifies '{fm_title.strip()}' but header specifies '{meta_title.strip()}'. Using header title '{meta_title.strip()}'.",
                    Severity.WARNING,
                    top_meta_lines.get("title"),
                )
            )
            quiz_title = meta_title.strip()
        else:
            quiz_title = meta_title.strip()
    elif fm_title is not None and len([s for s in raw_sections if not s.is_implicit]) == 1:
        # Single-section quiz where user provided frontmatter title AND # Header Title
        only_section = [s for s in raw_sections if not s.is_implicit][0]
        if fm_title.strip() != only_section.title.strip():
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent title: frontmatter specifies '{fm_title.strip()}' but header specifies '{only_section.title.strip()}'. Using header title '{only_section.title.strip()}'.",
                    Severity.WARNING,
                    only_section.start_line,
                )
            )
            quiz_title = only_section.title.strip()
            only_section.title = quiz_title
        else:
            quiz_title = fm_title.strip()
    elif fm_title is not None:
        # Multi-section quiz: YAML title strictly defines the overall test title
        quiz_title = fm_title.strip()
    elif meta_title is not None:
        quiz_title = meta_title.strip()
    elif first_explicit_section is not None:
        # If no test title given in YAML/meta, the first section title is also used as test title
        quiz_title = first_explicit_section.title
    else:
        quiz_title = DEFAULTS["quiz_title"]

    # Ensure implicit sections receive a meaningful title
    for s_blk in raw_sections:
        if s_blk.is_implicit or not s_blk.title:
            s_blk.title = quiz_title

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

    # 4. Topic
    fm_topic = frontmatter.get("topic")
    meta_topic = top_meta.get("topic")
    if fm_topic is not None and meta_topic is not None:
        if str(fm_topic).strip() != meta_topic.strip():
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent topic: frontmatter specifies '{fm_topic}' but header metadata specifies '{meta_topic.strip()}'. Using header metadata '{meta_topic.strip()}'.",
                    Severity.WARNING,
                    top_meta_lines.get("topic"),
                )
            )
            quiz_topic = meta_topic.strip()
        else:
            quiz_topic = meta_topic.strip()
    elif meta_topic is not None:
        quiz_topic = meta_topic.strip()
    elif fm_topic is not None:
        quiz_topic = str(fm_topic).strip()
    else:
        quiz_topic = None

    # 5. Keywords / Tags
    fm_kw = frontmatter.get("keywords") or frontmatter.get("tags")
    meta_kw = top_meta.get("keywords") or top_meta.get("tags")
    parsed_meta_kw = _split_keywords(meta_kw) if meta_kw else []
    parsed_fm_kw = _split_keywords(fm_kw) if fm_kw else []
    if parsed_fm_kw and parsed_meta_kw:
        if parsed_fm_kw != parsed_meta_kw:
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent keywords: frontmatter specifies '{parsed_fm_kw}' but header metadata specifies '{parsed_meta_kw}'. Using header metadata.",
                    Severity.WARNING,
                    top_meta_lines.get("keywords") or top_meta_lines.get("tags"),
                )
            )
            quiz_keywords = parsed_meta_kw
        else:
            quiz_keywords = parsed_meta_kw
    elif parsed_meta_kw:
        quiz_keywords = parsed_meta_kw
    elif parsed_fm_kw:
        quiz_keywords = parsed_fm_kw
    else:
        quiz_keywords = []

    # 6. Additional Info
    fm_info = frontmatter.get("additional_info") or frontmatter.get("additionalinformations")
    meta_info = top_meta.get("additional_info") or top_meta.get("additionalinformations")
    if fm_info is not None and meta_info is not None:
        if str(fm_info).strip() != meta_info.strip():
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent additional_info: frontmatter specifies '{fm_info}' but header metadata specifies '{meta_info.strip()}'. Using header metadata '{meta_info.strip()}'.",
                    Severity.WARNING,
                    top_meta_lines.get("additional_info") or top_meta_lines.get("additionalinformations"),
                )
            )
            quiz_additional_info = meta_info.strip()
        else:
            quiz_additional_info = meta_info.strip()
    elif meta_info is not None:
        quiz_additional_info = meta_info.strip()
    elif fm_info is not None:
        quiz_additional_info = str(fm_info).strip()
    else:
        quiz_additional_info = None

    # 7. Shuffle
    fm_shuffle = _parse_bool(frontmatter.get("shuffle"))
    meta_shuffle = _parse_bool(top_meta.get("shuffle"))
    if fm_shuffle is not None and meta_shuffle is not None:
        if fm_shuffle != meta_shuffle:
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent shuffle: frontmatter specifies '{fm_shuffle}' but header metadata specifies '{meta_shuffle}'. Using header metadata.",
                    Severity.WARNING,
                    top_meta_lines.get("shuffle"),
                )
            )
            quiz_shuffle = meta_shuffle
        else:
            quiz_shuffle = meta_shuffle
    elif meta_shuffle is not None:
        quiz_shuffle = meta_shuffle
    elif fm_shuffle is not None:
        quiz_shuffle = fm_shuffle
    else:
        quiz_shuffle = DEFAULTS["shuffle"]

    # 8. MC Scoring
    fm_scoring = frontmatter.get("scoring")
    meta_scoring = top_meta.get("scoring")
    if fm_scoring is not None and meta_scoring is not None:
        if str(fm_scoring).strip().lower() != str(meta_scoring).strip().lower():
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent scoring: frontmatter specifies '{fm_scoring}' but header metadata specifies '{meta_scoring.strip()}'. Using header metadata '{meta_scoring.strip()}'.",
                    Severity.WARNING,
                    top_meta_lines.get("scoring"),
                )
            )
            quiz_mc_scoring = meta_scoring.strip().lower()
        else:
            quiz_mc_scoring = meta_scoring.strip().lower()
    elif meta_scoring is not None:
        quiz_mc_scoring = meta_scoring.strip().lower()
    elif fm_scoring is not None:
        quiz_mc_scoring = str(fm_scoring).strip().lower()
    else:
        quiz_mc_scoring = DEFAULTS["mc_scoring"]

    # 9. Description
    quiz_description = (
        "\n".join(preamble_lines).strip()
        or top_meta.get("description")
        or frontmatter.get("description")
        or None
    )

    # Step 2: Line classification for each block across sections
    for s_blk in raw_sections:
        for block in s_blk.question_blocks:
            _classify_block_lines(block)

    # Step 3: Type inference and model creation by section
    sections: List[Section] = []
    global_q_idx = 0

    for s_blk in raw_sections:
        sec_questions: List[Question] = []
        for block in s_blk.question_blocks:
            try:
                q = _build_question_from_block(block, global_q_idx)
                if q is not None:
                    # Inherit quiz metadata to question if not explicitly overridden at question level
                    if q.topic is None and quiz_topic is not None:
                        q.topic = quiz_topic
                    if not q.keywords and quiz_keywords:
                        q.keywords = list(quiz_keywords)
                    if q.language is None and quiz_language is not None:
                        q.language = quiz_language
                    if q.shuffle is None:
                        q.shuffle = quiz_shuffle
                    if isinstance(q, MultipleChoiceQuestion) and (q.scoring is None or q.scoring == DEFAULTS["mc_scoring"]):
                        if quiz_mc_scoring != DEFAULTS["mc_scoring"] and "scoring" not in block.metadata:
                            q.scoring = quiz_mc_scoring
                    if q.additional_info is None:
                        if quiz_additional_info is not None:
                            q.additional_info = quiz_additional_info
                        elif quiz_version is not None:
                            q.additional_info = f"Version: {quiz_version}"

                    sec_questions.append(q)
            except QuizValidationError as e:
                for d in e.diagnostics:
                    d.question_index = global_q_idx
                    diagnostics.append(d)
            global_q_idx += 1

        sec_desc = "\n".join(s_blk.description_lines).strip() or None
        sections.append(
            Section(
                title=s_blk.title,
                description=sec_desc,
                questions=sec_questions,
                line_number=s_blk.start_line,
            )
        )

    # If no sections were produced (e.g. empty document), initialize with default section
    if not sections:
        sections = [Section(title=quiz_title, questions=[])]

    quiz = Quiz(
        title=quiz_title,
        description=quiz_description,
        sections=sections,
        language=quiz_language,
        version=quiz_version,
        topic=quiz_topic,
        keywords=quiz_keywords,
        additional_info=quiz_additional_info,
        shuffle=quiz_shuffle,
        mc_scoring=quiz_mc_scoring,
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
        if meta_match:
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

        # Check Order task list item: 1. [ ], 1. [x], 1. [X]
        order_match = RE_ORDER_TASK.match(stripped)
        if order_match:
            mark = order_match.group(1)
            item_text = order_match.group(2).strip()
            if mark == " ":
                block.order_items.append((item_text, line_no))
            else:
                block.order_invalid_marks.append((mark, line_no))
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
    hint = block.metadata.get("hint") or DEFAULTS["hint"]
    explicit_type = block.metadata.get("type", "").lower().replace("-", "").replace("_", "")

    # Question-level metadata overrides
    topic = block.metadata.get("topic")
    kw_raw = block.metadata.get("keywords") or block.metadata.get("tags")
    keywords = _split_keywords(kw_raw) if kw_raw else []
    additional_info = (
        block.metadata.get("additional_info")
        or block.metadata.get("additionalinformations")
        or (f"Version: {block.metadata['version']}" if "version" in block.metadata else None)
    )
    language = block.metadata.get("language")
    q_shuffle = _parse_bool(block.metadata.get("shuffle")) if "shuffle" in block.metadata else None
    q_scoring = block.metadata.get("scoring", "").strip().lower() if "scoring" in block.metadata else None

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
        "hint": hint,
        "identifier": identifier,
        "line_number": block.start_line,
        "topic": topic,
        "keywords": keywords,
        "additional_info": additional_info,
        "language": language,
        "shuffle": q_shuffle,
    }

    # Reject invalid numbered task-list items: 1. [x] or 1. [X]
    if block.order_invalid_marks:
        first_invalid_mark, line_no = block.order_invalid_marks[0]
        raise QuizValidationError(
            f"Numbered task-list items cannot contain [{first_invalid_mark}]; Order questions require empty checkboxes [ ].",
            [Diagnostic(
                f"Numbered task-list items cannot contain [{first_invalid_mark}]; Order questions require empty checkboxes [ ].",
                Severity.ERROR,
                line_no,
                q_idx,
            )],
        )

    # Prevent conflicting choice markers, Kprim markers, and Order items
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
    if block.order_items and (block.choices or block.kprim_items or block.is_kprim_mode):
        raise QuizValidationError(
            "Cannot combine Order items (N. [ ]) with choice or Kprim markers in the same question.",
            [Diagnostic(
                "Cannot combine Order items (N. [ ]) with choice or Kprim markers in the same question.",
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
            mc_kwargs = dict(common_kwargs)
            if q_scoring is not None:
                mc_kwargs["scoring"] = q_scoring
            return MultipleChoiceQuestion(**mc_kwargs, choices=choices)
        elif explicit_type in ("truefalse", "tf"):
            choices = [Choice(text=text, is_correct=is_corr) for is_corr, _, text, _ in block.choices]
            return TrueFalseQuestion(**common_kwargs, choices=choices)
        elif explicit_type in ("essay", "freetext", "open"):
            return EssayQuestion(**common_kwargs)
        elif explicit_type in ("fillinblank", "fillblank", "fib"):
            gaps = _parse_gaps(prompt)
            return FillBlankQuestion(**common_kwargs, gaps=gaps)
        elif explicit_type in ("numerical", "num"):
            val, tol = (block.numerical[0], block.numerical[1]) if block.numerical else (0.0, 0.0)
            return NumericalQuestion(**common_kwargs, answer=val, tolerance=tol)
        elif explicit_type == "kprim":
            stmts = [KprimStatement(text=it[1], is_correct=it[0]) for it in block.kprim_items]
            return KprimQuestion(**common_kwargs, statements=stmts)
        elif explicit_type in ("order", "sequence", "sequencing"):
            items = [OrderItem(text=it[0]) for it in block.order_items]
            return OrderQuestion(**common_kwargs, items=items)

    # 2. Inferred: Order / Sequencing (N. [ ] ...)
    if block.order_items:
        items = [OrderItem(text=it[0]) for it in block.order_items]
        return OrderQuestion(**common_kwargs, items=items)

    # 3. Inferred: Kprim
    if block.is_kprim_mode or block.kprim_items:
        stmts = [KprimStatement(text=it[1], is_correct=it[0]) for it in block.kprim_items]
        return KprimQuestion(**common_kwargs, statements=stmts)

    # 4. Inferred: Fill-in-the-Blank
    gaps_found = _parse_gaps(prompt)
    if gaps_found:
        return FillBlankQuestion(**common_kwargs, gaps=gaps_found)

    # 5. Inferred: Numerical
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
            mc_kwargs = dict(common_kwargs)
            if q_scoring is not None:
                mc_kwargs["scoring"] = q_scoring
            return MultipleChoiceQuestion(**mc_kwargs, choices=choices)

    # 6. Inferred: Essay / Free Text (question prompt with no answer tokens)
    return EssayQuestion(**common_kwargs)
