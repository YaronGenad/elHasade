"""
prompts — LLM prompt builders for Al-HaSadeh station generation.

Split by edition (Hebrew, STEAM, English, Math) for maintainability.
All build_*_prompt functions are re-exported here so existing
imports continue to work unchanged.
"""

from .hebrew import (
    build_roadmap_prompt,
    build_comprehension_prompt,
    build_methods_prompt,
    build_precision_prompt,
    build_vocabulary_prompt,
    build_teacher_prep_prompt,
)
from .steam import (
    build_stem_roadmap_prompt,
    build_stem_comprehension_prompt,
    build_stem_methods_prompt,
    build_stem_precision_prompt,
    build_stem_vocabulary_prompt,
    build_stem_teacher_prep_prompt,
)
from .english import (
    build_english_roadmap_prompt,
    build_english_comprehension_prompt,
    build_english_methods_prompt,
    build_english_precision_prompt,
    build_english_vocabulary_prompt,
    build_english_teacher_prep_prompt,
)
from .math import (
    build_math_roadmap_prompt,
    build_math_comprehension_prompt,
    build_math_methods_prompt,
    build_math_precision_prompt,
    build_math_vocabulary_prompt,
    build_math_teacher_prep_prompt,
)

__all__ = [
    "build_roadmap_prompt",
    "build_comprehension_prompt",
    "build_methods_prompt",
    "build_precision_prompt",
    "build_vocabulary_prompt",
    "build_teacher_prep_prompt",
    "build_stem_roadmap_prompt",
    "build_stem_comprehension_prompt",
    "build_stem_methods_prompt",
    "build_stem_precision_prompt",
    "build_stem_vocabulary_prompt",
    "build_stem_teacher_prep_prompt",
    "build_english_roadmap_prompt",
    "build_english_comprehension_prompt",
    "build_english_methods_prompt",
    "build_english_precision_prompt",
    "build_english_vocabulary_prompt",
    "build_english_teacher_prep_prompt",
    "build_math_roadmap_prompt",
    "build_math_comprehension_prompt",
    "build_math_methods_prompt",
    "build_math_precision_prompt",
    "build_math_vocabulary_prompt",
    "build_math_teacher_prep_prompt",
]
