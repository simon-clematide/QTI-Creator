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
    AssociationItem,
    AssociationQuestion,
    AssociationTarget,
    Choice,
    EssayQuestion,
    FillBlankQuestion,
    Gap,
    HottextItem,
    HottextQuestion,
    InlineChoice,
    InlineChoiceGap,
    InlineChoiceQuestion,
    InvalidQuestion,
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

from src.markdown import RE_GAP, RE_DROPDOWN_GAP, extract_hottexts, is_table_separator_row, split_table_row
from src.validation import Diagnostic, QuizValidationError, Severity




# Regex patterns
RE_H1 = re.compile(r"^#\s+(.+)$")
RE_H2 = re.compile(r"^##\s+(.+)$")
RE_H3_HINT = re.compile(r"^###\s+Hint(?:\s*:\s*(.*)|\s*)$", re.IGNORECASE)
RE_H3_FEEDBACK = re.compile(r"^###\s+Feedback(?:\s*:\s*(.*)|\s*)$", re.IGNORECASE)
RE_H3_OTHER = re.compile(r"^###\s+(.+)$")
RE_META = re.compile(r"^(points|type|feedback|hint|identifier|topic|keywords|tags|additional_info|additionalinformations|version|language|shuffle|scoring):\s*(.+)$", re.IGNORECASE)
RE_TASK_LIST = re.compile(r"^-\s*\[([ xX])\]\s*(.*)$")
RE_ORDER_TASK = re.compile(r"^\d+\.\s*\[([ xX])\]\s*(.*)$")
RE_KPRIM_HEADER = re.compile(r"^kprim:\s*$", re.IGNORECASE)
RE_KPRIM_ITEM = re.compile(r"^-\s*\[([+-])\]\s*(.*)$")
RE_NUMERICAL = re.compile(
    r"^=\s*([+-]?\d+(?:\.\d+)?)\s*(?:(?:±|\+-|\+/-)\s*(\d+(?:\.\d+)?))?$"
)



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
        self.hint_lines: List[str] = []
        self.hint_title: Optional[str] = None
        self.has_h3_hint = False
        self.feedback_lines: List[str] = []
        self.feedback_title: Optional[str] = None
        self.has_h3_feedback = False
        self.legacy_leak_warning: Optional[str] = None
        self.legacy_leak_line: Optional[int] = None


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


def _split_dropdown_inner(inner: str) -> List[str]:
    """Split dropdown token inner content by unescaped pipe (|)."""
    parts = []
    current = []
    i = 0
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner):
            escaped_char = inner[i + 1]
            if escaped_char in ("|", "]", "}", "\\"):
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


def _parse_dropdown_gaps(prompt: str, question_shuffle: Optional[bool] = None) -> List[InlineChoiceGap]:
    """Parse dropdown gap tokens {[opt1|**opt2**|opt3]} into InlineChoiceGap objects.
    
    If an option is wrapped in bold (**opt** or __opt__), it is marked as the correct answer.
    If no option has bold markup, the first option is the correct answer and shuffle="true"
    must be enforced on that gap.
    """
    raw_gaps = RE_DROPDOWN_GAP.findall(prompt)
    gaps: List[InlineChoiceGap] = []
    for g in raw_gaps:
        raw_options = _split_dropdown_inner(g)
        if not raw_options:
            continue

        choices: List[InlineChoice] = []
        has_bold_marked = False

        for opt in raw_options:
            # Check for **bold** or __bold__ marking
            is_bold = False
            opt_clean = opt
            if (opt.startswith("**") and opt.endswith("**") and len(opt) >= 4):
                is_bold = True
                opt_clean = opt[2:-2].strip()
            elif (opt.startswith("__") and opt.endswith("__") and len(opt) >= 4):
                is_bold = True
                opt_clean = opt[2:-2].strip()

            if is_bold:
                has_bold_marked = True
                choices.append(InlineChoice(text=opt_clean, is_correct=True))
            else:
                choices.append(InlineChoice(text=opt_clean, is_correct=False))

        if not has_bold_marked:
            # First item is correct; shuffle must be enforced
            if choices:
                choices[0].is_correct = True
            gap_shuffle = True
        else:
            gap_shuffle = question_shuffle

        gaps.append(InlineChoiceGap(choices=choices, shuffle=gap_shuffle))
    return gaps


