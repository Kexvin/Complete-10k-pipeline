from pydantic import BaseModel
from typing import List
from .qualitative import QualResult
from .quantitative import QuantResult

class SummaryReport(BaseModel):
    company_cik: str
    accession: str
    key_tone: str
    top_risks: List[str]
    financial_highlights: List[str]
    qualitative: List[QualResult]
    quantitative: List[QuantResult]
