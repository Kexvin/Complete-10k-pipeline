from typing import List
from ..models.qualitative import QualResult
from ..models.quantitative import QuantResult
from ..models.summary import SummaryReport
from Code.Assets.Tools.llm.openai_client import LLMClient

class SummarizerAgent:
    """Combines qualitative and quantitative findings into a single report."""

    def combine(self, company_name: str, cik: str, accession: str,
                qual: List[QualResult], quant: List[QuantResult]) -> SummaryReport:
        tones = [q.tone for q in qual]
        if tones:
            key_tone = max(set(tones), key=tones.count)
        else:
            key_tone = "neutral"

        # Collect unique risk signals with evidence
        risks = []
        seen_evidence = set()
        for q in qual:
            for s in q.signals:
                if s.label == "risk" and s.evidence not in seen_evidence:
                    risks.append(s.evidence)
                    seen_evidence.add(s.evidence)
        
        # Get top 5 most significant risks
        risks = risks[:5]
        
        # Collect unique financial metrics
        financials = []
        seen_metrics = set()
        for q in quant:
            for metric in q.metrics:
                metric_key = metric.split(":")[0]
                if metric_key not in seen_metrics:
                    financials.append(metric)
                    seen_metrics.add(metric_key)
        
        # Get top 10 most significant financials
        financials = financials[:10]

        # Document sources
        sources = [{
            "type": "SEC_EDGAR_API",
            "name": "SEC EDGAR API",
            "url": "https://www.sec.gov/edgar",
            "version": "1.0",
            "retrieved_at": "2025-10-20",
            "notes": "10-K Filing Data"
        }]

        # Collect similar companies (if any) referenced in qual results
        similar_companies = []
        for q in qual:
            for sc in getattr(q, 'similar_companies', []) or []:
                if sc.company not in [c['name'] for c in similar_companies]:
                    similar_companies.append({
                        'name': sc.company,
                        'tone': sc.tone,
                        'similarity': sc.similarity
                    })

        # Generate LLM explanation (falls back to deterministic if API not available)
        llm = LLMClient()
        # Prepare qual results as dicts
        qual_dicts = [q.dict() for q in qual]
        llm_explanation = llm.explain_qualitative(company_name, qual_dicts, similar_companies)

        return SummaryReport(
            company_name=company_name,
            cik=cik,
            accession=accession,
            key_tone=key_tone,
            tone_explanation=llm_explanation.split('\n')[0] if llm_explanation else "",
            risks=risks,
            financials=financials,
            qualitative_analysis=qual,
            similar_companies=similar_companies,
            llm_explanation=llm_explanation,
            sources=sources
        )
