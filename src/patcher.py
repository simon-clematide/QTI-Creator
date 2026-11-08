"""Source patching engine for revision-safe AST/span updates to QuizMD source.

Used by the interactive Hotspot Visual Editor (Milestone 3) to update, add,
toggle, or delete hotspot regions without disturbing surrounding questions,
hints, feedback, or custom markdown formatting.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Literal, Optional, Tuple

from src.model import HotspotQuestion, HotspotRegion
from src.parser import parse_quizmd


def compute_source_hash(source: str) -> str:
    """Compute deterministic SHA-256 hash of QuizMD source text."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def format_shape_call(
    shape: Literal["rect", "circle"],
    coords: Tuple[float, ...],
    unit: Literal["px", "pct"],
) -> str:
    """Format shape function call expression, e.g. 'circle(65%, 60%, 10%)' or 'rect(100, 200, 300, 400)'."""
    formatted_coords: List[str] = []
    for c in coords:
        if unit == "pct":
            # Format cleanly: omit trailing .0 if integer percentage
            val = round(c, 1)
            val_str = str(int(val)) if val == int(val) else f"{val:.1f}"
            formatted_coords.append(f"{val_str}%")
        else:
            formatted_coords.append(str(int(round(c))))
    return f"{shape}({', '.join(formatted_coords)})"


def _find_hotspot_question(quiz, q_idx: int) -> Optional[HotspotQuestion]:
    """Find the q_idx-th question (1-based) if it is a HotspotQuestion."""
    if q_idx < 1 or q_idx > len(quiz.questions):
        return None
    q = quiz.questions[q_idx - 1]
    if isinstance(q, HotspotQuestion):
        return q
    return None


