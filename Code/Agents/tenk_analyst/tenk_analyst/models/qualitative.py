from pydantic import BaseModel
from typing import List, Literal

Tone = Literal["positive", "neutral", "negative"]

class QualSignal(BaseModel):
    label: str                  # e.g., "risk", "management_efficiency", "supply_chain"
    evidence: str               # evidence sentence or span

class QualResult(BaseModel):
    chunk_id: str
    tone: Tone = "neutral"
    signals: List[QualSignal] = []
