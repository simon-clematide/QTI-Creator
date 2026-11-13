"""QTI-Creator programmatic API.

Exposes headless QuizMD validation, JQTI+ engine checks, QTI 2.1 package
generation, and Anki export without requiring Gradio to be installed.
"""

from qti_creator.api import (
    check_quiz_api,
    export_anki_api,
    export_qti_api,
    validate_jqti_api,
)
from qti_creator.core.version import __release_date__, __version__

__all__ = [
    "__version__",
    "__release_date__",
    "check_quiz_api",
    "validate_jqti_api",
    "export_qti_api",
    "export_anki_api",
]
