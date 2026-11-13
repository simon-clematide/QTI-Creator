"""Typed internal domain model for QTI-Creator.

Rule: Parsing and QTI generation should remain independent. Do not generate
QTI directly while parsing Markdown. The parser produces a typed intermediate
model where each question class enforces its own domain invariants.
"""

from dataclasses import dataclass, field
import math
from typing import List, Literal, Optional, Tuple
import uuid

from qti_creator.core.defaults import DEFAULTS
from qti_creator.core.markdown import find_gaps_in_math
from qti_creator.core.validation import Diagnostic, QuizValidationError, Severity


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
        gaps_in_math = find_gaps_in_math(self.prompt)
        if gaps_in_math:
            diagnostics_list = [
                Diagnostic(
                    f"Gap '{g_tok}' is located inside LaTeX math delimiters ('{m_span}'). "
                    f"OpenOLAT cannot render interactive input widgets inside MathJax formulas. "
                    f"Move the gap outside the math delimiters.",
                    Severity.ERROR,
                    self.line_number,
                )
                for _, g_tok, m_span in gaps_in_math
            ]
            raise QuizValidationError(diagnostics_list[0].message, diagnostics_list)


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
        gaps_in_math = find_gaps_in_math(self.prompt)
        if gaps_in_math:
            diagnostics_list = [
                Diagnostic(
                    f"Dropdown gap '{g_tok}' is located inside LaTeX math delimiters ('{m_span}'). "
                    f"OpenOLAT cannot render interactive input widgets inside MathJax formulas. "
                    f"Move the gap outside the math delimiters.",
                    Severity.ERROR,
                    self.line_number,
                )
                for _, g_tok, m_span in gaps_in_math
            ]
            raise QuizValidationError(diagnostics_list[0].message, diagnostics_list)
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


@dataclass(frozen=True)
class SourceSpan:
    """Character offset span within the QuizMD document."""
    start_offset: int
    end_offset: int
    line_number: Optional[int] = None


@dataclass(frozen=True)
class HotspotSourceLocation:
    """Source spans for a hotspot region choice and its shape(...) expression."""
    choice_span: SourceSpan
    shape_span: SourceSpan


@dataclass
class HotspotRegion:
    """A clickable region in a HotspotQuestion."""
    shape: Literal["rect", "circle", "poly"]
    coordinates: Tuple[float, ...]
    unit: Literal["px", "pct"]
    correct: bool
    author_label: str = ""
    identifier: str = ""
    source_location: Optional[HotspotSourceLocation] = None

    def resolve_pixel_coords(self, width: int, height: int) -> Tuple[int, ...]:
        """Convert region coordinates to integer pixel coordinates for an image of (width, height)."""
        if self.unit == "px":
            if self.shape == "circle":
                cx, cy, r = self.coordinates
                return (int(round(cx)), int(round(cy)), max(1, int(round(r))))
            return tuple(int(round(v)) for v in self.coordinates)
        # Percentage conversion:
        if self.shape == "rect":
            x1_pct, y1_pct, x2_pct, y2_pct = self.coordinates
            return (
                int(round((x1_pct / 100.0) * width)),
                int(round((y1_pct / 100.0) * height)),
                int(round((x2_pct / 100.0) * width)),
                int(round((y2_pct / 100.0) * height)),
            )
        elif self.shape == "circle":
            cx_pct, cy_pct, r_pct = self.coordinates
            min_dim = min(width, height)
            return (
                int(round((cx_pct / 100.0) * width)),
                int(round((cy_pct / 100.0) * height)),
                max(1, int(round((r_pct / 100.0) * min_dim))),
            )
        else:
            pts = []
            for idx, val in enumerate(self.coordinates):
                dim = width if idx % 2 == 0 else height
                pts.append(int(round((val / 100.0) * dim)))
            return tuple(pts)


