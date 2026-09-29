"""Quiz difficulty estimation for QTI-Creator.

Computes three heuristic scores for a Quiz, all in the range [0, 1]:

* ``random_score``   – expected fraction of total points earned by a uniform
                       random guesser (the hardness baseline).
* ``shortest_bias``  – fraction earned by a guesser who always selects the
                       shortest answer text (detects length cuing).
* ``longest_bias``   – same, always picking the longest answer.

When multiple choices share the same length (tied), *all* tied choices are
treated as selected.  This is conservative and keeps scores in [0, 1].

Question types that cannot be machine-graded (Essay, Numerical, FillBlank)
are counted as ``skipped`` and excluded from the weighted average.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from src.model import (
    AssociationQuestion,
    EssayQuestion,
    FillBlankQuestion,
    HottextQuestion,
    InlineChoiceQuestion,
    InvalidQuestion,
    KprimQuestion,
    MultipleChoiceQuestion,
    NumericalQuestion,
    OrderQuestion,
    Quiz,
    SingleChoiceQuestion,
    TrueFalseQuestion,
)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class QuestionDifficulty:
    """Difficulty breakdown for a single question."""

    question_index: int
    question_type: str
    points: float
    random_score: float        # expected points, random guesser
    shortest_score: float      # expected points, always pick shortest
    longest_score: float       # expected points, always pick longest
    skipped: bool = False      # True for free-text / numerical questions
    note: str = ""             # e.g. "Kprim options are always length-tied"


@dataclass
class DifficultyReport:
    """Aggregated difficulty scores for a whole quiz.

    All three headline figures are weighted means over *scorable* questions
    (weights = question points).  They are expressed as fractions in [0, 1].
    """

    random_score: float = 0.0
    shortest_bias: float = 0.0
    longest_bias: float = 0.0
    scorable_questions: int = 0
    skipped_questions: int = 0
    per_question: List[QuestionDifficulty] = field(default_factory=list)
    bias_warnings: List[str] = field(default_factory=list)
    """Non-empty when a length-bias strategy outperforms random guessing.

    Each string is a human-readable warning, e.g.:
    ``"Shortest-answer bias (45 %) beats random baseline (31 %): answer length
    may be cueing correct choices."``
    """


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pct(value: float, points: float) -> float:
    """Clamp ``value / points`` to [0, 1], guard against zero-point questions."""
    if points <= 0:
        return 0.0
    return max(0.0, min(1.0, value / points))


def _shortest_indices(texts: List[str]) -> List[int]:
    """Return indices of all strings that share the minimum length."""
    if not texts:
        return []
    min_len = min(len(t) for t in texts)
    return [i for i, t in enumerate(texts) if len(t) == min_len]


def _longest_indices(texts: List[str]) -> List[int]:
    """Return indices of all strings that share the maximum length."""
    if not texts:
        return []
    max_len = max(len(t) for t in texts)
    return [i for i, t in enumerate(texts) if len(t) == max_len]


# ---------------------------------------------------------------------------
# Per-type scoring
# ---------------------------------------------------------------------------

def _score_single_choice(choices, points: float) -> QuestionDifficulty:
    """Single correct answer from n choices."""
    n = len(choices)
    random_pts = points / n if n else 0.0

    texts = [c.text for c in choices]
    correct_idx = next((i for i, c in enumerate(choices) if c.is_correct), None)

    def _bias_pts(bias_indices):
        if correct_idx is None:
            return 0.0
        # If exactly one choice is shortest/longest and it's correct → full points.
        # If multiple tied and correct is among them → we "selected" correct → full.
        return points if correct_idx in bias_indices else 0.0

    short_pts = _bias_pts(_shortest_indices(texts))
    long_pts = _bias_pts(_longest_indices(texts))

    return QuestionDifficulty(
        question_index=-1,
        question_type="single",
        points=points,
        random_score=random_pts,
        shortest_score=short_pts,
        longest_score=long_pts,
    )


def _mc_partial_expected(choices, points: float, selected_mask: List[bool]) -> float:
    """MC partial scoring with a fixed selection mask (True = selected).

    per_correct = points / n_correct  (earn this for each correct selection)
    per_wrong   = points / n_correct  (lose this for each wrong selection)
    Total is floored at 0.
    """
    n_correct = sum(1 for c in choices if c.is_correct)
    if n_correct == 0:
        return 0.0
    per = points / n_correct
    score = 0.0
    for c, sel in zip(choices, selected_mask):
        if sel:
            score += per if c.is_correct else -per
    return max(0.0, score)


def _score_multiple_choice(q: MultipleChoiceQuestion) -> QuestionDifficulty:
    choices = q.choices
    points = q.points
    n = len(choices)
    n_correct = sum(1 for c in choices if c.is_correct)
    n_wrong = n - n_correct
    scoring = q.scoring

    # --- random ---
    if scoring == "all-correct":
        random_pts = (0.5 ** n) * points
    elif scoring == "per-answer":
        # Each correct choice hit with p=0.5, no deduction
        random_pts = points / 2.0
    else:  # partial (default)
        if n_correct == 0:
            random_pts = 0.0
        else:
            random_pts = max(0.0, (points / 2.0) * (n_correct - n_wrong) / n_correct)

    # --- length-biased ---
    texts = [c.text for c in choices]
    correct_set = {i for i, c in enumerate(choices) if c.is_correct}

    def _bias_pts(bias_indices: List[int]) -> float:
        selected = set(bias_indices)
        selected_mask = [i in selected for i in range(n)]
        if scoring == "all-correct":
            return points if selected == correct_set else 0.0
        elif scoring == "per-answer":
            n_correct_selected = sum(1 for i in selected if i in correct_set)
            return (n_correct_selected / n_correct * points) if n_correct else 0.0
        else:  # partial
            return _mc_partial_expected(choices, points, selected_mask)

    short_pts = _bias_pts(_shortest_indices(texts))
    long_pts = _bias_pts(_longest_indices(texts))

    return QuestionDifficulty(
        question_index=-1,
        question_type="multiple_choice",
        points=points,
        random_score=random_pts,
        shortest_score=short_pts,
        longest_score=long_pts,
    )


def _score_kprim(q: KprimQuestion) -> QuestionDifficulty:
    """Kprim: 4 statements, each ± .  Scoring: 4→full, 3→half, ≤2→0."""
    points = q.points
    # Closed-form: P(4/4) = C(4,4)/16 = 1/16, P(3/4) = C(4,3)/16 = 4/16
    # E[score] = 1/16 × points + 4/16 × points/2 = (1 + 2)/16 × points = 3/16 × points
    random_pts = points * (1 / 16 + 4 / 16 * 0.5)  # = 3/16 × points ≈ 0.1875

    # (+) and (-) are 3 chars each → always tied → treat as random
    note = "Kprim ± options are always length-tied; length bias equals random."

    return QuestionDifficulty(
        question_index=-1,
        question_type="kprim",
        points=points,
        random_score=random_pts,
        shortest_score=random_pts,
        longest_score=random_pts,
        note=note,
    )


def _score_hottext(q: HottextQuestion) -> QuestionDifficulty:
    """Hottext: selectable spans with partial or all-correct scoring."""
    items = q.items
    points = q.points
    n = len(items)
    n_correct = sum(1 for it in items if it.is_correct)
    scoring = q.scoring or "partial"

    # --- random ---
    if scoring == "all-correct":
        random_pts = (0.5 ** n) * points
    else:  # partial (default)
        n_wrong = n - n_correct
        if n_correct == 0:
            random_pts = 0.0
        else:
            random_pts = max(0.0, (points / 2.0) * (n_correct - n_wrong) / n_correct)

    # --- length-biased ---
    texts = [it.text for it in items]
    correct_set = {i for i, it in enumerate(items) if it.is_correct}

    def _bias_pts(bias_indices: List[int]) -> float:
        selected = set(bias_indices)
        if scoring == "all-correct":
            return points if selected == correct_set else 0.0
        else:  # partial
            n_correct_sel = sum(1 for i in selected if i in correct_set)
            n_wrong_sel = len(selected) - n_correct_sel
            if n_correct == 0:
                return 0.0
            per = points / n_correct
            return max(0.0, n_correct_sel * per - n_wrong_sel * per)

    short_pts = _bias_pts(_shortest_indices(texts))
    long_pts = _bias_pts(_longest_indices(texts))

    return QuestionDifficulty(
        question_index=-1,
        question_type="hottext",
        points=points,
        random_score=random_pts,
        shortest_score=short_pts,
        longest_score=long_pts,
    )


def _score_inline_choice(q: InlineChoiceQuestion) -> QuestionDifficulty:
    """Inline choice (dropdown): average of per-gap single-choice scores."""
    points = q.points
    gaps = q.gaps
    if not gaps:
        return QuestionDifficulty(
            question_index=-1, question_type="inline_choice", points=points,
            random_score=0.0, shortest_score=0.0, longest_score=0.0, skipped=True,
        )

    # Per gap: exactly one correct, pick one → single-choice logic
    gap_random = 0.0
    gap_short = 0.0
    gap_long = 0.0
    for gap in gaps:
        n = len(gap.choices)
        texts = [c.text for c in gap.choices]
        correct_idx = next((i for i, c in enumerate(gap.choices) if c.is_correct), None)
        gap_random += (1 / n) if n else 0
        gap_short += 1.0 if (correct_idx is not None and correct_idx in _shortest_indices(texts)) else 0.0
        gap_long += 1.0 if (correct_idx is not None and correct_idx in _longest_indices(texts)) else 0.0

    ng = len(gaps)
    return QuestionDifficulty(
        question_index=-1,
        question_type="inline_choice",
        points=points,
        random_score=(gap_random / ng) * points,
        shortest_score=(gap_short / ng) * points,
        longest_score=(gap_long / ng) * points,
    )


def _score_order(q: OrderQuestion) -> QuestionDifficulty:
    """Order/Sequencing: random score = 1/n!, length bias = same as random."""
    points = q.points
    n = len(q.items)
    random_pts = (1 / math.factorial(n)) * points if n > 0 else 0.0
    return QuestionDifficulty(
        question_index=-1,
        question_type="order",
        points=points,
        random_score=random_pts,
        shortest_score=random_pts,
        longest_score=random_pts,
        note="Order questions: length bias not applicable, inherits random score.",
    )


def _score_association(q: AssociationQuestion) -> QuestionDifficulty:
    """Association (Match/Drag): per source item, pick a target."""
    points = q.points
    items = q.items
    targets = q.targets
    n_targets = len(targets)
    if not items or not n_targets:
        return QuestionDifficulty(
            question_index=-1, question_type="association", points=points,
            random_score=0.0, shortest_score=0.0, longest_score=0.0, skipped=True,
        )

    target_texts = [t.text for t in targets]
    target_ids = [t.identifier for t in targets]
    short_tidx = set(_shortest_indices(target_texts))
    long_tidx = set(_longest_indices(target_texts))

    # Score per item: fraction of correct target assignments
    item_random = item_short = item_long = 0.0
    for item in items:
        correct_tidx = {target_ids.index(tid) for tid in item.target_ids if tid in target_ids}
        if not correct_tidx:
            continue
        # Random: pick one target uniformly → P(correct) = |correct| / n_targets
        item_random += len(correct_tidx) / n_targets
        # Shortest: select all shortest-text targets
        item_short += 1.0 if correct_tidx & short_tidx else 0.0
        # Longest: select all longest-text targets
        item_long += 1.0 if correct_tidx & long_tidx else 0.0

    n_items = len(items)
    return QuestionDifficulty(
        question_index=-1,
        question_type="association",
        points=points,
        random_score=(item_random / n_items) * points,
        shortest_score=(item_short / n_items) * points,
        longest_score=(item_long / n_items) * points,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def question_difficulty(q, idx: int) -> QuestionDifficulty:
    """Compute difficulty scores for a single question.

    Args:
        q: Any Question subclass from ``src.model``.
        idx: Zero-based question index (for reporting).

    Returns:
        A :class:`QuestionDifficulty` with ``skipped=True`` for question types
        that cannot be machine-graded.
    """
    skip_types = (EssayQuestion, NumericalQuestion, FillBlankQuestion, InvalidQuestion)
    if isinstance(q, skip_types):
        return QuestionDifficulty(
            question_index=idx,
            question_type=type(q).__name__,
            points=q.points,
            random_score=0.0,
            shortest_score=0.0,
            longest_score=0.0,
            skipped=True,
        )

    if isinstance(q, (SingleChoiceQuestion, TrueFalseQuestion)):
        result = _score_single_choice(q.choices, q.points)
    elif isinstance(q, MultipleChoiceQuestion):
        result = _score_multiple_choice(q)
    elif isinstance(q, KprimQuestion):
        result = _score_kprim(q)
    elif isinstance(q, HottextQuestion):
        result = _score_hottext(q)
    elif isinstance(q, InlineChoiceQuestion):
        result = _score_inline_choice(q)
    elif isinstance(q, OrderQuestion):
        result = _score_order(q)
    elif isinstance(q, AssociationQuestion):
        result = _score_association(q)
    else:
        # Unknown future type — skip
        return QuestionDifficulty(
            question_index=idx,
            question_type=type(q).__name__,
            points=q.points,
            random_score=0.0,
            shortest_score=0.0,
            longest_score=0.0,
            skipped=True,
            note="Unknown question type — skipped.",
        )

    result.question_index = idx
    result.question_type = type(q).__name__
    return result


def quiz_difficulty(quiz: Quiz) -> DifficultyReport:
    """Compute difficulty scores for an entire quiz.

    Args:
        quiz: A validated :class:`~src.model.Quiz` instance.

    Returns:
        A :class:`DifficultyReport` with weighted-average headline scores and
        per-question breakdowns.
    """
    per_q: List[QuestionDifficulty] = []
    for idx, q in enumerate(quiz.questions):
        per_q.append(question_difficulty(q, idx))

    scorable = [qd for qd in per_q if not qd.skipped]
    skipped = [qd for qd in per_q if qd.skipped]

    total_pts = sum(qd.points for qd in scorable)

    if not scorable or total_pts == 0:
        return DifficultyReport(
            scorable_questions=len(scorable),
            skipped_questions=len(skipped),
            per_question=per_q,
        )

    def _weighted_mean(attr: str) -> float:
        return sum(getattr(qd, attr) for qd in scorable) / total_pts

    random = round(_weighted_mean("random_score"), 4)
    shortest = round(_weighted_mean("shortest_score"), 4)
    longest = round(_weighted_mean("longest_score"), 4)

    # Warn when a length-bias strategy meaningfully outperforms random guessing.
    # A 0.5 pp noise floor avoids false positives from floating-point rounding.
    _EPS = 0.005
    warnings: List[str] = []
    if shortest - random > _EPS:
        warnings.append(
            f"Shortest-answer bias ({shortest * 100:.0f}\u202f%) beats the random "
            f"baseline ({random * 100:.0f}\u202f%): answer length may be cueing "
            f"correct choices."
        )
    if longest - random > _EPS:
        warnings.append(
            f"Longest-answer bias ({longest * 100:.0f}\u202f%) beats the random "
            f"baseline ({random * 100:.0f}\u202f%): answer length may be cueing "
            f"correct choices."
        )

    return DifficultyReport(
        random_score=random,
        shortest_bias=shortest,
        longest_bias=longest,
        scorable_questions=len(scorable),
        skipped_questions=len(skipped),
        per_question=per_q,
        bias_warnings=warnings,
    )
