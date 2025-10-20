from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.routed import RoutedChunksArtifact
from Knowledge.Schema.Artifacts.quant_results import QuantResultsArtifact
from Code.Agents.tenk_analyst.tenk_analyst.agents.quantitative import QuantitativeAgent

class QuantStage(Stage[RoutedChunksArtifact, QuantResultsArtifact]):
    def __init__(self, agent: QuantitativeAgent) -> None:
        super().__init__("quantitative", RoutedChunksArtifact, QuantResultsArtifact)
        self.agent = agent

    def run(self, inp: RoutedChunksArtifact, **kwargs):
        z_chunks = [rc.chunk for rc in inp.routed if rc.route == "quantitative"]
        results = self.agent.run(z_chunks, company_cik=inp.company_cik)
        return QuantResultsArtifact(company_cik=inp.company_cik, accession=inp.accession, results=results, sources=inp.sources)