@dataclass
class HotspotQuestion(Question):
    """Hotspot Image question: Clickable graphical regions over a packaged image."""
    image_src: str = ""
    image_alt: str = ""
    declared_width: Optional[int] = None
    declared_height: Optional[int] = None
    regions: List[HotspotRegion] = field(default_factory=list)
    multiple: bool = False
    scoring: str = field(default_factory=lambda: DEFAULTS["mc_scoring"])  # 'partial' or 'all-correct'

    def validate(self) -> None:
        super().validate()
        if not self.image_src or not self.image_src.strip():
            raise QuizValidationError(
                "Hotspot question requires a standalone background image ![alt](src).",
                [Diagnostic("Hotspot question requires a standalone background image ![alt](src).", Severity.ERROR, self.line_number)],
            )
        if not self.regions:
            raise QuizValidationError(
                "Hotspot question requires at least 1 hotspot region.",
                [Diagnostic("Hotspot question requires at least 1 hotspot region.", Severity.ERROR, self.line_number)],
            )

        # Deterministic identifier assignment & uniqueness check within question
        seen_ids = set()
        for idx, region in enumerate(self.regions, start=1):
            if not region.identifier:
                region.identifier = f"hc_{idx}"
            if region.identifier in seen_ids:
                line_no = (
                    region.source_location.choice_span.line_number
                    if (region.source_location and region.source_location.choice_span.line_number)
                    else self.line_number
                )
                raise QuizValidationError(
                    f"Duplicate hotspot region identifier '{region.identifier}'.",
                    [Diagnostic(f"Duplicate hotspot region identifier '{region.identifier}'.", Severity.ERROR, line_no)],
                )
            seen_ids.add(region.identifier)

        correct_count = sum(1 for r in self.regions if r.correct)
        if not self.multiple:
            if correct_count != 1:
                raise QuizValidationError(
                    f"Single-choice Hotspot question requires exactly 1 correct region, found {correct_count}.",
                    [Diagnostic(f"Single-choice Hotspot question requires exactly 1 correct region, found {correct_count}.", Severity.ERROR, self.line_number)],
                )
            if len(self.regions) == 1 and not self.warning_message:
                self.warning_message = "Single-choice Hotspot question has only 1 region (no distractor regions defined)."
        else:
            if correct_count < 1:
                raise QuizValidationError(
                    "Multiple-choice Hotspot question requires at least 1 correct region.",
                    [Diagnostic("Multiple-choice Hotspot question requires at least 1 correct region.", Severity.ERROR, self.line_number)],
                )

        # Stage 1 raw coordinate validation (no cross-axis percentage subtraction at parse time)
        seen_raw_regions = set()
        for idx, r in enumerate(self.regions, start=1):
            r_line = (
                r.source_location.choice_span.line_number
                if (r.source_location and r.source_location.choice_span.line_number)
                else self.line_number
            )
            if r.shape == "poly":
                raise QuizValidationError(
                    f"Hotspot region {idx}: polygon shape ('poly') is not yet supported in Milestone 1. Use 'rect(...)' or 'circle(...)'.",
                    [Diagnostic(f"Hotspot region {idx}: polygon shape ('poly') is not yet supported in Milestone 1. Use 'rect(...)' or 'circle(...)'.", Severity.ERROR, r_line)],
                )
            if r.shape not in ("rect", "circle"):
                raise QuizValidationError(
                    f"Hotspot region {idx}: unsupported shape '{r.shape}'. Supported shapes: 'rect', 'circle'.",
                    [Diagnostic(f"Hotspot region {idx}: unsupported shape '{r.shape}'. Supported shapes: 'rect', 'circle'.", Severity.ERROR, r_line)],
                )
            if r.unit not in ("px", "pct"):
                raise QuizValidationError(
                    f"Hotspot region {idx}: invalid coordinate unit '{r.unit}'.",
                    [Diagnostic(f"Hotspot region {idx}: invalid coordinate unit '{r.unit}'.", Severity.ERROR, r_line)],
                )
            if any(not math.isfinite(c) for c in r.coordinates):
                raise QuizValidationError(
                    f"Hotspot region {idx}: coordinates must be finite numbers.",
                    [Diagnostic(f"Hotspot region {idx}: coordinates must be finite numbers.", Severity.ERROR, r_line)],
                )

            if r.shape == "rect":
                if len(r.coordinates) != 4:
                    raise QuizValidationError(
                        f"Hotspot region {idx}: 'rect' requires 4 coordinates (x1, y1, x2, y2), got {len(r.coordinates)}.",
                        [Diagnostic(f"Hotspot region {idx}: 'rect' requires 4 coordinates (x1, y1, x2, y2), got {len(r.coordinates)}.", Severity.ERROR, r_line)],
                    )
                x1, y1, x2, y2 = r.coordinates
                if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
                    raise QuizValidationError(
                        f"Hotspot region {idx}: rectangle coordinates must be non-negative, got ({x1}, {y1}, {x2}, {y2}).",
                        [Diagnostic(f"Hotspot region {idx}: rectangle coordinates must be non-negative, got ({x1}, {y1}, {x2}, {y2}).", Severity.ERROR, r_line)],
                    )
                if x1 >= x2 or y1 >= y2:
                    raise QuizValidationError(
                        f"Hotspot region {idx}: rectangle requires x1 < x2 and y1 < y2, got ({x1}, {y1}, {x2}, {y2}).",
                        [Diagnostic(f"Hotspot region {idx}: rectangle requires x1 < x2 and y1 < y2, got ({x1}, {y1}, {x2}, {y2}).", Severity.ERROR, r_line)],
                    )
                if r.unit == "pct" and (x2 > 100.0 or y2 > 100.0):
                    raise QuizValidationError(
                        f"Hotspot region {idx}: percentage rectangle coordinates must be within 0%..100%, got ({x1}%, {y1}%, {x2}%, {y2}%).",
                        [Diagnostic(f"Hotspot region {idx}: percentage rectangle coordinates must be within 0%..100%, got ({x1}%, {y1}%, {x2}%, {y2}%).", Severity.ERROR, r_line)],
                    )
            elif r.shape == "circle":
                if len(r.coordinates) != 3:
                    raise QuizValidationError(
                        f"Hotspot region {idx}: 'circle' requires 3 coordinates (cx, cy, r), got {len(r.coordinates)}.",
                        [Diagnostic(f"Hotspot region {idx}: 'circle' requires 3 coordinates (cx, cy, r), got {len(r.coordinates)}.", Severity.ERROR, r_line)],
                    )
                cx, cy, rad = r.coordinates
                if cx < 0 or cy < 0:
                    raise QuizValidationError(
                        f"Hotspot region {idx}: circle center coordinates must be non-negative, got ({cx}, {cy}).",
                        [Diagnostic(f"Hotspot region {idx}: circle center coordinates must be non-negative, got ({cx}, {cy}).", Severity.ERROR, r_line)],
                    )
                if rad <= 0:
                    raise QuizValidationError(
                        f"Hotspot region {idx}: circle radius must be positive (> 0), got {rad}.",
                        [Diagnostic(f"Hotspot region {idx}: circle radius must be positive (> 0), got {rad}.", Severity.ERROR, r_line)],
                    )
                if r.unit == "pct" and (cx > 100.0 or cy > 100.0 or rad > 100.0):
                    raise QuizValidationError(
                        f"Hotspot region {idx}: percentage circle values must be within 0%..100%, got ({cx}%, {cy}%, {rad}%).",
                        [Diagnostic(f"Hotspot region {idx}: percentage circle values must be within 0%..100%, got ({cx}%, {cy}%, {rad}%).", Severity.ERROR, r_line)],
                    )

            raw_key = (r.shape, r.unit, tuple(round(c, 6) for c in r.coordinates))
            if raw_key in seen_raw_regions:
                raise QuizValidationError(
                    f"Hotspot region {idx}: duplicate region definition ({r.shape} with identical coordinates).",
                    [Diagnostic(f"Hotspot region {idx}: duplicate region definition ({r.shape} with identical coordinates).", Severity.ERROR, r_line)],
                )
            seen_raw_regions.add(raw_key)

        scoring_raw = (self.scoring or "").strip().lower()
        if scoring_raw in ("all-correct", "all_correct", "allcorrect"):
            self.scoring = "all-correct"
        elif scoring_raw in ("partial", ""):
            self.scoring = "partial"
        elif scoring_raw in ("points-per-answer", "per-answer", "points_per_answer", "per_answer"):
            raise QuizValidationError(
                f"Scoring method '{self.scoring}' is not supported for Hotspot questions in Milestone 1. Supported: 'partial', 'all-correct'.",
                [Diagnostic(f"Scoring method '{self.scoring}' is not supported for Hotspot questions in Milestone 1. Supported: 'partial', 'all-correct'.", Severity.ERROR, self.line_number)],
            )
        else:
            raise QuizValidationError(
                f"Invalid scoring method '{self.scoring}' for Hotspot question. Supported: 'partial', 'all-correct'.",
                [Diagnostic(f"Invalid scoring method '{self.scoring}' for Hotspot question. Supported: 'partial', 'all-correct'.", Severity.ERROR, self.line_number)],
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
            from qti_creator.core.markdown import contains_markdown
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
                if isinstance(q, HotspotQuestion) and not q.multiple and len(q.regions) == 1:
                    diagnostics.append(
                        Diagnostic(
                            "Single-choice Hotspot question has only 1 region (no distractor regions defined).",
                            Severity.WARNING,
                            q.line_number,
                            question_index=idx,
                        )
                    )
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
