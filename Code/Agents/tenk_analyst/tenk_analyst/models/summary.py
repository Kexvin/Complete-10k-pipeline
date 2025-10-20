from pydantic import BaseModel
from typing import List, Dict
from .qualitative import QualResult
from .quantitative import QuantResult

class SummaryReport(BaseModel):
    company_name: str
    cik: str
    accession: str
    key_tone: str 
    tone_explanation: str
    risks: List[str]
    financials: List[str]
    qualitative_analysis: List[QualResult]
    similar_companies: List[Dict] = []
    llm_explanation: str = ""
    sources: List[dict]
