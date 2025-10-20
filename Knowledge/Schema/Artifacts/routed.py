from dataclasses import dataclass
from typing import List
from Code.Assets.Tools.core.artifact import Artifact
from Code.Agents.tenk_analyst.tenk_analyst.models.core import RoutedChunk
from .datasources import DataSource

@dataclass
class RoutedChunksArtifact(Artifact):
    """Controller output — each chunk routed to qualitative or quantitative analysis."""
    schema_version: str = "1.0.0"

    company_cik: str = ""
    accession: str = ""
    routed: List[RoutedChunk] = None
    sources: List[DataSource] = None
