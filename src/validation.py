"""Validation and diagnostic messaging for QTI-Creator."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Diagnostic:
    message: str
    severity: Severity = Severity.ERROR
    line_number: Optional[int] = None
    question_index: Optional[int] = None

    def __str__(self) -> str:
        loc = []
        if self.question_index is not None:
            loc.append(f"Question {self.question_index + 1}")
        if self.line_number is not None:
            loc.append(f"line {self.line_number}")
        prefix = f"[{self.severity.value.upper()}] "
        if loc:
            prefix += f"({', '.join(loc)}): "
        return f"{prefix}{self.message}"


class QuizValidationError(Exception):
    """Exception raised when a question or quiz violates domain invariants."""

    def __init__(self, message: str, diagnostics: Optional[List[Diagnostic]] = None):
        super().__init__(message)
        self.diagnostics = diagnostics or [Diagnostic(message=message)]
