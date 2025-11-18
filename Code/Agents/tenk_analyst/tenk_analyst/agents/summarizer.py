import os
from typing import List, Dict, Any

from ..models.qualitative import QualResult
from ..models.quantitative import QuantResult
from ..models.summary import SummaryReport
from Code.Assets.Tools.llm.openai_client import LLMClient
from Code.Assets.Tools.rag.pinecone_client import RAG  # for RAG chunks


class SummarizerAgent:
    """Combines qualitative and quantitative findings into a single report."""

    # ────────────────────────────────────────────────────────────────────
    # Public entry point
    # ────────────────────────────────────────────────────────────────────

    def combine(
        self,
        company_name: str,
        cik: str,
        accession: str,
        qual: List[QualResult],
        quant: List[QuantResult],
    ) -> SummaryReport:
        # 1) Aggregate tone from qualitative results
        tones = [q.tone for q in qual]
        if tones:
            key_tone = max(set(tones), key=tones.count)
        else:
            key_tone = "neutral"

        # 2) Collect unique risk signals with evidence
        risks: List[str] = []
        seen_evidence = set()
        for q_res in qual:
            for s in q_res.signals:
                if s.label == "risk" and s.evidence not in seen_evidence:
                    risks.append(s.evidence)
                    seen_evidence.add(s.evidence)
        risks = risks[:5]  # top 5 evidences

        # 3) Build structured financial metrics primarily from QuantResult numeric fields
        financials_struct: Dict[str, Dict[str, Any]] = {}

        def add_metric(key: str, label: str, value: Any, currency: str = "USD", is_percent: bool = False):
            """Helper to add a metric into financials_struct in a consistent way."""
            if value is None:
                return
            if is_percent:
                # value is expected as a fraction, e.g. 0.7948 → 79.48%
                raw = f"{label}: {value * 100:.2f}%"
                num_value = float(value)  # store as fraction (0.7948)
                curr = None
            else:
                raw = f"{label}: ${value:,.0f}"
                num_value = float(value)
                curr = currency
            financials_struct[key] = {
                "value": num_value,
                "currency": curr,
                "raw": raw,
            }

        # Use the first QuantResult as the primary source for numeric financials
        primary_q: QuantResult | None = quant[0] if quant else None
        if primary_q is not None:
            add_metric("revenue", "Revenue", primary_q.revenue)
            add_metric("net_income", "Net Income", primary_q.net_income)
            add_metric("operating_cash_flow", "Operating Cash Flow", primary_q.operating_cash_flow)
            add_metric("capital_expenditures", "Capital Expenditures", primary_q.capex)
            add_metric("total_assets", "Total Assets", primary_q.total_assets)
            add_metric("total_liabilities", "Total Liabilities", primary_q.total_liabilities)
            add_metric("free_cash_flow", "Free Cash Flow", primary_q.free_cash_flow)
            add_metric("debt_ratio", "Debt Ratio", primary_q.debt_ratio, currency=None, is_percent=True)
            add_metric("net_margin", "Net Margin", primary_q.net_margin, currency=None, is_percent=True)

        # 3b) Parse free-form metric strings as a fallback / to capture extras
        #     (e.g., if future QuantResults add more metrics but we haven't wired them above yet)
        seen_metric_keys = set(financials_struct.keys())
        for q_res in quant:
            for metric in q_res.metrics:
                parts = metric.split(":", 1)
                if len(parts) != 2:
                    continue
                metric_name_raw = parts[0].strip()
                metric_key = metric_name_raw.lower().replace(" ", "_")
                if metric_key in seen_metric_keys:
                    continue  # already filled from numeric fields
                raw_val = parts[1].strip()
                value = None
                currency = None

                try:
                    # Handle percentages like "79.48%"
                    numeric_token = raw_val
                    # strip leading label decorations like "$"
                    numeric_token = numeric_token.replace("$", "").replace(",", "")
                    # take first whitespace-separated chunk
                    numeric_token = numeric_token.split()[0]
                    # strip parentheses used for negatives
                    numeric_token = numeric_token.replace("(", "-").replace(")", "")
                    # strip percent sign if present
                    is_percent = False
                    if "%" in numeric_token:
                        is_percent = True
                        numeric_token = numeric_token.replace("%", "")
                    value_float = float(numeric_token)

                    if is_percent:
                        # store as fraction (0.7948 for 79.48%)
                        value = value_float / 100.0
                        currency = None
                    else:
                        value = value_float
                        currency = "USD" if "$" in raw_val else None
                except Exception:
                    value = None
                    currency = None

                financials_struct[metric_key] = {
                    "value": value,
                    "currency": currency,
                    "raw": metric,
                }
                seen_metric_keys.add(metric_key)

        # Limit to top 12 metrics to keep things sane
        if len(financials_struct) > 12:
            keys = list(financials_struct.keys())[:12]
            financials_struct = {k: financials_struct[k] for k in keys}

        # 4) Document sources
        from datetime import datetime
        now_iso = datetime.utcnow().isoformat()
        sources = [
            {
                "type": "SEC_EDGAR_API",
                "name": "SEC EDGAR API",
                "url": "https://www.sec.gov/edgar",
                "version": "1.0",
                "retrieved_at": now_iso,
                "notes": "10-K Filing Data",
            }
        ]

        # 5) Collect similar companies from QualResult
        similar_companies: List[Dict[str, Any]] = []
        for q_res in qual:
            for sc in getattr(q_res, "similar_companies", []) or []:
                if sc.company not in [c["name"] for c in similar_companies]:
                    similar_companies.append(
                        {
                            "name": sc.company,
                            "tone": sc.tone,
                            "similarity": sc.similarity,
                        }
                    )

        # 6) Retrieve RAG chunks for this specific filing (risk factors, market risk, financials)
        rag_chunks: List[Dict[str, Any]] = []
        try:
            # IMPORTANT: use the same collection / namespace config as the rest of the pipeline.
            # Do NOT hard-code a different namespace (this is why Apple looked too generic).
            collection_name = os.getenv("PINECONE_COLLECTION", "knowledgepinecone")
            rag = RAG(collection=collection_name)  # no custom namespace; match indexing

            queries = [
                "key risk factors and business risks in this 10-K",
                "quantitative and qualitative disclosures about market risk",
                "management discussion and analysis key points",
                "overall financial statements, performance, and critical audit matters",
            ]
            for qtext in queries:
                res = rag.query_filing(
                    cik=cik,
                    accession=accession,
                    query_text=qtext,
                    top_k=3,
                )
                for m in res.get("matches", []):
                    meta = m.get("metadata") or {}
                    rag_chunks.append(
                        {
                            "id": m.get("id"),
                            "score": m.get("score"),
                            "section": meta.get("section") or meta.get("content_type"),
                            "text": meta.get("text"),
                        }
                    )
        except Exception as e:
            print(f"Warning: failed to retrieve RAG chunks for {cik} {accession}: {e}")

        # 7) Generate LLM explanation using qualitative + financials + RAG chunks
        llm = LLMClient()
        qual_dicts = [q_res.dict() for q_res in qual]

        llm_explanation = llm.explain_company_with_rag(
            company_name=company_name,
            cik=cik,
            accession=accession,
            key_tone=key_tone,
            risks=risks,
            financials=financials_struct,
            qual_results=qual_dicts,
            similar_companies=similar_companies,
            rag_chunks=rag_chunks,
        )

        # Extract a clean one-line tone summary
        tone_explanation = self._extract_tone_summary(llm_explanation)

        # 8) Sanity checks: detect implausible net margins
        sanity_warnings: List[str] = []
        ni_val = financials_struct.get("net_income", {}).get("value")
        rev_val = financials_struct.get("revenue", {}).get("value")
        if ni_val is not None and rev_val is not None and rev_val != 0:
            net_margin_pct = (ni_val / rev_val) * 100.0
            if abs(net_margin_pct) > 300:
                sanity_warnings.append(f"Unusual net margin detected: {net_margin_pct:.2f}%")

        # 9) Build SummaryReport Pydantic model
        return SummaryReport(
            company_name=company_name,
            cik=cik,
            accession=accession,
            key_tone=key_tone,
            tone_explanation=tone_explanation,
            risks=risks,
            financials=financials_struct,
            qualitative_analysis=qual,
            similar_companies=similar_companies,
            llm_explanation=llm_explanation,
            sources=sources,
            sanity_warnings=sanity_warnings,
        )

    # ────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_tone_summary(llm_text: str) -> str:
        """
        Pull out a good one-line tone summary from the full LLM explanation.

        Heuristics:
        - Prefer lines that explicitly describe the tone in a sentence
          (e.g. 'The overall tone of the filing is ...').
        - Skip section headings like '4. Tone & Overall Assessment'.
        - Otherwise, fall back to the first reasonably long sentence-like line.
        """
        if not llm_text:
            return ""

        # Non-empty trimmed lines
        lines = [ln.strip() for ln in llm_text.splitlines() if ln.strip()]
        if not lines:
            return ""

        def looks_like_heading(line: str) -> bool:
            lower = line.lower()
            # e.g. "4. Tone & Overall Assessment"
            if lower.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
                return True
            # very short and title-ish
            if len(line) < 30 and line.endswith(("Assessment", "Overview", "Tone")):
                return True
            return False

        # 1) Look for a line that clearly describes the overall tone
        for ln in lines:
            lower = ln.lower()
            if "overall tone" in lower and not looks_like_heading(ln):
                # This should catch e.g. "The overall tone of the filing is labeled as neutral..."
                return ln

        # 2) Look for any non-heading line that includes 'tone' and looks like a sentence
        for ln in lines:
            lower = ln.lower()
            if "tone" in lower and not looks_like_heading(ln) and len(ln) >= 40:
                if any(ch in ln for ch in ".!?"):
                    return ln

        # 3) Otherwise pick the first non-heading, reasonably long sentence-like line
        for ln in lines:
            if looks_like_heading(ln):
                continue
            if len(ln) >= 40 and any(ch in ln for ch in ".!?"):
                return ln

        # 4) Fallbacks
        if len(lines) == 1:
            return lines[0]
        return " ".join(lines[:2])