def _parse_hottexts(prompt: str) -> List[HottextItem]:
    """Parse hottext tokens from prompt into HottextItem objects."""
    raw_hottexts = extract_hottexts(prompt)
    items: List[HottextItem] = []
    for _start, _end, _raw_token, content, is_correct in raw_hottexts:
        items.append(HottextItem(text=content, is_correct=is_correct))
    return items


def _extract_association_table(
    prompt_lines: List[str],
    line_number: int,
    q_idx: int,
) -> Optional[Tuple[str, List[str], List[AssociationItem], List[AssociationTarget], bool]]:
    """Detect and parse an association table (Match or Drag & Drop) from question prompt lines.

    Expected header:
      | Item | Match |  -> interaction = "match"
      | Item | Drag |   -> interaction = "drag"
      | Item | Drag & Drop | -> interaction = "drag"

    Returns:
      (interaction, remaining_prompt_lines, items, targets, multiple)
      or None if no association table is present.
    """
    # Find table candidate: a header row followed by a separator row
    header_idx = None
    interaction_type = None

    for idx, line in enumerate(prompt_lines):
        stripped = line.strip()
        if "|" in stripped and idx + 1 < len(prompt_lines) and is_table_separator_row(prompt_lines[idx + 1]):
            cells = split_table_row(stripped)
            if len(cells) == 2:
                c0 = cells[0].strip().lower()
                c1 = cells[1].strip().lower()
                if c0 == "item":
                    if c1 == "match":
                        header_idx = idx
                        interaction_type = "match"
                        break
                    elif c1 in ("drag", "drag & drop", "drag&drop", "drag and drop"):
                        header_idx = idx
                        interaction_type = "drag"
                        break

    if header_idx is None or interaction_type is None:
        return None

    # Collect consecutive table lines starting from header_idx
    table_lines: List[str] = [prompt_lines[header_idx], prompt_lines[header_idx + 1]]
    end_idx = header_idx + 2
    while end_idx < len(prompt_lines):
        line = prompt_lines[end_idx]
        stripped = line.strip()
        if not stripped:
            break
        if "|" in stripped:
            table_lines.append(line)
            end_idx += 1
        else:
            break

    remaining_prompt_lines = prompt_lines[:header_idx] + prompt_lines[end_idx:]

    # Parse rows and apply ditto rule
    data_rows = table_lines[2:]
    if not data_rows:
        raise QuizValidationError(
            f"Association table for {interaction_type.capitalize()} has no data rows.",
            [Diagnostic(f"Association table for {interaction_type.capitalize()} has no data rows.", Severity.ERROR, line_number, q_idx)],
        )

    last_item_text: Optional[str] = None
    last_target_text: Optional[str] = None

    raw_pairs: List[Tuple[str, str]] = []
    seen_pairs = set()

    for r_idx, r_line in enumerate(data_rows):
        cells = split_table_row(r_line)
        c0 = cells[0].strip() if len(cells) > 0 else ""
        c1 = cells[1].strip() if len(cells) > 1 else ""

        # Completely empty row is ignored
        if not c0 and not c1:
            continue

        # Item ditto
        if not c0:
            if last_item_text is None:
                raise QuizValidationError(
                    "Empty Item cell has no preceding value to repeat.",
                    [Diagnostic("Empty Item cell has no preceding value to repeat.", Severity.ERROR, line_number, q_idx)],
                )
            c0 = last_item_text
        else:
            last_item_text = c0

        # Target ditto
        if not c1:
            if last_target_text is None:
                target_col_name = "Match" if interaction_type == "match" else "Drag"
                raise QuizValidationError(
                    f"Empty {target_col_name} cell has no preceding value to repeat.",
                    [Diagnostic(f"Empty {target_col_name} cell has no preceding value to repeat.", Severity.ERROR, line_number, q_idx)],
                )
            c1 = last_target_text
        else:
            last_target_text = c1

        pair_key = (c0, c1)
        if pair_key in seen_pairs:
            raise QuizValidationError(
                f"Duplicate association: '{c0}' → '{c1}'.",
                [Diagnostic(f"Duplicate association: '{c0}' → '{c1}'.", Severity.ERROR, line_number, q_idx)],
            )
        seen_pairs.add(pair_key)
        raw_pairs.append(pair_key)

    if not raw_pairs:
        raise QuizValidationError(
            f"Association table for {interaction_type.capitalize()} has no valid association rows.",
            [Diagnostic(f"Association table for {interaction_type.capitalize()} has no valid association rows.", Severity.ERROR, line_number, q_idx)],
        )

    # Collect targets in first-occurrence order
    targets: List[AssociationTarget] = []
    target_by_text: Dict[str, AssociationTarget] = {}
    for _, t_text in raw_pairs:
        if t_text not in target_by_text:
            target_obj = AssociationTarget(text=t_text)
            target_by_text[t_text] = target_obj
            targets.append(target_obj)

    # Collect items in first-occurrence order and their associated target IDs
    item_map: Dict[str, List[str]] = {}
    item_order: List[str] = []
    for i_text, t_text in raw_pairs:
        t_obj = target_by_text[t_text]
        if i_text not in item_map:
            item_map[i_text] = []
            item_order.append(i_text)
        item_map[i_text].append(t_obj.identifier)

    items: List[AssociationItem] = []
    multiple = False
    for i_text in item_order:
        t_ids = item_map[i_text]
        if len(t_ids) > 1:
            multiple = True
        items.append(AssociationItem(text=i_text, target_ids=t_ids))

    return interaction_type, remaining_prompt_lines, items, targets, multiple



