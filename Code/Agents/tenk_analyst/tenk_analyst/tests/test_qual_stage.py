from Code.Agents.tenk_analyst.tenk_analyst.stages.qual_stage import QualStage
from Code.Agents.tenk_analyst.tenk_analyst.agents.qualitative import QualitativeAgent
from Code.Assets.Tools.rag.pinecone_client import RAG
from Code.Assets.Tools.nlp.finbert import FinBert
from Knowledge.Schema.Artifacts.routed import RoutedChunksArtifact
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk, RoutedChunk

def test_qual_stage_runs():
    stage = QualStage(QualitativeAgent(FinBert(), RAG("Knowledge")))
    c = Chunk(id="1", company_cik="1", accession="a", text="Risk mentioned here.")
    routed = RoutedChunksArtifact(company_cik="1", accession="a", routed=[RoutedChunk(chunk=c, route="qualitative")], sources=[])
    art = stage.run(routed)
    assert art.company_cik == "1"
    assert len(art.results) == 1
