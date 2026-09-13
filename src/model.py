"""Typed internal domain model for QTI-Creator.

Rule: Parsing and QTI generation should remain independent. Do not generate
QTI directly while parsing Markdown. The parser produces a typed intermediate
model where each question class enforces its own domain invariants.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import uuid

from src.defaults import DEFAULTS
from src.validation import Diagnostic, QuizValidationError, Severity


def generate_id(prefix: str = "id") -> str:
    """Generate a clean, QTI-safe identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class Choice:
    """An alternative in a choice question."""
    text: str
    is_correct: bool
    identifier: str = field(default_factory=lambda: generate_id("choice"))
    feedback: Optional[str] = None


@dataclass
class KprimStatement:
    """One of exactly four statements in a Kprim question."""
    text: str
    is_correct: bool  # True = (+), False = (-)
    identifier: str = field(default_factory=lambda: generate_id("kprim_stmt"))


@dataclass
class Gap:
    """A blank to fill in a text-entry question."""
    expected_value: str
    alternatives: List[str] = field(default_factory=list)
    identifier: str = field(default_factory=lambda: generate_id("gap"))


@dataclass
class Question:
    """Base question class."""
    prompt: str
    title: str = ""
    points: float = field(default_factory=lambda: DEFAULTS["points"])
    feedback: Optional[str] = None
    identifier: str = field(default_factory=lambda: generate_id("item"))
    line_number: Optional[int] = None

    def __post_init__(self):
        if not self.title:
            # Fallback title from first line of prompt
            first_line = self.prompt.strip().split("\n")[0] if self.prompt else "Question"
            self.title = first_line[:60] + "..." if len(first_line) > 60 else first_line
        if self.points <= 0:
            raise QuizValidationError(
                f"Question points must be positive, got {self.points}",
                [Diagnostic(f"Question points must be positive, got {self.points}", Severity.ERROR, self.line_number)],
            )
        self.validate()

    def validate(self) -> None:
        """Enforce domain invariants. Subclasses override this."""
        pass


@dataclass
class SingleChoiceQuestion(Question):
    """Single Choice: Exactly one checked alternative."""
    choices: List[Choice] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if len(self.choices) < 2:
            raise QuizValidationError(
                f"Single Choice requires at least 2 choices, found {len(self.choices)}.",
                [Diagnostic(f"Single Choice requires at least 2 choices, found {len(self.choices)}.", Severity.ERROR, self.line_number)],
            )
        correct_count = sum(1 for c in self.choices if c.is_correct)
        if correct_count != 1:
            raise QuizValidationError(
                f"Single Choice question requires exactly 1 correct answer, found {correct_count}.",
                [Diagnostic(f"Single Choice question requires exactly 1 correct answer, found {correct_count}.", Severity.ERROR, self.line_number)],
            )


@dataclass
class MultipleChoiceQuestion(Question):
    """Multiple Choice: More than one checked alternative (or explicit MC)."""
    choices: List[Choice] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if len(self.choices) < 2:
            raise QuizValidationError(
                f"Multiple Choice requires at least 2 choices, found {len(self.choices)}.",
                [Diagnostic(f"Multiple Choice requires at least 2 choices, found {len(self.choices)}.", Severity.ERROR, self.line_number)],
            )
        correct_count = sum(1 for c in self.choices if c.is_correct)
        if correct_count < 1:
            raise QuizValidationError(
                "Multiple Choice requires at least 1 correct answer marked.",
                [Diagnostic("Multiple Choice requires at least 1 correct answer marked.", Severity.ERROR, self.line_number)],
            )


@dataclass
class TrueFalseQuestion(Question):
    """True/False: Exactly True and False alternatives."""
    choices: List[Choice] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if len(self.choices) != 2:
            raise QuizValidationError(
                f"True/False question requires exactly 2 alternatives, found {len(self.choices)}.",
                [Diagnostic(f"True/False question requires exactly 2 alternatives, found {len(self.choices)}.", Severity.ERROR, self.line_number)],
            )
        texts = [c.text.strip().lower() for c in self.choices]
        if not ("true" in texts and "false" in texts):
            raise QuizValidationError(
                f"True/False alternatives must be 'True' and 'False', found: {[c.text for c in self.choices]}",
                [Diagnostic("True/False alternatives must be 'True' and 'False'.", Severity.ERROR, self.line_number)],
            )
        correct_count = sum(1 for c in self.choices if c.is_correct)
        if correct_count != 1:
            raise QuizValidationError(
                f"True/False requires exactly 1 correct answer, found {correct_count}.",
                [Diagnostic(f"True/False requires exactly 1 correct answer, found {correct_count}.", Severity.ERROR, self.line_number)],
            )


@dataclass
class EssayQuestion(Question):
    """Essay / Free Text: Prompt with no answer specifications."""
    pass


@dataclass
class FillBlankQuestion(Question):
    """Fill-in-the-Blank: One or more {{gap}} placeholders in prompt."""
    gaps: List[Gap] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if not self.gaps:
            raise QuizValidationError(
                "Fill-in-the-Blank question requires at least one {{gap}}.",
                [Diagnostic("Fill-in-the-Blank question requires at least one {{gap}}.", Severity.ERROR, self.line_number)],
            )


@dataclass
class NumericalQuestion(Question):
    """Numerical: Numerical value with optional tolerance."""
    answer: float = 0.0
    tolerance: float = field(default_factory=lambda: DEFAULTS["tolerance"])

    def validate(self) -> None:
        super().validate()
        if self.tolerance < 0:
            raise QuizValidationError(
                f"Tolerance must be non-negative, got {self.tolerance}",
                [Diagnostic(f"Tolerance must be non-negative, got {self.tolerance}", Severity.ERROR, self.line_number)],
            )


@dataclass
class KprimQuestion(Question):
    """Kprim: Exactly four statements, each marked (+) or (-)."""
    statements: List[KprimStatement] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        num = DEFAULTS["kprim_num_statements"]
        if len(self.statements) != num:
            raise QuizValidationError(
                f"Kprim requires exactly {num} statements, found {len(self.statements)}.",
                [Diagnostic(f"Kprim requires exactly {num} statements, found {len(self.statements)}.", Severity.ERROR, self.line_number)],
            )


@dataclass
class Quiz:
    """Top-level Quiz container."""
    title: str = field(default_factory=lambda: DEFAULTS["quiz_title"])
    description: Optional[str] = None
    questions: List[Question] = field(default_factory=list)
    identifier: str = field(default_factory=lambda: generate_id("quiz"))
    language: str = field(default_factory=lambda: DEFAULTS["language"])
    version: str = field(default_factory=lambda: DEFAULTS["quiz_version"])

    def validate(self) -> List[Diagnostic]:
        """Validate the entire quiz and return all diagnostics."""
        diagnostics: List[Diagnostic] = []
        if not self.questions:
            diagnostics.append(Diagnostic("Quiz contains no questions.", Severity.WARNING))
        for idx, q in enumerate(self.questions):
            try:
                q.validate()
            except QuizValidationError as e:
                for diag in e.diagnostics:
                    diag.question_index = idx
                    diagnostics.append(diag)
        return diagnostics
