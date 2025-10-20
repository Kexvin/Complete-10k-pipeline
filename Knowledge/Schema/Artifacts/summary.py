from dataclasses import dataclass
from typing import Optional, List
from Code.Assets.Tools.core.artifact import Artifact
from Code.Agents.tenk_analyst.tenk_analyst.models.summary import SummaryReport
from .datasources import DataSource

@dataclass
class SummaryArtifact(Artifact):
    """Unified summary combining qualitative and quantitative insights."""
    schema_version: str = "1.0.0"

    company_cik: Optional[str] = None
    accession: Optional[str] = None
    report: SummaryReport = None
    sources: List[DataSource] = None
