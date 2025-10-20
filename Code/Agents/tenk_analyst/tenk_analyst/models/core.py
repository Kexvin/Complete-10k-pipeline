from pydantic import BaseModel
from typing import Literal, Optional

Route = Literal["qualitative", "quantitative"]

class Chunk(BaseModel):
    id: str
    company_cik: str
    accession: str
    section: Optional[str] = None
    text: str

class RoutedChunk(BaseModel):
    chunk: Chunk
    route: Route
