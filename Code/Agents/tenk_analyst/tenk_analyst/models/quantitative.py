from pydantic import BaseModel
from typing import List, Optional

class QuantResult(BaseModel):
    chunk_id: str
    metrics: List[str] = []
    debt_ratio: Optional[float] = None
    free_cash_flow: Optional[float] = None
    net_margin: Optional[float] = None
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
