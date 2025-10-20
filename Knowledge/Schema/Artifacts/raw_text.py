from dataclasses import dataclass
from typing import Optional, List
from Code.Assets.Tools.core.artifact import Artifact
from .datasources import DataSource

@dataclass
class RawTextArtifact(Artifact):
    """Raw 10-K report text as fetched from SEC EDGAR."""
    schema_version: str = "1.0.0"

    company_cik: str = ""
    accession: str = ""
    filing_period: Optional[str] = None
    text: str = ""
    sources: List[DataSource] = None
