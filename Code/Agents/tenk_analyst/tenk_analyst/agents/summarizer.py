from typing import List
from ..models.qualitative import QualResult
from ..models.quantitative import QuantResult
from ..models.summary import SummaryReport

class SummarizerAgent:
    """Combines qualitative and quantitative findings into a single report."""

    def combine(self, cik: str, accession: str,
                qual: List[QualResult], quant: List[QuantResult]) -> SummaryReport:
        tones = [q.tone for q in qual]
        if tones:
            key_tone = max(set(tones), key=tones.count)
        else:
            key_tone = "neutral"

        top_risks = [s.label for q in qual for s in q.signals if s.label == "risk"][:5]
        fin = [f"margin={q.margin}" for q in quant if q.margin is not None][:5]

        return SummaryReport(
            company_cik=cik,
            accession=accession,
            key_tone=key_tone,
            top_risks=top_risks,
            financial_highlights=fin,
            qualitative=qual,
            quantitative=quant
        )
