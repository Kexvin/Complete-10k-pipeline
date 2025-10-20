"""
Dev runner for the 10-K pipeline with Kaggle->EDGAR fetch.
Usage:
  python -m Code.Agents.tenk_analyst.run
"""
import os
import argparse
from Code.Assets.Tools.core.pipeline import Pipeline
from Knowledge.Schema.Artifacts.raw_text import RawTextArtifact
from Code.Agents.tenk_analyst.tenk_analyst.stages.identify_stage import IdentifyStage
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


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="tenk-run", description="Run 10-K pipeline: identify->fetch->chunk->route->analyze")
    p.add_argument("--ticker", help="Ticker symbol to fetch (e.g. AAPL)")
    p.add_argument("--kaggle-csv", help="Path to Kaggle company facts CSV to map ticker->CIK")
    p.add_argument("--user-agent", help="User-Agent string for SEC EDGAR requests (default: SEC_USER_AGENT env var)")
    p.add_argument("--rag-index", action="store_true", help="Index chunks into Pinecone after chunking")
    p.add_argument("--rag-collection", default="knowledgepinecone", help="Pinecone collection name to use when indexing chunks")
    p.add_argument("--pinecone-collection", default="knowledgepinecone", help="Pinecone collection name for qualitative pipeline RAG client")
    args = p.parse_args(argv)

    # Build pipelines
    base = Pipeline([IdentifyStage(), FetchStage(), ChunkStage(), RouteStage(ControllerAgent())])
    rag_client = RAG(collection=args.pinecone_collection)
    qual = Pipeline([QualStage(QualitativeAgent(FinBert(), rag_client))])
    quant = Pipeline([QuantStage(QuantitativeAgent())])

    # seed artifact (company info only; no text yet)
    seed = RawTextArtifact(company_cik="", accession="", text="", sources=[])

    # Get user agent from args or environment
    user_agent = args.user_agent or os.getenv("SEC_USER_AGENT")
    if not user_agent:
        raise ValueError("User agent must be provided via --user-agent or SEC_USER_AGENT env var")

    kwargs = dict(
        ticker=args.ticker,
        kaggle_csv=args.kaggle_csv,
        user_agent=user_agent,
        rag_index=args.rag_index,
        rag_collection=args.rag_collection,
    )

    # Run base pipeline
    routed = base.run(seed, **kwargs)

    # Run analysis pipelines (qualitative and quantitative)
    qual_art = qual.run(routed)
    quant_art = quant.run(routed)
    final = SummarizeStage().run((qual_art, quant_art))

    print(final.to_dict())


if __name__ == "__main__":
    main()
