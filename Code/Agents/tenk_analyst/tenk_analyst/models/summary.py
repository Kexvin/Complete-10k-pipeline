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
    # Structured financials: mapping metric_key -> {value, currency, raw}
    financials: Dict[str, Dict]
    qualitative_analysis: List[QualResult]
    similar_companies: List[Dict] = []
    llm_explanation: str = ""
    sanity_warnings: List[str] = []
    sources: List[dict]
