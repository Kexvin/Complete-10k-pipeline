from Code.Assets.Tools.core.stage import Stage
from Knowledge.Schema.Artifacts.routed import RoutedChunksArtifact
from Knowledge.Schema.Artifacts.qual_results import QualResultsArtifact
from Code.Agents.tenk_analyst.tenk_analyst.agents.qualitative import QualitativeAgent

class QualStage(Stage[RoutedChunksArtifact, QualResultsArtifact]):
    def __init__(self, agent: QualitativeAgent) -> None:
        super().__init__("qualitative", RoutedChunksArtifact, QualResultsArtifact)
        self.agent = agent

    def run(self, inp: RoutedChunksArtifact, **kwargs) -> QualResultsArtifact:
        q_chunks = [rc.chunk for rc in inp.routed if rc.route == "qualitative"]
        results = self.agent.run(q_chunks)
        return QualResultsArtifact(company_cik=inp.company_cik, accession=inp.accession, results=results, sources=inp.sources)
