from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.chunks import ChunksArtifact
from Knowledge.Schema.Artifacts.routed import RoutedChunksArtifact
from Code.Agents.tenk_analyst.tenk_analyst.agents.controller import ControllerAgent

class RouteStage(Stage[ChunksArtifact, RoutedChunksArtifact]):
    def __init__(self, controller: ControllerAgent) -> None:
        super().__init__("route", ChunksArtifact, RoutedChunksArtifact)
        self.controller = controller

    def run(self, inp: ChunksArtifact, **kwargs) -> RoutedChunksArtifact:
        # Allow routing to consider filing metadata (e.g., filing_type)
        filing_type = getattr(inp, "filing_type", None)
        routed = self.controller.route(inp.chunks, filing_type=filing_type)
        return RoutedChunksArtifact(company_cik=inp.company_cik, accession=inp.accession, routed=routed, sources=inp.sources)
