"""Typed internal domain model for QTI-Creator.

Rule: Parsing and QTI generation should remain independent. Do not generate
QTI directly while parsing Markdown. The parser produces a typed intermediate
model where each question class enforces its own domain invariants.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional
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
class InlineChoice:
    """An option in an inline choice / dropdown gap."""
    text: str
    is_correct: bool
    identifier: str = field(default_factory=lambda: generate_id("inline_choice"))


@dataclass
class InlineChoiceGap:
    """A dropdown gap containing multiple options."""
    choices: List[InlineChoice] = field(default_factory=list)
    identifier: str = field(default_factory=lambda: generate_id("gap"))
    shuffle: Optional[bool] = None


@dataclass
class HottextItem:
    """A selectable hottext span in a HottextQuestion."""
    text: str
    is_correct: bool
    identifier: str = field(default_factory=lambda: generate_id("ht"))



@dataclass
class Question:
    """Base question class."""
    prompt: str
    title: str = ""
    points: float = field(default_factory=lambda: DEFAULTS["points"])
    feedback: Optional[str] = None
    feedback_title: Optional[str] = None
    hint: Optional[str] = None
    hint_title: Optional[str] = None
    identifier: str = field(default_factory=lambda: generate_id("item"))
    line_number: Optional[int] = None
    topic: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    additional_info: Optional[str] = None
    language: Optional[str] = None
    shuffle: Optional[bool] = None
    warning_message: Optional[str] = None
    raw_markdown: str = ""

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
    scoring: str = field(default_factory=lambda: DEFAULTS["mc_scoring"])  # 'partial' or 'all-correct'

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
        scoring_raw = (self.scoring or "").strip().lower()
        if scoring_raw in ("all-correct", "all_correct", "allcorrect"):
            self.scoring = "all-correct"
        elif scoring_raw in ("points-per-answer", "per-answer", "points_per_answer", "per_answer"):
            self.scoring = "per-answer"
        elif scoring_raw in ("partial", ""):
            self.scoring = "partial"
        else:
            raise QuizValidationError(
                f"Invalid scoring method '{self.scoring}' for Multiple Choice. Supported: 'partial', 'all-correct', 'per-answer'.",
                [Diagnostic(f"Invalid scoring method '{self.scoring}' for Multiple Choice. Supported: 'partial', 'all-correct', 'per-answer'.", Severity.ERROR, self.line_number)],
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
class InlineChoiceQuestion(Question):
    """Inline Choice / Dropdown: One or more {[option1|option2]} placeholders in prompt."""
    gaps: List[InlineChoiceGap] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if not self.gaps:
            raise QuizValidationError(
                "Inline Choice question requires at least one {[...]} dropdown gap.",
                [Diagnostic("Inline Choice question requires at least one {[...]} dropdown gap.", Severity.ERROR, self.line_number)],
            )
        for idx, gap in enumerate(self.gaps):
            if len(gap.choices) < 2:
                raise QuizValidationError(
                    f"Dropdown gap {idx + 1} requires at least 2 options, found {len(gap.choices)}.",
                    [Diagnostic(f"Dropdown gap {idx + 1} requires at least 2 options, found {len(gap.choices)}.", Severity.ERROR, self.line_number)],
                )
            for c in gap.choices:
                if not c.text.strip():
                    raise QuizValidationError(
                        f"Dropdown gap {idx + 1} contains an empty option.",
                        [Diagnostic(f"Dropdown gap {idx + 1} contains an empty option.", Severity.ERROR, self.line_number)],
                    )
            correct_count = sum(1 for c in gap.choices if c.is_correct)
            if correct_count != 1:
                raise QuizValidationError(
                    f"Dropdown gap {idx + 1} requires exactly 1 correct answer, found {correct_count}.",
                    [Diagnostic(f"Dropdown gap {idx + 1} requires exactly 1 correct answer, found {correct_count}.", Severity.ERROR, self.line_number)],
                )


@dataclass
class HottextQuestion(Question):
    """Hottext: Text containing selectable words/phrases marked as correct or incorrect."""
    items: List[HottextItem] = field(default_factory=list)
    scoring: Optional[str] = None  # "partial", "all-correct", "per-answer"

    @property
    def correct_items(self) -> List[HottextItem]:
        return [it for it in self.items if it.is_correct]

    @property
    def incorrect_items(self) -> List[HottextItem]:
        return [it for it in self.items if not it.is_correct]

    def validate(self) -> None:
        super().validate()
        if not self.items:
            raise QuizValidationError(
                "Hottext question requires at least one selectable { hottext } element.",
                [Diagnostic("Hottext question requires at least one selectable { hottext } element.", Severity.ERROR, self.line_number)],
            )
        for idx, item in enumerate(self.items):
            if not item.text.strip():
                raise QuizValidationError(
                    f"Hottext item {idx + 1} has empty text.",
                    [Diagnostic(f"Hottext item {idx + 1} has empty text.", Severity.ERROR, self.line_number)],
                )
        correct_count = sum(1 for it in self.items if it.is_correct)
        if correct_count == 0:
            raise QuizValidationError(
                "Hottext question must have at least one correct hottext element.",
                [Diagnostic("Hottext question must have at least one correct hottext element.", Severity.ERROR, self.line_number)],
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
class OrderItem:
    """An item to be ordered in an Order/Sequencing question."""
    text: str
    identifier: str = field(default_factory=lambda: generate_id("order_item"))


@dataclass
class OrderQuestion(Question):
    """Order / Sequencing: Target sequence defined by source order."""
    items: List[OrderItem] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        min_items = DEFAULTS["order_min_items"]
        if len(self.items) < min_items:
            raise QuizValidationError(
                f"Order question requires at least {min_items} items, found {len(self.items)}.",
                [Diagnostic(f"Order question requires at least {min_items} items, found {len(self.items)}.", Severity.ERROR, self.line_number)],
            )


@dataclass
class AssociationTarget:
    """A target category / column choice in an AssociationQuestion (Match or Drag)."""
    text: str
    identifier: str = field(default_factory=lambda: generate_id("target"))


@dataclass
class AssociationItem:
    """A source item / row in an AssociationQuestion (Match or Drag)."""
    text: str
    target_ids: List[str] = field(default_factory=list)
    identifier: str = field(default_factory=lambda: generate_id("source"))


@dataclass
class AssociationQuestion(Question):
    """Association question: Match or Drag & Drop rendered from association tables."""
    interaction: Literal["match", "drag"] = "match"
    items: List[AssociationItem] = field(default_factory=list)
    targets: List[AssociationTarget] = field(default_factory=list)
    multiple: bool = False
    scoring: Optional[str] = None  # "partial", "all-correct", "per-answer"

    def validate(self) -> None:
        super().validate()
        if not self.items:
            raise QuizValidationError(
                "Association question requires at least one source Item.",
                [Diagnostic("Association question requires at least one source Item.", Severity.ERROR, self.line_number)],
            )
        if not self.targets:
            raise QuizValidationError(
                "Association question requires at least one target category.",
                [Diagnostic("Association question requires at least one target category.", Severity.ERROR, self.line_number)],
            )
        target_id_set = {t.identifier for t in self.targets}
        for idx, item in enumerate(self.items):
            if not item.text.strip():
                raise QuizValidationError(
                    f"Association item {idx + 1} has empty text.",
                    [Diagnostic(f"Association item {idx + 1} has empty text.", Severity.ERROR, self.line_number)],
                )
            if not item.target_ids:
                raise QuizValidationError(
                    f"Association item '{item.text}' has no target associations.",
                    [Diagnostic(f"Association item '{item.text}' has no target associations.", Severity.ERROR, self.line_number)],
                )
            for tid in item.target_ids:
                if tid not in target_id_set:
                    raise QuizValidationError(
                        f"Association item '{item.text}' references unknown target ID '{tid}'.",
                        [Diagnostic(f"Association item '{item.text}' references unknown target ID '{tid}'.", Severity.ERROR, self.line_number)],
                    )
        for idx, t in enumerate(self.targets):
            if not t.text.strip():
                raise QuizValidationError(
                    f"Association target {idx + 1} has empty text.",
                    [Diagnostic(f"Association target {idx + 1} has empty text.", Severity.ERROR, self.line_number)],
                )


@dataclass
class InvalidQuestion(Question):
    """Question that failed validation during parsing but is retained for preview."""
    errors: List[Diagnostic] = field(default_factory=list)
    raw_text: str = ""

    def __post_init__(self):
        # Bypass parent points check and validate() at construction time
        if not self.title:
            self.title = "⚠️ Invalid Question"

    def validate(self) -> None:
        """Raise stored diagnostics so Section/Quiz aggregation picks them up."""
        if self.errors:
            raise QuizValidationError("Invalid question", self.errors)


@dataclass
class Section:
    """An assessment section within a Quiz (<assessmentSection>)."""
    title: str = ""
    description: Optional[str] = None
    questions: List[Question] = field(default_factory=list)
    identifier: str = field(default_factory=lambda: generate_id("section"))
    line_number: Optional[int] = None

    def validate(self) -> List[Diagnostic]:
        """Validate this section and all questions within it."""
        diagnostics: List[Diagnostic] = []
        if self.title:
            from src.markdown import contains_markdown
            if contains_markdown(self.title):
                diagnostics.append(
                    Diagnostic(
                        f"Section title '{self.title}' contains Markdown syntax. OpenOLAT does not format Markdown in section titles; it will be displayed as raw text.",
                        Severity.WARNING,
                        self.line_number,
                    )
                )
        for idx, q in enumerate(self.questions):
            if q.title and contains_markdown(q.title):
                diagnostics.append(
                    Diagnostic(
                        f"Question title '{q.title}' contains Markdown or math syntax. OpenOLAT does not format Markdown or math in question titles; it will be displayed as raw text.",
                        Severity.WARNING,
                        q.line_number,
                        question_index=idx,
                    )
                )
            try:
                q.validate()
            except QuizValidationError as e:
                for diag in e.diagnostics:
                    diag.question_index = idx
                    diagnostics.append(diag)
        return diagnostics


class Quiz:
    """Top-level Quiz container."""

    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        questions: Optional[List[Question]] = None,
        sections: Optional[List[Section]] = None,
        identifier: Optional[str] = None,
        language: Optional[str] = None,
        version: Optional[str] = None,
        topic: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        additional_info: Optional[str] = None,
        shuffle: bool = True,
        mc_scoring: Optional[str] = None,
    ):

        self.title = title or DEFAULTS["quiz_title"]
        self.description = description
        self.identifier = identifier or generate_id("quiz")
        self.language = language or DEFAULTS["language"]
        self.version = version or DEFAULTS["quiz_version"]
        self.topic = topic
        self.keywords = keywords or []
        self.additional_info = additional_info
        self.shuffle = shuffle
        self.mc_scoring = mc_scoring or DEFAULTS["mc_scoring"]

        if sections is not None:
            self.sections = list(sections)
            if questions:
                # If both provided, append loose questions to last section or create default
                if not self.sections:
                    self.sections.append(Section(title=self.title, questions=list(questions)))
                else:
                    self.sections[-1].questions.extend(questions)
        elif questions is not None:
            self.sections = [Section(title=self.title, questions=list(questions))]
        else:
            # Default to one section with the quiz title so quiz.questions.append(...) works directly
            self.sections = [Section(title=self.title, questions=[])]

    @property
    def questions(self) -> List[Question]:
        """List of questions in the primary section, or flattened if multiple sections."""
        if len(self.sections) == 1:
            return self.sections[0].questions
        all_q: List[Question] = []
        for s in self.sections:
            all_q.extend(s.questions)
        return all_q

    @questions.setter
    def questions(self, value: List[Question]) -> None:
        """Setting questions sets them on the default / primary section."""
        if not self.sections:
            self.sections = [Section(title=self.title, questions=list(value))]
        else:
            self.sections[0].questions = list(value)

    def validate(self) -> List[Diagnostic]:
        """Validate the entire quiz and return all diagnostics."""
        diagnostics: List[Diagnostic] = []
        if not self.questions:
            diagnostics.append(Diagnostic("Quiz contains no questions.", Severity.WARNING))
        for s in self.sections:
            diagnostics.extend(s.validate())
        return diagnostics
