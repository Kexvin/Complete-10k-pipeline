from typing import List, Optional
import re
from decimal import Decimal
from Code.Assets.Tools.finance.ratios import (
    compute_debt_ratio,
    compute_fcf,
    compute_margin,
    _parse_first_number
)
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk
from Code.Agents.tenk_analyst.tenk_analyst.models.quantitative import QuantResult


class QuantitativeAgent:
    """Extracts financial metrics and ratios from text."""

    def extract_amount(self, text: str, keywords: List[str]) -> Optional[float]:
        """Extract numeric amount from text if it contains any of the keywords."""
        text_lower = text.lower()
        if not any(kw.lower() in text_lower for kw in keywords):
            return None
            
        # Match numbers with M/B suffixes and commas
        match = re.search(r'\$?\s*([\d,]+\.?\d*)\s*([MB]?)', text)
        if not match:
            return None
            
        number = float(match.group(1).replace(',', ''))
        suffix = match.group(2)
        
        if suffix == 'B':
            number *= 1000000000
        elif suffix == 'M':
            number *= 1000000
            
        return number

    def run(self, chunks: List[Chunk]) -> List[QuantResult]:
        results: List[QuantResult] = []
        
        # First pass: extract raw financial numbers
        revenue = None
        net_income = None
        operating_cash_flow = None
        capex = None
        total_assets = None
        total_liabilities = None

        for chunk in chunks:
            text = chunk.text
            
            # Revenue
            if revenue is None:
                revenue = self.extract_amount(text, ["revenue", "net sales"])
                
            # Net Income
            if net_income is None:
                net_income = self.extract_amount(text, ["net income", "net earnings"])
                
            # Operating Cash Flow    
            if operating_cash_flow is None:
                operating_cash_flow = self.extract_amount(text, 
                    ["operating cash flow", "cash from operations"])
                    
            # Capital Expenditures
            if capex is None:
                capex = self.extract_amount(text,
                    ["capital expenditures", "capex", "property, plant and equipment additions"])
                    
            # Total Assets
            if total_assets is None:
                total_assets = self.extract_amount(text, ["total assets"])
                
            # Total Liabilities
            if total_liabilities is None:
                total_liabilities = self.extract_amount(text, ["total liabilities"])

        # Second pass: compute ratios and create results
        for chunk in chunks:
            metrics = []
            
            # Add raw metrics if found in this chunk
            if revenue:
                metrics.append(f"Revenue: ${revenue:,.2f}")
            if net_income:
                metrics.append(f"Net Income: ${net_income:,.2f}")
            if operating_cash_flow:
                metrics.append(f"Operating Cash Flow: ${operating_cash_flow:,.2f}")
            if capex:
                metrics.append(f"Capital Expenditures: ${capex:,.2f}")
                
            # Compute derived metrics
            debt_ratio = compute_debt_ratio(chunk.text, total_liabilities, total_assets)
            fcf = compute_fcf(chunk.text, operating_cash_flow, capex)
            margin = compute_margin(chunk.text, revenue, net_income)
            
            if debt_ratio:
                metrics.append(f"Debt Ratio: {debt_ratio:.2%}")
            if fcf:
                metrics.append(f"Free Cash Flow: ${fcf:,.2f}")
            if margin:
                metrics.append(f"Net Margin: {margin:.2%}")

            results.append(QuantResult(
                chunk_id=chunk.id,
                metrics=metrics,
                debt_ratio=debt_ratio,
                free_cash_flow=fcf,
                net_margin=margin,
                revenue=revenue,
                net_income=net_income,
                operating_cash_flow=operating_cash_flow,
                capex=capex,
                total_assets=total_assets,
                total_liabilities=total_liabilities
            ))

        return results

