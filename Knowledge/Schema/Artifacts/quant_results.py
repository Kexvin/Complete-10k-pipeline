from dataclasses import dataclass, field
from typing import List
from Code.Assets.Tools.core.artifact import Artifact
from Code.Agents.tenk_analyst.tenk_analyst.models.quantitative import QuantResult
from .datasources import DataSource


@dataclass
class QuantResultsArtifact(Artifact):
    """Quantitative agent output: financial metrics like debt ratio, FCF, margins."""
    schema_version: str = "1.0.0"

    company_cik: str = ""
    accession: str = ""
    results: List[QuantResult] = field(default_factory=list)
    sources: List[DataSource] = field(default_factory=list)
