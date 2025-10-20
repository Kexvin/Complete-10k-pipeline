from dataclasses import dataclass
from typing import Optional, Literal

SourceType = Literal["SEC_EDGAR_API", "KAGGLE_COMPANY_FACTS"]

@dataclass
class DataSource:
    """Metadata describing a data source used in this pipeline."""
    type: SourceType
    name: str
    url: str
    version: Optional[str] = None
    retrieved_at: Optional[str] = None
    notes: Optional[str] = None


# Convenience constructors

def sec_edgar_api_source(retrieved_at: Optional[str] = None, notes: Optional[str] = None) -> DataSource:
    return DataSource(
        type="SEC_EDGAR_API",
        name="SEC EDGAR API",
        url="https://www.sec.gov/edgar",
        version=None,
        retrieved_at=retrieved_at,
        notes=notes,
    )

def kaggle_company_facts_source(
    version: str = "2023-09",
    retrieved_at: Optional[str] = None,
    notes: Optional[str] = None,
) -> DataSource:
    return DataSource(
        type="KAGGLE_COMPANY_FACTS",
        name="SEC-EDGAR Company Facts (September 2023)",
        url="https://www.kaggle.com/datasets/jamesglang/sec-edgar-company-facts-september2023",
        version=version,
        retrieved_at=retrieved_at,
        notes=notes,
    )
