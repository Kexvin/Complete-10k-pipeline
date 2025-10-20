from pydantic import BaseModel
from typing import Optional

class QuantResult(BaseModel):
    chunk_id: str
    debt_ratio: Optional[float] = None
    fcf: Optional[float] = None
    margin: Optional[float] = None
    notes: Optional[str] = None
