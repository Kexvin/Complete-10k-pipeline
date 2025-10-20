from __future__ import annotations
from typing import Optional
import re

_number = r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_num_re = re.compile(_number)

def _parse_first_number(text: str) -> Optional[float]:
    m = _num_re.search(text.replace("$", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None

def compute_debt_ratio(text: str,
                       total_liabilities: Optional[float] = None,
                       total_assets: Optional[float] = None) -> Optional[float]:
    """
    Heuristic: if explicit numbers aren't passed, try to parse the first two numbers
    from the text and treat them as liabilities/assets (rough stub for MVP).
    """
    if total_liabilities is not None and total_assets is not None and total_assets != 0:
        return total_liilities / total_assets  # type: ignore[name-defined]
    nums = _num_re.findall(text.replace("$", ""))
    if len(nums) >= 2:
        liab = float(nums[0].replace(",", ""))
        assets = float(nums[1].replace(",", ""))
        return (liab / assets) if assets else None
    return None

def compute_fcf(text: str, operating_cash_flow: Optional[float] = None,
                capex: Optional[float] = None) -> Optional[float]:
    """
    FCF = Operating Cash Flow - CapEx. If not provided, try a crude parse.
    """
    if operating_cash_flow is not None and capex is not None:
        return operating_cash_flow - capex
    nums = _num_re.findall(text.replace("$", ""))
    if len(nums) >= 2:
        ocf = float(nums[0].replace(",", ""))
        capex = float(nums[1].replace(",", ""))
        return ocf - capex
    return None

def compute_margin(text: str, revenue: Optional[float] = None,
                   net_income: Optional[float] = None) -> Optional[float]:
    """
    Net Margin = Net Income / Revenue. If not provided, try crude parse.
    """
    if revenue is not None and net_income is not None and revenue != 0:
        return net_income / revenue
    nums = _num_re.findall(text.replace("$", ""))
    if len(nums) >= 2:
        rev = float(nums[0].replace(",", ""))
        ni = float(nums[1].replace(",", ""))
        return (ni / rev) if rev else None
    return None
