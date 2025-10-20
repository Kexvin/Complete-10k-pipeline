from pydantic import BaseModel
from typing import List, Literal, Dict, Optional

Tone = Literal["positive", "neutral", "negative"]

class QualSignal(BaseModel):
    label: str                  # e.g., "risk", "tone", "management_efficiency"
    evidence: str               # evidence sentence or span
    context: Optional[str] = None  # additional context like similar companies

class SimilarCompany(BaseModel):
    company: str
    tone: Tone
    similarity: float

class QualResult(BaseModel):
    chunk_id: str
    tone: Tone = "neutral"
    signals: List[QualSignal] = []
    similar_companies: List[SimilarCompany] = []
