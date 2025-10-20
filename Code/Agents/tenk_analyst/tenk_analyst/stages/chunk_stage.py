from typing import List
from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Knowledge.Schema.Artifacts.chunks import ChunksArtifact
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk
from Code.Assets.Tools.nlp.chunker import simple_paragraph_chunker

class ChunkStage(Stage[RawTextArtifact, ChunksArtifact]):
    def __init__(self) -> None:
        super().__init__("chunk", RawTextArtifact, ChunksArtifact)

    def run(self, inp: RawTextArtifact, **kwargs) -> ChunksArtifact:
        parts: List[Chunk] = simple_paragraph_chunker(inp.company_cik, inp.accession, inp.text)
        return ChunksArtifact(company_cik=inp.company_cik, accession=inp.accession, chunks=parts, sources=inp.sources)
