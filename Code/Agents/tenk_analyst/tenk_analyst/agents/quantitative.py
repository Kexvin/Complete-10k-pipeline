from typing import List, Optional
from Code.Assets.Tools.finance.ratios import (
    compute_debt_ratio,
    compute_fcf,
    compute_margin
)
from Code.Assets.Tools.io.kaggle_data import KaggleFinancialData
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk
from Code.Agents.tenk_analyst.tenk_analyst.models.quantitative import QuantResult


class QuantitativeAgent:
    """Extracts financial metrics from Kaggle dataset and computes ratios."""
    
    def __init__(self, kaggle_csv_path: str = "Data/Primary/kaggle_facts/companyfacts.csv"):
        self.kaggle_data = KaggleFinancialData(kaggle_csv_path)

    def run(self, chunks: List[Chunk], company_cik: str = None) -> List[QuantResult]:
        """Extract financial metrics from Kaggle dataset for the company.
        
        Args:
            chunks: List of chunks (not used since we get data from Kaggle)
            company_cik: The CIK of the company to analyze
            
        Returns:
            List with a single QuantResult containing all metrics
        """
        if not company_cik:
            # Try to extract CIK from chunk metadata if available
            return [QuantResult(chunk_id="no_cik", metrics=[])]
            
        # Get latest financial metrics from Kaggle dataset
        metrics_data = self.kaggle_data.get_latest_metrics(company_cik)
        
        if not metrics_data:
            return [QuantResult(chunk_id=company_cik, metrics=["No financial data available"])]
        
        # Extract values
        revenue = metrics_data.get('revenue')
        net_income = metrics_data.get('net_income')
        total_assets = metrics_data.get('total_assets')
        total_liabilities = metrics_data.get('total_liabilities')
        operating_cash_flow = metrics_data.get('operating_cash_flow')
        capex = metrics_data.get('capex')
        
        # Build metrics list
        metrics = []
        if revenue:
            metrics.append(f"Revenue: ${revenue:,.0f}")
        if net_income:
            metrics.append(f"Net Income: ${net_income:,.0f}")
        if operating_cash_flow:
            metrics.append(f"Operating Cash Flow: ${operating_cash_flow:,.0f}")
        if capex:
            metrics.append(f"Capital Expenditures: ${capex:,.0f}")
        if total_assets:
            metrics.append(f"Total Assets: ${total_assets:,.0f}")
        if total_liabilities:
            metrics.append(f"Total Liabilities: ${total_liabilities:,.0f}")
            
        # Compute derived metrics using ratios module
        debt_ratio = None
        if total_liabilities and total_assets and total_assets != 0:
            debt_ratio = total_liabilities / total_assets
            metrics.append(f"Debt Ratio: {debt_ratio:.2%}")
            
        fcf = None
        if operating_cash_flow and capex:
            fcf = operating_cash_flow - capex
            metrics.append(f"Free Cash Flow: ${fcf:,.0f}")
            
        net_margin = None
        if revenue and net_income and revenue != 0:
            net_margin = net_income / revenue
            metrics.append(f"Net Margin: {net_margin:.2%}")

        result = QuantResult(
            chunk_id=company_cik,
            metrics=metrics,
            debt_ratio=debt_ratio,
            free_cash_flow=fcf,
            net_margin=net_margin,
            revenue=revenue,
            net_income=net_income,
            operating_cash_flow=operating_cash_flow,
            capex=capex,
            total_assets=total_assets,
            total_liabilities=total_liabilities
        )
        
        return [result]

