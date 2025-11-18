from typing import Optional 
from Code.Assets.Tools.core.stage import Stage 
from Code.Assets.Tools.router.routing import route_chunks
from Knowledge.Schema.Artifacts.chunks import ChunksArtifact
from Knowledge.Schema.Artifacts.routed import RoutedChunksArtifact



class RouteStage(Stage[ChunksArtifact, RoutedChunksArtifact]):
    def __init__(self, name: str = "route") -> None:
        super().__init__("route", ChunksArtifact, RoutedChunksArtifact)
        super().__init__(name, ChunksArtifact, RoutedChunksArtifact)

    def run(self, inp: ChunksArtifact, **kwargs) -> RoutedChunksArtifact:
      
        filing_type = getattr(inp, "filing_type", None)
        routed = route_chunks(inp.chunks, filing_type=filing_type)
        return RoutedChunksArtifact(company_cik=inp.company_cik, accession=inp.accession, routed=routed, sources=inp.sources)