def _split_keywords(val: Any) -> List[str]:
    """Parse keywords into a list of strings from string or list."""
    if isinstance(val, list):
        return [str(k).strip() for k in val if str(k).strip()]
    if isinstance(val, str):
        cleaned = val.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1]
        return [k.strip().strip("'\"") for k in cleaned.split(",") if k.strip().strip("'\"")]
    return []


def _resolve_meta_field(
    name: str,
    fm_val: Any,
    meta_val: Any,
    default: Any,
    diagnostics: List[Diagnostic],
    line_number: Optional[int] = None,
    transform=None,
    equality_fn=None,
) -> Any:
    """Resolve a metadata field between YAML frontmatter and header metadata.

    If both exist and differ, logs a warning and prefers header metadata (Way A).
    """
    val_fm = transform(fm_val) if (fm_val is not None and transform) else fm_val
    val_meta = transform(meta_val) if (meta_val is not None and transform) else meta_val

    if val_fm is not None and val_meta is not None:
        is_equal = equality_fn(val_fm, val_meta) if equality_fn else (val_fm == val_meta)
        if not is_equal:
            diagnostics.append(
                Diagnostic(
                    f"Inconsistent {name}: frontmatter specifies '{val_fm}' but header metadata specifies '{val_meta}'. Using header metadata.",
                    Severity.WARNING,
                    line_number,
                )
            )
        return val_meta
    elif val_meta is not None:
        return val_meta
    elif val_fm is not None:
        return val_fm
    return default


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
    quiz_version = _resolve_meta_field(
        "version",
        frontmatter.get("version"),
        top_meta.get("version"),
        default=DEFAULTS["quiz_version"],
        diagnostics=diagnostics,
        line_number=top_meta_lines.get("version"),
        transform=lambda v: str(v).strip(),
    )

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

    if fm_title is not None and meta_title is not None:
        quiz_title = _resolve_meta_field(
            "title",
            fm_title,
            meta_title,
            default=DEFAULTS["quiz_title"],
            diagnostics=diagnostics,
            line_number=top_meta_lines.get("title"),
            transform=lambda v: str(v).strip(),
        )
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
    quiz_language = _resolve_meta_field(
        "language",
        frontmatter.get("language"),
        top_meta.get("language"),
        default=DEFAULTS["language"],
        diagnostics=diagnostics,
        line_number=top_meta_lines.get("language"),
        transform=lambda v: str(v).strip(),
    )

    # 4. Topic
    quiz_topic = _resolve_meta_field(
        "topic",
        frontmatter.get("topic"),
        top_meta.get("topic"),
        default=None,
        diagnostics=diagnostics,
        line_number=top_meta_lines.get("topic"),
        transform=lambda v: str(v).strip(),
    )

    # 5. Keywords / Tags
    fm_kw = frontmatter.get("keywords") or frontmatter.get("tags")
    meta_kw = top_meta.get("keywords") or top_meta.get("tags")
    quiz_keywords = _resolve_meta_field(
        "keywords",
        _split_keywords(fm_kw) if fm_kw else None,
        _split_keywords(meta_kw) if meta_kw else None,
        default=[],
        diagnostics=diagnostics,
        line_number=top_meta_lines.get("keywords") or top_meta_lines.get("tags"),
    )

    # 6. Additional Info
    quiz_additional_info = _resolve_meta_field(
        "additional_info",
        frontmatter.get("additional_info") or frontmatter.get("additionalinformations"),
        top_meta.get("additional_info") or top_meta.get("additionalinformations"),
        default=None,
        diagnostics=diagnostics,
        line_number=top_meta_lines.get("additional_info") or top_meta_lines.get("additionalinformations"),
        transform=lambda v: str(v).strip(),
    )

    # 7. Shuffle
    quiz_shuffle = _resolve_meta_field(
        "shuffle",
        _parse_bool(frontmatter.get("shuffle")),
        _parse_bool(top_meta.get("shuffle")),
        default=DEFAULTS["shuffle"],
        diagnostics=diagnostics,
        line_number=top_meta_lines.get("shuffle"),
    )

    # 8. MC Scoring
    quiz_mc_scoring = _resolve_meta_field(
        "scoring",
        frontmatter.get("scoring"),
        top_meta.get("scoring"),
        default=DEFAULTS["mc_scoring"],
        diagnostics=diagnostics,
        line_number=top_meta_lines.get("scoring"),
        transform=lambda v: str(v).strip().lower(),
    )


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
                    if isinstance(q, InlineChoiceQuestion):
                        for gap in q.gaps:
                            if gap.shuffle is None:
                                gap.shuffle = q.shuffle
                    if (isinstance(q, (MultipleChoiceQuestion, HottextQuestion, AssociationQuestion))) and (q.scoring is None or q.scoring == DEFAULTS["mc_scoring"]):
                        if quiz_mc_scoring != DEFAULTS["mc_scoring"] and "scoring" not in block.metadata:
                            q.scoring = quiz_mc_scoring
                    if q.additional_info is None:
                        if quiz_additional_info is not None:
                            q.additional_info = quiz_additional_info
                        elif quiz_version is not None:
                            q.additional_info = f"Version: {quiz_version}"

                    if block.legacy_leak_warning:
                        diagnostics.append(
                            Diagnostic(
                                block.legacy_leak_warning,
                                Severity.WARNING,
                                block.legacy_leak_line or block.start_line,
                                global_q_idx,
                            )
                        )

                    sec_questions.append(q)
            except QuizValidationError as e:
                # Retain invalid questions for preview with error diagnostics
                points_val = DEFAULTS["points"]
                if "points" in block.metadata:
                    try:
                        p_cand = float(block.metadata["points"])
                        if p_cand > 0:
                            points_val = p_cand
                    except ValueError:
                        pass
                raw_block_text = "\n".join(line for _, line in block.raw_lines).strip()
                prompt_text = "\n".join(block.prompt_lines).strip()
                inv_raw_md = f"## {block.title}\n\n{raw_block_text}" if raw_block_text else f"## {block.title}"
                inv_q = InvalidQuestion(
                    prompt=prompt_text or raw_block_text,
                    title=block.title or "⚠️ Invalid Question",
                    points=points_val,
                    errors=list(e.diagnostics),
                    raw_text=raw_block_text,
                    raw_markdown=inv_raw_md,
                    line_number=block.start_line,
                )
                sec_questions.append(inv_q)
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
    """Classify lines inside a question block into prompt, choices, metadata, or hint/feedback sections."""
    in_code_block = False
    active_mode = "prompt"  # "prompt" | "hint" | "feedback"
    saw_legacy_feedback = False
    legacy_feedback_line = None
    saw_legacy_hint = False
    legacy_hint_line = None

    for line_no, line in block.raw_lines:
        stripped = line.strip()

        # Handle fenced code block toggle: ```lang ... ```
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if active_mode == "hint":
                block.hint_lines.append(line)
            elif active_mode == "feedback":
                block.feedback_lines.append(line)
            else:
                block.prompt_lines.append(line)
            continue

        # Lines inside a fenced code block belong exclusively to the active section
        if in_code_block:
            if active_mode == "hint":
                block.hint_lines.append(line)
            elif active_mode == "feedback":
                block.feedback_lines.append(line)
            else:
                block.prompt_lines.append(line)
            continue

        # Check Level 3 headings: ### Hint and ### Feedback
        hint_match = RE_H3_HINT.match(stripped)
        if hint_match:
            active_mode = "hint"
            block.has_h3_hint = True
            inline_title = hint_match.group(1)
            if inline_title and inline_title.strip():
                block.hint_title = inline_title.strip()
            continue

        feedback_match = RE_H3_FEEDBACK.match(stripped)
        if feedback_match:
            active_mode = "feedback"
            block.has_h3_feedback = True
            inline_title = feedback_match.group(1)
            if inline_title and inline_title.strip():
                block.feedback_title = inline_title.strip()
            continue

        # If we encounter another ### heading while in hint or feedback, it ends hint/feedback
        if stripped.startswith("###") and active_mode in ("hint", "feedback"):
            active_mode = "prompt"

        # Route lines if currently in ### Hint or ### Feedback mode
        if active_mode == "hint":
            block.hint_lines.append(line)
            continue
        elif active_mode == "feedback":
            block.feedback_lines.append(line)
            continue

        # In prompt mode:
        if not stripped:
            if not block.is_kprim_mode and block.prompt_lines:
                block.prompt_lines.append("")
            continue

        # Check metadata lines: Points, Type, Feedback, Hint, Identifier, etc.
        meta_match = RE_META.match(stripped)
        if meta_match:
            key = meta_match.group(1).lower()
            val = meta_match.group(2).strip()
            block.metadata[key] = val
            if key == "feedback":
                saw_legacy_feedback = True
                legacy_feedback_line = line_no
            elif key == "hint":
                saw_legacy_hint = True
                legacy_hint_line = line_no
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

        # Detect leakage: if regular text lines appear AFTER a legacy single-line Feedback: or Hint:
        if (saw_legacy_feedback or saw_legacy_hint) and not block.legacy_leak_warning:
            leaked_field = "Feedback:" if saw_legacy_feedback else "Hint:"
            leak_line = legacy_feedback_line if saw_legacy_feedback else legacy_hint_line
            block.legacy_leak_warning = (
                f"Content following '{leaked_field}' was absorbed into the question prompt. "
                f"To write multi-paragraph explanations or solutions, use '### Feedback' or '### Hint'."
            )
            block.legacy_leak_line = leak_line


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

    # Feedback: prefer ### Feedback section over legacy single-line Feedback:
    if block.has_h3_feedback:
        feedback = "\n".join(block.feedback_lines).strip() or None
        feedback_title = block.feedback_title
    else:
        feedback = block.metadata.get("feedback") or DEFAULTS["feedback"]
        feedback_title = None

    # Hint: prefer ### Hint section over legacy single-line Hint:
    if block.has_h3_hint:
        hint = "\n".join(block.hint_lines).strip() or None
        hint_title = block.hint_title
    else:
        hint = block.metadata.get("hint") or DEFAULTS["hint"]
        hint_title = None

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

    # Reconstruct raw Markdown source for this question block (heading + raw lines)
    raw_lines_text = "\n".join(line for _, line in block.raw_lines).strip()
    if raw_lines_text:
        question_markdown = f"## {block.title}\n\n{raw_lines_text}"
    else:
        question_markdown = f"## {block.title}"

    common_kwargs = {
        "title": block.title,
        "prompt": prompt,
        "points": points,
        "feedback": feedback,
        "feedback_title": feedback_title,
        "hint": hint,
        "hint_title": hint_title,
        "identifier": identifier,
        "line_number": block.start_line,
        "topic": topic,
        "keywords": keywords,
        "additional_info": additional_info,
        "language": language,
        "shuffle": q_shuffle,
        "warning_message": block.legacy_leak_warning,
        "raw_markdown": question_markdown,
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

    # Check for text entry vs dropdown gaps vs hottext mutual exclusivity
    has_text_gaps = bool(RE_GAP.search(prompt))
    has_dropdown_gaps = bool(RE_DROPDOWN_GAP.search(prompt))
    hottext_items = _parse_hottexts(prompt)
    has_hottexts = bool(hottext_items)

    if has_text_gaps and has_dropdown_gaps:
        raise QuizValidationError(
            "Cannot mix open text gaps {{...}} and dropdown gaps {[...]} in the same question (OpenOLAT does not support mixed cloze tests).",
            [Diagnostic(
                "Cannot mix open text gaps {{...}} and dropdown gaps {[...]} in the same question (OpenOLAT does not support mixed cloze tests).",
                Severity.ERROR,
                block.start_line,
                q_idx,
            )],
        )

    if has_hottexts and (has_text_gaps or has_dropdown_gaps):
        conflict_type = "open text gaps {{...}}" if has_text_gaps else "dropdown gaps {[...]}"
        raise QuizValidationError(
            f"Cannot mix hottext tokens and {conflict_type} in the same question.",
            [Diagnostic(
                f"Cannot mix hottext tokens and {conflict_type} in the same question.",
                Severity.ERROR,
                block.start_line,
                q_idx,
            )],
        )

    if has_dropdown_gaps and (block.choices or block.kprim_items or block.is_kprim_mode or block.order_items or block.numerical is not None):
        raise QuizValidationError(
            "Cannot combine dropdown gaps {[...]} with choices, Kprim, Order, or numerical answers in the same question.",
            [Diagnostic(
                "Cannot combine dropdown gaps {[...]} with choices, Kprim, Order, or numerical answers in the same question.",
                Severity.ERROR,
                block.start_line,
                q_idx,
            )],
        )

    if has_hottexts and (block.choices or block.kprim_items or block.is_kprim_mode or block.order_items or block.numerical is not None):
        raise QuizValidationError(
            "Cannot combine hottext tokens with choices, Kprim, Order, or numerical answers in the same question.",
            [Diagnostic(
                "Cannot combine hottext tokens with choices, Kprim, Order, or numerical answers in the same question.",
                Severity.ERROR,
                block.start_line,
                q_idx,
            )],
        )


    # Check for association table (| Item | Match | or | Item | Drag |)
    assoc_info = _extract_association_table(block.prompt_lines, block.start_line, q_idx)
    has_assoc_table = assoc_info is not None

    if has_assoc_table:
        if has_text_gaps or has_dropdown_gaps or has_hottexts:
            raise QuizValidationError(
                "Cannot mix association table with cloze gaps or hottext in the same question.",
                [Diagnostic(
                    "Cannot mix association table with cloze gaps or hottext in the same question.",
                    Severity.ERROR,
                    block.start_line,
                    q_idx,
                )],
            )
        if block.choices or block.kprim_items or block.is_kprim_mode or block.order_items or block.numerical is not None:
            raise QuizValidationError(
                "Cannot combine association table with choice markers, Kprim, Order, or numerical answers in the same question.",
                [Diagnostic(
                    "Cannot combine association table with choice markers, Kprim, Order, or numerical answers in the same question.",
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
        elif explicit_type in ("inlinechoice", "dropdown", "select", "ic"):
            dd_gaps = _parse_dropdown_gaps(prompt, question_shuffle=q_shuffle)
            return InlineChoiceQuestion(**common_kwargs, gaps=dd_gaps)
        elif explicit_type in ("hottext", "ht"):
            ht_kwargs = dict(common_kwargs)
            if q_scoring is not None:
                ht_kwargs["scoring"] = q_scoring
            return HottextQuestion(**ht_kwargs, items=hottext_items)
        elif explicit_type in ("match", "drag", "matchdraganddrop", "draganddrop", "dnd"):
            if not has_assoc_table:
                raise QuizValidationError(
                    f"Question marked as '{explicit_type}' requires an association table (| Item | Match | or | Item | Drag |).",
                    [Diagnostic(f"Question marked as '{explicit_type}' requires an association table (| Item | Match | or | Item | Drag |).", Severity.ERROR, block.start_line, q_idx)],
                )
            detected_interaction, rem_prompt_lines, items, targets, inferred_multiple = assoc_info
            forced_interaction = "drag" if "drag" in explicit_type or explicit_type == "dnd" else "match"
            assoc_prompt = "\n".join(rem_prompt_lines).strip() or block.title
            assoc_kwargs = dict(common_kwargs)
            assoc_kwargs["prompt"] = assoc_prompt
            if q_scoring is not None:
                assoc_kwargs["scoring"] = q_scoring
            return AssociationQuestion(
                **assoc_kwargs,
                interaction=forced_interaction,
                items=items,
                targets=targets,
                multiple=inferred_multiple,
            )
        elif explicit_type in ("numerical", "num"):
            val, tol = (block.numerical[0], block.numerical[1]) if block.numerical else (0.0, 0.0)
            return NumericalQuestion(**common_kwargs, answer=val, tolerance=tol)
        elif explicit_type == "kprim":
            stmts = [KprimStatement(text=it[1], is_correct=it[0]) for it in block.kprim_items]
            return KprimQuestion(**common_kwargs, statements=stmts)
        elif explicit_type in ("order", "sequence", "sequencing"):
            items = [OrderItem(text=it[0]) for it in block.order_items]
            return OrderQuestion(**common_kwargs, items=items)

    # 2. Inferred: Association Table (Match / Drag & Drop)
    if has_assoc_table:
        detected_interaction, rem_prompt_lines, items, targets, inferred_multiple = assoc_info
        assoc_prompt = "\n".join(rem_prompt_lines).strip() or block.title
        assoc_kwargs = dict(common_kwargs)
        assoc_kwargs["prompt"] = assoc_prompt
        if q_scoring is not None:
            assoc_kwargs["scoring"] = q_scoring
        return AssociationQuestion(
            **assoc_kwargs,
            interaction=detected_interaction,
            items=items,
            targets=targets,
            multiple=inferred_multiple,
        )

    # 3. Inferred: Order / Sequencing (N. [ ] ...)
    if block.order_items:
        items = [OrderItem(text=it[0]) for it in block.order_items]
        return OrderQuestion(**common_kwargs, items=items)

    # 4. Inferred: Kprim
    if block.is_kprim_mode or block.kprim_items:
        stmts = [KprimStatement(text=it[1], is_correct=it[0]) for it in block.kprim_items]
        return KprimQuestion(**common_kwargs, statements=stmts)

    # 5. Inferred: Inline Choice / Dropdown
    if has_dropdown_gaps:
        dd_gaps = _parse_dropdown_gaps(prompt, question_shuffle=q_shuffle)
        return InlineChoiceQuestion(**common_kwargs, gaps=dd_gaps)

    # 6. Inferred: Fill-in-the-Blank (Text Entry)
    gaps_found = _parse_gaps(prompt)
    if gaps_found:
        return FillBlankQuestion(**common_kwargs, gaps=gaps_found)

    # 7. Inferred: Hottext
    if has_hottexts:
        ht_kwargs = dict(common_kwargs)
        if q_scoring is not None:
            ht_kwargs["scoring"] = q_scoring
        return HottextQuestion(**ht_kwargs, items=hottext_items)


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
