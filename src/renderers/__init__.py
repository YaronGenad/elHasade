"""
renderers — HTML rendering for Al-HaSadeh station worksheets.

Split from the original monolithic renderers.py for maintainability.
All public render_* functions are re-exported here so that existing
imports (e.g. ``from .renderers import render_comprehension``) continue
to work unchanged.
"""

from .comprehension import render_comprehension
from .methods import render_methods
from .precision import render_precision
from .vocabulary import render_vocabulary
from .teacher import render_teacher_prep, render_answer_key
from .roadmap import render_roadmap

__all__ = [
    "render_comprehension",
    "render_methods",
    "render_precision",
    "render_vocabulary",
    "render_teacher_prep",
    "render_answer_key",
    "render_roadmap",
]
