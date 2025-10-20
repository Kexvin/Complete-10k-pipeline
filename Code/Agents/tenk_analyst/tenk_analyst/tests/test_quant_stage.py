from Code.Agents.tenk_analyst.tenk_analyst.stages.quant_stage import QuantStage
from Code.Agents.tenk_analyst.tenk_analyst.agents.quantitative import QuantitativeAgent
from Knowledge.Schema.Artifacts.routed import RoutedChunksArtifact
from Code.Agents.tenk_analyst.tenk_analyst.models.core import Chunk, RoutedChunk

def test_quant_stage_runs():
    stage = QuantStage(QuantitativeAgent())
    c = Chunk(id="1", company_cik="1", accession="a", text="Consolidated revenue ...")
    routed = RoutedChunksArtifact(company_cik="1", accession="a", routed=[RoutedChunk(chunk=c, route="quantitative")], sources=[])
    art = stage.run(routed)
    assert art.company_cik == "1"
    assert len(art.results) == 1
