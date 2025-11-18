# Code/Agents/tenk_analyst/tenk_analyst/agents/quantitative.py

from typing import List, Optional

from Code.Assets.Tools.io.sec_facts_client import SECCompanyFacts
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk
from Code.Agents.tenk_analyst.tenk_analyst.models.quantitative import QuantResult


class QuantitativeAgent:
    """
    Extracts quantitative metrics from SEC companyfacts API and computes ratios.

    Inputs:
        - chunks: not used directly here (metrics come from companyfacts)
        - company_cik: used to query SEC companyfacts

    Outputs:
        - a single QuantResult with raw metrics and derived ratios
    """

    def __init__(self, sec_client: Optional[SECCompanyFacts] = None) -> None:
        self.sec_client = sec_client or SECCompanyFacts()

    def run(self, chunks: List[Chunk], company_cik: str = None) -> List[QuantResult]:
        if not company_cik:
            return [
                QuantResult(
                    chunk_id="no_cik",
                    metrics=["Missing CIK; no quantitative metrics extracted."],
                )
            ]

        metrics_data = self.sec_client.get_latest_metrics(company_cik)

        revenue = metrics_data.get("revenue")
        net_income = metrics_data.get("net_income")
        operating_cash_flow = metrics_data.get("operating_cash_flow")
        capex = metrics_data.get("capex")
        total_assets = metrics_data.get("total_assets")
        total_liabilities = metrics_data.get("total_liabilities")

        metrics: List[str] = []

        def fmt_dollars(label: str, value: Optional[float]) -> None:
            if value is not None:
                metrics.append(f"{label}: ${value:,.0f}")
            else:
                metrics.append(f"{label}: N/A")

        # Raw metrics
        fmt_dollars("Revenue", revenue)
        fmt_dollars("Net Income", net_income)
        fmt_dollars("Operating Cash Flow", operating_cash_flow)
        fmt_dollars("Capital Expenditures", capex)
        fmt_dollars("Total Assets", total_assets)
        fmt_dollars("Total Liabilities", total_liabilities)

        # Derived metrics
        debt_ratio: Optional[float] = None
        if total_liabilities is not None and total_assets not in (None, 0):
            debt_ratio = total_liabilities / total_assets
            metrics.append(f"Debt Ratio: {debt_ratio:.2%}")

        free_cash_flow: Optional[float] = None
        if operating_cash_flow is not None and capex is not None:
            free_cash_flow = operating_cash_flow - capex
            metrics.append(f"Free Cash Flow: ${free_cash_flow:,.0f}")

        net_margin: Optional[float] = None
        if revenue not in (None, 0) and net_income is not None:
            net_margin = net_income / revenue
            metrics.append(f"Net Margin: {net_margin:.2%}")

        result = QuantResult(
            chunk_id=company_cik,
            metrics=metrics,
            debt_ratio=debt_ratio,
            free_cash_flow=free_cash_flow,
            net_margin=net_margin,
            revenue=revenue,
            net_income=net_income,
            operating_cash_flow=operating_cash_flow,
            capex=capex,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
        )

        return [result]
