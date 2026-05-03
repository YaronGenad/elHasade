import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Characters that are meaningful in LLM prompt context and must not come from user input:
#   \n \r \t  — allow injecting new instruction paragraphs
#   **  ##     — mimic system-prompt markdown formatting
#   ` (backtick) — code blocks / template delimiters
#   < >        — XML/HTML tag injection (used for structural separation markers)
_INJECTION_RE = re.compile(r'[\n\r\t]|\*\*|##|`|<[^>]*>|<|>')


def _sanitize(value: str) -> str:
    """Strip prompt-injection characters and normalize whitespace."""
    value = _INJECTION_RE.sub(' ', value)
    return re.sub(r' {2,}', ' ', value).strip()


class GenerationRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1, max_length=500)
    grade: str = Field(..., min_length=1, max_length=20)
    rounds: int = Field(default=4, ge=1, le=10)
    force_new: bool = Field(
        default=False,
        description="Skip cache/similarity checks and always generate fresh materials",
    )

    @field_validator('subject', 'topic', 'grade', mode='before')
    @classmethod
    def sanitize_text_fields(cls, v: str) -> str:
        return _sanitize(str(v))


class SimilarQueryResult(BaseModel):
    generation_id: str
    subject: str
    topic: str
    grade: str
    rounds: int
    similarity_score: float
    created_at: Optional[datetime] = None
    status: str


class GenerationResponse(BaseModel):
    generation_id: str
    status: str
    message: str
    from_cache: bool = False
    similar_queries: List[SimilarQueryResult] = []


class GenerationStatusResponse(BaseModel):
    generation_id: str
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    subject: str
    topic: str
    grade: str
    rounds: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    material_id: Optional[str] = None  # set when status == "completed"
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None


class GenerationListItem(BaseModel):
    generation_id: str
    status: str
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    subject: str
    topic: str
    grade: str
    rounds: int


class GenerationListResponse(BaseModel):
    generations: List[GenerationListItem]
    limit: int
    offset: int


# ── Approval / versions (Sprint 4.5) ─────────────────────────────────────────

class MaterialApprovalResponse(BaseModel):
    status: str           # "approved" | "rejected"
    material_id: str
    approval_count: Optional[int] = None


class MaterialVersionItem(BaseModel):
    material_id: str
    version: int
    approval_count: int
    times_served: int
    subject: str
    topic: str
    grade: str
    created_at: Optional[datetime] = None


class MaterialVersionsResponse(BaseModel):
    subject: str
    topic: str
    grade: str
    versions: List[MaterialVersionItem]
