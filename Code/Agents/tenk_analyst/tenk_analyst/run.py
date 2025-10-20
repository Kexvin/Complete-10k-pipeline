"""
Dev runner for the 10-K pipeline with Kaggle->EDGAR fetch.
Usage:
  python -m Code.Agents.tenk_analyst.run
"""
from Code.Assets.Tools.core.pipeline import Pipeline
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Code.Agents.tenk_analyst.tenk_analyst.stages.fetch_stage import FetchStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.chunk_stage import ChunkStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.route_stage import RouteStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.qual_stage import QualStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.quant_stage import QuantStage
from Code.Agents.tenk_analyst.tenk_analyst.stages.summarize_stage import SummarizeStage
from Code.Agents.tenk_analyst.tenk_analyst.agents.controller import ControllerAgent
from Code.Agents.tenk_analyst.tenk_analyst.agents.qualitative import QualitativeAgent
from Code.Agents.tenk_analyst.tenk_analyst.agents.quantitative import QuantitativeAgent
from Code.Assets.Tools.nlp.finbert import FinBert
from Code.Assets.Tools.rag.pinecone_client import RAG

def main() -> None:
    # Build pipelines
    base = Pipeline([FetchStage(), ChunkStage(), RouteStage(ControllerAgent())])
    qual = Pipeline([QualStage(QualitativeAgent(FinBert(), RAG("Knowledge/pinecone")))])
    quant = Pipeline([QuantStage(QuantitativeAgent())])

    # seed artifact (company info only; no text yet)
    seed = RawTextArtifact(company_cik="", accession="", text="", sources=[])

    # kwargs control the new Kaggle->EDGAR flow
    kwargs = dict(
        ticker="AAPL",                                  # <— change this ticker
        kaggle_csv="Data/Primary/kaggle_facts/company_facts_sample.csv",
        user_agent="Your Name (your.email@example.com)"
    )

    routed = base.run(seed, **kwargs)
    qual_art = qual.run(routed)
    quant_art = quant.run(routed)
    final = SummarizeStage().run((qual_art, quant_art))

    print(final.to_dict())

if __name__ == "__main__":
    main()
