"""Centralized defaults for QTI-Creator.

Rule: Defaults should be centralized rather than scattered through the parser
and QTI generator. Changing a default should not require changing the authoring syntax.
"""

from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    # Quiz level defaults
    "language": "en",
    "quiz_title": "Untitled Quiz",
    "quiz_version": "1.0.0",
    
    # Question level defaults
    "points": 1.0,
    "feedback": None,
    "hint": None,
    "shuffle": True,
    "mc_scoring": "partial",  # 'partial' (default) or 'all-correct'
    
    # Kprim specific defaults (Swiss university scoring)
    # 4/4 correct = full points, 3/4 correct = half points, <=2/4 correct = 0 points
    "kprim_full_points": 1.0,
    "kprim_half_points": 0.5,
    "kprim_num_statements": 4,

    # Order question defaults
    "order_min_items": 2,
    
    # Numerical tolerance defaults
    "tolerance": 0.0,
}

