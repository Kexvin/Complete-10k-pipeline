# Code/Assets/Tools/io/sec_facts_client.py

import os
import time
from typing import Dict, Any, List, Optional

import requests


class SECCompanyFacts:
    """
    Thin client over the SEC companyfacts API.

    - Fetches companyfacts JSON for a CIK
    - Picks the latest 10-K fact for multiple candidate us-gaap concepts
    - Returns a small metrics dict for the quantitative agent
    """

    BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    def __init__(self, user_agent: Optional[str] = None, throttle: float = 0.2) -> None:
        # SEC requires a descriptive User-Agent
        self.user_agent = user_agent or os.getenv(
            "SEC_USER_AGENT",
            "YourName Contact@Email ExampleScript",
        )
        self.throttle = throttle
        self._cache: Dict[str, Dict[str, Any]] = {}

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    def _fetch_companyfacts(self, cik: str) -> Dict[str, Any]:
        """Fetch and cache the companyfacts JSON for a given CIK."""
        cik10 = str(cik).zfill(10)
        if cik10 in self._cache:
            return self._cache[cik10]

        url = self.BASE_URL.format(cik=cik10)
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        self._cache[cik10] = data

        # Gentle throttle to be nice to SEC
        time.sleep(self.throttle)
        return data

    def _pick_latest_fact(
        self,
        facts: Dict[str, Any],
        candidates: List[str],
        preferred_units: List[str] = ("USD",),
        form_filter: str = "10-K",
    ) -> Optional[float]:
        """
        From the us-gaap facts, pick the latest value for any of the candidate concepts.

        - Restricts to given units (default: USD)
        - Restricts to form type (default: 10-K)
        - Chooses the fact with the latest 'end' date
        """
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        best_val: Optional[float] = None
        best_end: Optional[str] = None

        for concept in candidates:
            concept_obj = us_gaap.get(concept)
            if not concept_obj:
                continue

            for unit_name, series in concept_obj.get("units", {}).items():
                if preferred_units and unit_name not in preferred_units:
                    continue

                for inst in series:
                    if form_filter and inst.get("form") != form_filter:
                        continue

                    val = inst.get("val")
                    end = inst.get("end")
                    if not isinstance(val, (int, float)):
                        continue

                    # pick the chronologically latest 'end' date
                    if best_end is None or (end and end > best_end):
                        best_val = float(val)
                        best_end = end

        return best_val

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def get_latest_metrics(self, cik: str) -> Dict[str, Optional[float]]:
        """
        Return a dict of numeric metrics for the most recent 10-K:

        - revenue
        - net_income
        - operating_cash_flow
        - capex
        - total_assets
        - total_liabilities
        """
        facts = self._fetch_companyfacts(cik)

        # Revenue: try multiple common us-gaap concepts
        revenue = self._pick_latest_fact(
            facts,
            [
                "Revenues",
                "SalesRevenueNet",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenuesNetOfInterestExpense",
                "NetSales",
                "SalesRevenueServicesNet",
            ],
        )

        # Net income / profit
        net_income = self._pick_latest_fact(
            facts,
            [
                "NetIncomeLoss",
                "ProfitLoss",
            ],
        )

        # Operating cash flow
        operating_cash_flow = self._pick_latest_fact(
            facts,
            [
                "NetCashProvidedByUsedInOperatingActivities",
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            ],
        )

        # Capex (various purchase-of-PP&E concepts)
        capex = self._pick_latest_fact(
            facts,
            [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "CapitalExpendituresIncurredButNotYetPaid",
                "PaymentsToAcquireBusinessesAndInterestsInAffiliates",
            ],
        )

        # Assets / liabilities
        total_assets = self._pick_latest_fact(
            facts,
            [
                "Assets",
            ],
        )

        total_liabilities = self._pick_latest_fact(
            facts,
            [
                "Liabilities",
                "LiabilitiesCurrentAndNoncurrent",
            ],
        )

        return {
            "revenue": revenue,
            "net_income": net_income,
            "operating_cash_flow": operating_cash_flow,
            "capex": capex,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
        }


# Convenience wrapper used by run_from_sec.py or other callers
def build_financials_from_sec_facts(cik: str, user_agent: str = None) -> dict:
    """
    Helper to fetch the latest financial metrics for a given CIK from SEC companyfacts.

    Returns a dict with:
      - revenue
      - net_income
      - operating_cash_flow
      - capex
      - total_assets
      - total_liabilities
    """
    client = SECCompanyFacts(user_agent=user_agent)
    return client.get_latest_metrics(cik)