def patch_hotspot_coordinates(
    source: str,
    question_idx: int,
    region_idx: int,
    new_shape: Literal["rect", "circle"],
    new_coords: Tuple[float, ...],
    unit: Optional[Literal["px", "pct"]] = None,
    expected_hash: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Update coordinates of an existing hotspot region using its exact shape_span.

    Returns:
      (new_source, error_message)
    """
    if expected_hash and compute_source_hash(source) != expected_hash:
        return source, "Source text was modified since preview was generated. Please refresh."

    quiz, _ = parse_quizmd(source)
    hq = _find_hotspot_question(quiz, question_idx)
    if not hq:
        return source, f"Question #{question_idx} is not a valid Hotspot question."

    if region_idx < 1 or region_idx > len(hq.regions):
        return source, f"Region #{region_idx} not found in question #{question_idx}."

    region = hq.regions[region_idx - 1]
    if not region.source_location or not region.source_location.shape_span:
        return source, f"Source location span missing for region #{region_idx}."

    target_unit = unit or region.unit
    new_shape_str = format_shape_call(new_shape, new_coords, target_unit)

    span = region.source_location.shape_span
    old_slice = source[span.start_offset : span.end_offset]

    # Sanity check: Ensure span begins with a shape keyword
    if not re.match(r"^(rect|rectangle|circle)", old_slice.strip(), re.IGNORECASE):
        return source, f"Source span offset mismatch (expected shape expression, found '{old_slice[:20]}...')."

    new_source = source[: span.start_offset] + new_shape_str + source[span.end_offset :]
    return new_source, None


def toggle_hotspot_correctness(
    source: str,
    question_idx: int,
    region_idx: int,
    expected_hash: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Toggle correctness marker between correct and distractor.

    Single-choice questions ([X]):
      Toggling a distractor to correct unmarks the previous [X] region so exactly 1 is correct.
    Multiple-choice questions ([x]):
      Toggles [x] <-> [ ].

    Returns:
      (new_source, error_message)
    """
    if expected_hash and compute_source_hash(source) != expected_hash:
        return source, "Source text was modified since preview was generated. Please refresh."

    quiz, _ = parse_quizmd(source)
    hq = _find_hotspot_question(quiz, question_idx)
    if not hq:
        return source, f"Question #{question_idx} is not a valid Hotspot question."

    if region_idx < 1 or region_idx > len(hq.regions):
        return source, f"Region #{region_idx} not found in question #{question_idx}."

    target_region = hq.regions[region_idx - 1]
    if not target_region.source_location:
        return source, f"Source location span missing for region #{region_idx}."

    # If single-choice and target is distractor, unmark existing [X] region first
    edits: List[Tuple[int, int, str]] = []  # (start, end, replacement)

    if not hq.multiple:
        # Single choice: ensure only target_region becomes [X]
        if target_region.correct:
            return source, "Single-choice hotspot question must have at least one correct [X] region."
        # Unmark current correct region(s)
        for r in hq.regions:
            if r.correct and r.source_location:
                line_span = r.source_location.choice_span
                line_text = source[line_span.start_offset : line_span.end_offset]
                m = re.search(r"-\s*\[([X])\]", line_text)
                if m:
                    rel_start = m.start(1)
                    edits.append((line_span.start_offset + rel_start, line_span.start_offset + rel_start + 1, " "))

        # Mark target region [X]
        target_line_span = target_region.source_location.choice_span
        target_line_text = source[target_line_span.start_offset : target_line_span.end_offset]
        m = re.search(r"-\s*\[([ ])\]", target_line_text)
        if m:
            rel_start = m.start(1)
            edits.append((target_line_span.start_offset + rel_start, target_line_span.start_offset + rel_start + 1, "X"))
    else:
        # Multiple choice: toggle between 'x' and ' '
        target_line_span = target_region.source_location.choice_span
        target_line_text = source[target_line_span.start_offset : target_line_span.end_offset]
        m = re.search(r"-\s*\[([ x])\]", target_line_text)
        if m:
            new_mark = " " if m.group(1) == "x" else "x"
            rel_start = m.start(1)
            edits.append((target_line_span.start_offset + rel_start, target_line_span.start_offset + rel_start + 1, new_mark))

    if not edits:
        return source, "Failed to locate task marker in source text."

    # Apply edits in reverse offset order to keep indices stable
    edits.sort(key=lambda e: e[0], reverse=True)
    patched = source
    for start, end, repl in edits:
        patched = patched[:start] + repl + patched[end:]

    return patched, None


def delete_hotspot_region(
    source: str,
    question_idx: int,
    region_idx: int,
    expected_hash: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Delete an entire region choice line from a HotspotQuestion.

    Returns:
      (new_source, error_message)
    """
    if expected_hash and compute_source_hash(source) != expected_hash:
        return source, "Source text was modified since preview was generated. Please refresh."

    quiz, _ = parse_quizmd(source)
    hq = _find_hotspot_question(quiz, question_idx)
    if not hq:
        return source, f"Question #{question_idx} is not a valid Hotspot question."

    if len(hq.regions) <= 1:
        return source, "Cannot delete the only region in a Hotspot question."

    if region_idx < 1 or region_idx > len(hq.regions):
        return source, f"Region #{region_idx} not found in question #{question_idx}."

    region = hq.regions[region_idx - 1]
    if not region.source_location or not region.source_location.choice_span:
        return source, f"Source location span missing for region #{region_idx}."

    span = region.source_location.choice_span
    start = span.start_offset
    end = span.end_offset

    # Include trailing newline if present to avoid leaving a blank line
    if end < len(source) and source[end] == "\n":
        end += 1
    elif start > 0 and source[start - 1] == "\n" and end == len(source):
        start -= 1

    new_source = source[:start] + source[end:]
    return new_source, None


def add_hotspot_region(
    source: str,
    question_idx: int,
    shape: Literal["rect", "circle"],
    coords: Tuple[float, ...],
    unit: Literal["px", "pct"] = "pct",
    correct: bool = False,
    author_label: str = "",
    expected_hash: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Append a new hotspot region choice line after the last region of question_idx.

    Returns:
      (new_source, error_message)
    """
    if expected_hash and compute_source_hash(source) != expected_hash:
        return source, "Source text was modified since preview was generated. Please refresh."

    quiz, _ = parse_quizmd(source)
    hq = _find_hotspot_question(quiz, question_idx)
    if not hq:
        return source, f"Question #{question_idx} is not a valid Hotspot question."

    # Determine marker style
    if hq.multiple:
        mark = "x" if correct else " "
    else:
        # Single choice: if correct, unmark existing [X] first
        mark = "X" if correct else " "

    shape_call = format_shape_call(shape, coords, unit)
    label_suffix = f" {author_label.strip()}" if author_label.strip() else ""
    new_line = f"- [{mark}] {shape_call}{label_suffix}"

    # Find insertion anchor: after the choice_span of the last region
    last_region = hq.regions[-1]
    if not last_region.source_location:
        return source, "Last region has no source span for insertion anchor."

    insert_offset = last_region.source_location.choice_span.end_offset
    # Ensure there is a newline right after last region line
    prefix = "\n" if not source[:insert_offset].endswith("\n") else ""
    suffix = "\n" if (insert_offset < len(source) and not source[insert_offset:].startswith("\n")) else ""

    patched = source[:insert_offset] + prefix + new_line + suffix + source[insert_offset:]

    # If single-choice and new region is marked correct, unmark previous correct region(s)
    if not hq.multiple and correct:
        re_quiz, _ = parse_quizmd(patched)
        re_hq = _find_hotspot_question(re_quiz, question_idx)
        if re_hq:
            # All regions except the newly added last one should be [ ]
            edits = []
            for r in re_hq.regions[:-1]:
                if r.correct and r.source_location:
                    span = r.source_location.choice_span
                    txt = patched[span.start_offset : span.end_offset]
                    m = re.search(r"-\s*\[([X])\]", txt)
                    if m:
                        rel = m.start(1)
                        edits.append((span.start_offset + rel, span.start_offset + rel + 1, " "))
            edits.sort(key=lambda e: e[0], reverse=True)
            for s, e, repl in edits:
                patched = patched[:s] + repl + patched[e:]

    return patched, None


def update_hotspot_author_label(
    source: str,
    question_idx: int,
    region_idx: int,
    new_label: str,
    expected_hash: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Update only the author label of an existing hotspot region.

    Returns:
      (new_source, error_message)
    """
    if expected_hash and compute_source_hash(source) != expected_hash:
        return source, "Source text was modified since preview was generated. Please refresh."

    quiz, _ = parse_quizmd(source)
    hq = _find_hotspot_question(quiz, question_idx)
    if not hq:
        return source, f"Question #{question_idx} is not a valid Hotspot question."

    if region_idx < 1 or region_idx > len(hq.regions):
        return source, f"Region #{region_idx} not found in question #{question_idx}."

    region = hq.regions[region_idx - 1]
    if not region.source_location or not region.source_location.choice_span or not region.source_location.shape_span:
        return source, f"Source location span missing for region #{region_idx}."

    choice_span = region.source_location.choice_span
    shape_span = region.source_location.shape_span

    # The label is the text between shape_span.end_offset and choice_span.end_offset
    label_start = shape_span.end_offset
    label_end = choice_span.end_offset

    clean_label = f" {new_label.strip()}" if new_label.strip() else ""
    new_source = source[:label_start] + clean_label + source[label_end:]
    return new_source, None
