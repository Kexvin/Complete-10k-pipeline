from dataclasses import dataclass
from typing import List
from Code.Assets.Tools.core.artifact import Artifact
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk
from .datasources import DataSource

@dataclass
class ChunksArtifact(Artifact):
    """Result of chunking raw 10-K text into smaller labeled segments."""
    schema_version: str = "1.0.0"

    company_cik: str = ""
    accession: str = ""
    filing_type: str = ""
    chunks: List[Chunk] = None
    sources: List[DataSource] = None
